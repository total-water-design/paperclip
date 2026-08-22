/* Total Water Design Suite PWA static service worker.
   This intentionally uses network-first behavior so hosted TWDS deployments stay
   authoritative. Engineering API responses, project data and HTML navigation are
   never cached by this worker. */

const CACHE_NAME = 'twds-mobile-static-v1';
const CORE_ASSETS = [
  '/static/manifest.webmanifest',
  '/static/mobile.css',
  '/static/mobile.js',
  '/static/branding/suite/total_water_design_suite_icon_256.png',
  '/static/branding/suite/total_water_design_suite_icon_512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(CORE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if(request.method !== 'GET') return;

  const url = new URL(request.url);
  if(url.origin !== self.location.origin || !url.pathname.startsWith('/static/')) return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        if(response && response.ok){
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});
