/* RoleHint public PWA: avoid trapping users on obsolete releases. */
const CACHE='rolehint-shell-20261021-v6';
const SHELL=['./','./index.html','./workspace.html','./pricing.html','./subscription.html','./install.html','./privacy.html','./favicon.svg','./manifest.webmanifest','./design-v2.css','./design-v2.js'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>Promise.allSettled(SHELL.map(url=>cache.add(url)))).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{const request=event.request;const url=new URL(request.url);if(request.method!=='GET'||url.origin!==self.location.origin)return;
if(request.mode==='navigate'){event.respondWith(fetch(new Request(request,{cache:'no-store'})).then(response=>{if(response.ok){const clone=response.clone();caches.open(CACHE).then(cache=>cache.put(request,clone))}return response}).catch(()=>caches.match(request)));return}
event.respondWith(fetch(request).then(response=>{if(response.ok){const clone=response.clone();caches.open(CACHE).then(cache=>cache.put(request,clone))}return response}).catch(()=>caches.match(request)))});
