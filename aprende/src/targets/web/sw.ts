/* eslint-disable @typescript-eslint/no-explicit-any */
import { cacheKind } from './sw-rules';

const SHELL_CACHE = 'aprende-shell-v1';
const LESSON_CACHE = 'aprende-lessons-v1';

self.addEventListener('install', () => {
  (self as any).skipWaiting();
});

self.addEventListener('activate', (event: any) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter((n) => n !== SHELL_CACHE && n !== LESSON_CACHE).map((n) => caches.delete(n)));
    await (self as any).clients.claim();
  })());
});

self.addEventListener('fetch', (event: any) => {
  const req = event.request;
  const API_ORIGIN = (import.meta.env && import.meta.env.VITE_API_ORIGIN) || '';
  const kind = cacheKind({ url: req.url, method: req.method, mode: req.mode, destination: req.destination }, (self as any).registration.scope, API_ORIGIN);
  // apiOrigin not passed; sw-rules derives from scope origin if empty? Check: allowedOrigins adds new URL(apiOrigin || scope, scope).origin => scope origin. Fine for same origin. For separate API origin, need apiOrigin. We don't know at runtime? registration scope only. But test uses api origin carbon-law.onrender.com. Service worker scope is app origin. Need apiOrigin. Hmm.
  if (!kind) return;
  // We need api origin; infer from a known constant? The brief says apiOrigin param. In sw, we can pass self origin? But API may be different origin. For push/lesson from API origin, cacheKind checks allowedOrigins includes scope origin and apiOrigin. If we pass empty, only scope origin. Test expects lesson from API origin carbon-law.onrender.com to be cached by sw? The e2e test caches /learn/lessons/will on API origin? Wait fetch goes through Vite proxy in dev, so same origin scope? In e2e, page fetches /learn/lessons/will (relative) => same origin as page (carbon.../aprende? Actually scope origin carbon.bailment.tech). Hmm test URL API maybe not used in browser fetch; they use relative /learn/lessons/will. cacheKind with apiOrigin '' allows scope origin. OK.
  if (kind === 'shell' && req.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const res = await fetch(req);
        const cache = await caches.open(SHELL_CACHE);
        cache.put(req, res.clone());
        return res;
      } catch {
        const cached = await caches.match(req);
        if (cached) return cached;
        return caches.match(new URL('index.html', (self as any).registration.scope).href);
      }
    })());
    return;
  }
  if (kind === 'shell') {
    event.respondWith((async () => {
      const cached = await caches.match(req);
      if (cached) return cached;
      const res = await fetch(req);
      const cache = await caches.open(SHELL_CACHE);
      cache.put(req, res.clone());
      return res;
    })());
    return;
  }
  if (kind === 'lesson') {
    event.respondWith((async () => {
      try {
        const res = await fetch(req);
        const cache = await caches.open(LESSON_CACHE);
        cache.put(req, res.clone());
        return res;
      } catch {
        const cached = await caches.match(req);
        if (cached) return cached;
        throw new Error('offline');
      }
    })());
    return;
  }
});

self.addEventListener('push', (event: any) => {
  let data: any = {};
  try { data = event.data ? event.data.json() : {}; } catch { data = { title: '', body: event.data?.text?.() }; }
  event.waitUntil((self as any).registration.showNotification(data.title || '', {
    body: data.body || '',
    icon: 'img/calavera-face.png',
    data: { url: data.url || '' },
  }));
});

self.addEventListener('notificationclick', (event: any) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '';
  event.waitUntil((async () => {
    const clientsList = await (self as any).clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const client of clientsList) {
      if (client.url.includes((self as any).registration.scope) && 'focus' in client) {
        await client.focus();
        if (url) client.navigate((self as any).registration.scope + url.replace(/^#?\//, ''));
        return;
      }
    }
    await (self as any).clients.openWindow((self as any).registration.scope + (url || ''));
  })());
});
