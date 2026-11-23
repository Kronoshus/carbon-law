import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function signUp(page: Page, email: string) {
  await page.goto('/#/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill(email);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
}

test('signup in Spanish lands on the day-1 gate without tabs; the app has tabs with aria-current', async ({ page }) => {
  await page.goto('/#/bienvenida');
  await page.getByRole('link', { name: /Crear cuenta/i }).click();
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill(`ana-${Date.now()}@example.com`);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
  await expect(page.locator('nav.tabs')).toHaveCount(0);                // the gate is one thing at a time
  await expect(page.getByRole('button', { name: /Cerrar sesión/i })).toBeVisible();
  await page.goto('/#/aprender');
  const tabs = page.locator('nav.tabs a');
  await expect(tabs).toHaveCount(4);
  await expect(page.locator('nav.tabs a[aria-current="page"]')).toHaveCount(1);
});

test('rail replaces tabs above 64em', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('aprende_token', 'tok'));   // before any page: no public-page redirect
  await page.setViewportSize({ width: 1200, height: 800 });
  await page.goto('/#/sin-pagina');                                              // a page that makes no API call (T8-03: Perfil reads /progress)
  await expect(page.locator('nav.rail')).toBeVisible();
  await expect(page.locator('nav.tabs')).toBeHidden();
});

test('sign-out clears token and returns to entrar', async ({ page }) => {
  // a real sign-up: since T8-02 the app checks the token with the API, so a made-up one signs her out
  await signUp(page, `ana-${Date.now()}-out@example.com`);
  await page.goto('/#/perfil');
  await page.getByRole('button', { name: /Cerrar sesión/i }).click();
  await expect(page).toHaveURL(/#\/entrar/);
  const tok = await page.evaluate(() => localStorage.getItem('aprende_token'));
  expect(tok).toBeNull();
});

test('auth guard redirects unauthed to bienvenida', async ({ page }) => {
  await page.goto('/#/bienvenida');
  await page.evaluate(() => localStorage.removeItem('aprende_token'));
  await page.goto('/#/perfil');
  await expect(page).toHaveURL(/#\/bienvenida/);
});

test('signed-in user opening entrar goes to landing', async ({ page }) => {
  await signUp(page, `ana-${Date.now()}-in@example.com`);
  await page.goto('/#/entrar');
  await expect(page).toHaveURL(/#\/(inicio\/ia|aprender)/);
});

test('sign-in existing client without ai_disclosed lands on inicio/ia', async ({ page }) => {
  const email = `ana-${Date.now()}-back@example.com`;
  await signUp(page, email);
  await page.getByRole('button', { name: /Cerrar sesión/i }).click();
  await expect(page).toHaveURL(/#\/entrar/);
  await page.getByLabel(/Correo/i).fill(email);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByRole('button', { name: /Entrar/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
});

test('English sign-up labels and html lang', async ({ page }) => {
  await page.goto('/#/bienvenida');
  await page.getByRole('link', { name: /Crear cuenta|Create account/i }).click();
  // switch language
  const sel = page.locator('select');
  await sel.selectOption('en');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { name: 'Create account' })).toBeVisible();
});

test('language persists across reload', async ({ page }) => {
  await page.goto('/#/cuenta-nueva');
  const sel = page.locator('select');
  if (await sel.count()) await sel.selectOption('en');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
});

test('axe no violations on four screens', async ({ page }) => {
  for (const r of ['/bienvenida', '/cuenta-nueva', '/entrar']) {
    await page.goto('/#' + r);
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  }
});

test('when the server cannot be reached, sign-up and sign-in say so instead of "wrong password"', async ({ page }) => {
  await page.route('**/auth/**', (route) => route.abort('connectionrefused'));
  await page.goto('/#/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill('sin-servidor@example.com');
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page.getByText(/No pudimos conectar con el servidor/)).toBeVisible();
  await expect(page.getByText(/incorrect/i)).toHaveCount(0);
  await page.goto('/#/entrar');
  await page.getByLabel(/Correo/i).fill('sin-servidor@example.com');
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByRole('button', { name: /Entrar/i }).click();
  await expect(page.getByText(/No pudimos conectar con el servidor/)).toBeVisible();
});
