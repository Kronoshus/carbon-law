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

test('signed documents and the trust checklist download with the client\'s token', async ({ page }) => {
  await signUp(page);
  const id = 'k'.repeat(40);
  await page.route('**/signed-documents', (r) => r.fulfill({ json: [{ id, name: 'Pour-over will', filename: 'will-signed.pdf', url: `/signed-documents/${id}` }] }));
  await page.route(`**/signed-documents/${id}`, (r) => r.fulfill({ body: '%PDF-1.4', contentType: 'application/pdf' }));
  await page.route('**/funding-checklist', (r) => r.fulfill({ body: '# Trust Funding Checklist', contentType: 'text/markdown' }));
  await page.goto('/#/firmados');
  await expect(page.getByRole('heading', { name: 'Sus documentos firmados' })).toBeVisible();
  const axe = await new AxeBuilder({ page }).exclude('canvas').analyze();
  expect(axe.violations.map((v) => v.id)).toEqual([]);
  const one = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Descargar Pour-over will' }).click();
  expect((await one).suggestedFilename()).toMatch(/\.pdf$/);
  const two = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Descargar la lista para el fideicomiso' }).click();
  expect((await two).suggestedFilename()).toMatch(/\.md$/);
  await expect(page.getByRole('link', { name: 'Tomar la lección final: cuide sus documentos' })).toBeVisible();
});

test('before the signing the page says when they will appear', async ({ page }) => {
  await signUp(page);
  await page.route('**/signed-documents', (r) => r.fulfill({ json: [] }));
  await page.route('**/funding-checklist', (r) => r.fulfill({ status: 409, json: { error: 'not_signed' } }));
  await page.goto('/#/firmados');
  await expect(page.getByText('Sus documentos aparecerán aquí después de la firma.')).toBeVisible();
});
