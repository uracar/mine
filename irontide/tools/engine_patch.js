// Engine side of the Blender remaster: a small synchronous inflate and the decoder for 'mesh' parts.
// Inserted into the game script just before forgeMesh(); forgeMesh/forgeVehicle get a few small hooks (see apply_patch.js).
// v7.0 Blender meshes: each remastered model carries one deflated blob; its 'mesh' parts point into it.
function fgInflate(src,outLen){                        // raw deflate (RFC 1951), enough for our own blobs
 const out=new Uint8Array(outLen);let op=0,bp=0,bb=0,bn=0;
 const bits=n=>{while(bn<n){bb|=src[bp++]<<bn;bn+=8;}const v=bb&((1<<n)-1);bb>>>=n;bn-=n;return v;};
 const build=(lens,n)=>{const cnt=new Uint16Array(16),offs=new Uint16Array(16),sym=new Uint16Array(n);for(let i=0;i<n;i++)cnt[lens[i]]++;cnt[0]=0;
  for(let i=1;i<16;i++)offs[i]=offs[i-1]+cnt[i-1];for(let i=0;i<n;i++)if(lens[i])sym[offs[lens[i]]++]=i;return {cnt,sym};};
 const dec=h=>{let code=0,first=0,idx=0;for(let l=1;l<16;l++){code|=bits(1);const c=h.cnt[l];if(code-c<first)return h.sym[idx+(code-first)];idx+=c;first+=c;first<<=1;code<<=1;}return -1;};
 const LB=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258],LE=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0];
 const DB=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577],DE=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13];
 let fixL=null,fixD=null,last=0;
 while(!last){last=bits(1);const t=bits(2);
  if(t===0){bb=0;bn=0;const len=src[bp]|src[bp+1]<<8;bp+=4;out.set(src.subarray(bp,bp+len),op);op+=len;bp+=len;continue;}
  let hl,hd;
  if(t===1){if(!fixL){const l=new Uint8Array(288);l.fill(8,0,144);l.fill(9,144,256);l.fill(7,256,280);l.fill(8,280,288);fixL=build(l,288);fixD=build(new Uint8Array(30).fill(5),30);}hl=fixL;hd=fixD;}
  else{const nl=bits(5)+257,nd=bits(5)+1,nc=bits(4)+4,ord=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15],cl=new Uint8Array(19);
   for(let i=0;i<nc;i++)cl[ord[i]]=bits(3);const hc=build(cl,19),ls=new Uint8Array(nl+nd);
   for(let i=0;i<nl+nd;){const s=dec(hc);if(s<16)ls[i++]=s;else if(s===16){const p=ls[i-1];for(let r=3+bits(2);r--;)ls[i++]=p;}else if(s===17){i+=3+bits(3);}else{i+=11+bits(7);}}
   hl=build(ls.subarray(0,nl),nl);hd=build(ls.subarray(nl),nd);}
  for(;;){const s=dec(hl);if(s<256){out[op++]=s;continue;}if(s===256)break;
   const li=s-257,len=LB[li]+bits(LE[li]),ds=dec(hd),dist=DB[ds]+bits(DE[ds]);for(let k=0;k<len;k++,op++)out[op]=out[op-dist];}
 }
 return out;
}
const fgBlobs=new WeakMap();
function fgBlob(model){let b=fgBlobs.get(model);if(!b){const s=atob(model.blob),z=new Uint8Array(s.length);for(let i=0;i<s.length;i++)z[i]=s.charCodeAt(i);b=fgInflate(z,model.blobN);fgBlobs.set(model,b);}return b;}
// one Blender mesh part: positions, hardened normals and the baked shade (light, wear, grime) per corner
function fgMeshPart(model,p){
 const B=fgBlob(model),nv=p.nv,nt=p.nt,[x0,y0,z0,sx,sy,sz]=p.box;let o=p.at;
 const P=new Float32Array(nv*3),N=new Float32Array(nv*3),S=new Float32Array(nv);
 {const n=nv*3;let a=0,b=0,c=0;for(let i=0;i<nv;i++){for(let k=0;k<3;k++){const j=i*3+k,z=B[o+j]|B[o+n+j]<<8,d=(z&1)?-((z+1)>>1):z>>1;if(k===0)a=(a+d)&65535;else if(k===1)b=(b+d)&65535;else c=(c+d)&65535;}
   P[i*3]=x0+a/65535*sx;P[i*3+1]=y0+b/65535*sy;P[i*3+2]=z0+c/65535*sz;}o+=n*2;}
 for(let i=0;i<nv;i++){let x=((B[o+i]<<24)>>24)/127,y=((B[o+nv+i]<<24)>>24)/127,z=1-Math.abs(x)-Math.abs(y);
  if(z<0){const tx=x;x=(1-Math.abs(y))*(tx>=0?1:-1);y=(1-Math.abs(tx))*(y>=0?1:-1);}const l=Math.hypot(x,y,z)||1;N[i*3]=x/l;N[i*3+1]=y/l;N[i*3+2]=z/l;}
 o+=nv*2;for(let i=0;i<nv;i++)S[i]=B[o+i]/255*1.7;o+=nv;
 const I=new Uint32Array(nt*3),n3=nt*3;let hw=0;for(let i=0;i<n3;i++){const v=hw-(B[o+i]|B[o+n3+i]<<8);I[i]=v;if(v===hw)hw++;}
 return {P,N,S,I};
}
