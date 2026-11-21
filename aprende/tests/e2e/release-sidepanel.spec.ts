import { test, expect, chromium } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { API, nextWeekday, releaseJourney, type ClientApp } from '../../e2e/journey-steps';

// T8-06 (Opus): the same release journey in the Chrome side panel (brief section 5: "the same works in the Chrome side
// panel"). Needs `npm run build:ext`. Runs in the "release" project, after every other test, one test at a time.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EXT_PATH = path.resolve(__dirname, '../../dist/extension');
const EXECUTABLE = process.env.PW_CHROMIUM;
// the API paths, as in vite.config.ts's proxy list ('/characters' also names the character files)
const PROD = 'https://carbon-law.onrender.com';
const API_PATH = /^\/(auth|journey|health|payments|learn|content|progress|datos|chat|engagement|staff|conflicts|booking|signed-documents|funding-checklist|review|settings|e2e|documents)(\/|\?|$)|^\/characters(\/[a-z_]+)?$/;

test('a new client goes through the whole journey in the Chrome side panel, each step on its planned day', async () => {
  const context = await chromium.launchPersistentContext('', {
    headless: false,
    viewport: { width: 360, height: 800 },
    locale: 'es-US',
    timezoneId: 'America/Los_Angeles',
    ...(EXECUTABLE ? { executablePath: EXECUTABLE } : {}),
    // without WebGL the characters are their still images (the app's own fallback): the journey, not the 3D, is tested here
    args: ['--headless=new', '--disable-webgl', `--disable-extensions-except=${EXT_PATH}`, `--load-extension=${EXT_PATH}`],
  });
  const sw = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
  const extId = new URL(sw.url()).host;
  // The extension build calls the production API: send those calls to the e2e backend, keeping the extension's Origin
  // header so the firm's extension switch is still checked. Nothing is played back.
  await context.route((url) => (url.origin === PROD || url.protocol === 'chrome-extension:') && API_PATH.test(url.pathname), async (route) => {
    const u = new URL(route.request().url());
    const response = await route.fetch({ url: `${API}${u.pathname}${u.search}`, headers: { ...route.request().headers(), origin: `chrome-extension://${extId}` } });
    await route.fulfill({ response });
  });
  const page = await context.newPage();
  const c: ClientApp = {
    page, context,
    go: async (hash) => {                                                 // the same address again: open it fresh
      const url = `chrome-extension://${extId}/sidepanel.html#${hash}`;
      if (page.url() === url) await page.reload(); else await page.goto(url);
    },
    backFromStripe: async (url) => {                                       // F3: Stripe returned her to the web address
      expect(url.startsWith(`http://127.0.0.1:${process.env.E2E_WEB_PORT || '5173'}/`)).toBe(true);
      await page.goto(`chrome-extension://${extId}/sidepanel.html#${new URL(url).hash.slice(1)}`);
    },
    token: async () => (await page.evaluate(async () => (await chrome.storage.session.get('aprende_token')).aprende_token as string)),
  };
  await releaseJourney(c, await nextWeekday(3), 'Sofía Torres');
  await context.close();
});
