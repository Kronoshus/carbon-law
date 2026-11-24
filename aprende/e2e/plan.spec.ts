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

const step = (step: string, day: number, date: string, status: string, shifted = 0, reason: string | null = null) =>
  ({ step, day, date, due: null, status, shifted_days: shifted, reason_key: reason });

test('Mi plan: every step with its date, a moved date explained, a late step said calmly', async ({ page }) => {
  await signUp(page);
  await page.route(/\/journey$/, async (r) => {
    const real = await (await r.fetch()).json();
    real.timeline = [
      step('lesson_will', 1, '2026-11-30', 'done'), step('lesson_trust', 2, '2026-12-01', 'done'),
      step('lesson_ahcd', 3, '2026-12-02', 'done'), step('lesson_poa', 4, '2026-12-03', 'done'),
      step('pay', 5, '2026-12-04', 'done'), step('attorney_review', 10, '2026-12-09', 'late', 2, 'weekend'),
      step('client_review', 11, '2026-12-10', 'waiting', 2, 'weekend'), step('signing', 15, '2026-12-14', 'waiting', 2, 'weekend'),
      step('final_lesson', 16, '2026-12-15', 'waiting', 2, 'weekend'),
    ];
    await r.fulfill({ json: real });
  });
  await page.goto('/#/plan');
  await expect(page.getByRole('heading', { name: 'Mi plan' })).toBeVisible();
  await expect(page.locator('.plan-step')).toHaveCount(9);
  await expect(page.getByText('Día 10, miércoles, 9 de diciembre', { exact: false })).toBeVisible();
  await expect(page.getByText('El fin de semana movió esta fecha 2 días.').first()).toBeVisible();
  await expect(page.getByText('La oficina va un poco atrasada con este paso.', { exact: false })).toBeVisible();
  await expect(page.getByText(/atrasad[oa]/i)).toHaveCount(1);                 // only the calm sentence: no "late" label or alarm
  const axe = await new AxeBuilder({ page }).exclude('canvas').analyze();
  expect(axe.violations.map((v) => v.id)).toEqual([]);
});
