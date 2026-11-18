import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('signup in Spanish lands on inicio/ia, tabs are links with aria-current', async ({ page }) => {
  await page.goto('/#/bienvenida');
  await page.getByRole('link', { name: /Crear cuenta/i }).click();
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill('ana@example.com');
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
  const tabs = page.locator('nav.tabs a');
  await expect(tabs).toHaveCount(4);
  // aria-current on one tab
  await expect(page.locator('nav.tabs a[aria-current="page"]')).toHaveCount(1);
});

test('axe no violations on four screens', async ({ page }) => {
  for (const r of ['/bienvenida', '/cuenta-nueva', '/entrar', '/inicio/ia']) {
    await page.goto('/#' + r);
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  }
});
