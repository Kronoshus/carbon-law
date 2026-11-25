import { test, expect, type Page, type Request } from '@playwright/test';

// T7-04 acceptance (Opus, t7-tests): web/admin.html#clients against docs/tickets/T7-04.md; every API answer is played back.
const ADMIN = `http://127.0.0.1:${process.env.E2E_ADMIN_PORT || '5174'}`;
const ROW = { journey_id: 'j1', client_name: 'Ana Torres', day: 9, next_step: 'client_review', late: ['attorney_review'],
  due: '2026-11-18', conflict: 'hold', datos: { done: 12, total: 29, complete: false },
  payment: { paid: true, paid_cents: 260000, refunded_cents: 0 }, drafts_waiting: 2,
  appointments: [{ kind: 'signing', start_utc: '2026-11-28T17:00:00Z' }], questions: { open: 1, answered: 0 } };
const DETAIL = { ...ROW, timeline: [], questions: [
  { id: 'q1', question: '¿Mi hijo puede ser albacea si vive en México?', lesson_id: 'will', character: 'calavera',
    created_at: '2026-11-18T18:00:00', answer: null, answered_by: null, answered_at: null }] };

async function open(page: Page, role: 'attorney' | 'paralegal') {
  const user = { id: role, role, name: role === 'attorney' ? 'Pankaj Raval' : 'Rosa Paralegal', email: `${role}@example.com` };
  await page.addInitScript((u) => { localStorage.setItem('carbon_token', 'tok'); localStorage.setItem('carbon_user', JSON.stringify(u)); }, user);
  await page.route('https://carbon-law.onrender.com/**', (r) => r.fulfill({ json: [] }));
  await page.route('**/auth/me', (r) => r.fulfill({ json: user }));
  // the staff-only conflict queue has the matched names; the Clients screen must never show them
  await page.route('**/conflicts/queue', (r) => r.fulfill({ json: [{ journey_id: 'j1', names: ['Ana Torres', 'Roberto Méndez'],
    matches: ['Roberto Méndez'], result: 'possible', decision: null }] }));
  await page.route(/\/staff\/journeys$/, (r) => r.fulfill({ json: [ROW] }));
  await page.route(/\/staff\/journeys\/j1$/, (r) => r.fulfill({ json: DETAIL }));
  const answers: Request[] = [];
  await page.route(/\/staff\/attorney-questions\/q1\/answer$/, (r) => { answers.push(r.request());
    return r.fulfill({ json: { id: 'q1', answer: r.request().postDataJSON().answer, answered_by: 'attorney@example.com', answered_at: '2026-11-19T20:00:00' } }); });
  await page.goto(`${ADMIN}/admin.html#clients`);
  return answers;
}

test('the clients list shows each column and no conflict names', async ({ page }) => {
  await open(page, 'paralegal');
  const section = page.locator('#clientes');
  for (const header of ['Client', 'Day', 'Late', 'Conflict check', 'Details', 'Payment', 'Drafts', 'Appointments', 'Questions']) {
    await expect(section.getByRole('columnheader', { name: header, exact: true })).toBeVisible();
  }
  const row = section.getByRole('row').filter({ hasText: 'Ana Torres' });
  await expect(row).toContainText('On hold');
  await expect(row).toContainText('12 of 29');
  await expect(row).toContainText('Paid');
  await row.getByRole('button', { name: 'Ana Torres' }).click();
  await expect(section.getByText('¿Mi hijo puede ser albacea si vive en México?')).toBeVisible();
  await expect(page.locator('body')).not.toContainText('Roberto');
  await expect(page.locator('body')).not.toContainText('Méndez');
});

test('the attorney answers a question from the client detail', async ({ page }) => {
  const answers = await open(page, 'attorney');
  await page.locator('#clientes').getByRole('button', { name: 'Ana Torres' }).click();
  await page.getByLabel("Attorney's answer").fill('Sí, puede. Lo vemos en su cita.');
  await page.getByRole('button', { name: 'Send answer' }).click();
  await expect.poll(() => answers.length).toBe(1);
  expect(answers[0].method()).toBe('POST');
  expect(answers[0].postDataJSON()).toEqual({ answer: 'Sí, puede. Lo vemos en su cita.' });
});

test('a paralegal cannot answer', async ({ page }) => {
  await open(page, 'paralegal');
  await page.locator('#clientes').getByRole('button', { name: 'Ana Torres' }).click();
  await expect(page.getByText('Only the attorney answers questions.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Send answer' })).toHaveCount(0);
});
