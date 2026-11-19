import { test, expect, type Page } from '@playwright/test';

async function signUp(page: Page) {
  await page.goto('/#/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill(`ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
}

test('the payment page: test mode, the server total, Stripe opens, and there is no card field anywhere', async ({ page }) => {
  await signUp(page);
  await page.route(/\/journey$/, async (r) => {
    const j = await (await r.fetch()).json();
    j.gates.may_pay = true; j.documents.confirmed = ['will'];
    await r.fulfill({ json: j });
  });
  await page.route('**/payments/checkout', (r) => r.fulfill({ json: { url: 'https://checkout.stripe.test/1', mode: 'test' } }));
  await page.route('https://checkout.stripe.test/**', (r) => r.fulfill({ body: '<h1>Stripe test page</h1>', contentType: 'text/html' }));
  await page.goto('/#/pago');
  await expect(page.getByText('Modo de prueba: no se cobra nada.')).toBeVisible();
  await expect(page.getByText(/Total a pagar: \$3,000/)).toBeVisible();
  for (const sel of ['input[autocomplete^="cc-"]', 'input[name*="card" i]', 'iframe[src*="stripe"]']) {
    await expect(page.locator(sel)).toHaveCount(0);
  }
  await page.getByRole('button', { name: 'Pagar con Stripe' }).click();
  await expect(page).toHaveURL('https://checkout.stripe.test/1');
});

test('coming back from Stripe waits for the webhook; the redirect alone is not a payment', async ({ page }) => {
  await signUp(page);
  await page.route('**/payments/return**', (r) => r.fulfill({ json: { paid: false } }));
  await page.goto('/#/pago/listo?session_id=cs_test_1');
  await expect(page.getByText('Estamos confirmando su pago con Stripe', { exact: false })).toBeVisible();
});
