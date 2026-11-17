// Loads the game in order: the terrain source (kept as text, because the page and the chunk workers both run it),
// then the shaders, then the game itself. Also registers the service worker so repeat visits start from the local cache.
(function(){
 'use strict';
 function loadScript(src){
  return new Promise((ok,bad)=>{const s=document.createElement('script');s.src=src;s.onload=ok;s.onerror=()=>bad(new Error('Could not load '+src));document.body.appendChild(s);});
 }
 function fail(e){const el=document.getElementById('err');el.style.display='block';el.textContent+=String(e&&e.message||e)+'\n';}
 fetch('js/terrain.js').then(r=>{if(!r.ok)throw new Error('Could not load js/terrain.js');return r.text();}).then(src=>{
  const t=document.createElement('script');t.id='terrainsrc';t.type='text/plain';t.textContent=src;document.body.appendChild(t);
  return loadScript('js/shaders.js');
 }).then(()=>loadScript('js/game.js')).catch(fail);
 if('serviceWorker' in navigator&&location.protocol==='https:'){
  addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));
 }
})();
