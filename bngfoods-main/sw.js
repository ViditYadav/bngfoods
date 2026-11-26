/* BNG Foods offline helper. Pages and store.json: always try the network first (so edits show up straight away).
   Images and fonts: served from the phone's cache, refreshed in the background. Google Sheet and order services are never cached. */
const V = "bng-v2-1";
self.addEventListener("install", e => { self.skipWaiting(); e.waitUntil(caches.open(V).then(c => c.addAll(["./", "index.html", "store.json", "images/logo.png", "images/range.webp"]).catch(() => {}))); });
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if(r.method !== "GET") return;
  const same = u.origin === location.origin, font = /fonts\.(googleapis|gstatic)\.com$/.test(u.hostname);
  if(!same && !font) return;                                   // Google Sheet, WhatsApp, pincode API: straight to network
  if(r.mode === "navigate" || u.pathname.endsWith(".json") || u.pathname.endsWith(".html")){
    e.respondWith(fetch(r).then(res => { const c = res.clone(); caches.open(V).then(x => x.put(r, c)); return res; }).catch(() => caches.match(r).then(m => m || caches.match("./"))));
    return;
  }
  e.respondWith(caches.match(r).then(m => { const net = fetch(r).then(res => { if(res.ok || res.type === "opaque"){ const c = res.clone(); caches.open(V).then(x => x.put(r, c)); } return res; }).catch(() => m); return m || net; }));
});
