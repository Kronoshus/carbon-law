import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

async function signUp(page: Page) {
  await page.goto('/#/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill(`ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
}

const cont = (page: Page) => page.getByRole('button', { name: 'Continuar' });

test('the will lesson: explain, a wrong answer that comes back, sources, resume', async ({ page }) => {
  await signUp(page);
  await page.goto('/#/leccion/will');
  await expect(page.locator('.bubble')).toContainText('Un testamento dice quién recibe sus bienes');
  await expect(page.getByLabel('Avance de la lección')).toHaveAttribute('value', '0');
  for (let i = 0; i < 3; i++) await cont(page).click();                     // three explanations

  await expect(page.getByRole('heading', { name: /Cuántos testigos/ })).toBeVisible();
  await page.getByRole('radio', { name: 'Ninguno' }).check();
  await page.getByRole('button', { name: 'Comprobar' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Casi' })).toBeVisible();
  await cont(page).click();

  await expect(page.getByRole('heading', { name: /escrito totalmente a mano/ })).toBeVisible();   // the true/false comes next
  await page.getByRole('radio', { name: 'Cierto' }).check();
  await page.getByRole('button', { name: 'Comprobar' }).click();
  const sheet = page.locator('.feedback');
  await expect(sheet).toContainText('¡Muy bien!');
  await expect(sheet.getByRole('link', { name: 'Código de Sucesiones de Calif., sección 6111' })).toHaveAttribute('href', /sectionNum=6111/);
  await expect(sheet).toContainText('Información general, no asesoría legal.');
  await expect(sheet).toContainText('+10');
  await cont(page).click();
  await cont(page).click();                                                 // will.1.6 explanation

  await expect(page.getByRole('heading', { name: /Cuántos testigos/ })).toBeVisible();     // the wrong one came back
  await page.reload();                                                     // resume where she was
  await expect(page.getByRole('heading', { name: /Cuántos testigos/ })).toBeVisible();
  await page.getByRole('radio', { name: 'Dos, presentes al mismo tiempo' }).check();
  await page.getByRole('button', { name: 'Comprobar' }).click();
  await expect(page.locator('.feedback')).toContainText('sección 6110');

  const axe = await new AxeBuilder({ page }).exclude('canvas').analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
});

test('a locked lesson says so', async ({ page }) => {
  await signUp(page);
  await page.goto('/#/leccion/trust');
  await expect(page.getByRole('alert')).toContainText('todavía no está abierta');
});
