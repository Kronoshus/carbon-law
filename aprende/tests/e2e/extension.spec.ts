import { test, expect, chromium } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';
import os from 'node:os';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EXT_PATH = path.resolve(__dirname, '../../dist/extension');
const EXECUTABLE = process.env.PW_CHROMIUM || '/home/dkkm10/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome';

test('popup reads journey and opens side panel', async () => {
  const context = await chromium.launchPersistentContext('', {
    headless: true,
    executablePath: EXECUTABLE,
    args: [
      `--disable-extensions-except=${EXT_PATH}`,
      `--load-extension=${EXT_PATH}`,
    ],
  });
  const [sw] = context.serviceWorkers();
  const extId = new URL(sw.url()).host;
  const page = await context.newPage();
  const consoleErrors: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', (e) => consoleErrors.push(String(e)));

  await page.addInitScript(() => {
    (window as unknown as { __sidePanelCalls: unknown[] }).__sidePanelCalls = [];
    const chromeAny = (window as unknown as { chrome: { sidePanel: { open: (o: unknown) => unknown } } }).chrome;
    const orig = chromeAny.sidePanel.open.bind(chromeAny.sidePanel);
    chromeAny.sidePanel.open = (opts: unknown) => {
      (window as unknown as { __sidePanelCalls: unknown[] }).__sidePanelCalls.push(opts);
      return orig(opts);
    };
  });

  await page.route('**/journey', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 'j1', user_id: 'u1', day: 3, gates: { may_disclose: true, may_consent: false }, conflict: 'clear' }),
    });
  });

  await page.goto(`chrome-extension://${extId}/popup.html`);
  await expect(page.getByText('Racha: 0')).toBeVisible();
  await expect(page.getByText('Paso de hoy: 3 · Dar su consentimiento')).toBeVisible();

  const winId = await page.evaluate(async () => (await chrome.windows.getCurrent()).id);
  await page.getByRole('button', { name: 'Abrir' }).click();
  const calls = await page.evaluate(() => (window as unknown as { __sidePanelCalls: unknown[] }).__sidePanelCalls);
  expect(calls).toEqual([ { windowId: winId } ]);
  expect(consoleErrors).toEqual([]);

  await context.close();
});

test('storage.local stays empty and token clears on restart', async () => {
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'cl-t2-12-'));
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: true,
    executablePath: EXECUTABLE,
    args: [
      `--disable-extensions-except=${EXT_PATH}`,
      `--load-extension=${EXT_PATH}`,
    ],
  });
  const [sw] = context.serviceWorkers();
  const sidePage = await context.newPage();
  await sidePage.goto(`chrome-extension://${new URL(sw.url()).host}/sidepanel.html`);
  await sidePage.evaluate(async () => {
    await chrome.storage.session.set({ aprende_token: 'tok' });
  });
  const sessionBefore = await sidePage.evaluate(async () => (await chrome.storage.session.get('aprende_token')).aprende_token);
  expect(sessionBefore).toBe('tok');
  const localBefore = await sidePage.evaluate(async () => Object.keys(await chrome.storage.local.get(null)));
  const syncBefore = await sidePage.evaluate(async () => Object.keys(await chrome.storage.sync.get(null)));
  expect(localBefore).toEqual([]);
  expect(syncBefore).toEqual([]);

  await context.close();

  const context2 = await chromium.launchPersistentContext(userDataDir, {
    headless: true,
    executablePath: EXECUTABLE,
    args: [
      `--disable-extensions-except=${EXT_PATH}`,
      `--load-extension=${EXT_PATH}`,
    ],
  });
  const [sw2] = context2.serviceWorkers();
  const page2 = await context2.newPage();
  await page2.goto(`chrome-extension://${new URL(sw2.url()).host}/sidepanel.html`);
  const sessionAfter = await page2.evaluate(async () => (await chrome.storage.session.get('aprende_token')).aprende_token ?? null);
  expect(sessionAfter).toBeNull();
  await context2.close();
  fs.rmSync(userDataDir, { recursive: true, force: true });
});
