import { test, expect, type Page, type TestInfo } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// T8-04 acceptance (Opus, p8-tests): axe on every screen state, in Spanish and in English, with zero violations; and
// reflow at 320 px and at 200 % text without loss of content. Real backend where the state is cheap to reach; the
// server's answers played back (the shapes the screens' own specs use) where it is not. Screenshots of every state go to
// the test's output folder for the reviewer. A new screen or state is added to STATES; none is ever removed or skipped.
const ATTORNEY = { email: 'attorney-e2e@example.com', password: 'attorney-e2e-password' };   // scripts/seed-e2e-content.py
type Lang = 'es' | 'en';
type State = { name: string; path: string; signedIn?: boolean; prep?: (page: Page, lang: Lang) => Promise<void>; act?: (page: Page, lang: Lang) => Promise<void> };

async function signUp(page: Page) {
  await page.goto('/#/bienvenida');
  await page.evaluate(async () => {
    const r = await fetch('/auth/signup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      name: 'Ana Torres', email: `ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`,
      password: 'long-secure-password', source: 'aprende', adult: true }) });
    localStorage.setItem('aprende_token', (await r.json()).token);
  });
}

/** The client's own journey events, and the attorney's steps, through the real API. */
async function steps(page: Page, list: string[]) {
  await page.evaluate(async ([s, att]) => {
    const tok = localStorage.getItem('aprende_token');
    const json = (t: string | null) => ({ Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' });
    const me = (type: string, payload: object = {}) => fetch('/journey/events', { method: 'POST', headers: json(tok), body: JSON.stringify({ type, payload }) });
    for (const step of s as string[]) {
      if (step === 'disclosed') await me('ai_disclosed');
      if (step === 'consent_yes') await me('consent', { answer: 'yes' });
      if (step === 'consent_no') await me('consent', { answer: 'no' });
      if (step === 'names_clear') await me('names_submitted', { names: ['Ana Torres'] });
      if (step === 'names_hold') await me('names_submitted', { names: ['Ana Torres', 'Roberto Méndez'] });
      if (step === 'tentative') await me('documents_tentative', { codes: ['will'] });
      if (step === 'answers') {
        await fetch('/datos/nombre', { method: 'PUT', headers: json(tok), body: JSON.stringify({ answer: 'Ana Torres' }) });
        await fetch('/datos/nacimiento', { method: 'PUT', headers: json(tok), body: JSON.stringify({ skipped: true }) });
      }
      if (step === 'scope') {
        const a = (await (await fetch('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(att) })).json()).token;
        const jid = (await (await fetch('/journey', { headers: json(tok) })).json()).id;
        await fetch(`/conflicts/${jid}/decision`, { method: 'POST', headers: json(a), body: JSON.stringify({ result: 'cleared' }) });
        await me('documents_confirmed', { codes: ['will'] });
        await fetch(`/staff/journeys/${jid}/scope-approval`, { method: 'POST', headers: json(a) });
      }
    }
  }, [list, ATTORNEY] as const);
}
const cleared = (page: Page) => steps(page, ['disclosed', 'consent_yes', 'names_clear']);
const btn = (page: Page, es: string, en: string, lang: Lang) => page.getByRole('button', { name: lang === 'es' ? es : en, exact: true });

const SLOTS = [{ start: '2027-03-16T16:00:00Z', local: '2027-03-16T09:00:00' }, { start: '2027-03-16T16:30:00Z', local: '2027-03-16T09:30:00' }];
const REVIEW_DOC = (id: string, name: string) => ({ id, name, version: 1, decision: null, content: '# LAST WILL\n\n## ARTICLE ONE\n\nDeclarations.',
  summary: [{ article: 1, text: 'Quién es usted, dónde vive y quiénes son su familia.' }] });
const playJourney = (page: Page, edit: (j: Record<string, any>) => void) => page.route(/\/journey$/, async (r) => {   // eslint-disable-line @typescript-eslint/no-explicit-any
  const j = await (await r.fetch()).json();
  edit(j);
  await r.fulfill({ json: j });
});

const STATES: State[] = [
  { name: 'bienvenida', path: '/bienvenida', signedIn: false },
  { name: 'cuenta-nueva', path: '/cuenta-nueva', signedIn: false },
  { name: 'entrar', path: '/entrar', signedIn: false },
  { name: 'entrar, wrong password', path: '/entrar', signedIn: false, act: async (page) => {
    await page.locator('input[type="email"]').fill('nadie@example.com');
    await page.locator('input[type="password"]').fill('not-the-password');
    await page.locator('form button[type="submit"], form button').first().click();
    await expect(page.getByRole('alert')).toBeVisible();
  } },
  { name: 'gate: AI disclosure', path: '/inicio/ia' },
  { name: 'gate: consent', path: '/inicio/consentimiento', prep: (p) => steps(p, ['disclosed']) },
  { name: 'gate: refused', path: '/inicio/no-acepto', prep: (p) => steps(p, ['disclosed', 'consent_no']) },
  { name: 'gate: names', path: '/inicio/nombres', prep: (p) => steps(p, ['disclosed', 'consent_yes']) },
  { name: 'gate: waiting (possible conflict looks like any wait)', path: '/inicio/espera', prep: (p) => steps(p, ['disclosed', 'consent_yes', 'names_hold']) },
  { name: 'map', path: '/aprender', prep: cleared },
  { name: 'lesson: explanation', path: '/leccion/will', prep: cleared },
  { name: 'lesson: question with feedback', path: '/leccion/will', prep: cleared, act: async (page, lang) => {
    for (let i = 0; i < 4; i++) await btn(page, 'Continuar', 'Continue', lang).click();
    await page.getByRole('radio').first().check();
    await btn(page, 'Comprobar', 'Check', lang).click();
    await expect(page.locator('.feedback')).toBeVisible();
  } },
  { name: 'lesson: locked', path: '/leccion/trust', prep: cleared },
  { name: 'Mi plan', path: '/plan', prep: cleared },
  { name: 'Preguntas: none yet', path: '/preguntas', prep: cleared },
  { name: 'Preguntas: an answer and a wait', path: '/preguntas', prep: async (page) => {
    await cleared(page);
    await page.route('**/journey/questions', (r) => r.fulfill({ json: { questions: [
      { id: 'q2', question: '¿Quién cuida a Mateo si me pasa algo?', created_at: '2026-11-19T18:00:00', answer: null, answered_at: null },
      { id: 'q1', question: '¿Mi hijo puede ser albacea?', created_at: '2026-11-18T18:00:00', answer: 'Sí, lo vemos en su cita.', answered_at: '2026-11-19T19:00:00' }] } }));
  } },
  { name: 'Perfil', path: '/perfil', prep: cleared },
  { name: 'Tus datos (intake chat)', path: '/datos/poa', prep: async (page) => {
    await cleared(page);
    await page.route('**/chat', (r) => r.fulfill({ json: { text: '¿A quién quiere nombrar como apoderado?', history: '', reasoning: null,
      covered: [], open: [], docs: [], attorney_question: false, next_question: { id: 'poder_agente', text: '' } } }));
  } },
  { name: 'document choice', path: '/documentos', prep: cleared },
  { name: 'summary', path: '/resumen', prep: (p) => steps(p, ['disclosed', 'consent_yes', 'names_clear', 'tentative', 'answers']) },
  { name: 'agreement: not ready yet', path: '/acuerdo', prep: cleared },
  { name: 'agreement: ready to sign', path: '/acuerdo', prep: (p) => steps(p, ['disclosed', 'consent_yes', 'names_clear', 'scope']) },
  { name: 'payment', path: '/pago', prep: async (page) => {
    await cleared(page);
    await playJourney(page, (j) => { j.gates.may_pay = true; j.documents.confirmed = ['will']; });
  } },
  { name: 'payment: waiting for Stripe', path: '/pago/listo?session_id=cs_test_1', prep: async (page) => {
    await cleared(page);
    await page.route('**/payments/return**', (r) => r.fulfill({ json: { paid: false } }));
  } },
  { name: 'client review', path: '/revisar', prep: async (page) => {
    await cleared(page);
    await page.route('**/review/documents?*', (r) => r.fulfill({ json: { documents: [REVIEW_DOC('d1', 'Last will and testament'), REVIEW_DOC('d2', 'Advance health care directive')] } }));
  } },
  { name: 'appointment: times', path: '/cita?kind=consultation', prep: async (page) => {
    await cleared(page);
    await page.route('**/booking/slots**', (r) => r.fulfill({ json: { slots: SLOTS } }));
    await page.route(/\/booking$/, (r) => r.fulfill({ json: [] }));
  } },
  { name: 'appointment: confirm dialog', path: '/cita?kind=consultation', prep: async (page) => {
    await cleared(page);
    await page.route('**/booking/slots**', (r) => r.fulfill({ json: { slots: SLOTS } }));
    await page.route(/\/booking$/, (r) => r.fulfill({ json: [] }));
  }, act: async (page) => {
    await page.getByRole('button', { name: /9:00/ }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
  } },
  { name: 'appointment: signing locked', path: '/cita?kind=signing', prep: async (page) => {
    await cleared(page);
    await page.route('**/booking/slots**', (r) => r.fulfill({ status: 409, json: { error: 'gate', missing: ['may_book_signing'] } }));
    await page.route(/\/booking$/, (r) => r.fulfill({ json: [] }));
  } },
  { name: 'signed documents', path: '/firmados', prep: async (page) => {
    await cleared(page);
    await page.route('**/signed-documents', (r) => r.fulfill({ json: [{ id: 'Qx7k2pL9aa', name: 'Pour-over will', filename: 'will-signed.pdf', url: '/signed-documents/Qx7k2pL9aa' }] }));
    await page.route('**/funding-checklist', (r) => r.fulfill({ body: '# Trust Funding Checklist', contentType: 'text/markdown' }));
  } },
  { name: 'signed documents: none yet', path: '/firmados', prep: async (page) => {
    await cleared(page);
    await page.route('**/signed-documents', (r) => r.fulfill({ json: [] }));
    await page.route('**/funding-checklist', (r) => r.fulfill({ status: 409, json: { error: 'not_signed' } }));
  } },
  { name: 'not available', path: '/aprender', prep: async (page) => {
    await cleared(page);
    await page.route(/\/(journey|learn\/map|progress|payments\/quote)(\?.*)?$/, (r) => r.fulfill({ status: 503, json: { error: 'extension_off' } }));
  } },
];

async function open(page: Page, s: State, lang: Lang) {
  await page.addInitScript((l) => localStorage.setItem('aprende_lang', l), lang);
  if (s.signedIn !== false) await signUp(page);
  await s.prep?.(page, lang);
  await page.goto('/#' + s.path);
  await expect(page.locator('html')).toHaveAttribute('lang', lang);
  await page.locator('h1').first().waitFor({ timeout: 15000 }).catch(() => undefined);   // axe reports a missing h1 itself
  await page.waitForLoadState('networkidle');
  await s.act?.(page, lang);
}

async function axeClean(page: Page) {
  const axe = await new AxeBuilder({ page }).exclude('canvas').analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
}

/** WCAG 1.4.10 / 1.4.4: nothing scrolls sideways and no visible text sits outside the viewport. */
async function reflows(page: Page) {
  const out = await page.evaluate(() => {
    const w = document.documentElement.clientWidth;
    const bad: string[] = [];
    for (const el of document.querySelectorAll<HTMLElement>('h1, h2, h3, p, li, label, a, button, input, select, textarea, dt, dd, th, td, figcaption')) {
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height || getComputedStyle(el).visibility === 'hidden' || el.closest('.visually-hidden')) continue;
      if (r.left < -1 || r.right > w + 1) bad.push(`${el.tagName.toLowerCase()}.${el.className}: ${Math.round(r.left)}–${Math.round(r.right)} > ${w}`);
    }
    return { scroll: document.documentElement.scrollWidth, w, bad: bad.slice(0, 8) };
  });
  expect(out.bad).toEqual([]);
  expect(out.scroll).toBeLessThanOrEqual(out.w);
}

const shot = (page: Page, info: TestInfo, name: string) =>
  page.screenshot({ path: info.outputPath(`${name.replace(/[^a-z0-9]+/gi, '-')}.png`), fullPage: true });

test('index.html opts into the phone\'s text size (meta text-scale) and sets no root font size', async ({ page }) => {
  await page.goto('/#/bienvenida');
  await expect(page.locator('meta[name="text-scale"]')).toHaveAttribute('content', 'scale');
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).fontSize)).toBe('16px');
});

for (const lang of ['es', 'en'] as const) {
  for (const s of STATES) {
    test(`axe (${lang}): ${s.name}`, async ({ page }, info) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await open(page, s, lang);
      await axeClean(page);
      await shot(page, info, `${lang}-${s.name}`);
    });
  }
}

const REFLOW = ['bienvenida', 'cuenta-nueva', 'gate: names', 'map', 'lesson: question with feedback', 'Mi plan', 'Perfil', 'summary',
  'agreement: ready to sign', 'payment', 'appointment: times', 'signed documents'];
for (const name of REFLOW) {
  const s = STATES.find((x) => x.name === name)!;
  test(`reflow at 320 px: ${name}`, async ({ page }, info) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await open(page, s, 'es');
    await reflows(page);
    await shot(page, info, `320-${name}`);
  });
  test(`200 % text: ${name}`, async ({ page, context }, info) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const cdp = await context.newCDPSession(page);
    await cdp.send('Page.setFontSizes', { fontSizes: { standard: 32, fixed: 26 } });   // the browser's text size at 200 %
    await open(page, s, 'es');
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).fontSize)).toBe('32px');   // the emulation took
    await reflows(page);
    await shot(page, info, `200-${name}`);
  });
}
