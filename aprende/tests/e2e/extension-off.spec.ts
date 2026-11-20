import { test, expect, chromium, type BrowserContext } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// T7-05 acceptance (Opus, t7-tests): with the extension switched off, the API answers the extension's origin with
// 503 extension_off (pytest proves that); here the side panel and the popup must say "No disponible". Needs build:ext.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EXT_PATH = path.resolve(__dirname, '../../dist/extension');
const EXECUTABLE = process.env.PW_CHROMIUM;

async function launch(): Promise<{ context: BrowserContext; extId: string }> {
  const context = await chromium.launchPersistentContext('', {
    headless: false,
    ...(EXECUTABLE ? { executablePath: EXECUTABLE } : {}),
    args: ['--headless=new', `--disable-extensions-except=${EXT_PATH}`, `--load-extension=${EXT_PATH}`],
  });
  const sw = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
  return { context, extId: new URL(sw.url()).host };
}

test('the side panel and the popup say "No disponible" when the firm turned the extension off', async () => {
  const { context, extId } = await launch();
  await context.route(/\/(settings\/public|journey|auth\/.*)$/, (r) => r.fulfill({ status: 503, json: { error: 'extension_off' } }));
  const panel = await context.newPage();
  await panel.goto(`chrome-extension://${extId}/sidepanel.html`);
  await expect(panel.getByRole('heading', { name: 'No disponible' })).toBeVisible();
  await expect(panel.getByText('carbon.bailment.tech/aprende/')).toBeVisible();
  await expect(panel.getByRole('link', { name: 'Iniciar sesión' })).toHaveCount(0);      // nothing else is offered
  const popup = await context.newPage();
  await popup.goto(`chrome-extension://${extId}/popup.html`);
  await expect(popup.getByText('No disponible')).toBeVisible();
  await expect(popup.getByRole('button', { name: 'Abrir' })).toHaveCount(0);
  await context.close();
});

test('with the extension on, the side panel opens as usual', async () => {
  const { context, extId } = await launch();
  await context.route(/\/settings\/public$/, (r) => r.fulfill({ json: { switches: { ai_chat: true, voice_recording: true, extension: true } } }));
  const panel = await context.newPage();
  await panel.goto(`chrome-extension://${extId}/sidepanel.html`);
  await expect(panel.getByRole('link', { name: 'Iniciar sesión' })).toBeVisible();
  await expect(panel.getByText('No disponible')).toHaveCount(0);
  await context.close();
});
