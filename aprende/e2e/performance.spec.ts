import { test, expect, type Page } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

// T8-05 acceptance (Opus, p8-tests): on a mid-range phone. three.js and the character GLB load only after the first
// paint and only on screens with a character stage; INP on the lesson player stays under 200 ms with the CPU slowed 4×
// (web-vitals, the library the `interaction-paint-timing` guide names). Lighthouse runs in its own CI job
// (`aprende/scripts/lighthouse.mjs`), not here.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_VITALS = path.resolve(__dirname, '../node_modules/web-vitals/dist/web-vitals.iife.js');   // devDependency `web-vitals`

async function signUp(page: Page) {
  await page.goto('/#/bienvenida');
  await page.evaluate(async () => {
    const json = { 'Content-Type': 'application/json' };
    const r = await fetch('/auth/signup', { method: 'POST', headers: json, body: JSON.stringify({ name: 'Ana Torres',
      email: `ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`, password: 'long-secure-password', source: 'aprende', adult: true }) });
    const tok = (await r.json()).token;
    localStorage.setItem('aprende_token', tok);
    const me = (type: string, payload: object = {}) => fetch('/journey/events', { method: 'POST',
      headers: { ...json, Authorization: `Bearer ${tok}` }, body: JSON.stringify({ type, payload }) });
    await me('ai_disclosed'); await me('consent', { answer: 'yes' }); await me('names_submitted', { names: ['Ana Torres'] });
  });
}

/** A fresh document load of `hash` (a hash change alone would keep the first page's paint timings). */
async function load(page: Page, hash: string) {
  await page.goto('about:blank');
  await page.goto('/' + hash);
}

const timings = (page: Page) => page.evaluate(() => ({
  fcp: performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? null,
  heavy: (performance.getEntriesByType('resource') as PerformanceResourceTiming[])
    .filter((r) => /three|GLTFLoader|\.glb(\?|$)/.test(new URL(r.name).pathname))
    .map((r) => ({ url: new URL(r.name).pathname, start: r.startTime })),
}));

test('the course map loads no three.js and no character file', async ({ page }) => {
  await signUp(page);
  await load(page, '#/aprender');
  await expect(page.locator('.map')).toBeVisible();
  await page.waitForLoadState('networkidle');
  expect((await timings(page)).heavy).toEqual([]);
});

test('on the lesson, three.js and the GLB start only after the first contentful paint', async ({ page }) => {
  await signUp(page);
  await load(page, '#/leccion/will');
  await expect(page.locator('canvas:not([hidden]), .character-still')).toBeVisible({ timeout: 30000 });
  await expect.poll(async () => (await timings(page)).heavy.some((r) => r.url.endsWith('.glb')), { timeout: 30000 }).toBe(true);
  const t = await timings(page);
  expect(t.fcp).not.toBeNull();
  for (const r of t.heavy) expect(r.start, r.url).toBeGreaterThan(t.fcp!);
});

test('INP on the lesson player stays under 200 ms on a 4× slower CPU', async ({ page, context }) => {
  expect(fs.existsSync(WEB_VITALS), 'add web-vitals as a devDependency').toBe(true);
  await signUp(page);
  // one init script: the library's `var webVitals` is only visible to code in the same script
  await page.addInitScript({ content: `${fs.readFileSync(WEB_VITALS, 'utf8')}
    window.__inp = [];
    webVitals.onINP((m) => { window.__inp.push(m.value); }, { reportAllChanges: true, durationThreshold: 16 });` });
  await load(page, '#/leccion/will');
  const cont = page.getByRole('button', { name: 'Continuar' });
  await expect(cont).toBeVisible({ timeout: 30000 });
  const cdp = await context.newCDPSession(page);
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });                // Moto G Power–class
  for (let i = 0; i < 4; i++) await cont.click();                               // four explanations
  await page.getByRole('radio').first().check();
  await page.getByRole('button', { name: 'Comprobar' }).click();
  await expect(page.locator('.feedback')).toBeVisible();
  await cont.click();
  await page.waitForTimeout(1000);
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 });
  await page.evaluate(() => {                                                   // the page is hidden: web-vitals reports the final INP
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  const inp = await page.evaluate(() => (window as unknown as { __inp: number[] }).__inp);
  expect(inp.length, 'web-vitals measured at least one interaction').toBeGreaterThan(0);
  expect(Math.max(...inp)).toBeLessThan(200);
});
