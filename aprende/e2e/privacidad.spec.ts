import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// T8-02 acceptance (Opus, p8-tests): the privacy policy page on the web app (the Store listing links to it).
// The text is a draft that needs the attorney's approval (#52); the page says so.
const axeClean = async (page: import('@playwright/test').Page) => {
  const axe = await new AxeBuilder({ page }).analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
};

test('the privacy policy opens from the welcome page without signing in, in Spanish', async ({ page }) => {
  await page.goto('/#/bienvenida');
  await page.getByRole('link', { name: 'Aviso de privacidad' }).click();
  await expect(page).toHaveURL(/#\/privacidad$/);
  await expect(page.getByRole('heading', { level: 1, name: 'Aviso de privacidad' })).toBeVisible();
  await expect(page.getByText('Borrador: el abogado debe aprobar este texto antes de publicarlo.')).toBeVisible();
  await expect(page.getByText('No le preguntamos sobre su situación migratoria.', { exact: false })).toBeVisible();
  await expect(page.getByText('La extensión guarda solo su sesión', { exact: false })).toBeVisible();
  await expect(page.getByRole('link', { name: 'kevin@carbonlg.com' })).toHaveAttribute('href', 'mailto:kevin@carbonlg.com');
  await axeClean(page);
  await page.reload();
  await expect(page).toHaveURL(/#\/privacidad$/);                               // a public page: no redirect to bienvenida
});

test('the privacy policy in English', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('aprende_lang', 'en'));
  await page.goto('/#/privacidad');
  await expect(page.getByRole('heading', { level: 1, name: 'Privacy notice' })).toBeVisible();
  await expect(page.getByText('Draft: the attorney must approve this text before it is published.')).toBeVisible();
  await expect(page.getByText('We do not ask about your immigration status.', { exact: false })).toBeVisible();
  await axeClean(page);
});

test('a signed-in client can open it too, inside the app', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('aprende_token', 'tok'));
  await page.goto('/#/privacidad');
  await expect(page.getByRole('heading', { level: 1, name: 'Aviso de privacidad' })).toBeVisible();
  await expect(page).toHaveURL(/#\/privacidad$/);
});
