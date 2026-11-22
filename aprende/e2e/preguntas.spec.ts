import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// T7-04 acceptance (Opus, t7-tests): the attorney's reply in the client's Preguntas tab. Contract: docs/tickets/T7-04.md.
// pytest proves the reply reaches GET /journey/questions; here the answer is played back (no model in e2e to log a question).
async function signUp(page: Page) {
  await page.goto('/#/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill(`ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
}

test("the attorney's reply appears in the Preguntas tab", async ({ page }) => {
  await signUp(page);
  await page.route('**/journey/questions', (r) => r.fulfill({ json: { questions: [
    { id: 'q2', question: '¿Quién cuida a Mateo si me pasa algo?', created_at: '2026-11-19T18:00:00', answer: null, answered_at: null },
    { id: 'q1', question: '¿Mi hijo puede ser albacea si vive en México?', created_at: '2026-11-18T18:00:00',
      answer: 'Sí, puede. <b>Lo vemos</b> en su cita.', answered_at: '2026-11-19T19:00:00' },
  ] } }));
  await page.goto('/#/aprender');
  await page.getByRole('link', { name: 'Preguntas', exact: true }).filter({ visible: true }).first().click();
  await expect(page).toHaveURL(/#\/preguntas/);
  await expect(page.getByRole('heading', { name: 'Preguntas para el abogado' })).toBeVisible();
  const answered = page.getByRole('listitem').filter({ hasText: '¿Mi hijo puede ser albacea si vive en México?' });
  await expect(answered).toContainText('Respuesta del abogado Raval:');
  await expect(answered).toContainText('Sí, puede. <b>Lo vemos</b> en su cita.');                  // shown as text
  const waiting = page.getByRole('listitem').filter({ hasText: '¿Quién cuida a Mateo si me pasa algo?' });
  await expect(waiting).toContainText('El abogado Raval todavía no ha respondido.');
  await expect(page.locator('main b')).toHaveCount(0);
  const axe = await new AxeBuilder({ page }).exclude('canvas').analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
});

test('with no questions yet, Preguntas says how they get there', async ({ page }) => {
  await signUp(page);
  await page.goto('/#/preguntas');
  await expect(page.getByText('Todavía no tiene preguntas para el abogado.', { exact: false })).toBeVisible();     // real backend: none yet
});
