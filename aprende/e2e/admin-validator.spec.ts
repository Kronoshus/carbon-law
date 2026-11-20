import { test, expect, type Page, type Request } from '@playwright/test';

// T7-02 acceptance (Opus, t7-tests): validator errors in web/admin.html#contenido (docs/tickets/T7-02.md).
// The API is played back, like admin-content.spec.ts; pytest proves the server refuses invalid versions.
const ADMIN = `http://127.0.0.1:${process.env.E2E_ADMIN_PORT || '5174'}`;
const PARALEGAL = { id: 'par', role: 'paralegal', name: 'Rosa Paralegal', email: 'p@example.com' };
const ATTORNEY = { id: 'att', role: 'attorney', name: 'Pankaj Raval', email: 'a@example.com' };
const REASON = 'No se puede enviar ni publicar mientras haya errores.';

const choice = (answer: number) => ({ answer, source: 'pc-6110',
  es: { prompt: '¿Cuántos testigos?', options: ['Ninguno', 'Uno', 'Dos'], explain: 'Dos testigos.' },
  en: { prompt: 'How many witnesses?', options: ['None', 'One', 'Two'], explain: 'Two witnesses.' } });
const version = (v: number, state: string, body: unknown, errors: string[]) => ({ version: v, state, body, errors,
  created_by: 'p@example.com', created_at: '2026-11-20T10:00:00+00:00', submitted_by: null, submitted_at: null,
  approved_by: null, approved_at: null, published_by: null, published_at: null });

async function open(page: Page, user: typeof PARALEGAL, id: string, legal: boolean, pending: { version: number; state: string }, detail: unknown) {
  await page.addInitScript((u) => { localStorage.setItem('carbon_token', 'tok'); localStorage.setItem('carbon_user', JSON.stringify(u)); }, user);
  await page.route('https://carbon-law.onrender.com/**', (r) => r.fulfill({ json: [] }));
  await page.route('**/auth/me', (r) => r.fulfill({ json: user }));
  await page.route(/\/staff\/content\?kind=item$/, (r) => r.fulfill({ json: { entries: [{ entry_id: id, kind: 'item', lesson_id: 'will',
    legal, live_version: 1, pending }] } }));
  const esc = id.replace(/\./g, '\\.');
  await page.route(new RegExp(`/staff/content/${esc}$`), (r) => r.fulfill({ json: detail }));
  const calls: Request[] = [];
  await page.route(new RegExp(`/staff/content/${esc}/(submit|approve|publish)$`), (r) => { calls.push(r.request()); return r.fulfill({ json: {} }); });
  await page.goto(`${ADMIN}/admin.html#contenido`);
  await page.getByRole('button', { name: new RegExp('^' + esc) }).click();
  return calls;
}

const ERR = ['will.1.2: answer out of range 5', 'will.1.2: unknown source nope'];

test("the validator's errors appear beside the item and sending is disabled with the reason", async ({ page }) => {
  const detail = { entry_id: 'will.1.2', kind: 'item', legal: true, live: { version: 1, body: choice(2) },
    versions: [version(2, 'draft', { ...choice(5), source: 'nope' }, ERR), version(1, 'published', choice(2), [])] };
  const calls = await open(page, PARALEGAL, 'will.1.2', true, { version: 2, state: 'draft' }, detail);
  const list = page.locator('#contentDetail ul.content-errors');
  await expect(page.locator('#contentDetail').getByText('Errores del validador:')).toBeVisible();
  await expect(list.locator('li')).toHaveText(ERR);
  await expect(page.getByText(REASON)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Enviar a revisión' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Guardar borrador' })).toBeEnabled();
  await page.getByRole('button', { name: 'Enviar a revisión' }).click({ force: true });
  expect(calls).toEqual([]);
});

test('the attorney cannot approve an invalid version', async ({ page }) => {
  const detail = { entry_id: 'will.1.2', kind: 'item', legal: true, live: { version: 1, body: choice(2) },
    versions: [version(2, 'review', choice(5), [ERR[0]]), version(1, 'published', choice(2), [])] };
  await open(page, ATTORNEY, 'will.1.2', true, { version: 2, state: 'review' }, detail);
  await expect(page.getByRole('button', { name: 'Aprobar versión 2' })).toBeDisabled();
  await expect(page.getByText(REASON)).toBeVisible();
  await expect(page.locator('#contentDetail ul.content-errors li')).toHaveText([ERR[0]]);
});

test('a non-legal item with errors cannot be published', async ({ page }) => {
  const tf = (answer: unknown) => ({ answer, es: { statement: 'Un testamento necesita notario.', explain: 'No.' },
    en: { statement: 'A will needs a notary.', explain: 'No.' } });
  const detail = { entry_id: 'will.1.3', kind: 'item', legal: false, live: { version: 1, body: tf(false) },
    versions: [version(2, 'draft', tf(1), ['will.1.3: truefalse needs a bool']), version(1, 'published', tf(false), [])] };
  await open(page, PARALEGAL, 'will.1.3', false, { version: 2, state: 'draft' }, detail);
  await expect(page.getByRole('button', { name: 'Publicar versión 2' })).toBeDisabled();
  await expect(page.getByText(REASON)).toBeVisible();
});

test('a valid version shows no errors and its buttons work', async ({ page }) => {
  const detail = { entry_id: 'will.1.2', kind: 'item', legal: true, live: { version: 1, body: choice(2) },
    versions: [version(2, 'review', choice(1), []), version(1, 'published', choice(2), [])] };
  const calls = await open(page, ATTORNEY, 'will.1.2', true, { version: 2, state: 'review' }, detail);
  await expect(page.locator('#contentDetail ul.content-errors')).toHaveCount(0);
  await expect(page.getByText(REASON)).toHaveCount(0);
  await page.getByRole('button', { name: 'Aprobar versión 2' }).click();
  await expect.poll(() => calls.length).toBe(1);
  expect(calls[0].postDataJSON()).toEqual({ version: 2 });
});
