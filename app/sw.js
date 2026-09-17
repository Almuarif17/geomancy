/* Service worker for the geomancy reader - no build step, so the cache name is the version and is bumped by hand.
 *
 * The rule this file exists to enforce: the interface is a fixed set of files, so it is cached and served offline;
 * the answers are not. Nothing from /api/* is ever stored here, because a stale reading shown beside a live chart
 * is worse than an honest "the engine is not answering". Saved charts come from the app's own storage instead, which
 * is per-device and already sized for it.
 */
const SHELL = "geomancy-shell-v1";
const FILES = ["mobile.html", "manifest.webmanifest", "icon-192.png", "icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES.map(f => new Request(f, { cache: "reload" }))))
    .catch(() => {}));                     // a missing file must not strand the install in a broken state
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(k => k !== SHELL).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;            // same-origin only: no third party is ever pulled in
  if (url.pathname.includes("/api/")) {                        // answers: network, always, or a clear failure
    e.respondWith(fetch(req).then(res => {
      // an engine answer is never cached; this branch exists so a future edit cannot change that by accident
      return res;
    }).catch(() => new Response(JSON.stringify({ error: "offline: the engine is unreachable, so nothing new can be cast. Saved charts remain readable from this device." }),
      { status: 503, headers: { "content-type": "application/json" } })));
    return;
  }
  if (req.mode === "navigate") {                               // opening the app: fresh if possible, cached if not
    e.respondWith(fetch(new Request(req.url, { cache: "no-store" }))
      .then(res => {
        const copy = res.clone();
        caches.open(SHELL).then(c => c.put("mobile.html", copy));
        return res;
      })
      .catch(() => caches.match("mobile.html").then(r => r || Response.error())));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
    const copy = res.clone();
    caches.open(SHELL).then(c => c.put(req, copy));            // icons and the manifest, once
    return res;
  }).catch(() => Response.error())));
});
