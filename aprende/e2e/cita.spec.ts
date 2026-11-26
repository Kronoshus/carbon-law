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

// The booking rules are proven in the backend tests; here the screen is driven with the server's answers played back.
const SLOTS = [
  { start: '2027-03-16T16:00:00Z', local: '2027-03-16T09:00:00' },
  { start: '2027-03-16T16:30:00Z', local: '2027-03-16T09:30:00' },
  { start: '2027-03-17T17:00:00Z', local: '2027-03-17T10:00:00' },
];

test('book a consultation, then see it with cancel and change', async ({ page }) => {
  await signUp(page);
  let booked: { id: string; kind: string; start: string; local: string } | null = null;
  let tries = 0;
  await page.route('**/booking/slots**', (r) => r.fulfill({ json: { slots: SLOTS } }));
  await page.route(/\/booking$/, async (r) => {
    if (r.request().method() === 'GET') return r.fulfill({ json: booked ? [booked] : [] });
    tries += 1;
    const body = r.request().postDataJSON();
    if (tries === 1) return r.fulfill({ status: 409, json: { error: 'taken' } });           // someone was faster
    booked = { id: 'b1', kind: body.kind, start: body.start, local: SLOTS.find((s) => s.start === body.start)!.local };
    return r.fulfill({ json: booked });
  });
  await page.goto('/#/cita?kind=consultation');
  await expect(page.getByRole('heading', { name: 'Su cita' })).toBeVisible();
  await expect(page.getByRole('button', { name: /9:00/ })).toBeVisible();
  await expect(page.getByText(/martes,? 16 de marzo/i)).toBeVisible();                     // days in Spanish, Los Angeles time
  const axe = await new AxeBuilder({ page }).exclude('canvas').analyze();
  expect(axe.violations.map((v) => v.id)).toEqual([]);

  await page.getByRole('button', { name: /9:00/ }).click();
  const dialog = page.getByRole('dialog', { name: '¿Confirmar esta cita?' });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Sí, reservar' }).click();
  await expect(page.getByText('Alguien acaba de reservar ese horario', { exact: false })).toBeVisible();

  await page.getByRole('button', { name: /9:30/ }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Sí, reservar' }).click();
  await expect(page.getByText(/Su cita: .*9:30/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cancelar la cita' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cambiar la hora' })).toBeVisible();
});

test('signing stays locked until the documents are approved', async ({ page }) => {
  await signUp(page);
  await page.route('**/booking/slots**', (r) => r.fulfill({ status: 409, json: { error: 'gate', missing: ['may_book_signing'] } }));
  await page.goto('/#/cita?kind=signing');
  await expect(page.getByText('Podrá reservar la firma cuando apruebe sus documentos.')).toBeVisible();
});

test('a booked signing shows the office with a map link, and inside 24 hours the phone to call', async ({ page }) => {
  await signUp(page);
  const soon = new Date(Date.now() + 3 * 3_600_000).toISOString();
  await page.route('**/booking/slots**', (r) => r.fulfill({ json: { slots: SLOTS } }));
  await page.route(/\/booking$/, (r) => r.fulfill({ json: [{ id: 'b1', kind: 'signing', start: soon }] }));
  await page.goto('/#/cita?kind=signing');
  await expect(page.getByText('La firma es en la oficina:')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Carbon Law Group, 13925 City Center Drive, Suite 200, Chino Hills, CA 91709' }))
    .toHaveAttribute('href', 'https://maps.google.com/?q=13925+City+Center+Drive+Suite+200+Chino+Hills+CA+91709');
  await expect(page.getByText('Faltan menos de 24 horas: para cambiarla, llame a la oficina:')).toBeVisible();
  await expect(page.getByRole('link', { name: '845-587-4420' })).toHaveAttribute('href', 'tel:+18455874420');

  await page.evaluate(() => localStorage.setItem('aprende_lang', 'en'));
  await page.reload();
  await expect(page.getByText('The signing is at the office:')).toBeVisible();
  await expect(page.getByText('Less than 24 hours left: to change it, call the office:')).toBeVisible();
  await expect(page.getByRole('link', { name: '845-587-4420' })).toHaveAttribute('href', 'tel:+18455874420');
});

test('a booked consultation names no place', async ({ page }) => {
  await signUp(page);
  await page.route('**/booking/slots**', (r) => r.fulfill({ json: { slots: SLOTS } }));
  await page.route(/\/booking$/, (r) => r.fulfill({ json: [{ id: 'b1', kind: 'consultation', start: '2099-03-16T17:00:00Z' }] }));
  await page.goto('/#/cita?kind=consultation');
  await expect(page.getByRole('button', { name: 'Cancelar la cita' })).toBeVisible();
  await expect(page.getByText('City Center Drive')).toHaveCount(0);
});
