import { test, expect, chromium } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

// T8-02 acceptance (Opus, p8-tests): the packaged side panel talks only to the firm's API origin (the one in
// host_permissions), never to its own chrome-extension:// origin for API paths. Needs `npm run build:ext`.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EXT_PATH = path.resolve(__dirname, '../../dist/extension');
const EXECUTABLE = process.env.PW_CHROMIUM;

test('the side panel calls the API at the origin in host_permissions, and nothing else', async () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(EXT_PATH, 'manifest.json'), 'utf8'));
  const apiOrigin = new URL(manifest.host_permissions[0].replace(/\*$/, '')).origin;
  const context = await chromium.launchPersistentContext('', {
    headless: false,
    ...(EXECUTABLE ? { executablePath: EXECUTABLE } : {}),
    args: ['--headless=new', `--disable-extensions-except=${EXT_PATH}`, `--load-extension=${EXT_PATH}`],
  });
  const sw = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
  const extId = new URL(sw.url()).host;
  const own: string[] = [];
  const elsewhere: string[] = [];
  await context.route('**/*', (r) => {
    const url = new URL(r.request().url());
    if (url.protocol === 'chrome-extension:') {
      if (!fs.existsSync(path.join(EXT_PATH, decodeURIComponent(url.pathname)))) own.push(url.pathname);
      return r.fallback();
    }
    if (url.origin !== apiOrigin) { elsewhere.push(url.href); return r.abort(); }
    const p = url.pathname;
    if (p === '/settings/public') return r.fulfill({ json: { switches: { ai_chat: true, voice_recording: true, extension: true } } });
    if (p === '/auth/login') return r.fulfill({ json: { token: 'tok-ana' } });
    if (p === '/journey') return r.fulfill({ json: { id: 'j1', user_id: 'u1', day: 1, facts: {}, gates: {}, conflict: 'pending',
      documents: { tentative: [], confirmed: [] }, timeline: [] } });
    return r.fulfill({ json: {} });
  });
  const page = await context.newPage();
  await page.goto(`chrome-extension://${extId}/sidepanel.html`);
  await page.getByRole('link', { name: 'Iniciar sesión' }).click();
  await page.getByLabel('Correo electrónico').fill('ana@example.com');
  await page.getByLabel('Contraseña').fill('long-secure-password');
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);                               // signed in through the API origin
  const popup = await context.newPage();
  await popup.goto(`chrome-extension://${extId}/popup.html`);
  await expect(popup.getByRole('button', { name: 'Abrir' })).toBeVisible();
  expect(own).toEqual([]);                                                      // no API call to chrome-extension://<id>/…
  expect(elsewhere).toEqual([]);                                                // no other host at all (fonts are packaged)
  await context.close();
});
