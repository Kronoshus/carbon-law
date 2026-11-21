import { describe, it, expect } from 'vitest';
import { resolve } from 'node:path';

// T8-03 acceptance (Opus, p8-tests): what the service worker may keep. Only the app shell and published lesson content;
// never journey, datos, documents or any other client data. `cacheKind` is the one rule the worker uses (sw.ts calls it
// for every fetch and does not call respondWith when it returns null).
const SCOPE = 'https://carbon.bailment.tech/aprende/';
const API = 'https://carbon-law.onrender.com';

type Req = { url: string; method?: string; mode?: string; destination?: string };
async function kind(r: Req, apiOrigin = API) {
  const path = resolve('src/targets/web/sw-rules.ts');   // collects before the file exists
  const { cacheKind } = (await import(/* @vite-ignore */ path)) as { cacheKind: (r: Required<Req>, scope: string, api: string) => 'shell' | 'lesson' | null };
  return cacheKind({ method: 'GET', mode: 'cors', destination: '', ...r }, SCOPE, apiOrigin);
}

describe('T8-03 service worker cache rules', () => {
  it('keeps the app shell: the start page, its scripts, styles, fonts, images, manifest and character files', async () => {
    expect(await kind({ url: SCOPE, mode: 'navigate', destination: 'document' })).toBe('shell');
    expect(await kind({ url: SCOPE + 'index.html', mode: 'navigate', destination: 'document' })).toBe('shell');
    expect(await kind({ url: SCOPE + 'assets/index-FJ2VYcRu.js', destination: 'script' })).toBe('shell');
    expect(await kind({ url: SCOPE + 'assets/index-CKMy-8qJ.css', destination: 'style' })).toBe('shell');
    expect(await kind({ url: SCOPE + 'assets/work-sans-latin-400-normal-jUejSri3.woff2', destination: 'font' })).toBe('shell');
    expect(await kind({ url: SCOPE + 'img/calavera-face.png', destination: 'image' })).toBe('shell');
    expect(await kind({ url: SCOPE + 'manifest.webmanifest', destination: 'manifest' })).toBe('shell');
    expect(await kind({ url: SCOPE + 'characters/calavera.glb' })).toBe('shell');
  });

  it('keeps published lessons, from the API origin or the same origin', async () => {
    expect(await kind({ url: `${API}/learn/lessons/will?lang=es` })).toBe('lesson');
    expect(await kind({ url: 'https://carbon.bailment.tech/learn/lessons/trust?lang=en' }, '')).toBe('lesson');
  });

  it('never keeps client data', async () => {
    for (const p of ['/journey', '/journey/questions', '/datos', '/datos/nombre', '/signed-documents', '/signed-documents/Qx7k2pL9',
      '/funding-checklist', '/review/documents', '/engagement', '/engagement/pdf', '/progress', '/booking', '/booking/slots?kind=signing',
      '/payments/quote?codes=will', '/payments/receipt', '/auth/me', '/learn/map', '/settings/public', '/chat']) {
      expect(await kind({ url: API + p }), p).toBeNull();
    }
  });

  it('never keeps a write, a lesson sub-path, another site, or a navigation away from the start page', async () => {
    expect(await kind({ url: `${API}/learn/lessons/will?lang=es`, method: 'POST' })).toBeNull();
    expect(await kind({ url: `${API}/learn/lessons/will/complete`, method: 'POST' })).toBeNull();
    expect(await kind({ url: `${API}/learn/lessons/will/complete` })).toBeNull();
    expect(await kind({ url: 'https://cdn.example.com/x.js', destination: 'script' })).toBeNull();
    expect(await kind({ url: 'https://cdn.example.com/a.png', destination: 'image' })).toBeNull();
    expect(await kind({ url: SCOPE + 'signed-documents/Qx7k2pL9', mode: 'navigate', destination: 'document' })).toBeNull();
    expect(await kind({ url: 'https://carbon.bailment.tech/dashboard.html', mode: 'navigate', destination: 'document' })).toBeNull();
    expect(await kind({ url: `${API}/learn/lessons/will?lang=es`, method: 'GET' }, 'https://other.example.com')).toBeNull();
  });
});
