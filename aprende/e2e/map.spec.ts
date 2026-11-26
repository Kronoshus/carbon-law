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

test('a signed-in client opening the map never sees the welcome page first', async ({ page }) => {
  await signUp(page);
  await page.addInitScript(() => {
    new MutationObserver(() => { if (document.querySelector('.welcome-shell')) (window as unknown as { sawWelcome: boolean }).sawWelcome = true; })
      .observe(document, { childList: true, subtree: true });
  });
  await page.goto('/#/aprender');
  await page.reload();
  await expect(page.locator('.bubble')).toContainText('El testamento');
  expect(await page.evaluate(() => (window as unknown as { sawWelcome?: boolean }).sawWelcome ?? false)).toBe(false);
});

test('the course map: today\'s lesson, the price, locked days and their reason', async ({ page }) => {
  await signUp(page);
  await page.goto('/#/aprender');
  await expect(page.getByText('Día 1 de 14')).toBeVisible();
  await expect(page.locator('.bubble')).toContainText('El testamento');
  await expect(page.locator('.card.price')).toContainText('$3,000');
  await expect(page.locator('.card.price')).toContainText('Cada lección completada baja el precio $100.');
  const start = page.getByRole('link', { name: 'Empezar' });
  await expect(start).toHaveAttribute('href', '#/leccion/will');
  await expect(page.locator('.node.locked').filter({ hasText: 'El fideicomiso en vida' })).toContainText('Se abre después de la lección anterior');
  await expect(page.locator('.node.locked').filter({ hasText: 'Cuide sus documentos' })).toContainText('Se abre después de la firma');
  const axe = await new AxeBuilder({ page }).analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
  await start.click();
  await expect(page).toHaveURL(/#\/leccion\/will/);
});
