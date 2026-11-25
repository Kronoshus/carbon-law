import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// the full Chromium build: the headless shell CI uses by default has no Notification API for service workers
test.use({ channel: 'chromium' });

// T8-03 acceptance (Opus, p8-tests): installable web app, the service worker's cache, and the Perfil tab
// (language, daily reminder with push only after she turns it on, install, sign out). Real backend; the push service
// and the browser's install prompt are stubbed.
const PUSH_KEY = 'BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM';
const ENDPOINT = 'https://fcm.googleapis.com/fcm/send/e2e-ana-device';

async function signUp(page: Page) {
  await page.goto('/#/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill(`ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
}

/** Counts calls to the browser's permission prompt and push subscription; the push service is never reached. */
async function stubPush(page: Page) {
  await page.addInitScript(({ endpoint }) => {
    const w = window as unknown as { __perm: number; __subs: number; __unsubs: number };
    w.__perm = 0; w.__subs = 0; w.__unsubs = 0;
    // the browser's state survives a reload (sessionStorage), the counters do not
    Notification.requestPermission = async () => { w.__perm += 1; sessionStorage.setItem('fake_perm', 'granted'); return 'granted'; };
    Object.defineProperty(Notification, 'permission', { get: () => sessionStorage.getItem('fake_perm') ?? 'default' });
    const fake = { endpoint, expirationTime: null, options: {},
      toJSON: () => ({ endpoint, expirationTime: null, keys: { p256dh: 'BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA', auth: 'tBHItJI5svbpez7KI4CCXg' } }),
      unsubscribe: async () => { w.__unsubs += 1; sessionStorage.removeItem('fake_sub'); return true; }, getKey: () => null };
    PushManager.prototype.subscribe = async function () { w.__subs += 1; sessionStorage.setItem('fake_sub', '1'); return fake as unknown as PushSubscription; };
    PushManager.prototype.getSubscription = async function () { return (sessionStorage.getItem('fake_sub') ? fake : null) as PushSubscription | null; };
  }, { endpoint: ENDPOINT });
  await page.route('**/progress/push-key', (r) => r.fulfill({ json: { public_key: PUSH_KEY } }));
}
const counts = (page: Page) => page.evaluate(() => {
  const w = window as unknown as { __perm: number; __subs: number; __unsubs: number };
  return { perm: w.__perm, subs: w.__subs, unsubs: w.__unsubs };
});

test('installable: a manifest with a stable id, standalone display and 192/512 icons, and a service worker', async ({ page, request }) => {
  await page.goto('/#/bienvenida');
  await expect(page.locator('link[rel="manifest"]')).toHaveCount(1);
  const href = await page.locator('link[rel="manifest"]').getAttribute('href');
  expect(href).toBeTruthy();
  const res = await request.get(new URL(href!, page.url()).href);
  expect(res.ok()).toBe(true);
  const m = await res.json();
  expect(m.id).toBeTruthy();
  expect(m.display).toBe('standalone');
  expect(m.name).toBe('Memento Mori');
  expect(m.start_url).toBeTruthy();
  for (const size of ['192x192', '512x512']) {
    const icon = (m.icons as { src: string; sizes: string; type: string }[]).find((i) => i.sizes === size);
    expect(icon, size).toBeTruthy();
    expect((await request.get(new URL(icon!.src, res.url()).href)).headers()['content-type']).toContain('image/png');
  }
  const maskable = (m.icons as { src: string; purpose?: string }[]).find((i) => i.purpose === 'maskable');
  expect((await request.get(new URL(maskable!.src, res.url()).href)).headers()['content-type']).toContain('image/png');
  for (const rel of ['icon', 'apple-touch-icon']) {
    const src = await page.locator(`link[rel="${rel}"]`).getAttribute('href');
    expect((await request.get(new URL(src!, page.url()).href)).headers()['content-type'], rel).toContain('image/png');
  }
  await expect(page.locator('meta[name="theme-color"]')).toHaveCount(1);
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
});

test('the service worker keeps the shell and the lesson, never journey, datos or documents (and serves the lesson offline)', async ({ page, context }) => {
  await signUp(page);
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
  const token = await page.evaluate(() => localStorage.getItem('aprende_token'));
  const get = (p: string) => page.evaluate(async ({ p, token }) => {
    try { return (await fetch(p, { headers: { Authorization: `Bearer ${token}` } })).status; } catch { return 'offline'; }
  }, { p, token });
  for (const p of ['/journey', '/datos', '/progress', '/learn/map', '/signed-documents', '/funding-checklist', '/review/documents', '/learn/lessons/will?lang=es']) {
    await get(p);
  }
  const cached = await page.evaluate(async () => {
    const urls: string[] = [];
    for (const name of await caches.keys()) for (const req of await (await caches.open(name)).keys()) urls.push(new URL(req.url).pathname);
    return urls;
  });
  expect(cached).toContain('/learn/lessons/will');
  expect(cached.filter((u) => /^\/(journey|datos|progress|learn\/map|signed-documents|funding-checklist|review|engagement|booking|auth|payments|chat)/.test(u))).toEqual([]);
  await context.setOffline(true);
  expect(await get('/learn/lessons/will?lang=es')).toBe(200);                   // published lesson content, from the cache
  expect(await get('/journey')).toBe('offline');                                // never from the cache
  expect(await get('/datos')).toBe('offline');
  await context.setOffline(false);
});

test('a push message shows the notification with the app icon and opens the app where it points', async ({ page, context, baseURL }) => {
  await context.grantPermissions(['notifications'], { origin: baseURL });
  await page.goto('/#/bienvenida');
  await page.evaluate(() => navigator.serviceWorker.ready);
  const cdp = await context.newCDPSession(page);
  let registrationId = '';
  cdp.on('ServiceWorker.workerRegistrationUpdated', (e) => {
    for (const r of e.registrations) if (r.scopeURL.startsWith(baseURL!) && !r.isDeleted) registrationId = r.registrationId;
  });
  await cdp.send('ServiceWorker.enable');
  await expect.poll(() => registrationId).not.toBe('');
  await cdp.send('ServiceWorker.deliverPushMessage', { origin: new URL(baseURL!).origin, registrationId,
    data: JSON.stringify({ title: 'La Calavera', body: 'Su lección de hoy le espera.', url: '#/aprender' }) });
  await expect.poll(() => page.evaluate(async () => (await (await navigator.serviceWorker.ready).getNotifications())
    .map((n) => `${n.title}|${n.body}|${(n.data as { url?: string } | null)?.url}|${n.icon}`))).toContain(`La Calavera|Su lección de hoy le espera.|#/aprender|${baseURL}/icons/app-192.png`);
});

test('Perfil: the daily reminder asks for push only when she turns it on, and lets go when she turns it off', async ({ page }) => {
  await stubPush(page);
  await signUp(page);
  const sent: string[] = [];
  page.on('request', (r) => { if (/\/progress\/(reminders|push)$/.test(r.url())) sent.push(`${r.method()} ${new URL(r.url()).pathname} ${r.postData() ?? ''}`); });
  await page.goto('/#/perfil');
  await expect(page.getByRole('heading', { level: 1, name: 'Perfil' })).toBeVisible();
  const toggle = page.getByRole('switch', { name: 'Recordatorio diario' }).or(page.getByRole('checkbox', { name: 'Recordatorio diario' }));
  await expect(toggle).not.toBeChecked();
  expect(await counts(page)).toEqual({ perm: 0, subs: 0, unsubs: 0 });          // nothing asked on load
  await page.getByLabel('Hora del recordatorio').fill('19:15');
  expect(await counts(page)).toEqual({ perm: 0, subs: 0, unsubs: 0 });
  const pushed = page.waitForResponse((r) => r.url().endsWith('/progress/push') && r.request().method() === 'PUT');
  await toggle.check();
  expect((await pushed).status()).toBe(200);                                    // the server accepted it: reminders were on first
  expect(await counts(page)).toEqual({ perm: 1, subs: 1, unsubs: 0 });
  expect(sent[0]).toMatch(/^PUT \/progress\/reminders .*"enabled":true.*"local_time":"19:15"/);
  expect(sent[1]).toContain(ENDPOINT);
  expect(sent[1]).toContain('"lang":"es"');
  await page.reload();
  await expect(toggle).toBeChecked();                                           // read back from GET /progress
  await expect(page.getByLabel('Hora del recordatorio')).toHaveValue('19:15');
  await toggle.uncheck();
  await expect.poll(() => sent.some((s) => /^PUT \/progress\/reminders .*"enabled":false/.test(s))).toBe(true);
  await expect.poll(async () => (await counts(page)).unsubs).toBe(1);
  const axe = await new AxeBuilder({ page }).analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
});

test('no page asks for notifications or push before she turns reminders on', async ({ page }) => {
  await stubPush(page);
  await signUp(page);
  for (const r of ['/#/aprender', '/#/plan', '/#/preguntas', '/#/perfil']) {
    await page.goto(r);
    await page.waitForLoadState('networkidle');
  }
  expect(await counts(page)).toEqual({ perm: 0, subs: 0, unsubs: 0 });
});

test('Perfil: install with navigator.install() when the browser has it', async ({ page }) => {
  await page.addInitScript(() => {
    (window as unknown as { __installs: number }).__installs = 0;
    (Navigator.prototype as unknown as { install: () => Promise<void> }).install = async function () { (window as unknown as { __installs: number }).__installs += 1; };
  });
  await signUp(page);
  await page.goto('/#/perfil');
  await page.getByRole('button', { name: 'Instalar la aplicación' }).click();
  expect(await page.evaluate(() => (window as unknown as { __installs: number }).__installs)).toBe(1);
  await expect(page.getByRole('status').filter({ hasText: 'La aplicación quedó instalada.' })).toBeVisible();
});

test('Perfil: install through beforeinstallprompt when navigator.install() is missing, and no button when neither exists', async ({ page }) => {
  await page.addInitScript(() => { delete (Navigator.prototype as unknown as { install?: unknown }).install; });
  await signUp(page);
  await page.goto('/#/perfil');
  await expect(page.getByRole('heading', { level: 1, name: 'Perfil' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Instalar la aplicación' })).toHaveCount(0);   // nothing that cannot work
  await page.evaluate(() => {
    const w = window as unknown as { __prompted: number };
    w.__prompted = 0;
    const e = new Event('beforeinstallprompt', { cancelable: true }) as Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };
    e.prompt = async () => { w.__prompted += 1; };
    e.userChoice = Promise.resolve({ outcome: 'accepted' });
    window.dispatchEvent(e);
  });
  await page.getByRole('button', { name: 'Instalar la aplicación' }).click();
  expect(await page.evaluate(() => (window as unknown as { __prompted: number }).__prompted)).toBe(1);
  await expect(page.getByRole('status').filter({ hasText: 'La aplicación quedó instalada.' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Instalar la aplicación' })).toHaveCount(0);   // the prompt is single-use
});

test('Perfil: language and sign out', async ({ page }) => {
  await signUp(page);
  await page.goto('/#/perfil');
  await page.getByLabel('Idioma').selectOption('en');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { level: 1, name: 'Profile' })).toBeVisible();
  await expect(page.getByText('Próximamente')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Sign out' })).toHaveCount(1);   // one sign-out in the app: Perfil's
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/#\/entrar/);
  expect(await page.evaluate(() => localStorage.getItem('aprende_token'))).toBeNull();
});
