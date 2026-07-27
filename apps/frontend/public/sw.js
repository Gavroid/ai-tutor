// Sprint 98: Service Worker для offline support.
//
// Стратегия:
// - App shell (HTML, CSS, JS, manifest): CacheFirst с fallback на network
// - API запросы (/api/*): NetworkFirst с timeout 3 сек, fallback на offline page
// - Images: CacheFirst с expiration
// - Cache version: при изменении версии — invalidate old caches

const CACHE_VERSION = "v1.0.0";
const CACHE_NAME = `ai-tutor-${CACHE_VERSION}`;

// Static assets для offline app shell
const APP_SHELL = [
  "/",
  "/offline",
  "/manifest.json",
  "/icon.svg",
];

// === Install: cache app shell ===
self.addEventListener("install", (event) => {
  console.log("[SW] Installing version:", CACHE_VERSION);
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[SW] Caching app shell");
      return cache.addAll(APP_SHELL).catch((err) => {
        console.warn("[SW] Failed to cache some shell assets:", err);
      });
    })
  );
  // Activate immediately (skip waiting)
  self.skipWaiting();
});

// === Activate: cleanup old caches ===
self.addEventListener("activate", (event) => {
  console.log("[SW] Activating version:", CACHE_VERSION);
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName.startsWith("ai-tutor-")) {
            console.log("[SW] Deleting old cache:", cacheName);
            return caches.delete(cacheName);
          }
          return null;
        })
      );
    })
  );
  return self.clients.claim();
});

// === Fetch: cache strategies ===
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== "GET") return;

  // Skip cross-origin requests
  if (url.origin !== self.location.origin) return;

  // API запросы — NetworkFirst (3 сек timeout)
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirstStrategy(request, 3000));
    return;
  }

  // Static assets — CacheFirst
  event.respondWith(cacheFirstStrategy(request));
});

// CacheFirst: cache → network
async function cacheFirstStrategy(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (err) {
    // Offline fallback
    if (request.mode === "navigate") {
      const offlineResponse = await caches.match("/offline");
      if (offlineResponse) return offlineResponse;
    }
    return new Response("Offline", {
      status: 503,
      statusText: "Service Unavailable",
    });
  }
}

// NetworkFirst: network → cache (с timeout)
async function networkFirstStrategy(request, timeoutMs) {
  try {
    const networkResponse = await Promise.race([
      fetch(request),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error("Network timeout")), timeoutMs)
      ),
    ]);
    return networkResponse;
  } catch (err) {
    // Offline fallback на cache
    const cachedResponse = await caches.match(request);
    if (cachedResponse) return cachedResponse;
    if (request.mode === "navigate") {
      const offlineResponse = await caches.match("/offline");
      if (offlineResponse) return offlineResponse;
    }
    return new Response("Offline", {
      status: 503,
      statusText: "Service Unavailable",
    });
  }
}

// === Messages: skip waiting или update ===
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});