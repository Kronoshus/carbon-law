import { test, expect, type Page } from '@playwright/test';

// The staff dashboard is split into screens, one per hash route, with a side menu that reaches every screen (web/console.js).
// Every API answer is played back.
const ADMIN = `http://127.0.0.1:${process.env.E2E_ADMIN_PORT || '5174'}`;
const MATTER = { id: 'CLG-2026-041', client_name: 'María Guadalupe Flores', stage: '5 Review Queue', owner: 'Rosa Medina', attorney_reviewer: null,
  risk_level: 'Medium', priority: 'Normal', due_date: '2026-12-09', next_action: 'Review' };

async function open(page: Page, hash: string) {
  const user = { id: 'att', role: 'attorney', name: 'Pankaj Raval', email: 'a@example.com' };
  await page.addInitScript((u) => { localStorage.setItem('carbon_token', 'tok'); localStorage.setItem('carbon_user', JSON.stringify(u)); }, user);
  await page.route('https://carbon-law.onrender.com/**', (r) => r.fulfill({ json: [] }));
  await page.route('**/auth/me', (r) => r.fulfill({ json: user }));
  await page.route(/\/matters$/, (r) => r.fulfill({ json: [MATTER] }));
  await page.goto(`${ADMIN}/admin.html${hash}`);
}

test('the side menu reaches every screen, shows one at a time and marks where you are', async ({ page }) => {
  await open(page, '');
  const nav = page.getByRole('navigation', { name: 'Staff dashboard' });
  const links = nav.locator('a[href^="#"]');
  await expect(links).toHaveCount(12);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Today');                 // the default screen
  for (const link of await links.all()) {
    const name = (await link.textContent())!.trim();
    await link.click();
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(name);                  // only this screen's heading is shown
    await expect(link).toHaveAttribute('aria-current', 'page');
    await expect(nav.locator('[aria-current="page"]')).toHaveCount(1);
  }
});

test('old links to the Spanish section names still land on their screen', async ({ page }) => {
  await open(page, '#contenido');
  await expect(page).toHaveURL(/admin\.html#content$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Lesson content');
});

test('on a phone the menu folds behind a button and table rows become cards', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await open(page, '#review');
  const menu = page.getByRole('button', { name: 'Menu' });
  await expect(menu).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('link', { name: 'Matters', exact: true })).toBeHidden();
  await menu.click();
  await expect(menu).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByRole('link', { name: 'Sign out' })).toBeVisible();
  await page.getByRole('link', { name: 'Matters', exact: true }).click();
  await expect(menu).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Matters');
  const row = page.locator('#adminMatterRows tr').first();
  await expect(row.locator('td[data-label="Client"]')).toHaveText('María Guadalupe Flores');
  const stage = row.locator('td[data-label="Update stage"] select');
  await stage.scrollIntoViewIfNeeded();
  await expect(stage).toBeInViewport({ ratio: 1 });                                         // the row's action is on screen, not off to the side
  const box = await row.boundingBox();
  expect(box!.width).toBeLessThanOrEqual(390);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);   // nothing scrolls sideways
});
