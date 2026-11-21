export function cacheKind(req: {url: string; method?: string; mode?: string; destination?: string}, scope: string, apiOrigin: string): 'shell' | 'lesson' | null {
  const method = (req.method || 'GET').toUpperCase();
  if (method !== 'GET') return null;
  let url: URL;
  try { url = new URL(req.url); } catch { return null; }
  const scopeUrl = new URL(scope, url.origin + '/');
  const scopeOrigin = scopeUrl.origin;
  const scopePath = scopeUrl.pathname.endsWith('/') ? scopeUrl.pathname : scopeUrl.pathname + '/';
  const origin = url.origin;
  const path = url.pathname;
  const destination = req.destination || '';
  const mode = req.mode || '';

  // lesson check: path /learn/lessons/<id> on api or scope origin
  const allowedOrigins = new Set<string>();
  try { allowedOrigins.add(new URL(apiOrigin || scope, scope).origin); } catch { /* ignore */ }
  try { allowedOrigins.add(new URL(scope).origin); } catch { /* ignore */ }
  if (allowedOrigins.has(origin)) {
    const segs = path.split('/').filter(Boolean);
    // find learn/lessons/<id> as a suffix-ish: path must be exactly /learn/lessons/<id>
    if (segs.length === 3 && segs[0] === 'learn' && segs[1] === 'lessons' && segs[2]) {
      return 'lesson';
    }
  }

  // shell requires same origin as scope
  if (origin !== scopeOrigin) return null;
  if (!path.startsWith(scopePath)) return null;

  // navigation to exactly scope or scope + index.html
  if (mode === 'navigate' && (path === scopePath || path === scopePath + 'index.html')) {
    return 'shell';
  }
  // script/style/font/image/manifest destination under scope
  if (['script','style','font','image','manifest'].includes(destination)) {
    return 'shell';
  }
  // path under scope + characters/
  if (path.startsWith(scopePath + 'characters/')) {
    return 'shell';
  }
  return null;
}
