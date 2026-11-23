// Pulls the game's own mesh builders out of an Iron Tide HTML file so Node can build and count Forge models.
const fs=require('fs');
module.exports=function(html){
 const L=fs.readFileSync(html,'utf8').split('\n');
 const find=(re,from=0)=>{for(let i=from;i<L.length;i++)if(re.test(L[i]))return i;return -1;};
 const a=find(/^const sub=\(a,b\)/),b=find(/^var BEVEL_OFF=/);
 const c=find(/^const forgeBase=new Map\(\)/),d=find(/^function fgPlace\(/);
 const fm=L[find(/^const FORGE_MODELS=/)];
 const src=['const PART_SLOTS=97,MAX_PARTS=96;',L.slice(a,b+1).join('\n'),L.slice(c,d).join('\n'),fm.replace('const FORGE_MODELS','var FORGE_MODELS'),
  'return {forgeMesh,FORGE_MODELS,typeof_inflate:typeof fgInflate!=="undefined"?fgInflate:null};'].join('\n');
 return new Function(src)();
};
