// Pure terrain code. No DOM, no libraries: the same text runs in Node (tests), in the page, and in the workers.
// World units are metres. x east, z south, y up. Sea level is y = 0.
function makeTerrain(seed){
 seed=seed|0;
 const hash=(ix,iy)=>{let h=(Math.imul(ix,374761393)^Math.imul(iy,668265263)^seed)|0;h=Math.imul(h^(h>>>13),1274126177);h^=h>>>16;return h;};
 const GX=[1,-1,0,0,.7071,-.7071,.7071,-.7071],GY=[0,0,1,-1,.7071,.7071,-.7071,-.7071];
 const fade=t=>t*t*t*(t*(t*6-15)+10);
 // gradient noise, roughly -1..1
 function noise(x,y){
  const xi=Math.floor(x),yi=Math.floor(y),xf=x-xi,yf=y-yi,u=fade(xf),v=fade(yf);
  const h00=hash(xi,yi)&7,h10=hash(xi+1,yi)&7,h01=hash(xi,yi+1)&7,h11=hash(xi+1,yi+1)&7;
  const a=GX[h00]*xf+GY[h00]*yf,b=GX[h10]*(xf-1)+GY[h10]*yf,c=GX[h01]*xf+GY[h01]*(yf-1),d=GX[h11]*(xf-1)+GY[h11]*(yf-1);
  const ab=a+(b-a)*u,cd=c+(d-c)*u;return (ab+(cd-ab)*v)*1.41;
 }
 // fractal sum; each octave is rotated a little so the grid never shows
 function fbm(x,y,oct,gain){
  let s=0,a=1,n=0;gain=gain||.5;
  for(let i=0;i<oct;i++){s+=a*noise(x,y);n+=a;a*=gain;const nx=x*1.94+y*.34+17.3,ny=y*1.94-x*.34-9.1;x=nx;y=ny;}
  return s/n;
 }
 // ridged noise: sharp crests, 0..1
 function ridge(x,y,oct){
  let s=0,a=1,n=0,w=1;
  for(let i=0;i<oct;i++){let r=1-Math.abs(noise(x,y));r*=r;r*=w;w=Math.min(1,Math.max(0,r*1.6));s+=a*r;n+=a;a*=.5;const nx=x*2.03+y*.41+5.2,ny=y*2.03-x*.41+3.7;x=nx;y=ny;}
  return s/n;
 }
 const sstep=(a,b,x)=>{const t=Math.min(1,Math.max(0,(x-a)/(b-a)));return t*t*(3-2*t);};
 const mix=(a,b,t)=>a+(b-a)*t;
 // "g" is the land field: above 0 is land, below is sea. Everything else is derived from it.
 const CONT=42000,SEA_T=.04,IS=13500,GK=2.3;   // IS: island wavelength, GK: keeps coast slopes the same on the bigger islands
 function landField(x,z){
  const wx=x+2600*noise(x/7300+3.1,z/7300-8.7)+700*noise(x/1900-1.3,z/1900+4.2);
  const wz=z+2600*noise(x/7300-6.4,z/7300+2.9)+700*noise(x/1900+7.7,z/1900-2.2);
  const c=fbm(wx/CONT+.37,wz/CONT-.81,4,.5);                  // continents: tens of km wide
  const e=fbm(wx/IS+9.5,wz/IS+1.5,3,.5);                  // smaller islands scattered between
  return Math.max(c-SEA_T,(e-.34)*1.25-.02);
 }
 // height in metres at (x,z)
 function height0(x,z){
  const g=landField(x,z)*GK;
  if(g<=0){                                                      // sea floor: shelf, slope, abyss
   const s=-g;
   return -(2.5*sstep(0,.004,s)+s*220+Math.pow(s,1.6)*3200)+fbm(x/260,z/260,2,.5)*4*sstep(0,.05,s);
  }
   const cliff=sstep(.15,.55,fbm(x/2400+4,z/2400-7,2,.5)*.5+.5);      // some coasts are sheer, most are beach
  const beach=Math.min(1,g/mix(.020,.0045,cliff));                // ramps from the waterline
  let h=beach*beach*(3-2*beach)*(2.2+3*cliff)+g*mix(150,420,cliff)*sstep(.005,.05,g);
  // inland: rolling hills, big ranges, plateaus
  const inl=sstep(.03,.22,g);
  const hills=fbm(x/3200+2,z/3200-3,4,.5)*.5+.5;
  const rng=sstep(.30,.55,fbm(x/12000-5,z/12000+6,3,.5)*.5+.5);            // where the mountain ranges are
  const ridgeH=ridge(x/5200+8,z/5200-4,5);
  h+=inl*(hills*130+rng*sstep(.06,.4,g)*(ridgeH*1700));
  h+=inl*fbm(x/260+1,z/260-1,4,.5)*26*(.4+hills);                // gullies and bumps
  h+=fbm(x/55,z/55,3,.5)*2.4*sstep(0,.03,g);                       // fine ground roughness
  return h;
 }

 // ---------------- harbours ----------------
 // The world is cut into cells; a cell may hold one port. A port is a rectangle of flat quay land, a dredged basin in front of it,
 // a deep channel out to sea and two breakwaters. Everything is computed from (u,v): u runs from the quay out to sea, v runs along the quay.
 const PC=8000,PR=1250,QH=3.2;
 const portCache=new Map(),nearCache=new Map();
 function rnd(a,b,c){let h=(Math.imul(a,374761393)^Math.imul(b,668265263)^Math.imul(c,1274126177)^seed)|0;h=Math.imul(h^(h>>>13),1274126177);h^=h>>>16;return (h>>>0)/4294967296;}
 function findPort(ci,cj){
  if(rnd(ci,cj,1)>.62)return null;
  for(let t=0;t<70;t++){
   const px=(ci+rnd(ci,cj,10+t*3))*PC,pz=(cj+rnd(ci,cj,11+t*3))*PC;
   if(height0(px,pz)<8)continue;
   const a=rnd(ci,cj,12+t*3)*6.2832,dx=Math.cos(a),dz=Math.sin(a);
   let d=40,found=-1;
   for(;d<4200;d+=40){if(height0(px+dx*d,pz+dz*d)<0){found=d;break;}}
   if(found<0)continue;
   let lo=found-40,hi=found;
   for(let k=0;k<9;k++){const m=(lo+hi)/2;if(height0(px+dx*m,pz+dz*m)<0)hi=m;else lo=m;}
   const sx=px+dx*hi,sz=pz+dz*hi,ux=dx,uz=dz,vx=-dz,vz=dx;
   const H=(u,v)=>height0(sx+ux*u+vx*v,sz+uz*u+vz*v);
   let ok=true,mn=1e9,mx=-1e9;
   for(const u of [-380,-300,-220,-140,-60]){for(const v of [-260,-130,0,130,260]){const h=H(u,v);if(h<.8||h>75){ok=false;break;}mn=Math.min(mn,h);mx=Math.max(mx,h);}if(!ok)break;}
   if(!ok||mx-mn>60)continue;
   for(const u of [120,300,500,800,1100]){if(H(u,0)>-3){ok=false;break;}}
   if(!ok||H(1100,0)>-12)continue;
   for(const v of [-250,250]){if(H(260,v)>3||H(400,v)>3){ok=false;break;}}
   if(!ok)continue;
   return {x:sx,z:sz,ux,uz,vx,vz,id:ci+'_'+cj,k:rnd(ci,cj,99)};
  }
  return null;
 }
 function portOf(ci,cj){const k=ci+','+cj;let p=portCache.get(k);if(p===undefined){p=findPort(ci,cj);portCache.set(k,p);}return p;}
 // the ports that can touch a given cell
 function nearOf(ci,cj){
  const k=ci+','+cj;let l=nearCache.get(k);
  if(l===undefined){l=[];for(let j=cj-1;j<=cj+1;j++)for(let i=ci-1;i<=ci+1;i++){const p=portOf(i,j);if(p)l.push(p);}nearCache.set(k,l);}
  return l;
 }
 let lastKey=-1e9,lastList=[];
 function portsAt(x,z){
  const ci=Math.floor(x/PC),cj=Math.floor(z/PC),k=ci*100003+cj;
  if(k!==lastKey){lastKey=k;lastList=nearOf(ci,cj);}
  return lastList;
 }
 function dseg(px,py,ax,ay,bx,by){const dx=bx-ax,dy=by-ay;let t=((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy);t=t<0?0:t>1?1:t;const qx=ax+dx*t-px,qy=ay+dy*t-py;return Math.sqrt(qx*qx+qy*qy);}

 // ---------------- the road network between bases ----------------
 // Every base is linked to its two nearest neighbours (within 32 km) by a road found with A* over the terrain:
 // it keeps to dry land, avoids steep ground and prefers to stay low. Roads are polylines kept in 500 m buckets.
 const RB=500,LINKR=32000,ROAD_STEP=40;
 const routeCache=new Map(),bucket=new Map(),neighCache=new Map(),cellDone=new Set();
 function gateOf(p){return {x:p.x-p.ux*352,z:p.z-p.uz*352};}
 function neighbours(p){
  let l=neighCache.get(p.id);
  if(l)return l;
  const ci=Math.floor(p.x/PC),cj=Math.floor(p.z/PC),c=[];
  for(let j=cj-4;j<=cj+4;j++)for(let i=ci-4;i<=ci+4;i++){const q=portOf(i,j);if(q&&q!==p){const d=Math.hypot(q.x-p.x,q.z-p.z);if(d<LINKR)c.push([d,q]);}}
  c.sort((a,b)=>a[0]-b[0]);
  l=c.slice(0,2).map(e=>e[1]);neighCache.set(p.id,l);return l;          // v3.7 two nearest (was three): fewer, more purposeful roads
 }
 function lonelyPort(p){return neighbours(p).length===0;}
 function distSeg(px,pz,ax,az,bx,bz){const dx=bx-ax,dz=bz-az,t=Math.max(0,Math.min(1,((px-ax)*dx+(pz-az)*dz)/(dx*dx+dz*dz+1e-9)));return Math.hypot(ax+dx*t-px,az+dz*t-pz);}
 function addSeg(ax,az,bx,bz,bk,ri,k){
  bk=bk||bucket;
  const i0=Math.floor(Math.min(ax,bx)/RB-.25),i1=Math.floor(Math.max(ax,bx)/RB+.25),j0=Math.floor(Math.min(az,bz)/RB-.25),j1=Math.floor(Math.max(az,bz)/RB+.25);
  for(let j=j0;j<=j1;j++)for(let i=i0;i<=i1;i++){const kk=i*100003+j;let l=bk.get(kk);if(!l){l=[];bk.set(kk,l);}l.push(ax,az,bx,bz,ri,k);}
 }
 // ---- v2.1 graded roads: every route gets a smoothed height profile, so it runs on a level bed - cut through high ground and built up
 // over dips - instead of riding every bump. Where two roads cross, one is lifted onto an overpass (no two roads meet at grade). ----
 const routeList=[],routeIdx=new Map();
 function regRoute(id,pts,bk){
  if(routeIdx.has(id))return routeIdx.get(id);
  const n=pts.length,raw=new Float32Array(n);for(let i=0;i<n;i++)raw[i]=Math.max(2.6,heightNR(pts[i][0],pts[i][1]));
  // distance along, then a distance-weighted moving average (~700 m wide, three passes), the ends held to the real ground
  const dist=new Float32Array(n);for(let i=1;i<n;i++)dist[i]=dist[i-1]+Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);
  let a=Float32Array.from(raw);
  for(let pass=0;pass<3;pass++){const b=new Float32Array(n);let lo=0,hi=0,sum=0;
   for(let i=0;i<n;i++){while(hi<n&&dist[hi]-dist[i]<=85){sum+=a[hi];hi++;}while(dist[i]-dist[lo]>85){sum-=a[lo];lo++;}b[i]=sum/(hi-lo);}a=b;}
  const prof=new Float32Array(n);
  for(let i=0;i<n;i++){const e=Math.min(1,Math.min(dist[i],dist[n-1]-dist[i])/260),k=e*e*(3-2*e);prof[i]=Math.max(2.6,raw[i]*(1-k)+a[i]*k);}
  const ri=routeList.length;routeList.push({id,pts,prof,dist,town:id[0]==='T'});routeIdx.set(id,ri);
  for(let k=0;k<n-1;k++)addSeg(pts[k][0],pts[k][1],pts[k+1][0],pts[k+1][1],bk,ri,k);
  // a new road changes which segments are dropped and where overpasses go in every cell it passes: forget those answers
  for(let k=0;k<n;k++){const ci=Math.floor(pts[k][0]/RB),cj=Math.floor(pts[k][1]/RB);for(let a=-1;a<=1;a++)for(let b=-1;b<=1;b++){const kk=(ci+a)*100003+(cj+b);supCache.delete(kk);crossCache.delete(kk);}}
  return ri;
 }
 // crossings, per 500 m bucket cell, worked out once every road that can pass through the cell exists
 const crossCache=new Map(),gradeCells=new Set();
 function ensureNear(x,z){
  const ci=Math.floor(x/PC),cj=Math.floor(z/PC),key=ci+','+cj;
  if(gradeCells.has(key))return;gradeCells.add(key);
  ensureRoads(ci,cj);ensureTownRoads(ci,cj);                          // the same roads the asphalt tint (roadPave) sees
 }
 function segList(i,j){const k=i*100003+j,a=bucket.get(k),b=bucketT.get(k);return a&&b?a.concat(b):a||b||null;}
 function crossingsIn(i,j){
  const key=i*100003+j;let c=crossCache.get(key);if(c)return c;
  ensureNear((i+.5)*RB,(j+.5)*RB);
  c=[];const l=segList(i,j);
  if(l)for(let p=0;p<l.length;p+=6)for(let q=p+6;q<l.length;q+=6){
   const ra=l[p+4],rb=l[q+4];if(ra===rb||isSup(ra,l[p+5])||isSup(rb,l[q+5]))continue;
   const ax=l[p],az=l[p+1],bx=l[p+2],bz=l[p+3],cx=l[q],cz=l[q+1],dx=l[q+2],dz=l[q+3];
   const den=(bx-ax)*(dz-cz)-(bz-az)*(dx-cx);if(Math.abs(den)<1e-6)continue;
   const t=((cx-ax)*(dz-cz)-(cz-az)*(dx-cx))/den,u=((cx-ax)*(bz-az)-(cz-az)*(bx-ax))/den;
   if(t<0||t>1||u<0||u>1)continue;
   const X=ax+(bx-ax)*t,Z=az+(bz-az)*t;if(Math.floor(X/RB)!==i||Math.floor(Z/RB)!==j)continue;
   const A=routeList[ra],B=routeList[rb],ka=l[p+5],kb=l[q+5];
   const da=A.dist[ka]+(A.dist[ka+1]-A.dist[ka])*t,db=B.dist[kb]+(B.dist[kb+1]-B.dist[kb])*u;
   if(da<90||da>A.dist[A.dist.length-1]-90||db<90||db>B.dist[B.dist.length-1]-90)continue;   // roads that meet at a gate or a town edge join there

   const upA=A.town!==B.town?A.town:A.id>B.id;                                                   // town roads go over the main roads
   const hA=A.prof[ka]+(A.prof[ka+1]-A.prof[ka])*t,hB=B.prof[kb]+(B.prof[kb+1]-B.prof[kb])*u;
   const up=upA?ra:rb,hUp=upA?hA:hB,hLo=upA?hB:hA,lx=upA?dx-cx:bx-ax,lz=upA?dz-cz:bz-az,ll=Math.hypot(lx,lz)||1;
   if(c.some(o=>Math.hypot(o.x-X,o.z-Z)<60))continue;
   c.push({x:X,z:Z,up,lo:upA?rb:ra,need:Math.max(0,hLo+10-hUp),deck:Math.max(hUp,hLo+10),lx:lx/ll,lz:lz/ll});
  }
  crossCache.set(key,c);return c;
 }
 // v2.5 no two roads run on top of each other: a segment of a lesser road (town < main; then by id) that lies within 26 m of a greater
 // road is dropped (not drawn, not graded, not crossing-tested) - the lesser road joins the greater one where they meet
 const supCache=new Map();
 const rank=ri=>{const r=routeList[ri];return (r.town?0:2)+0;};
 const greater=(a,b)=>{const ra=rank(a),rb=rank(b);return ra!==rb?ra>rb:routeList[a].id<routeList[b].id;};
 function supIn(i,j){
  const key=i*100003+j;let set=supCache.get(key);if(set)return set;
  ensureNear((i+.5)*RB,(j+.5)*RB);set=new Set();const l=segList(i,j);
  if(l)for(let p=0;p<l.length;p+=6){const ra=l[p+4],mx=(l[p]+l[p+2])/2,mz=(l[p+1]+l[p+3])/2;if(Math.floor(mx/RB)!==i||Math.floor(mz/RB)!==j)continue;
   for(let q=0;q<l.length;q+=6){const rb=l[q+4];if(rb===ra||!greater(rb,ra))continue;
    if(distSeg(mx,mz,l[q],l[q+1],l[q+2],l[q+3])<26){set.add(ra*1e6+l[p+5]);break;}}}
  supCache.set(key,set);return set;
 }
 function isSup(ri,k){const r=routeList[ri],a=r.pts[k],b=r.pts[Math.min(k+1,r.pts.length-1)],mx=(a[0]+b[0])/2,mz=(a[1]+b[1])/2;return supIn(Math.floor(mx/RB),Math.floor(mz/RB)).has(ri*1e6+k);}
 function routeSup(id,i){const ri=routeIdx.get(id);if(ri===undefined)return false;const r=routeList[ri];return (i<r.pts.length-1&&isSup(ri,i))||(i>0&&isSup(ri,i-1));}
 // how far route ri is lifted at (x,z), and whether (x,z) is over the open span of a bridge
 const SPAN=34,RAMP=230;
 function liftAt(ri,x,z,out){
  let lift=0,span=false;const i0=Math.floor((x-RAMP)/RB),i1=Math.floor((x+RAMP)/RB),j0=Math.floor((z-RAMP)/RB),j1=Math.floor((z+RAMP)/RB);
  for(let j=j0;j<=j1;j++)for(let i=i0;i<=i1;i++){const c=crossingsIn(i,j);for(let n=0;n<c.length;n++){const o=c[n];if(o.up!==ri||o.need<=0)continue;
   const d=Math.hypot(o.x-x,o.z-z);if(d>=RAMP)continue;
   const e=d<SPAN+12?1:1-sstep(SPAN+12,RAMP,d);if(o.need*e>lift)lift=o.need*e;
   if(d<SPAN&&Math.abs((x-o.x)*o.lz-(z-o.z)*o.lx)<SPAN*.9)span=true;}}
  if(out){out.span=span;}
  return lift;
 }
 const _lo={span:false};
 // road surface height of route ri at point index k plus fraction t (with any overpass lift)
 function roadHAt(ri,k,t,x,z,out){const r=routeList[ri],p=r.prof;return p[k]+(p[Math.min(k+1,p.length-1)]-p[k])*t+liftAt(ri,x,z,out);}
 // the graded ground: blend toward the road bed within its shoulders. Cuts get ~50 degree walls, fills gentler banks
 function gradeAt(x,z,h){
  ensureNear(x,z);
  const l=segList(Math.floor(x/RB),Math.floor(z/RB));if(!l)return h;
  let bestW=0,bestH=h;
  for(let p=0;p<l.length;p+=6){
   const ax=l[p],az=l[p+1],bx=l[p+2],bz=l[p+3],ex=bx-ax,ez=bz-az,L2=ex*ex+ez*ez+1e-9;
   const t=Math.max(0,Math.min(1,((x-ax)*ex+(z-az)*ez)/L2)),qx=ax+ex*t-x,qz=az+ez*t-z,d=Math.sqrt(qx*qx+qz*qz);
   if(d>130||isSup(l[p+4],l[p+5]))continue;
   const rh=roadHAt(l[p+4],l[p+5],t,ax+ex*t,az+ez*t,_lo);
   if(_lo.span)continue;                                           // the open span of an overpass: the ground below is left alone
   const dh=h-rh,outer=Math.min(170,10+Math.abs(dh)*(dh>0?2.1:2.7)),w=1-sstep(8.4,outer,d);   // v4.6 gentler cuttings and embankments
   if(w>bestW){bestW=w;bestH=rh;}
  }
  return bestW>0?h+(bestH-h)*bestW:h;
 }
 function roadDist(x,z){
  ensureNear(x,z);const l=segList(Math.floor(x/RB),Math.floor(z/RB));if(!l)return 1e9;
  let d=1e9;for(let p=0;p<l.length;p+=6){const e=distSeg(x,z,l[p],l[p+1],l[p+2],l[p+3]);if(e<d)d=e;}return d;
 }
 // for the renderer: the surface height of route id at its point i, and the overpass (if any) there
 function routeHeight(id,i){const ri=routeIdx.get(id);if(ri===undefined)return null;const r=routeList[ri];return roadHAt(ri,Math.min(i,r.prof.length-1),0,r.pts[i][0],r.pts[i][1],null);}
 function routeSpan(id,i){const ri=routeIdx.get(id);if(ri===undefined)return false;const r=routeList[ri],o={span:false};liftAt(ri,r.pts[i][0],r.pts[i][1],o);return o.span;}
 // the deck a vehicle at (x,z,y) stands on, if it is up on an overpass (else null)
 function deckAt(x,z,y){
  const l=segList(Math.floor(x/RB),Math.floor(z/RB));if(!l)return null;
  for(let p=0;p<l.length;p+=6){const ax=l[p],az=l[p+1],bx=l[p+2],bz=l[p+3],ex=bx-ax,ez=bz-az,L2=ex*ex+ez*ez+1e-9;
   const t=Math.max(0,Math.min(1,((x-ax)*ex+(z-az)*ez)/L2)),d=Math.hypot(ax+ex*t-x,az+ez*t-z);if(d>8.5)continue;
   const o={span:false},rh=roadHAt(l[p+4],l[p+5],t,ax+ex*t,az+ez*t,o);if(o.span&&y>rh-4)return rh;}
  return null;
 }
 const bucketT=new Map(),townDone=new Set();                   // roads out to the towns live in their own buckets (see townAt)
 function route(a,b,avoid){
  const AV=avoid||[],inAv=(x,z)=>{for(const t of AV){const dx=x-t.x,dz=z-t.z;if(dx*dx+dz*dz<(t.R+60)*(t.R+60))return true;}return false;};   // v3.7 other towns: go round
  const S=240,A=a,B=b,L=Math.hypot(B.x-A.x,B.z-A.z),ex=(B.x-A.x)/L,ez=(B.z-A.z)/L,W=6000;
  const minx=Math.min(A.x,B.x)-W,minz=Math.min(A.z,B.z)-W;
  const nx=Math.ceil((Math.abs(B.x-A.x)+2*W)/S)+1,nz=Math.ceil((Math.abs(B.z-A.z)+2*W)/S)+1;
  const Hh=new Float32Array(nx*nz).fill(NaN);
  const hAt=(i,j)=>{const k=j*nx+i;let v=Hh[k];if(v!==v){v=height0(minx+i*S,minz+j*S);Hh[k]=v;}return v;};
  const inCorr=(i,j)=>{const x=minx+i*S-A.x,z=minz+j*S-A.z,al=x*ex+z*ez,cr=Math.abs(x*ez-z*ex);return cr<W&&al>-W&&al<L+W;};
  const si=Math.round((A.x-minx)/S),sj=Math.round((A.z-minz)/S),gi=Math.round((B.x-minx)/S),gj=Math.round((B.z-minz)/S);
  const N=nx*nz,g=new Float32Array(N).fill(1e30),par=new Int32Array(N).fill(-1),closed=new Uint8Array(N);
  // binary heap of node indices keyed by f
  const heap=[],fk=new Float32Array(N);
  const push=(n,f)=>{fk[n]=f;heap.push(n);let i=heap.length-1;while(i>0){const p=(i-1)>>1;if(fk[heap[p]]<=fk[heap[i]])break;const t=heap[p];heap[p]=heap[i];heap[i]=t;i=p;}};
  const pop=()=>{const top=heap[0],last=heap.pop();if(heap.length){heap[0]=last;let i=0;for(;;){let l=i*2+1,r=l+1,m=i;if(l<heap.length&&fk[heap[l]]<fk[heap[m]])m=l;if(r<heap.length&&fk[heap[r]]<fk[heap[m]])m=r;if(m===i)break;const t=heap[m];heap[m]=heap[i];heap[i]=t;i=m;}}return top;};
  const sIdx=sj*nx+si,gIdx=gj*nx+gi;
  g[sIdx]=0;push(sIdx,Math.hypot((gi-si)*S,(gj-sj)*S));
  let found=false,guard=0;
  while(heap.length&&guard++<400000){
   const n=pop();if(closed[n])continue;closed[n]=1;
   if(n===gIdx){found=true;break;}
   const ci=n%nx,cj=(n/nx)|0,h0=hAt(ci,cj);
   for(let dj=-1;dj<=1;dj++)for(let di=-1;di<=1;di++){
    if(!di&&!dj)continue;
    const ni=ci+di,nj=cj+dj;if(ni<0||nj<0||ni>=nx||nj>=nz)continue;
    const m=nj*nx+ni;if(closed[m])continue;
    const goal=m===gIdx;
    if(!goal&&!inCorr(ni,nj))continue;
    const h1=hAt(ni,nj);
    if(!goal&&h1<2.2)continue;
    if(!goal&&AV.length&&inAv(minx+ni*S,minz+nj*S))continue;
    const d=Math.hypot(di,dj)*S,sl=Math.abs(h1-h0)/d;
    if(sl>.62)continue;
    // climbing is dear, high ground dearer - but graded roads (v2.1) cut through ridges, so less so than before
    const c=d*(1+5*sl*sl+2.5*sl)*(1+.25*Math.max(0,(h1-300)/600));
    const ng=g[n]+c;
    if(ng<g[m]){g[m]=ng;par[m]=n;push(m,ng+Math.hypot((gi-ni)*S,(gj-nj)*S));}
   }
  }
  if(!found)return null;
  let pts=[];for(let n=gIdx;n>=0;n=par[n])pts.push([minx+(n%nx)*S,minz+((n/nx)|0)*S]);
  pts.reverse();pts[0]=[A.x,A.z];pts[pts.length-1]=[B.x,B.z];
  // v2.5 smooth roads: pull the grid path tight (skip ahead while the straight line stays on dry, passable ground), round the corners,
  // then resample at an even ROAD_STEP so the ribbon and the graded bed have no kinks
  const clearLine=(a,b)=>{const L=Math.hypot(b[0]-a[0],b[1]-a[1]),n=Math.max(1,Math.ceil(L/80)),st=L/n;let ph=height0(a[0],a[1]);
   for(let k=1;k<=n;k++){const t=k/n,x=a[0]+(b[0]-a[0])*t,z=a[1]+(b[1]-a[1])*t,h=height0(x,z);if(h<2.2||Math.abs(h-ph)/st>.55||(AV.length&&inAv(x,z)))return false;ph=h;}return true;};
  {const out=[pts[0]];let i=0;while(i<pts.length-1){let j=i+1;while(j+1<pts.length&&j-i<5&&clearLine(pts[i],pts[j+1]))j++;out.push(pts[j]);i=j;}pts=out;}
  // v4.6 roads wander like real country roads: a gentle sideways weave (fading out at the ends), kept only on dry, passable ground
  {const sd=Math.sin(A.x*.0123+A.z*.0371+B.x*.0057)*1e4,ph=sd-Math.floor(sd),tot=pts.reduce((s,p,i)=>i?s+Math.hypot(p[0]-pts[i-1][0],p[1]-pts[i-1][1]):0,0);let acc=0;
   for(let i=1;i<pts.length-1;i++){acc+=Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);const a=pts[i-1],b=pts[i+1],tx=b[0]-a[0],tz=b[1]-a[1],l=Math.hypot(tx,tz)||1,taper=Math.min(1,acc/500,(tot-acc)/500);
    const off=taper*(42*Math.sin(ph*6.28+acc/560)+18*Math.sin(ph*17+acc/230)),x=pts[i][0]-tz/l*off,z=pts[i][1]+tx/l*off;if(height0(x,z)>=2.4&&!(AV.length&&inAv(x,z)))pts[i]=[x,z];}}
  for(let it=0;it<4;it++){const q=[pts[0]];for(let i=0;i<pts.length-1;i++){const p0=pts[i],p1=pts[i+1];q.push([p0[0]*.75+p1[0]*.25,p0[1]*.75+p1[1]*.25],[p0[0]*.25+p1[0]*.75,p0[1]*.25+p1[1]*.75]);}q.push(pts[pts.length-1]);pts=q;}
  {const out=[pts[0]];let carry=0;for(let i=0;i<pts.length-1;i++){const a=pts[i],b=pts[i+1],L=Math.hypot(b[0]-a[0],b[1]-a[1]);let d=ROAD_STEP-carry;
    while(d<L){out.push([a[0]+(b[0]-a[0])*d/L,a[1]+(b[1]-a[1])*d/L]);d+=ROAD_STEP;}carry=L-(d-ROAD_STEP);}
   const last=pts[pts.length-1],pl=out[out.length-1];if(Math.hypot(last[0]-pl[0],last[1]-pl[1])<ROAD_STEP*.4)out[out.length-1]=last;else out.push(last);pts=out;}
  return pts;
 }
 function ensureRoads(cx,cz){   // cx,cz: 8 km cell
  const key=cx+','+cz;if(cellDone.has(key))return;cellDone.add(key);
  const mx=(cx+.5)*PC,mz=(cz+.5)*PC;
  for(let j=cz-5;j<=cz+5;j++)for(let i=cx-5;i<=cx+5;i++){
   const p=portOf(i,j);if(!p)continue;
   for(const q of neighbours(p)){
    const pk=p.id<q.id?p.id+'|'+q.id:q.id+'|'+p.id;
    if(routeCache.has(pk))continue;
    const a=p.id<q.id?gateOf(p):gateOf(q),b=p.id<q.id?gateOf(q):gateOf(p);
    if(distSeg(mx,mz,a.x,a.z,b.x,b.z)>6000+PC*.71)continue;
    const r=route(a,b);routeCache.set(pk,r||false);
    if(r)regRoute(pk,r,bucket);
   }
  }
 }
 let rKey=-1e9,rKeyT=-1e9;
 function bucketPave(bk,x,z,raw){
  const l=bk.get(Math.floor(x/RB)*100003+Math.floor(z/RB));
  if(!l)return 0;
  let d=1e9;
  for(let i=0;i<l.length;i+=6){const e=distSeg(x,z,l[i],l[i+1],l[i+2],l[i+3]);if(e<d&&(raw||((e>7||!liftAt(l[i+4],x,z,_lo)||!_lo.span)&&!isSup(l[i+4],l[i+5]))))d=e;}   // no asphalt painted under an overpass span
  return d<7?.26*(1-sstep(4.5,6.8,d)):0;   // v4.9 dirt roads
 }
 // the roads between bases only (towns are placed clear of these, before their own roads exist)
 function baseRoadPave(x,z){
  const ci=Math.floor(x/PC),cj=Math.floor(z/PC),k=ci*100003+cj;
  if(k!==rKey){ensureRoads(ci,cj);rKey=k;}
  return bucketPave(bucket,x,z,true);                      // raw: town placement must not depend on suppression or overpasses
 }
 function roadPave(x,z){
  const b=baseRoadPave(x,z);if(b>=.45)return b;
  const ci=Math.floor(x/PC),cj=Math.floor(z/PC),k=ci*100003+cj;
  if(k!==rKeyT){ensureTownRoads(ci,cj);rKeyT=k;}
  return Math.max(b,bucketPave(bucketT,x,z));
 }
 // ---- towns: one candidate per 1.7 km cell on level, dry ground clear of harbours and base roads (the main script builds them) ----
 const TOWN_CELL=1700,townCache=new Map();
 function hsh(a,b,s){let x=Math.imul(a|0,374761393)^Math.imul(b|0,668265263)^Math.imul(s|0,1274126177);x=Math.imul(x^(x>>>13),1274126177);return((x^(x>>>16))>>>0)/4294967296;}
 function basePave(x,z){
  const L=portsAt(x,z);let r=0;
  for(let i=0;i<L.length;i++){const p=L[i],dx=x-p.x,dz=z-p.z;if(dx*dx+dz*dz>11000000)continue;
   portShape(dx*p.ux+dz*p.uz,dx*p.vx+dz*p.vz,0,_o,p.k,lonelyPort(p));if(_o.pave>r)r=_o.pave;}
  if(r<.5){const q=baseRoadPave(x,z);if(q>r)r=q;}
  return r;
 }
 function townAt(ci,cj){
  const key=ci+','+cj;let t=townCache.get(key);if(t!==undefined)return t;
  t=null;
  if(hsh(ci,cj,901)<.55){
   const big=hsh(ci,cj,905)<.34,R=big?240:130;
   for(let a=0;a<6&&!t;a++){                                              // up to six trial sites per cell
    const x=(ci+.18+.64*hsh(ci,cj,902+a*10))*TOWN_CELL,z=(cj+.18+.64*hsh(ci,cj,903+a*10))*TOWN_CELL;
    const h0=heightNR(x,z);let ok=h0>6&&h0<170;
    for(let k=0;ok&&k<12;k++){                                           // level, dry, clear of roads and harbours
     const an=k*.5236,r=R*(k&1?.5:.95),sx=x+Math.cos(an)*r,sz=z+Math.sin(an)*r,h=heightNR(sx,sz);
     if(h<3.5||Math.abs(h-h0)>26||portW(sx,sz)>.01||basePave(sx,sz)>.04)ok=false;
    }
    if(ok&&portsIn(x-1200,z-1200,x+1200,z+1200).length)ok=false;
    if(ok)t={x,z,R,big,ci,cj,yaw:hsh(ci,cj,904)*1.5708,id:'t'+ci+'_'+cj};
   }
  }
  townCache.set(key,t);return t;
 }
 // ---- town roads: every town is joined to the nearest base it can reach over land (A* fails across the sea, so roads never leave
 // their island), and to its nearest neighbouring town, so each island's bases and towns form one network ----
 function townEdge(t,tx,tz){const d=Math.hypot(tx-t.x,tz-t.z)||1;return {x:t.x+(tx-t.x)/d*(t.R+28),z:t.z+(tz-t.z)/d*(t.R+28)};}
 function linkTown(t){
  if(townDone.has(t.id))return;townDone.add(t.id);
  const ports=[];for(let j=Math.floor(t.z/PC)-2;j<=Math.floor(t.z/PC)+2;j++)for(let i=Math.floor(t.x/PC)-2;i<=Math.floor(t.x/PC)+2;i++){const p=portOf(i,j);if(p){const g=gateOf(p),d=Math.hypot(g.x-t.x,g.z-t.z);if(d<15000)ports.push([d,g,p]);}}
  ports.sort((a,b)=>a[0]-b[0]);
  const others=[];for(let j=t.cj-9;j<=t.cj+9;j++)for(let i=t.ci-9;i<=t.ci+9;i++){if(i===t.ci&&j===t.cj)continue;const o=townAt(i,j);if(o)others.push(o);}
  let linked=false;
  for(const [d,g,p] of ports.slice(0,3)){
   const pk='T'+t.id+'|'+p.id;if(routeCache.has(pk)){if(routeCache.get(pk)){linked=true;break;}continue;}
   const a=townEdge(t,g.x,g.z),r=heightNR(a.x,a.z)>2.2?route(a,g,others):null;routeCache.set(pk,r||false);
   if(r){regRoute(pk,r,bucketT);linked=true;break;}
  }
  if(linked)return;                     // v3.7 a town on the base network needs no second road out
  // and the nearest other town within 9 km (once per pair)
  let best=null,bd=9000;
  for(let j=t.cj-5;j<=t.cj+5;j++)for(let i=t.ci-5;i<=t.ci+5;i++){if(i===t.ci&&j===t.cj)continue;const o=townAt(i,j);if(!o)continue;const d=Math.hypot(o.x-t.x,o.z-t.z);if(d<bd){bd=d;best=o;}}
  if(best){
   const pk=t.id<best.id?'T'+t.id+'|'+best.id:'T'+best.id+'|'+t.id;
   if(!routeCache.has(pk)){const A=t.id<best.id?t:best,B=t.id<best.id?best:t,a=townEdge(A,B.x,B.z),b=townEdge(B,A.x,A.z);
    const r=heightNR(a.x,a.z)>2.2&&heightNR(b.x,b.z)>2.2?route(a,b,others.filter(o=>o!==best)):null;routeCache.set(pk,r||false);
    if(r)regRoute(pk,r,bucketT);}
  }
 }
 const townRoadCells=new Set();
 function ensureTownRoads(cx,cz){        // cx,cz: 8 km cell; links every town within reach of it
  const key=cx+','+cz;if(townRoadCells.has(key))return;townRoadCells.add(key);
  const x0=(cx-1)*PC,x1=(cx+2)*PC,z0=(cz-1)*PC,z1=(cz+2)*PC;
  for(let j=Math.floor(z0/TOWN_CELL);j<=Math.floor(z1/TOWN_CELL);j++)for(let i=Math.floor(x0/TOWN_CELL);i<=Math.floor(x1/TOWN_CELL);i++){const t=townAt(i,j);if(t)linkTown(t);}
 }
 function routesNear(x,z,R){
  // make sure every road within R of (x,z) exists, then list all finished roads: [{id, pts:[[x,z],...]}]
  for(let j=Math.floor((z-R)/PC);j<=Math.floor((z+R)/PC);j++)for(let i=Math.floor((x-R)/PC);i<=Math.floor((x+R)/PC);i++){ensureRoads(i,j);ensureTownRoads(i,j);}
  return [...routeCache.entries()].filter(e=>e[1]).map(([id,pts])=>({id,pts}));
 }
 // returns height, and fills out.pave
 function portShape(u,v,h,out,k,lonely){
  const av=Math.abs(v);
  const dv=Math.max(0,av-260),di=Math.max(0,-380-u);
  const dB=Math.sqrt(dv*dv+di*di);
  const wL=(1-sstep(0,170,dB))*(1-sstep(2,6,u));
  h=h+(QH-h)*wL;
  const wB=sstep(2,12,u)*(1-sstep(430,520,u))*(1-sstep(215,265,av));
  if(wB>0)h=h+(Math.min(h,-10)-h)*wB;
  const wC=sstep(400,470,u)*(1-sstep(1000,1100,u))*(1-sstep(60,120,av));
  if(wC>0)h=h+(Math.min(h,-9)-h)*wC;
  let pave=0;
  for(let sgn=-1;sgn<=1;sgn+=2){
   const d=dseg(u,v,-12,sgn*262,430,sgn*125);
   const wW=1-sstep(10,34,d);
   if(wW>0){h=h+(Math.max(h,4.2)-h)*wW;pave=Math.max(pave,.15*(1-sstep(14,34,d)));}
  }
  // concrete yard, asphalt road inland
  const yard=(1-sstep(0,4,Math.max(-340-u,u-12,av-215)));
  if(yard>0)pave=Math.max(pave,.7+.3*yard);
  // the main road wanders inland from the gate, with a branch that peels off sideways
  if(lonely&&u<-340&&u>-3600){
   const t=-u-340,amp=(200+260*k)*sstep(0,500,t),per=1100+900*k;
   const vc=amp*Math.sin(t/per+k*6),vc2=amp*Math.sin((t+1)/per+k*6);
   const dd=Math.abs(v-vc)/Math.sqrt(1+(vc2-vc)*(vc2-vc));
   let r=1-sstep(5,7.5,dd);
   if(t>1300){const tb=t-1300,sg=k<.5?.55:-.55,dB=Math.abs(v-(amp*Math.sin(1300/per+k*6)+tb*sg))*.87;if(tb<1500)r=Math.max(r,1-sstep(4,6.5,dB));}
   if(r>0&&pave<.5)pave=Math.max(pave,.45*r);
  }
  if(out)out.pave=pave;
  return h;
 }
 const _o={pave:0};
 function heightNR(x,z){                     // natural ground with harbours, before roads are graded into it
  let h=height0(x,z);
  const L=portsAt(x,z);
  for(let i=0;i<L.length;i++){
   const p=L[i],dx=x-p.x,dz=z-p.z;
   if(dx*dx+dz*dz>1600000)continue;
   h=portShape(dx*p.ux+dz*p.uz,dx*p.vx+dz*p.vz,h,null,p.k,lonelyPort(p));
  }
  return h;
 }
 function height(x,z){
  let h=heightNR(x,z);
  if(h>-6)h=gradeAt(x,z,h);
  if(editN>0&&editOn)h+=editDelta(x,z,h);
  return h;
 }
 // ---- edits: what players do to the ground (craters and scorching) lives in 64 m tiles of 1 m samples, laid over the generated terrain ----
 // Tiles exist only where something happened. height() adds the edit; the chunk streamer patches the textures it has already built.
 const ET=64,EK=100003,etH=new Map(),etS=new Map();
 let editN=0,editOn=true,editVer=0;
 const eKey=(ix,iz)=>(ix>>6)*EK+(iz>>6);
 function eAt(ix,iz){const t=etH.get(eKey(ix,iz));return t?t[((iz&63)<<6)|(ix&63)]:0;}
 function editRaw(x,z){
  const fx=Math.floor(x),fz=Math.floor(z);
  let a,b,c,d;
  if((fx&63)<63&&(fz&63)<63){const t=etH.get(eKey(fx,fz));if(!t)return 0;const k=((fz&63)<<6)|(fx&63);a=t[k];b=t[k+1];c=t[k+64];d=t[k+65];}
  else{a=eAt(fx,fz);b=eAt(fx+1,fz);c=eAt(fx,fz+1);d=eAt(fx+1,fz+1);}
  const u=x-fx,v=z-fz;
  return (a*(1-u)+b*u)*(1-v)+(c*(1-u)+d*u)*v;
 }
 // the change to a ground height of h at (x,z): nothing is dug below sea level and nothing is piled up under water
 function editDelta(x,z,h){
  if(h<0)return 0;
  const d=editRaw(x,z);if(d===0)return 0;
  const h2=Math.max(h+d,Math.min(h,.25));
  return h2-h;
 }
 function tileOf(map,ix,iz,Cls){const k=eKey(ix,iz);let t=map.get(k);if(!t){t=new Cls(ET*ET);map.set(k,t);editN=etH.size+etS.size;}return t;}
 // dig a bowl of radius R and the given depth with a raised rim, adding to what is there. Returns the rectangle touched.
 function carve(x,z,R,depth){
  const reach=R*1.7,x0=Math.floor(x-reach),x1=Math.ceil(x+reach),z0=Math.floor(z-reach),z1=Math.ceil(z+reach);
  for(let iz=z0;iz<=z1;iz++)for(let ix=x0;ix<=x1;ix++){
   const r=Math.hypot(ix-x,iz-z),t=r/R;if(t>1.7)continue;
   const bowl=t<1?(1-t*t)*(1-t*t):0,rim=.24*Math.exp(-((t-1.12)/.24)*((t-1.12)/.24));
   const dh=-depth*bowl+depth*rim;if(Math.abs(dh)<.004)continue;
   const T_=tileOf(etH,ix,iz,Float32Array),k=((iz&63)<<6)|(ix&63);
   T_[k]=Math.max(-14,Math.min(6,T_[k]+dh));
  }
  editVer++;return {x0,z0,x1,z1};
 }
 // v4.9 one 3.2 m slab of a great trench, laid across (nx,nz) (+ is toward the enemy). Depths are taken as the deepest of what is
 // there, so slabs overlap cleanly; the berms are only raised on ground nobody has dug. mode 1 raises the floor instead (ramps, tank pits).
 // P: D floor depth, fi half-width of the floor, fs fire-step depth (enemy side), fw fire-step width, rw rear wall width, bh/bw berm, ph/pw parados
 function trench(x,z,nx,nz,P,mode){
  const ex=-nz,ez=nx,half=P.fi+.8+P.fw+1.2,reach=half+Math.max(P.bw||0,P.pw||0)+2,len=1.7;
  const x0=Math.floor(x-reach-len),x1=Math.ceil(x+reach+len),z0=Math.floor(z-reach-len),z1=Math.ceil(z+reach+len);
  for(let iz=z0;iz<=z1;iz++)for(let ix=x0;ix<=x1;ix++){
   const dx=ix-x,dz=iz-z,u=dx*ex+dz*ez;if(u>len||u<-len)continue;const v=dx*nx+dz*nz;
   let g=-1,b=0;
   if(v>=-P.fi&&v<=P.fi)g=P.D;
   else if(v>P.fi&&v<=P.fi+.8)g=P.D+(P.fs-P.D)*(v-P.fi)/.8;
   else if(v>P.fi+.8&&v<=P.fi+.8+P.fw)g=P.fs;
   else if(v>P.fi+.8+P.fw&&v<half)g=P.fs*(half-v)/1.2;
   else if(v<-P.fi&&v>-P.fi-P.rw)g=P.D*(1-(-v-P.fi)/P.rw);
   else if(v>=half&&v<half+(P.bw||0))b=(P.bh||0)*Math.sin(Math.PI*(v-half)/P.bw);
   else if(v<=-P.fi-P.rw&&v>-P.fi-P.rw-(P.pw||0))b=(P.ph||0)*Math.sin(Math.PI*(-v-P.fi-P.rw)/P.pw);
   if(g<0&&b<=0)continue;
   const T_=tileOf(etH,ix,iz,Float32Array),k=((iz&63)<<6)|(ix&63);
   if(mode===1){if(g>=0&&T_[k]<-g)T_[k]=-g;}
   else if(g>=0)T_[k]=Math.max(-14,Math.min(T_[k],-g));
   else if(T_[k]>=-.01)T_[k]=Math.min(6,Math.max(T_[k],b));
  }
  editVer++;return {x0,z0,x1,z1};
 }
 // scorching rides along as 0..255 per sample (a blackened, churned look in the terrain shader)
 function scorch(x,z,R,amount){
  const reach=R*1.15,x0=Math.floor(x-reach),x1=Math.ceil(x+reach),z0=Math.floor(z-reach),z1=Math.ceil(z+reach);
  for(let iz=z0;iz<=z1;iz++)for(let ix=x0;ix<=x1;ix++){
   const t=Math.hypot(ix-x,iz-z)/R;if(t>1.1)continue;
   const w=amount*(1-Math.min(1,t*t*.8))*(1-.12*((ix*7+iz*13)%5)/4);if(w<.02)continue;
   const T_=tileOf(etS,ix,iz,Uint8Array),k=((iz&63)<<6)|(ix&63),v=Math.min(255,Math.max(T_[k],Math.round(w*255)));
   T_[k]=v;
  }
  editVer++;return {x0,z0,x1,z1};
 }
 function scorchAt(x,z){
  const fx=Math.floor(x),fz=Math.floor(z),t=etS.get(eKey(fx,fz));
  return t?t[((fz&63)<<6)|(fx&63)]/255:0;
 }
 // does any edit tile overlap this rectangle? (a newly built chunk uses it to decide whether it needs patching)
 function editTouches(x0,z0,x1,z1){
  if(editN===0)return false;
  for(let tz=Math.floor(z0/ET);tz<=Math.floor(z1/ET);tz++)for(let tx=Math.floor(x0/ET);tx<=Math.floor(x1/ET);tx++){const k=tx*EK+tz;if(etH.has(k)||etS.has(k))return true;}
  return false;
 }
 const edit={carve,trench,scorch,scorchAt,editDelta,editRaw,editTouches,get version(){return editVer;},get tiles(){return etH.size+etS.size;},get on(){return editOn;},set on(v){editOn=!!v;},
  reset(){etH.clear();etS.clear();editN=0;editVer++;},
  dump(){const o=[];for(const [k,t] of etH)o.push(['h',k,Array.from(t)]);for(const [k,t] of etS)o.push(['s',k,Array.from(t)]);return o;}};
 // 0 = untouched, 1 = flat harbour ground (used to keep trees away)
 function portW(x,z){
  const L=portsAt(x,z);let w=0;
  for(let i=0;i<L.length;i++){const p=L[i],dx=x-p.x,dz=z-p.z;if(dx*dx+dz*dz>1600000)continue;
   const u=dx*p.ux+dz*p.uz,v=dx*p.vx+dz*p.vz;
   const dv=Math.max(0,Math.abs(v)-260),di=Math.max(0,-380-u);
   w=Math.max(w,(1-sstep(0,170,Math.sqrt(dv*dv+di*di)))*(1-sstep(2,6,u)));}
  return w;
 }
 // pavement class for the shader: 0 none, ~.15 breakwater rock, ~.45 asphalt, ~1 concrete
 function pave(x,z){
  const L=portsAt(x,z);let r=0;
  for(let i=0;i<L.length;i++){const p=L[i],dx=x-p.x,dz=z-p.z;if(dx*dx+dz*dz>11000000)continue;
   portShape(dx*p.ux+dz*p.uz,dx*p.vx+dz*p.vz,0,_o,p.k,lonelyPort(p));if(_o.pave>r)r=_o.pave;}
  if(r<.5){const q=roadPave(x,z);if(q>r)r=q;}
  return r;
 }
 function portsIn(x0,z0,x1,z1){
  const out=[];
  for(let j=Math.floor(z0/PC);j<=Math.floor(z1/PC);j++)for(let i=Math.floor(x0/PC);i<=Math.floor(x1/PC);i++){const p=portOf(i,j);if(p)out.push(p);}
  return out;
 }
 // 0..1 "how wet and lush" for plant cover and shading
 function moisture(x,z){return Math.min(1,Math.max(0,fbm(x/3800+20,z/3800-13,3,.5)*.9+.5+.55*fbm(x/650+3,z/650-9,2,.5)));}   // big wet and dry regions, with groves inside them
 return {noise,fbm,ridge,height,height0,heightNR,landField,moisture,sstep,pave,portW,portsIn,portShape,roadsNear:routesNear,gateOf,edit,townAt,TOWN_CELL,roadDist,routeHeight,routeSpan,routeSup,deckAt,crossingsNear:(x,z,R)=>{const o=[];for(let j=Math.floor((z-R)/RB);j<=Math.floor((z+R)/RB);j++)for(let i=Math.floor((x-R)/RB);i<=Math.floor((x+R)/RB);i++)for(const c of crossingsIn(i,j))o.push({...c,upId:routeList[c.up].id,loId:routeList[c.lo].id});return o;}};
}
if(typeof module!=='undefined')module.exports={makeTerrain};

