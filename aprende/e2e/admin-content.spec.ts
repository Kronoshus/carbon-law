import { test, expect, type Page, type Request } from '@playwright/test';

// T7-01 acceptance (Opus, t7-tests). web/admin.html#content against the contract in docs/tickets/T7-01.md.
// The admin calls the production API base, so every answer is played back (like admin-review.spec.ts).
const ADMIN = `http://127.0.0.1:${process.env.E2E_ADMIN_PORT || '5174'}`;
const PARALEGAL = { id: 'par', role: 'paralegal', name: 'Rosa Paralegal', email: 'p@example.com' };
const ATTORNEY = { id: 'att', role: 'attorney', name: 'Pankaj Raval', email: 'a@example.com' };

const explain = (es: string, en: string) => ({ es: { text: es }, en: { text: en }, source: 'pc-6110' });
const version = (v: number, state: string, body: unknown) => ({ version: v, state, body, created_by: 'p@example.com',
  created_at: '2026-11-19T10:00:00+00:00', submitted_by: state === 'review' ? 'p@example.com' : null, submitted_at: null,
  approved_by: null, approved_at: null, published_by: null, published_at: null });

async function open(page: Page, user: typeof PARALEGAL, entry: { entry_id: string; legal: boolean; pending: { version: number; state: string } },
  detail: unknown) {
  await page.addInitScript((u) => { localStorage.setItem('carbon_token', 'tok'); localStorage.setItem('carbon_user', JSON.stringify(u)); }, user);
  // Playwright tries the most recently added route first: the catch-all goes first.
  await page.route('https://carbon-law.onrender.com/**', (r) => r.fulfill({ json: [] }));
  await page.route('**/auth/me', (r) => r.fulfill({ json: user }));
  await page.route(/\/staff\/content\?kind=item$/, (r) => r.fulfill({ json: { entries: [{ kind: 'item', lesson_id: 'will', live_version: 1, ...entry }] } }));
  const id = entry.entry_id.replace(/\./g, '\\.');
  await page.route(new RegExp(`/staff/content/${id}$`), (r) => r.fulfill({ json: detail }));
  await page.goto(`${ADMIN}/admin.html#content`);
  // the list names each entry by its text; the code id is only its tooltip
  await page.locator(`#contentEntries button[title="${entry.entry_id}"]`).click();
}

function capture(page: Page, pattern: RegExp, answer: unknown) {
  const seen: Request[] = [];
  return page.route(pattern, (r) => { seen.push(r.request()); return r.fulfill({ json: answer }); }).then(() => seen);
}

test('a paralegal edits a legal item and sends it to review, but cannot approve or publish it', async ({ page }) => {
  const live = explain('Un testamento escrito a máquina lo firman usted y dos testigos.', 'A typed will is signed by you and two witnesses.');
  const detail = { entry_id: 'will.1.1', kind: 'item', legal: true, live: { version: 1, body: live },
    versions: [version(2, 'draft', explain('Texto nuevo.', 'New text.')), version(1, 'published', live)] };
  await open(page, PARALEGAL, { entry_id: 'will.1.1', legal: true, pending: { version: 2, state: 'draft' } }, detail);
  await expect(page.getByText('Live: version 1')).toBeVisible();
  await expect(page.getByText(/Waiting: version 2/)).toBeVisible();
  await expect(page.getByLabel('Text (Spanish)')).toHaveValue('Texto nuevo.');
  const puts = await capture(page, /\/staff\/content\/will\.1\.1\/draft$/, { entry_id: 'will.1.1', version: 2, state: 'draft' });
  const submits = await capture(page, /\/staff\/content\/will\.1\.1\/submit$/, { entry_id: 'will.1.1', version: 2, state: 'review' });
  await page.getByLabel('Text (English)').fill('The paralegal\'s new text.');
  await page.getByRole('button', { name: 'Save draft' }).click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0].method()).toBe('PUT');
  const sent = puts[0].postDataJSON().body;
  expect(sent.es.text).toBe('Texto nuevo.');
  expect(sent.en.text).toBe('The paralegal\'s new text.');
  expect(sent).not.toHaveProperty('legal');
  await page.getByRole('button', { name: 'Send for review' }).click();
  await expect.poll(() => submits.length).toBe(1);
  await expect(page.getByRole('button', { name: /Approve|Publish/ })).toHaveCount(0);
  await expect(page.getByText('Only the attorney can approve and publish this content.')).toBeVisible();
});

test('the attorney approves the exact version he is reading', async ({ page }) => {
  const live = explain('Texto publicado.', 'Published text.');
  const detail = { entry_id: 'will.1.1', kind: 'item', legal: true, live: { version: 1, body: live },
    versions: [version(2, 'review', explain('Texto para aprobar.', 'Text to approve.')), version(1, 'published', live)] };
  await open(page, ATTORNEY, { entry_id: 'will.1.1', legal: true, pending: { version: 2, state: 'review' } }, detail);
  await expect(page.getByLabel('Text (Spanish)')).toHaveValue('Texto para aprobar.');
  const approvals = await capture(page, /\/staff\/content\/will\.1\.1\/approve$/, { entry_id: 'will.1.1', version: 2, state: 'published',
    approved_by: 'a@example.com', approved_at: '2026-11-19T11:00:00+00:00' });
  await page.getByRole('button', { name: 'Approve version 2' }).click();
  await expect.poll(() => approvals.length).toBe(1);
  expect(approvals[0].method()).toBe('POST');
  expect(approvals[0].postDataJSON()).toEqual({ version: 2 });
  await expect(page.getByRole('button', { name: /^Publish/ })).toHaveCount(0);
});

test('a non-legal item shows "Publicar" to a paralegal', async ({ page }) => {
  const body = { es: { statement: 'Un testamento necesita notario.', explain: 'No es obligatorio.' },
    en: { statement: 'A will needs a notary.', explain: 'It is not required.' }, answer: false };
  const detail = { entry_id: 'will.1.3', kind: 'item', legal: false, live: { version: 1, body },
    versions: [version(2, 'draft', body), version(1, 'published', body)] };
  await open(page, PARALEGAL, { entry_id: 'will.1.3', legal: false, pending: { version: 2, state: 'draft' } }, detail);
  await expect(page.getByLabel('Statement (Spanish)')).toHaveValue('Un testamento necesita notario.');
  await expect(page.getByLabel('Explanation (English)')).toHaveValue('It is not required.');
  const pubs = await capture(page, /\/staff\/content\/will\.1\.3\/publish$/, { entry_id: 'will.1.3', version: 2, state: 'published' });
  await page.getByRole('button', { name: 'Publish version 2' }).click();
  await expect.poll(() => pubs.length).toBe(1);
  expect(pubs[0].postDataJSON()).toEqual({ version: 2 });
  await expect(page.getByText('Only the attorney can approve and publish this content.')).toHaveCount(0);
});

test('content text is shown as text and never runs as HTML', async ({ page }) => {
  const evil = '<img src="x" onerror="window.__pwned = 1"><script>window.__pwned = 2</script>';
  const body = explain(evil, 'Plain.');
  const detail = { entry_id: 'will.1.1', kind: 'item', legal: true, live: { version: 1, body }, versions: [version(1, 'published', body)] };
  await open(page, ATTORNEY, { entry_id: 'will.1.1', legal: true, pending: null as unknown as { version: number; state: string } }, detail);
  await expect(page.getByLabel('Text (Spanish)')).toHaveValue(evil);
  await page.route(/\/staff\/content\/will\.1\.1\/preview/, (r) => r.fulfill({ json: { character: 'calavera', item: { id: 'will.1.1', kind: 'explain', text: evil }, explain: null } }));
  await page.getByRole('button', { name: 'Preview' }).click();
  await expect(page.locator('.content-preview')).toContainText('<img src="x"');
  expect(await page.evaluate(() => (window as unknown as { __pwned?: number }).__pwned)).toBeUndefined();
  await expect(page.locator('#contenido img[src="x"], #contenido script')).toHaveCount(0);
});
