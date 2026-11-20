import { expect, test, request as pwRequest, type APIRequestContext, type BrowserContext, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/* The release journey (T8-06, brief section 5), shared by the phone test (e2e/release.spec.ts) and the side-panel test
   (tests/e2e/release-sidepanel.spec.ts). Everything a client does goes through the screens; staff steps that have no
   screen yet are "staff fixtures" through the staff API. Time is the fake clock: the server's (/e2e/clock, only in the
   test backend) and the browser's (Playwright's clock) move together. People are fictional. */

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const API = `http://127.0.0.1:${process.env.E2E_API_PORT || '8011'}`;
export const FAKES = `http://127.0.0.1:${process.env.E2E_FAKE_PORT || '8291'}`;
export const ADMIN = `http://127.0.0.1:${process.env.E2E_ADMIN_PORT || '5174'}`;
const PYTHON = process.env.PYTHON || 'python';
const STAFF = {
  attorney: { email: 'attorney-e2e@example.com', password: 'attorney-e2e-password' },
  paralegal: { email: 'paralegal-e2e@example.com', password: 'paralegal-e2e-password' },
};

/** The client's app: the web app on a phone, or the Chrome side panel. */
export interface ClientApp {
  page: Page;
  context: BrowserContext;
  go(hash: string): Promise<void>;
  token(): Promise<string>;
}

// --- the API, from the test (not the browser) ---

let api: APIRequestContext | null = null;
async function http() { return (api ??= await pwRequest.newContext({ baseURL: API })); }

async function call(method: string, url: string, token: string | null, data?: unknown) {
  const r = await (await http()).fetch(url, { method, data, headers: token ? { Authorization: `Bearer ${token}` } : {} });
  return { status: r.status(), body: await r.json().catch(() => null) };
}

const staffTokens: Record<string, string> = {};
export async function staff(who: keyof typeof STAFF) {
  if (!staffTokens[who]) staffTokens[who] = (await call('POST', '/auth/login', null, STAFF[who])).body.token;
  return staffTokens[who];
}
export const asStaff = async (who: keyof typeof STAFF, method: string, url: string, data?: unknown) =>
  call(method, url, await staff(who), data);
export const asClient = async (c: ClientApp, method: string, url: string, data?: unknown) =>
  call(method, url, await c.token(), data);

export async function journey(c: ClientApp) {
  const r = await asClient(c, 'GET', '/journey');
  expect(r.status).toBe(200);
  return r.body as { id: string; matter_id: string; facts: Record<string, string>; gates: Record<string, boolean>;
    conflict: string; documents: { tentative: string[]; confirmed: string[] }; timeline: PlanStep[]; day: number };
}

export async function modelCalls(): Promise<number> {
  return ((await (await (await http()).get(`${FAKES}/calls`)).json()) as unknown[]).length;
}

export function dbCounts(jid: string): Record<string, number> & { events: string[] } {
  const db = `/tmp/cl-e2e-${process.env.E2E_API_PORT || '8011'}.db`;
  return JSON.parse(execFileSync(PYTHON, [path.join(ROOT, 'scripts', 'e2e-db.py'), jid], { env: { ...process.env, CARBON_DB_PATH: db } }).toString());
}

// --- the fake clock ---

const LA = 'America/Los_Angeles';
const laParts = (d: Date) => Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: LA, year: 'numeric', month: '2-digit',
  day: '2-digit', hour: '2-digit', hourCycle: 'h23' }).formatToParts(d).map((p) => [p.type, p.value]));
export const laDate = (d: Date) => { const p = laParts(d); return `${p.year}-${p.month}-${p.day}`; };
export const addDays = (ymd: string, n: number) => new Date(Date.parse(`${ymd}T12:00:00Z`) + n * 86_400_000).toISOString().slice(0, 10);
/** 10:00 (or another hour) in Los Angeles on that date. */
export function laTime(ymd: string, hour = 10): Date {
  for (const off of ['-08:00', '-07:00']) {
    const d = new Date(`${ymd}T${String(hour).padStart(2, '0')}:00:00${off}`);
    if (Number(laParts(d).hour) === hour) return d;
  }
  throw new Error(`no ${hour}:00 in Los Angeles on ${ymd}`);
}

export async function serverNow(): Promise<Date> {
  return new Date((await call('GET', '/e2e/clock', null)).body.now);
}

/** The first date after the server's today that falls on this weekday (0 = Sunday … 3 = Wednesday). */
export async function nextWeekday(weekday: number): Promise<string> {
  let d = addDays(laDate(await serverNow()), 1);
  while (new Date(`${d}T12:00:00Z`).getUTCDay() !== weekday) d = addDays(d, 1);
  return d;
}

/** Move the server's clock and the browser's date to the same moment. The browser's timers stay real (a fake timer
 *  clock stalls the 3D characters); the app only needs the date, for example to show the right week of signing slots. */
export async function moveTo(c: ClientApp, when: Date) {
  const r = await call('POST', '/e2e/clock', null, { now: when.toISOString() });
  expect(r.status, 'the server clock moved').toBe(200);
  await c.context.clock.setFixedTime(when);
}

// --- the plan ---

export type PlanStep = { step: string; day: number; date: string; due: string | null; status: string };
export const byStep = (tl: PlanStep[]) => Object.fromEntries(tl.map((s) => [s.step, s]));

/** The step is done, today is the date the plan gave it, and no step of this journey is late for staff. */
export async function landsOnItsDay(c: ClientApp, step: string, planned: Record<string, PlanStep>) {
  const j = await journey(c);
  const now = byStep(j.timeline)[step];
  expect(now.status, `${step} is done`).toBe('done');
  expect(now.date, `${step} happened on its planned day ${planned[step].day}`).toBe(planned[step].date);
  expect(laDate(await serverNow()), `today is day ${planned[step].day}`).toBe(planned[step].date);
  const row = (await asStaff('paralegal', 'GET', `/staff/journeys/${j.id}`)).body;
  expect(row.late, 'staff see no late step').toEqual([]);
}

// --- lessons, from the content files (the server never sends answers) ---

type Key = { kind: string; answer?: number | boolean; options?: string[]; pairs?: [string, string][]; steps?: string[] };
let KEYS: Record<string, Key> | null = null;
function answerKey(): Record<string, Key> {
  KEYS ??= JSON.parse(execFileSync(PYTHON, ['-c', `
import glob, json, yaml
out = {}
for f in glob.glob(${JSON.stringify(path.join(ROOT, 'aprende', 'content', 'lessons', '*.yaml'))}):
    for step in yaml.safe_load(open(f, encoding="utf-8"))["steps"]:
        for it in step["items"]:
            es = it.get("es", {})
            out[it["id"]] = {"kind": it["kind"], "answer": it.get("answer"), "options": es.get("options"),
                             "pairs": es.get("pairs"), "steps": es.get("steps")}
print(json.dumps(out))`]).toString());
  return KEYS!;
}

/** Open the lesson from the map and answer every item correctly, through the lesson player. */
export async function takeLesson(c: ClientApp, lessonId: string) {
  const { page } = c;
  await c.go('/aprender');
  await page.locator(`a[href="#/leccion/${lessonId}"]`, { hasText: 'Empezar' }).click();
  const bar = page.getByLabel('Avance de la lección');
  const celebration = page.locator('.celebration');
  for (let i = 0; i < 120 && !(await celebration.isVisible()); i++) {
    await expect(bar.or(celebration).first()).toBeVisible();
    const before = await bar.getAttribute('value');
    const heading = page.locator('h1[id^="q-"]');
    if (await heading.count()) {
      const id = (await heading.getAttribute('id'))!.slice(2);
      const k = answerKey()[id];
      if (k.kind === 'truefalse') await page.getByRole('radio', { name: k.answer ? 'Cierto' : 'Falso', exact: true }).check();
      else if (k.kind === 'match') {
        const [left, right] = [page.locator('.match-col').nth(0), page.locator('.match-col').nth(1)];
        for (const [a, b] of k.pairs!) {
          await left.getByRole('button', { name: a, exact: true }).click();
          await right.getByRole('button', { name: b, exact: true }).click();
        }
      } else if (k.kind === 'order') {
        for (let s = 0; s < k.steps!.length; s++) {
          let at = (await page.locator('.order-text').allTextContents()).indexOf(k.steps![s]);
          for (; at > s; at--) await page.getByRole('button', { name: `Subir «${k.steps![s]}»` }).click();
        }
      } else await page.getByRole('radio', { name: k.options![k.answer as number], exact: true }).check();
      await page.getByRole('button', { name: 'Comprobar' }).click();
      await expect(page.locator('.feedback.correct'), `item ${id} answered correctly`).toBeVisible();
      await page.locator('.feedback').getByRole('button', { name: 'Continuar' }).click();
    } else {
      await page.getByRole('button', { name: 'Continuar' }).click();
    }
    await expect.poll(async () => (await celebration.isVisible()) || (await bar.getAttribute('value')) !== before,
      { timeout: 30_000 }).toBe(true);                                 // a new character loads in software rendering
  }
  await expect(celebration.getByRole('heading')).toHaveText(/Lección completada|Gracias por pensar en esto con calma/);
}

// --- "Tus datos", through the character chat (the fake model plays the character) ---

let QUESTIONS: Record<string, string> | null = null;
function questionIds(): Record<string, string> {
  QUESTIONS ??= JSON.parse(execFileSync(PYTHON, ['-c', `
import json, yaml
print(json.dumps({q["es"].strip(): q["id"] for q in yaml.safe_load(open(${JSON.stringify(path.join(ROOT, 'aprende', 'content', 'datos.yaml'))}, encoding="utf-8"))}))`]).toString());
  return QUESTIONS!;
}

/** Fictional answers; any other question Ana skips. */
export const ANSWERS: Record<string, string> = {
  nombre: 'Ana Torres', nacimiento: '3 de mayo de 1970', domicilio: 'Los Ángeles, condado de Los Ángeles, California',
  estado_civil: 'Casada con Luis Torres', hijos: 'Sofía Torres, 19 años, y Mateo Torres, 15 años',
  herederos: 'A mi esposo Luis Torres; si él falta, a Sofía y Mateo por partes iguales', tutor: 'Mi hermana Rosa Pérez',
  albacea: 'Mi esposo Luis Torres', fid_tipo: 'Conjunto, con mi esposo', fid_sucesor: 'Mi hija Sofía Torres',
  fid_bienes: 'Nuestra casa en Los Ángeles y la cuenta de ahorros', fid_menores: 'Que Mateo reciba su parte a los 25 años',
  bienes: 'La casa y una cuenta de ahorros', contacto: '(323) 555-0100, ana.torres@example.com',
};

export async function giveDatos(c: ClientApp, group: string) {
  const { page } = c;
  await c.go(`/datos/${group}`);
  const done = page.getByRole('heading', { name: '¡Listo! Ya tenemos sus respuestas de esta lección.' });
  for (let i = 0; i < 20; i++) {
    const lines = page.locator('.transcript li.them');
    await expect(lines.last().or(done).first()).toBeVisible();
    if (await done.isVisible()) return;
    const asked = (await lines.last().innerText()).trim();
    const qid = questionIds()[asked];
    expect(qid, `Ana can read the question she is asked (on screen: "${asked}")`).toBeDefined();
    const count = await lines.count();
    if (ANSWERS[qid]) {
      await page.getByLabel('Su respuesta').fill(ANSWERS[qid]);
      await page.getByRole('button', { name: 'Enviar' }).click();
    } else {
      await page.getByRole('button', { name: 'Saltar' }).click();
    }
    await expect.poll(async () => (await done.isVisible()) || (await lines.count()) > count).toBe(true);
  }
  throw new Error(`Tus datos (${group}) did not finish`);
}

// --- the attorney's review screen (web/admin.html), against the e2e backend ---

/** The staff admin calls the production API: forward those calls to the e2e backend (nothing is played back). */
export async function openAdminReview(context: BrowserContext): Promise<Page> {
  const page = await context.newPage();
  const token = await staff('attorney');
  const me = (await call('GET', '/auth/me', token)).body;
  await page.addInitScript(([t, u]) => { localStorage.setItem('carbon_token', t); localStorage.setItem('carbon_user', u); }, [token, JSON.stringify(me)] as const);
  await page.route('https://carbon-law.onrender.com/**', async (route) => {
    const url = route.request().url().replace('https://carbon-law.onrender.com', API);
    await route.fulfill({ response: await route.fetch({ url }) });
  });
  await page.goto(`${ADMIN}/admin.html#review`);
  return page;
}

/** In the review queue, the attorney opens the client's document, edits its text and uploads the revised version. */
export async function attorneyRevises(context: BrowserContext, clientName: string, addition: string) {
  const admin = await openAdminReview(context);
  await admin.getByRole('button', { name: clientName, exact: true }).click();
  const text = admin.getByLabel('Texto corregido');
  await expect(text).toHaveCount(1);                                    // only the document she asked to change
  await text.fill(`${await text.inputValue()}\n\n${addition}\n`);
  const saved = admin.waitForResponse((r) => r.url().includes('/versions') && r.request().method() === 'POST');
  await admin.getByRole('button', { name: 'Subir versión corregida' }).click();
  expect((await saved).status()).toBe(200);
  await admin.close();
}

export async function attorneyApproves(context: BrowserContext, clientName: string) {
  const admin = await openAdminReview(context);
  await admin.getByRole('button', { name: clientName, exact: true }).click();
  await expect(admin.locator('.draft').first()).toBeVisible();
  await expect(admin.locator('mark.complete')).toHaveCount(0);
  await admin.getByRole('button', { name: 'Aprobar' }).click();
  await expect(admin.getByRole('button', { name: clientName, exact: true })).toHaveCount(0);   // gone from the queue
  await admin.close();
}

// --- the whole journey ---

const b64 = (s: string) => Buffer.from(s).toString('base64');

export async function signUp(c: ClientApp, name: string) {
  const { page } = c;
  await c.go('/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill(name);
  await page.getByLabel(/Correo/i).fill(`${name.split(' ')[0].toLowerCase()}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
}

export async function disclosureAndConsent(c: ClientApp, answer: string) {
  const { page } = c;
  await expect(page.getByText('No soy el abogado ni una persona', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Entendido' }).click();
  await page.getByLabel('Su respuesta, con sus palabras').fill(answer);
  await page.getByRole('button', { name: 'Responder' }).click();
}

export async function giveNames(c: ClientApp, names: string[]) {
  const { page } = c;
  await expect(page.getByRole('heading', { name: '¿Quiénes son las personas de su familia?' })).toBeVisible();
  for (let i = 0; i < names.length; i++) {
    if (i) await page.getByRole('button', { name: 'Agregar otro nombre' }).click();
    await page.getByLabel(`Nombre completo ${i + 1}`).fill(names[i]);
  }
  await page.getByRole('button', { name: 'Continuar' }).click();
}

/** The whole release journey. `start` is day 1 (a date in Los Angeles). Returns the journey id. */
export async function releaseJourney(c: ClientApp, start: string, name = 'Ana Torres') {
  const { page } = c;
  const day = (n: number) => laTime(addDays(start, n - 1));
  let plan: Record<string, PlanStep> = {};
  let jid = '';

  await test.step('Day 1: Ana signs up, hears that the character is an AI, says yes to recording, and gives her family names', async () => {
    await moveTo(c, day(1));
    await signUp(c, name);
    await disclosureAndConsent(c, 'Sí, acepto');
    await giveNames(c, [name, 'Luis Torres', 'Sofía Torres', 'Mateo Torres']);
    await expect(page).toHaveURL(/#\/aprender/);                         // the automatic conflict check is clear
    const j = await journey(c);
    jid = j.id;
    expect(j.conflict).toBe('clear');
  });

  await test.step('Day 1: her plan shows every step with its date, about two weeks in all', async () => {
    plan = byStep((await journey(c)).timeline);
    expect([plan.lesson_will.day, plan.lesson_trust.day, plan.lesson_ahcd.day, plan.lesson_poa.day]).toEqual([1, 2, 3, 4]);
    expect(plan.final_lesson.day).toBe(14);                             // spec 6.3: a Wednesday or Thursday start, no changes
    await c.go('/plan');
    await expect(page.getByRole('heading', { name: 'Mi plan' })).toBeVisible();
    await expect(page.locator('.plan-step')).toHaveCount(Object.keys(plan).length);
  });

  await test.step('Day 1: Ana takes the will lesson and gives her details to La Calavera', async () => {
    await takeLesson(c, 'will');
    await giveDatos(c, 'will');
    await landsOnItsDay(c, 'lesson_will', plan);
  });

  await test.step('Day 2: the trust lesson, her trust details, and her choice of documents (a will and a trust)', async () => {
    await moveTo(c, day(2));
    await takeLesson(c, 'trust');
    await c.go('/documentos');
    await page.getByLabel('Testamento').check();
    await page.getByLabel('Fideicomiso en vida').check();
    await page.getByRole('button', { name: 'Guardar mi elección' }).click();
    await expect(page).toHaveURL(/#\/aprender/);
    await giveDatos(c, 'trust');
    await landsOnItsDay(c, 'lesson_trust', plan);
  });

  await test.step('Day 2: staff clear the conflict check (staff fixture), on its due date', async () => {
    expect((await asStaff('paralegal', 'POST', `/conflicts/${jid}/decision`, { result: 'cleared' })).status).toBe(200);
  });

  await test.step('Day 3: the health care directive lesson, in calm mode; the attorney approves the scope (staff fixture)', async () => {
    await moveTo(c, day(3));
    await takeLesson(c, 'ahcd');
    await expect(page.getByRole('heading', { name: 'Gracias por pensar en esto con calma.' })).toBeVisible();
    expect((await asStaff('attorney', 'POST', `/staff/journeys/${jid}/scope-approval`)).status).toBe(200);
    await landsOnItsDay(c, 'lesson_ahcd', plan);
  });

  await test.step('Day 4: the power of attorney lesson, her summary, the last questions, and she confirms her documents', async () => {
    await moveTo(c, day(4));
    await takeLesson(c, 'poa');
    await c.go('/resumen');
    await expect(page.getByRole('heading', { name: 'Su resumen' })).toBeVisible();
    await page.getByRole('button', { name: 'Completar con La Calavera' }).click();
    await giveDatos(c, 'resumen');
    await c.go('/resumen');
    await page.getByRole('button', { name: 'Confirmar mis documentos' }).click();
    await expect(page.getByText('Documentos confirmados', { exact: false })).toBeVisible();
    const j = await journey(c);
    expect([...j.documents.confirmed].sort()).toEqual(['trust', 'will']);
    expect(Object.keys(j.facts)).toContain('intake_completed');
    expect(Object.keys(j.facts)).not.toContain('scope_reopened');      // the same two documents the attorney approved
    await landsOnItsDay(c, 'lesson_poa', plan);
  });

  await test.step(`Day ${plan.pay?.day ?? 5}: Ana reads and signs the engagement letter; the attorney countersigns; she downloads her copy`, async () => {
    await moveTo(c, day(plan.pay.day));
    await c.go('/acuerdo');
    await expect(page.getByRole('heading', { name: 'Su acuerdo con la oficina' })).toBeVisible();
    await expect(page.locator('.letter')).toContainText(name);
    await expect(page.locator('.letter')).toContainText('Fideicomiso en vida');
    await page.getByLabel('Escriba su nombre completo').fill(name);
    await page.getByLabel('Leí este acuerdo y lo acepto').check();
    await page.getByRole('button', { name: 'Firmar' }).click();
    await expect(page.getByText('Usted firmó el acuerdo', { exact: false })).toBeVisible();
    expect((await asStaff('attorney', 'POST', `/staff/journeys/${jid}/engagement/countersign`)).status).toBe(200);
    await page.reload();
    await expect(page.getByText('Firmado por usted y por el abogado Raval.')).toBeVisible();
    const pdf = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Descargar mi copia (PDF)' }).click();
    expect((await pdf).suggestedFilename()).toMatch(/\.pdf$/);
  });

  await test.step(`Day ${plan.pay?.day ?? 5}: Ana pays in Stripe test mode; the signed webhook, not the browser, records the payment`, async () => {
    await page.getByRole('button', { name: 'Ir a pagar' }).click();
    await expect(page.getByText('Modo de prueba: no se cobra nada.')).toBeVisible();
    await page.getByRole('button', { name: 'Pagar con Stripe' }).click();
    await expect(page.getByRole('heading', { name: 'Stripe: pago de prueba' })).toBeVisible();
    await page.getByRole('button', { name: 'Pagar (prueba)' }).click();
    await expect(page.getByText('¡Pago recibido!', { exact: false })).toBeVisible();
    expect(dbCounts(jid).payments).toBe(1);
    await landsOnItsDay(c, 'pay', plan);
  });

  await test.step('Days 6 to 8: drafts reach the attorney queue, and Ana sees none of them', async () => {
    const matter = (await journey(c)).matter_id;
    const attorneyId = (await call('GET', '/auth/me', await staff('attorney'))).body.id;
    expect((await asStaff('paralegal', 'PATCH', `/matters/${matter}`, { attorney_reviewer: attorneyId })).status).toBe(200);
    await expect.poll(async () => ((await asStaff('attorney', 'GET', '/staff/review-queue')).body as { journey_id: string }[])
      .some((r) => r.journey_id === jid), { timeout: 60_000 }).toBe(true);
    const row = ((await asStaff('attorney', 'GET', '/staff/review-queue')).body as { journey_id: string; due: string; late: boolean;
      documents: { name: string }[] }[]).find((r) => r.journey_id === jid)!;
    expect(row.documents.map((d) => d.name).sort()).toEqual(['Pour-over will', 'Revocable living trust']);
    expect(row.due).toBe(plan.attorney_review.due);
    expect(row.late).toBe(false);
    for (const d of [6, 7].filter((n) => n < plan.attorney_review.day)) {
      await moveTo(c, day(d));
      await c.go('/revisar');
      await expect(page.getByText('Sus documentos aparecerán aquí cuando el abogado Raval los apruebe.')).toBeVisible();
      expect((await asClient(c, 'GET', '/review/documents')).status).toBe(409);
      expect((await asClient(c, 'GET', '/documents')).body).toEqual([]);
    }
  });

  await test.step(`Day ${plan.attorney_review?.day ?? 8}: the attorney reads the drafts in the staff admin and approves them, on the due date`, async () => {
    await moveTo(c, day(plan.attorney_review.day));
    await attorneyApproves(c.context, name);
    await landsOnItsDay(c, 'attorney_review', plan);
  });

  await test.step(`Day ${plan.client_review?.day ?? 9}: Ana reviews her documents: the trust is fine, and she asks one change to the will`, async () => {
    await moveTo(c, day(plan.client_review.day));
    await c.go('/revisar');
    await expect(page.getByRole('heading', { name: 'Revise sus documentos' })).toBeVisible();
    const trust = page.getByRole('region', { name: 'Revocable living trust' });
    await trust.getByRole('button', { name: 'Está bien' }).click();
    await expect(trust.getByText('Usted dijo que está bien.')).toBeVisible();
    const will = page.getByRole('region', { name: 'Pour-over will' });
    await will.getByRole('button', { name: 'Quiero un cambio' }).click();
    await will.getByLabel('¿Qué quiere cambiar?').selectOption({ label: 'Quién está a cargo (albacea, fiduciario, agente)' });
    await will.getByLabel('Cuéntenos el cambio con sus palabras').fill('Quiero que mi hija Sofía sea la albacea suplente.');
    await will.getByRole('button', { name: 'Enviar el cambio al abogado' }).click();
    await expect(will.getByText('Pidió un cambio.', { exact: false })).toBeVisible();
  });

  await test.step('The plan now has the change: the attorney has 2 business days, and the journey ends on day 16', async () => {
    plan = { ...plan, ...byStep((await journey(c)).timeline) };
    expect(plan.changes.status).toBe('done');
    expect(plan.final_lesson.day).toBe(16);                             // spec 6.3: one change adds two days
  });

  const revised = byStep((await journey(c)).timeline).changes;
  await test.step(`Day ${revised ? revised.day - 1 : 13}: the attorney finds the change in his queue, uploads the revised will and approves it again, on the due date`, async () => {
    await moveTo(c, laTime(plan.changes.due!));
    await attorneyRevises(c.context, name, 'Alternate executor: Sofía Torres.');
    await attorneyApproves(c.context, name);
  });

  await test.step(`Day ${plan.changes?.day ?? 14}: Ana reads the revised will and says it is fine`, async () => {
    await moveTo(c, day(plan.changes.day));
    await c.go('/revisar');
    const will = page.getByRole('region', { name: 'Pour-over will' });
    await will.getByText('Ver el documento completo').click();
    await expect(will.getByText('Alternate executor: Sofía Torres.', { exact: false })).toBeVisible();
    await will.getByRole('button', { name: 'Está bien' }).click();
    await expect(page.getByText('¡Listo! Ya puede reservar su cita de firma.')).toBeVisible();
    await landsOnItsDay(c, 'client_review', plan);
  });

  await test.step(`Day ${plan.changes?.day ?? 14}: staff set office hours (fixture) and Ana books her signing for day ${plan.signing?.day ?? 15}`, async () => {
    const weekdays = Object.fromEntries(['mon', 'tue', 'wed', 'thu', 'fri'].map((d) => [d, [['09:00', '17:00']]]));
    expect((await asStaff('paralegal', 'PUT', '/staff/availability', { hours: weekdays, slot_minutes: { signing: 60, consultation: 30 } })).status).toBe(200);
    await page.getByRole('button', { name: 'Reservar la firma' }).click();
    await expect(page.getByRole('heading', { name: 'Su cita' })).toBeVisible();
    const signingDay = new Intl.DateTimeFormat('es', { weekday: 'long', day: 'numeric', month: 'long', timeZone: LA }).format(day(plan.signing.day));
    const slots = page.locator('.slot-day').filter({ has: page.getByRole('heading', { name: signingDay }) });
    await slots.getByRole('button', { name: /^10:00/ }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Sí, reservar' }).click();
    await expect(page.getByText(`Su cita: ${signingDay}`, { exact: false })).toBeVisible();
    expect(Object.keys((await journey(c)).facts)).toContain('signing_booked');
  });

  await test.step(`Day ${plan.signing?.day ?? 15}: the signing; staff record it by uploading the signed documents (fixture); Ana downloads them`, async () => {
    await moveTo(c, day(plan.signing.day));
    const pdf = b64('%PDF-1.4\n% signed copy, test only\n');
    expect((await asStaff('paralegal', 'POST', `/staff/journeys/${jid}/executed`, { documents: [
      { name: 'Pour-over will', filename: 'testamento-firmado.pdf', content_b64: pdf },
      { name: 'Revocable living trust', filename: 'fideicomiso-firmado.pdf', content_b64: pdf }] })).status).toBe(200);
    await c.go('/firmados');
    await expect(page.getByRole('heading', { name: 'Sus documentos firmados' })).toBeVisible();
    const dl = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Descargar Pour-over will' }).click();
    expect((await dl).suggestedFilename()).toMatch(/\.pdf$/);
    await landsOnItsDay(c, 'signing', plan);
  });

  await test.step(`Day ${plan.final_lesson?.day ?? 16}: the final lesson is open, and Ana finishes it`, async () => {
    await moveTo(c, day(plan.final_lesson.day));
    await takeLesson(c, 'final');
    await landsOnItsDay(c, 'final_lesson', plan);
  });

  await test.step('Every step landed on the day the plan showed, and no staff alert was raised', async () => {
    const end = byStep((await journey(c)).timeline);
    for (const [step, s] of Object.entries(plan)) {
      expect(end[step].date, step).toBe(s.date);
      expect(end[step].status, step).toBe('done');
    }
    expect(dbCounts(jid).timeline_alerts).toBe(0);
  });
  return jid;
}
