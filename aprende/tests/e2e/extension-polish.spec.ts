import { test, expect, chromium, type BrowserContext, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

// T8-01 acceptance (Opus, p8-tests): side panel and popup polish. Needs `npm run build:ext`.
// The API is played back (the popup and the panel only read it); the rules behind it are proven in pytest.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const EXT_PATH = path.resolve(__dirname, '../../dist/extension');
const EXECUTABLE = process.env.PW_CHROMIUM;

const lesson = (id: string, day: number | null, unit: string, es: string, en: string, status: string) =>
  ({ id, day, character: unit === 'poa' ? 'oso' : unit === 'trust' ? 'pinata' : 'calavera', title: { es, en }, status, unlock_at: null, unit });
const MAP = { units: [
  { id: 'will', lessons: [lesson('will', 1, 'will', 'El testamento', 'The will', 'available')] },
  { id: 'trust', lessons: [lesson('trust', 2, 'trust', 'El fideicomiso en vida', 'The living trust', 'locked')] },
  { id: 'ahcd', lessons: [lesson('ahcd', 3, 'ahcd', 'Sus decisiones de salud', 'Your health care decisions', 'locked')] },
  { id: 'poa', lessons: [lesson('poa', 4, 'poa', 'El poder para finanzas', 'The financial power of attorney', 'locked')] },
  { id: 'final', lessons: [lesson('final', null, 'final', 'Cuide sus documentos', 'Look after your documents', 'locked')] },
] };
const GATES_AFTER_DAY1 = { may_disclose: true, may_consent: true, may_name: true, may_collect_details: true, may_chat: true,
  may_sign_engagement: false, may_pay: false, may_see_documents: false, may_book_signing: false, may_take_final_lesson: false };
const JOURNEY = { id: 'j1', user_id: 'u1', day: 1, facts: { ai_disclosed: 'x', consent: 'x', names_submitted: 'x' }, gates: GATES_AFTER_DAY1,
  conflict: 'clear', documents: { tentative: [], confirmed: [] }, timeline: [] };
const PROGRESS = { petals: 120, level: { name_key: 'level.aprendiz', next_at: 300 }, streak: { count: 5, rested_this_week: false },
  seals: [], reminders: { enabled: false, local_time: null } };
const QUOTE = { items: [{ code: 'will', base: 300000, discounts: [], price: 300000, placeholder: true }], total: 300000, currency: 'usd', test_mode: true };

async function launch(): Promise<{ context: BrowserContext; extId: string }> {
  const context = await chromium.launchPersistentContext('', {
    headless: false,
    ...(EXECUTABLE ? { executablePath: EXECUTABLE } : {}),
    args: ['--headless=new', `--disable-extensions-except=${EXT_PATH}`, `--load-extension=${EXT_PATH}`],
  });
  const sw = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
  return { context, extId: new URL(sw.url()).host };
}

/** The API the panel and the popup read, played back (relative or absolute API origin alike). */
async function playBack(context: BrowserContext, journey: object = JOURNEY) {
  const answers: Record<string, object> = {
    'settings/public': { switches: { ai_chat: true, voice_recording: true, extension: true } },
    journey, 'learn/map': MAP, progress: PROGRESS, 'payments/quote': QUOTE,
  };
  await context.route(/\/(settings\/public|journey|learn\/map|progress|payments\/quote)(\?.*)?$/, (r) => {
    const p = new URL(r.request().url()).pathname.replace(/^\//, '').replace(/^.*?(settings\/public|journey|learn\/map|progress|payments\/quote)$/, '$1');
    return r.fulfill({ json: answers[p] });
  });
}

async function signIn(page: Page, extId: string) {
  await page.goto(`chrome-extension://${extId}/popup.html`);
  await page.evaluate(async () => { await chrome.storage.session.set({ aprende_token: 'tok-ana' }); });
}

for (const size of [{ width: 360, height: 640 }, { width: 320, height: 640 }]) {
  test(`side panel at ${size.width}×${size.height}: today's lesson is above the fold`, async () => {
    const { context, extId } = await launch();
    await playBack(context);
    const page = await context.newPage();
    await page.setViewportSize(size);
    await signIn(page, extId);
    await page.goto(`chrome-extension://${extId}/sidepanel.html#/aprender`);
    const start = page.getByRole('link', { name: 'Empezar' });
    await expect(start).toBeVisible();
    await expect(page.locator('.bubble')).toContainText('El testamento');        // the host still says what today is
    const box = (await start.boundingBox())!;
    const tabs = (await page.locator('nav.tabs').boundingBox())!;
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.y + box.height).toBeLessThanOrEqual(tabs.y);                      // not under the bottom tabs, no scrolling
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width);   // no sideways scroll
    await context.close();
  });
}

test('the popup has no character stage: no canvas, and no three.js in its bundle', async () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(EXT_PATH, '.vite/manifest.json'), 'utf8')) as
    Record<string, { file: string; imports?: string[]; isEntry?: boolean }>;
  const key = Object.keys(manifest).find((k) => manifest[k].isEntry && k.endsWith('popup.html'))!;
  expect(key).toBeTruthy();
  const seen = new Set<string>();
  const walk = (k: string) => { if (seen.has(k)) return; seen.add(k); for (const i of manifest[k].imports ?? []) walk(i); };
  walk(key);                                                                     // static imports only: what the popup loads
  for (const k of seen) {
    const src = fs.readFileSync(path.join(EXT_PATH, manifest[k].file), 'utf8');
    expect(src, manifest[k].file).not.toContain('WebGLRenderer');
  }
  const { context, extId } = await launch();
  await playBack(context);
  const page = await context.newPage();
  await signIn(page, extId);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Abrir' })).toBeVisible();
  await expect(page.locator('canvas')).toHaveCount(0);
  await context.close();
});

test('the popup shows her real streak and today\'s lesson, in Spanish and in English', async () => {
  const { context, extId } = await launch();
  await playBack(context);
  const page = await context.newPage();
  await signIn(page, extId);
  await page.reload();
  await expect(page.getByText('Racha: 5')).toBeVisible();                     // from GET /progress, not a fixed 0
  await expect(page.getByText('Día 1 de 14')).toBeVisible();
  await expect(page.getByText('El testamento')).toBeVisible();                 // the day-1 gate is done: today is the lesson
  await page.evaluate(() => localStorage.setItem('aprende_lang', 'en'));
  await page.reload();
  await expect(page.getByText('Streak: 5')).toBeVisible();
  await expect(page.getByText('The will')).toBeVisible();
  await context.close();
});

test('before the day-1 gate is done, the popup still names the gate step', async () => {
  const { context, extId } = await launch();
  await playBack(context, { ...JOURNEY, facts: { ai_disclosed: 'x' }, gates: { ...GATES_AFTER_DAY1, may_consent: false, may_name: false,
    may_collect_details: false, may_chat: false } });
  const page = await context.newPage();
  await signIn(page, extId);
  await page.reload();
  await expect(page.getByText('Dar su consentimiento')).toBeVisible();
  await expect(page.getByText('El testamento')).toHaveCount(0);
  await context.close();
});

test('signed out, the popup asks her to sign in from the panel and shows no made-up day', async () => {
  const { context, extId } = await launch();
  await playBack(context);
  const page = await context.newPage();
  await page.goto(`chrome-extension://${extId}/popup.html`);
  await expect(page.getByText('Inicie sesión en el panel para ver su día.')).toBeVisible();
  await expect(page.getByText(/Día \d+ de 14/)).toHaveCount(0);
  await expect(page.getByText(/Racha/)).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Abrir' })).toBeVisible();      // "Abrir" opens the panel to sign in
  await context.close();
});

test('the popup and the side panel map have no axe violations', async () => {
  const { context, extId } = await launch();
  await playBack(context);
  const page = await context.newPage();
  await signIn(page, extId);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Abrir' })).toBeVisible();
  const popup = await new AxeBuilder({ page }).analyze();
  expect(popup.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
  await page.setViewportSize({ width: 360, height: 640 });
  await page.goto(`chrome-extension://${extId}/sidepanel.html#/aprender`);
  await expect(page.getByRole('link', { name: 'Empezar' })).toBeVisible();
  const panel = await new AxeBuilder({ page }).analyze();
  expect(panel.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
  await context.close();
});

test('no extension page asks for the microphone (F-003: typed answers and the browser voice)', async () => {
  const { context, extId } = await launch();
  await playBack(context);
  await context.addInitScript(() => {
    (window as unknown as { __mic: number }).__mic = 0;
    if (navigator.mediaDevices) navigator.mediaDevices.getUserMedia = async () => { (window as unknown as { __mic: number }).__mic += 1; throw new Error('no'); };
  });
  const page = await context.newPage();
  await signIn(page, extId);
  await page.reload();
  await expect(page.getByRole('button', { name: 'Abrir' })).toBeVisible();
  expect(await page.evaluate(() => (window as unknown as { __mic: number }).__mic)).toBe(0);
  await page.goto(`chrome-extension://${extId}/sidepanel.html#/aprender`);
  await expect(page.getByRole('link', { name: 'Empezar' })).toBeVisible();
  expect(await page.evaluate(() => (window as unknown as { __mic: number }).__mic)).toBe(0);
  await context.close();
});
