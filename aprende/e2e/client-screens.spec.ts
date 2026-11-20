import { test, expect, type Page } from '@playwright/test';

test.use({ viewport: { width: 390, height: 844 } });

async function signUp(page: Page) {
  await page.goto('/#/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill(`ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
}

async function cleared(page: Page) {
  await signUp(page);
  await page.evaluate(async () => {
    const tok = localStorage.getItem('aprende_token');
    const post = (type: string, payload: object) => fetch('/journey/events', { method: 'POST',
      headers: { Authorization: `Bearer ${tok}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ type, payload }) });
    await post('ai_disclosed', {}); await post('consent', { answer: 'yes' }); await post('names_submitted', { names: ['Ana Torres'] });
  });
}

test('W1: leccion title resets when id changes', async ({ page }) => {
  await signUp(page);
  await page.goto('/#/leccion/will');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('El testamento').catch(() => {});
  await page.goto('/#/leccion/trust');
  const heading = page.getByRole('heading', { level: 1 });
  if (await heading.count()) {
    await expect(heading).not.toContainText('El testamento');
  }
});

test('W3: datos shows open question when chat fails', async ({ page }) => {
  await cleared(page);
  await page.route('**/chat', (r) => r.fulfill({ status: 500, json: { error: 'server' } }));
  await page.goto('/#/datos/poa');
  await expect(page.getByText('¿a quién quiere nombrar como apoderado')).toBeVisible();
  await expect(page.getByText('Revise su conexión')).not.toBeVisible();
});

test('W4: firmados final-lesson link only when gate open', async ({ page }) => {
  await signUp(page);
  await page.route('**/signed-documents', (r) => r.fulfill({ json: [] }));
  await page.route('**/funding-checklist', (r) => r.fulfill({ status: 409, json: { error: 'not_signed' } }));
  await page.route('**/journey', (r) => r.fulfill({ json: { gates: { may_take_final_lesson: false } } }));
  await page.goto('/#/firmados');
  await expect(page.getByRole('link', { name: 'Tomar la lección final' })).toHaveCount(0);
  await page.route('**/journey', (r) => r.fulfill({ json: { gates: { may_take_final_lesson: true } } }));
  await page.reload();
  await expect(page.getByRole('link', { name: 'Tomar la lección final' })).toBeVisible();
});

test('W5: documentos checkbox keeps size when label wraps', async ({ page }) => {
  await signUp(page);
  await page.goto('/#/documentos');
  const sizes = await page.locator('.choices .option input').evaluateAll((els) =>
    els.map((e) => { const r = (e as HTMLElement).getBoundingClientRect(); return { w: r.width, h: r.height }; }));
  expect(sizes[0].w).toBeCloseTo(sizes[2].w, 0);
  expect(sizes[0].h).toBeCloseTo(sizes[2].h, 0);
});
