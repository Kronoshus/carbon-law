import { test, expect } from '@playwright/test';

// web/admin.html is served from a static server (playwright.config: a webServer for ../web on E2E_ADMIN_PORT, default 5174);
// it calls the production API base, so every API answer here is played back.
const DRAFT = '**DRAFT — FOR ATTORNEY REVIEW — NOT FOR SIGNING**\n\nYellow [ATTORNEY TO COMPLETE] marks facts the client did not give.\n\n# LAST WILL\n\n## ARTICLE ONE\n\nExecutor: [ATTORNEY TO COMPLETE - executor\'s address]. ' +
  'Bond waived [ATTORNEY TO CONFIRM - bond waived].\n\n<script>window.__pwned = 1</script><img src="x" onerror="window.__pwned = 2">';
const ADMIN = `http://127.0.0.1:${process.env.E2E_ADMIN_PORT || '5174'}`;

test('the attorney reads a draft with its marks, and no script in a draft runs', async ({ page }) => {
  const user = { id: 'att', role: 'attorney', name: 'Pankaj Raval', email: 'a@example.com' };
  await page.addInitScript((u) => { localStorage.setItem('carbon_token', 'tok'); localStorage.setItem('carbon_user', JSON.stringify(u)); }, user);
  // Playwright tries the most recently added route first: the catch-all goes first, the specific answers after it.
  await page.route('https://carbon-law.onrender.com/**', (r) => r.fulfill({ json: [] }));
  await page.route('**/auth/me', (r) => r.fulfill({ json: user }));
  await page.route('**/staff/review-queue', (r) => r.fulfill({ json: [{ journey_id: 'j1', client_name: 'Ana Torres', due: '2026-12-09', late: false, note: null,
    documents: [{ id: 'd1', name: 'Last will and testament', version: 1 }] }] }));
  await page.route('**/staff/drafts/d1', (r) => r.fulfill({ json: { id: 'd1', name: 'Last will and testament', version: 1, content: DRAFT } }));
  await page.goto(`${ADMIN}/admin.html#review`);
  await page.getByRole('button', { name: /Ana Torres/ }).click();
  await expect(page.locator('mark.complete')).toHaveText("[ATTORNEY TO COMPLETE - executor's address]");
  await expect(page.locator('mark.confirm')).toHaveText('[ATTORNEY TO CONFIRM - bond waived]');
  await expect(page.getByRole('button', { name: 'Aprobar' })).toBeDisabled();             // something is left to complete
  expect(await page.evaluate(() => (window as unknown as { __pwned?: number }).__pwned)).toBeUndefined();
  await expect(page.locator('.draft script, .draft img')).toHaveCount(0);
});

test('a draft whose only "[ATTORNEY TO COMPLETE]" is the notice can be approved', async ({ page }) => {
  const user = { id: 'att', role: 'attorney', name: 'Pankaj Raval', email: 'a@example.com' };
  await page.addInitScript((u) => { localStorage.setItem('carbon_token', 'tok'); localStorage.setItem('carbon_user', JSON.stringify(u)); }, user);
  await page.route('https://carbon-law.onrender.com/**', (r) => r.fulfill({ json: [] }));
  await page.route('**/auth/me', (r) => r.fulfill({ json: user }));
  await page.route('**/staff/review-queue', (r) => r.fulfill({ json: [{ journey_id: 'j1', client_name: 'Ana Torres', due: '2026-12-09', late: false, note: null,
    documents: [{ id: 'd1', name: 'Last will and testament', version: 1 }] }] }));
  await page.route('**/staff/drafts/d1', (r) => r.fulfill({ json: { id: 'd1', name: 'Last will and testament', version: 1,
    content: 'Yellow [ATTORNEY TO COMPLETE] marks facts the client did not give.\n\n# LAST WILL\n\nDone.' } }));
  await page.goto(`${ADMIN}/admin.html#review`);
  await page.getByRole('button', { name: /Ana Torres/ }).click();
  await expect(page.locator('mark.complete')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Aprobar' })).toBeEnabled();
});
