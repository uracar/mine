// Iron Tide service worker: the game files are cached on first visit, so later visits start without downloading 1.3 MB again.
// Bump VERSION on every release: the new worker fetches the new files and drops the old cache.
const VERSION='iron-tide-5.3.0';
const FILES=['./','index.html','css/style.css','js/boot.js','js/terrain.js','js/shaders.js','js/game.js','manifest.webmanifest','icon.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(VERSION).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==VERSION).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
 const u=new URL(e.request.url);
 if(e.request.method!=='GET'||u.origin!==location.origin||u.pathname.startsWith('/api'))return;   // the live server is never cached
 e.respondWith(caches.match(e.request,{ignoreSearch:true}).then(hit=>hit||fetch(e.request)));
});
