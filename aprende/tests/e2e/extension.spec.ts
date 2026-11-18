import { test, expect, chromium } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const EXT_PATH = path.resolve(__dirname, '../../dist/extension');

test('popup reads journey and opens side panel', async () => {
  const context = await chromium.launchPersistentContext('', {
    headless: true,
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || '/home/dkkm10/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',
    args: [
      `--disable-extensions-except=${EXT_PATH}`,
      `--load-extension=${EXT_PATH}`,
    ],
  });
  const [sw] = context.serviceWorkers();
  const extId = new URL(sw.url()).host;
  const page = await context.newPage();
  await page.route('**/journey', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 'j1', user_id: 'u1', day: 3, gates: { may_disclose: true, may_consent: false }, conflict: 'clear' }),
    });
  });
  await page.goto(`chrome-extension://${extId}/popup.html`);
  await expect(page.getByText('Racha: 0')).toBeVisible();
  await expect(page.getByText(/Paso de hoy/)).toBeVisible();
  await page.getByRole('button', { name: 'Abrir' }).click();
  await context.close();
});


test('storage.local is empty and token uses session', async () => {
  const context = await chromium.launchPersistentContext('', {
    headless: true,
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || '/home/dkkm10/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',
    args: [
      `--disable-extensions-except=${EXT_PATH}`,
      `--load-extension=${EXT_PATH}`,
    ],
  });
  const [sw] = context.serviceWorkers();
  const local = await sw.evaluate(async () => {
    const r = await chrome.storage.local.get(null);
    return Object.keys(r);
  });
  expect(local).toEqual([]);
  await context.close();
});
