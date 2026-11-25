import { test, expect, type Page } from '@playwright/test';

/* The states the app reaches late in the journey or only when something fails: paid, a booked appointment, the change
   request on Revisar, the map after the signing, and a screen that cannot load. The server's answers are played back
   (the release test walks the real journey). */

async function signUp(page: Page) {
  await page.goto('/#/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill(`ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const playJourney = (page: Page, edit: (j: Record<string, any>) => void) => page.route(/\/journey$/, async (r) => {
  const j = await (await r.fetch()).json();
  edit(j);
  await r.fulfill({ json: j });
});

test('after paying, Pagar says it is paid and offers no second payment', async ({ page }) => {
  await signUp(page);
  await playJourney(page, (j) => { j.gates.may_pay = true; j.documents.confirmed = ['will']; j.facts.paid = true; });
  await page.goto('/#/pago');
  await expect(page.getByRole('heading', { name: 'Su pago' })).toBeVisible();
  await expect(page.getByText('¡Pago recibido!', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Pagar con Stripe' })).toHaveCount(0);
  await expect(page.getByRole('main').getByRole('link', { name: 'Mi plan' })).toHaveAttribute('href', '#/plan');
});

const API = /\/(journey|learn\/map|progress|booking|booking\/slots|payments\/\w+|review\/documents)(\?.*)?$/;
for (const [path, title] of [['/aprender', 'Aprender'], ['/cita?kind=consultation', 'Su cita'], ['/pago', 'Pagar'], ['/revisar', 'Revise sus documentos']] as const) {
  test(`${path} that cannot load says whether the server or the connection failed, and tries again`, async ({ page }) => {
    await signUp(page);
    await page.route(API, (r) => r.fulfill({ status: 500, body: 'Internal Server Error' }));
    await page.goto('/#' + path);
    await expect(page.getByRole('heading', { name: title })).toBeVisible();
    await expect(page.getByRole('alert')).toHaveText('El servidor tuvo un problema. Intente otra vez en unos minutos.');

    await page.unroute(API);
    await page.route(API, (r) => r.abort('internetdisconnected'));
    await page.getByRole('button', { name: 'Intentar otra vez' }).click();
    await expect(page.getByRole('alert')).toHaveText('No pudimos conectar con el servidor. Revise su internet e intente otra vez.');

    await page.unroute(API);
    await page.getByRole('button', { name: 'Intentar otra vez' }).click();
    await expect(page.getByRole('button', { name: 'Intentar otra vez' })).toHaveCount(0);
    await expect(page.getByRole('alert')).toHaveCount(0);
  });
}

test('sign-in on a server error says the server failed, not the password or the internet', async ({ page }) => {
  await page.route('**/auth/login', (r) => r.fulfill({ status: 500, body: 'Internal Server Error' }));
  await page.goto('/#/entrar');
  await page.getByLabel(/Correo/i).fill('ana.torres@example.com');
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByRole('button', { name: /Entrar/i }).click();
  await expect(page.getByRole('alert')).toHaveText('El servidor tuvo un problema. Intente otra vez en unos minutos.');
});

test('cancelling an appointment asks first; "No, volver" keeps it', async ({ page }) => {
  await signUp(page);
  let booked: { id: string; kind: string; start: string } | null = { id: 'b1', kind: 'consultation', start: '2099-03-16T17:00:00Z' };
  const deletes: string[] = [];
  await page.route('**/booking/slots**', (r) => r.fulfill({ json: { slots: [{ start: '2099-03-16T16:00:00Z', local: '2099-03-16T09:00:00' }] } }));
  await page.route(/\/booking$/, (r) => r.fulfill({ json: booked ? [booked] : [] }));
  await page.route(/\/booking\/b1$/, (r) => { deletes.push(r.request().method()); booked = null; return r.fulfill({ json: { ok: true } }); });
  await page.goto('/#/cita?kind=consultation');
  await expect(page.getByText(/Su cita: .*16 de marzo/)).toBeVisible();

  await page.getByRole('button', { name: 'Cancelar la cita' }).click();
  const ask = page.getByRole('dialog', { name: '¿Cancelar esta cita?' });
  await expect(ask).toContainText(/16 de marzo/);
  await ask.getByRole('button', { name: 'No, volver' }).click();
  await expect(ask).toBeHidden();
  expect(deletes).toEqual([]);

  await page.getByRole('button', { name: 'Cancelar la cita' }).click();
  await ask.getByRole('button', { name: 'Sí, cancelar' }).click();
  await expect(page.getByRole('heading', { name: 'Elija un horario' })).toBeVisible();
  expect(deletes).toEqual(['DELETE']);
});

test('the change request: each label sits over its field, a note is needed, and a failed send says so', async ({ page }) => {
  await signUp(page);
  const doc = { id: 'd1', name: 'Pour-over will', version: 1, decision: null, content: 'Declarations.',
    summary: [{ article: 1, text: 'Quién es usted, dónde vive y quiénes son su familia.' }] };
  const posts: unknown[] = [];
  await page.route('**/review/documents?*', (r) => r.fulfill({ json: { documents: [doc] } }));
  await page.route(/\/review\/documents\/d1$/, (r) => { posts.push(r.request().postDataJSON()); return r.fulfill({ status: 500, body: 'Internal Server Error' }); });
  await page.goto('/#/revisar');
  const will = page.getByRole('region', { name: 'Testamento complementario' });
  const change = will.getByRole('button', { name: 'Quiero un cambio' });
  await expect(change).toHaveAttribute('aria-expanded', 'false');
  await change.click();
  await expect(change).toHaveAttribute('aria-expanded', 'true');
  const note = will.getByLabel('Cuéntenos el cambio con sus palabras');
  const [labelBottom, fieldTop] = await note.evaluate((el) => {
    const words = document.createRange();
    words.selectNodeContents(el.parentElement!.firstChild!);
    return [words.getBoundingClientRect().bottom, el.getBoundingClientRect().top];
  });
  expect(fieldTop).toBeGreaterThanOrEqual(labelBottom - 1);                     // under its label's words, not beside them

  await will.getByRole('button', { name: 'Enviar el cambio al abogado' }).click();
  expect(await note.evaluate((el: HTMLTextAreaElement) => el.validity.valueMissing)).toBe(true);
  expect(posts).toEqual([]);

  await note.fill('Quiero que mi hija Sofía sea la albacea suplente.');
  await will.getByRole('button', { name: 'Enviar el cambio al abogado' }).click();
  await expect(will.getByRole('alert')).toHaveText('No se pudo enviar. Revise su conexión e intente de nuevo.');
  expect(posts).toHaveLength(1);
});

test('after the signing, the map shows the office steps done, no price, and opens the final lesson', async ({ page }) => {
  await signUp(page);
  await playJourney(page, (j) => { Object.assign(j.facts, { paid: true, attorney_approved: true, client_confirmed: true, signed: true }); });
  await page.route('**/learn/map', async (r) => {
    const m = await (await r.fetch()).json();
    for (const u of m.units) for (const l of u.lessons) l.status = u.id === 'final' ? 'available' : 'done';
    await r.fulfill({ json: m });
  });
  await page.goto('/#/aprender');
  for (const step of ['Su plan y su pago', 'Revisión del abogado', 'Revise sus documentos', 'La firma']) {
    await expect(page.locator('.node.done').filter({ hasText: step })).toBeVisible();
  }
  await expect(page.locator('.node.locked')).toHaveCount(0);
  await expect(page.locator('.card.price')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Empezar' })).toHaveAttribute('href', '#/leccion/final');
});
