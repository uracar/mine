// Iron Tide test harness: one CLI for every browser check (headless Chromium + swiftshader).
// Serve the game first:  cd iron-tide && python3 -m http.server 8765 &
// Usage (from iron-tide/):
//   node tools/test/it.js nodes                  build every vehicle in every tree (TT1+TT2): failures, tris, part counts, Forge model used
//   node tools/test/it.js nodes file:///abs/dist/iron-tide-vX.Y.html   same against the single-file build
//   node tools/test/it.js shot OUT ID [views]    close views of a vehicle; views = JSON [[distK,pitch,yawOffset],...] (distK x length)
//   node tools/test/it.js fire ID AIM [ID AIM]   aim AIM rad off the bow at the horizon, report turrets/barrels/flashes and shells fired
//   node tools/test/it.js drive ID               hold W 4 s: do wheels / track runs move, speed
//   node tools/test/it.js water OUT [hash]       four sea views (near, mid, high, shore)
//   node tools/test/it.js forest OUT [hash]      four views at a forest edge (hash '#play&q=2&still&t=0.95' = night)
//   node tools/test/it.js gallery OUT ID...      one framed view per vehicle, contact sheet
// Screens are stacked into one PNG with Pillow (python3). Use Read on the PNG to look at it.
const {chromium}=require('playwright');const {execSync}=require('child_process');const path=require('path');
const BASE=process.env.ITURL||'http://localhost:8765/';
const ARGS=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'];
const stack=(out,files,cols=1)=>execSync(`python3 -c "import sys;from PIL import Image;f=sys.argv[3:];c=int(sys.argv[2]);ims=[Image.open(x) for x in f];w,h=ims[0].size;r=(len(ims)+c-1)//c;o=Image.new('RGB',(w*c,h*r));[o.paste(im,((i%c)*w,(i//c)*h)) for i,im in enumerate(ims)];o.save(sys.argv[1])" ${out} ${cols} ${files.join(' ')}`);
async function open(hash,w=800,h=450){
 const b=await chromium.launch({args:ARGS}),p=await b.newPage({viewport:{width:w,height:h}}),errs=[];
 p.on('pageerror',e=>errs.push(e.message));
 const url=/^(file|https?):/.test(hash||'')?hash:BASE+(hash||'#play&q=1&still');
 await p.goto(url);await p.waitForFunction(()=>window.__ready===true,null,{timeout:300000,polling:1000});
 await p.addStyleTag({content:'#ui,#map,#hud,#gsight{display:none!important}'});
 return {b,p,errs};
}
// put the player in a vehicle and on fitting ground (deep water for ships, flat land for the rest)
const place=(p,id)=>p.evaluate(id=>{const D=window.__dev;D.setVehicle(D.nodeSpec(id));const W=window.__world,T=W.__T,pl=W.player,ship=D.VS.type==='ship';
 for(let r=200;r<9000;r+=200)for(let a=0;a<6.28;a+=.25){const x=pl.x+Math.cos(a)*r,z=pl.z+Math.sin(a)*r,h=T.height(x,z);let flat=true;
  if(!ship)for(const [dx,dz] of [[25,0],[-25,0],[0,25],[0,-25]])if(Math.abs(T.height(x+dx,z+dz)-h)>2.5)flat=false;
  if(ship?h<-40:(h>4&&h<50&&flat)){pl.x=x;pl.z=z;if(!ship)pl.y=h;return D.VS.type+' '+Math.round(D.VS.length)+'m';}}return 'no spot';},id);
const view=(p,d,pi,y,abs)=>p.evaluate(([d,pi,y,abs])=>{const W=window.__world,o=W.orbit,pl=W.player,V=window.__dev.VS;o.zt=null;o.dist=abs?d:V.length*d+4;o.pitch=pi;o.yaw=pl.hd+y;o.idle=-1e9;},[d,pi,y,abs]);
const wait=(p,ms)=>p.waitForTimeout(ms);
const cmds={
 async nodes(url){const {b,p,errs}=await open(url||'#play&q=1&still',480,270);
  const r=await p.evaluate(()=>window.__dev.allNodes());for(const x of r)if(x[4]||x[5])console.log(x.join(' '));
  console.log('total',r.length,'failed',r.filter(x=>x[4]).length,'errors',errs);await b.close();},
 async shot(out,id,vj){const {b,p,errs}=await open('#play&q=2&still&t=0.4');console.log(await place(p,id));await wait(p,5000);const fs=[];
  for(const [i,[d,pi,y]] of JSON.parse(vj||'[[1.4,0.3,0.9],[1.2,0.2,-2.3]]').entries()){await view(p,d,pi,y);await wait(p,4500);const f=`${out}_${i}.png`;await p.screenshot({path:f});fs.push(f);}
  console.log('parts',JSON.stringify(await p.evaluate(()=>window.__dev.parts())),'errors',errs);stack(out+'.png',fs);await b.close();},
 async fire(...a){const {b,p,errs}=await open();
  for(let i=0;i<a.length;i+=2){const id=a[i],aim=+a[i+1];console.log(id,await place(p,id));
   await p.evaluate(y=>{const o=window.__world.orbit,pl=window.__world.player;o.pitch=.02;o.yaw=pl.hd-Math.PI/2+y;o.idle=-1e9;},aim);await wait(p,9000);
   console.log(' aim',aim,'->',await p.evaluate(()=>{const D=window.__dev,o=[];D.pp().forEach(d=>{
    if(d.kind==='turret')o.push(`T ang ${d.ang.toFixed(2)} rest ${d.rest.toFixed(2)}`);
    if(d.kind==='barrel')o.push(`B el ${d.el.toFixed(3)} want ${(d.want||0).toFixed(3)}`);
    if(d.kind==='flash'){const G=D.gs(d),f=D.ff(d);o.push(`F${d.noShot?'(missile)':''}${d.med?'(coax)':''} onTarget ${G.onTarget} shells+${f[1]-f[0]}`);}});return o.join(' | ');}));}
  console.log('errors',errs);await b.close();},
 async drive(id){const {b,p,errs}=await open();console.log(await place(p,id));await wait(p,3000);
  const st=()=>p.evaluate(()=>{const P=window.__parts();return P.defs.map((d,i)=>[d.kind,P.A[(i+1)*4+3]||0,P.C[(i+1)*4]||0]);});
  const a0=await st();await p.keyboard.down('KeyW');await wait(p,4000);const a1=await st();await p.keyboard.up('KeyW');
  const mv=k=>a1.filter((q,i)=>q[0]===k&&(q[1]!==a0[i][1]||q[2]!==a0[i][2])).length+'/'+a1.filter(q=>q[0]===k).length;
  console.log('speed',(await p.evaluate(()=>window.__world.player.v)).toFixed(1),'wheels',mv('wheel'),'treads',mv('tread'),'props',mv('prop'),'errors',errs);await b.close();},
 async water(out,hash){const {b,p,errs}=await open(hash||'#play&q=2&still&t=0.38');
  await p.evaluate(()=>{const D=window.__dev;D.setVehicle(D.nodeSpec('S1'));const W=window.__world,T=W.__T,pl=W.player;
   for(let r=300;r<9000;r+=150)for(let a=0;a<6.28;a+=.2){const x=pl.x+Math.cos(a)*r,z=pl.z+Math.sin(a)*r;if(T.height(x,z)<-30)for(let q=0;q<6.28;q+=.4)if(T.height(x+Math.cos(q)*700,z+Math.sin(q)*700)>2){pl.x=x;pl.z=z;pl.hd=-q;return;}}});
  await wait(p,5000);const fs=[];for(const [i,[d,pi,y]] of [[60,.06,2.4],[160,.16,1.2],[600,.35,.3],[220,.1,-1.6]].entries()){await view(p,d,pi,y,1);await wait(p,4000);const f=`${out}_${i}.png`;await p.screenshot({path:f});fs.push(f);}
  console.log('errors',errs);stack(out+'.png',fs);await b.close();},
 async forest(out,hash){const {b,p,errs}=await open(hash||'#play&q=2&still&t=0.4');
  console.log('spot',await p.evaluate(()=>{const D=window.__dev;D.setVehicle(D.nodeSpec('L1'));const W=window.__world,T=W.__T,pl=W.player;
   for(let r=300;r<12000;r+=150)for(let a=0;a<6.28;a+=.15){const x=pl.x+Math.cos(a)*r,z=pl.z+Math.sin(a)*r,h=T.height(x,z);if(h<6||h>200||D.forestAt(x,z)>=.02)continue;
    for(let q=0;q<6.28;q+=.3){const fx=x+Math.cos(q)*250,fz=z+Math.sin(q)*250;if(D.forestAt(fx,fz)>.5&&T.height(fx,fz)>6){pl.x=x;pl.z=z;pl.y=h;pl.hd=-q;return [x|0,z|0];}}}return null;}));
  await wait(p,8000);const fs=[];for(const [i,[d,pi,y]] of [[30,.05,Math.PI/2],[120,.12,Math.PI/2],[500,.2,Math.PI/2],[60,.35,Math.PI/2+.8]].entries()){await view(p,d,pi,y,1);await wait(p,5000);const f=`${out}_${i}.png`;await p.screenshot({path:f});fs.push(f);}
  console.log('errors',errs);stack(out+'.png',fs);await b.close();},
 async gallery(out,...ids){const {b,p,errs}=await open('#play&q=1&still&t=0.36',640,360);const fs=[];
  for(const id of ids){console.log(id,await place(p,id));await wait(p,6000);await view(p,.8,.22,1.1);await wait(p,4000);const f=`${out}_${id}.png`;await p.screenshot({path:f});fs.push(f);}
  console.log('errors',errs);stack(out+'.png',fs,3);await b.close();},
};
const [cmd,...rest]=process.argv.slice(2);
if(!cmds[cmd]){console.log(require('fs').readFileSync(__filename,'utf8').split('\n').slice(0,14).join('\n'));process.exit(1);}
cmds[cmd](...rest).catch(e=>{console.error(e.message);process.exit(1);});
