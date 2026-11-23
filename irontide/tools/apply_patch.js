// Builds the remastered game: original HTML + Blender models (blender/out/*.json) + the engine hooks for 'mesh' parts.
// node tools/apply_patch.js original.html out.html
const fs=require('fs'),path=require('path');
const [src,dst]=process.argv.slice(2);
let L=fs.readFileSync(src,'utf8').split('\n');
const idx=re=>{const i=L.findIndex(l=>re.test(l));if(i<0)throw new Error('not found: '+re);return i;};
const rep=(re,from,to)=>{const i=idx(re);if(!L[i].includes(from))throw new Error('no "'+from+'" on line '+(i+1));L[i]=L[i].split(from).join(to);};
// 1. the models
const fi=idx(/^const FORGE_MODELS=/);
const FM=JSON.parse(L[fi].replace(/^const FORGE_MODELS=/,'').replace(/;\s*$/,''));
const outDir=path.join(__dirname,'..','blender','out');let n=0;
for(const f of fs.readdirSync(outDir))if(f.endsWith('.json')){const k=f.slice(0,-5);if(!FM[k])continue;FM[k]=JSON.parse(fs.readFileSync(path.join(outDir,f),'utf8'));n++;}
L[fi]='const FORGE_MODELS='+JSON.stringify(FM)+';';
// 2. decoder, before forgeMesh
const ei=idx(/^function fgColour\(/);
L.splice(ei,0,fs.readFileSync(path.join(__dirname,'engine_patch.js'),'utf8').trimEnd(),
 'const fgNamed=m=>m.logic?m.parts.filter(p=>p.shape!==\'mesh\').concat(m.logic):m.parts;   // v7.0 the parts forgeMesh reads by name, for a Blender model too');
// 3. hooks
rep(/^ let ref=\.42;\{const n=new Map\(\);for\(const p of model\.parts\)/,'for(const p of model.parts)if(p.material===\'paint\'){n.set(p.color,(n.get(p.color)||0)+1);}let bc=null,bn=0;',
 'for(const p of model.parts)if(p.material===\'paint\'){n.set(p.color,(n.get(p.color)||0)+1);}let bc=model.ref||null,bn=model.ref?1e9:0;');
rep(/^ const partsOf=new Map\(\);for\(const p of model\.parts\)/,'for(const p of model.parts)','for(const p of fgNamed(model))');
const ti=idx(/^ \/\/ the triangles$/);if(!/^ for\(const p of model\.parts\)\{$/.test(L[ti+1]))throw new Error('triangle loop moved');
const gi=ti+4;if(!/^  const T=fgPart\(p\)/.test(L[gi]))throw new Error('fgPart line moved: '+L[gi]);
L.splice(gi,0,"  if(p.shape==='mesh'){const D=fgMeshPart(model,p);let [col,code]=fgColour(p,pal,ref);if(o.plant&&code!==7)code=p.leaf?(p.leaf==='mass'?2.25:2.31):0;M.grp=grp;const t0=M.P.length/9;   // v7.0 a Blender mesh: shade baked per corner\n"+
 "   for(let i=0;i<D.I.length;i++){const v=D.I[i],s=D.S[v];vert(M,[D.P[v*3],D.P[v*3+1],D.P[v*3+2]],[D.N[v*3],D.N[v*3+1],D.N[v*3+2]],[Math.min(1,col[0]*s),Math.min(1,col[1]*s),Math.min(1,col[2]*s)],code);}\n"+
 "   if(type==='ship'&&!grp&&p.thin)(M.noClr||(M.noClr=[])).push([t0,M.P.length/9]);continue;}");
rep(/^  if\(t==='ship'\)\{let wl=-1e9;for\(const p of model\.parts\)/,"let wl=-1e9;for(const p of model.parts)","let wl=model.wl!=null?model.wl:-1e9;for(const p of model.wl!=null?[]:model.parts)");
rep(/^   M\.exhaust=\[\];let ft=0;for\(const p of model\.parts\)/,'for(const p of model.parts)','for(const p of fgNamed(model))');
rep(/^   M\.funTop=ft;M\.aa=\[\];for\(const p of model\.parts\)/,'for(const p of model.parts)','for(const p of fgNamed(model))');
rep(/^const GAME_TITLE='IRON TIDE',GAME_VERSION='v6\.9'/,"GAME_VERSION='v6.9'","GAME_VERSION='v7.0'");
fs.writeFileSync(dst,L.join('\n'));
console.log('models replaced:',n,' size:',(fs.statSync(dst).size/1048576).toFixed(2),'MB');
// 4. the paint grain was seeded from the vertex colour itself; a baked shade varies across a face, so seed it from the hue only
{let L2=fs.readFileSync(dst,'utf8');const a='float grain=vnoise3(vP*vec3(2.,2.,2.)*(dist<80.?3.:1.)+vCol.rgb*7.);';
 if(!L2.includes(a))throw new Error('grain line moved');
 L2=L2.replace(a,'float grain=vnoise3(vP*vec3(2.,2.,2.)*(dist<80.?3.:1.)+normalize(vCol.rgb+1e-4)*7.);   // v7.0 hue only: Blender models carry a baked shade');
 fs.writeFileSync(dst,L2);console.log('shader grain patched');}
