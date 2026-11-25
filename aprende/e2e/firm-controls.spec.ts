import { test, expect, type Page, type Request } from '@playwright/test';

// T7-05 acceptance (Opus, t7-tests). Contract: docs/tickets/T7-05.md.
const ADMIN = `http://127.0.0.1:${process.env.E2E_ADMIN_PORT || '5174'}`;

async function cleared(page: Page) {
  await page.goto('/#/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill(`ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
  await page.evaluate(async () => {             // the e2e seed's conflict list does not match Ana Torres: an automatic clear
    const tok = localStorage.getItem('aprende_token');
    const post = (type: string, payload: object) => fetch('/journey/events', { method: 'POST',
      headers: { Authorization: `Bearer ${tok}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ type, payload }) });
    await post('ai_disclosed', {}); await post('consent', { answer: 'yes' }); await post('names_submitted', { names: ['Ana Torres'] });
  });
}

test('AI chat off: Tus datos says so kindly, and the lessons still open', async ({ page }) => {
  await cleared(page);
  // The firm switched AI chat off: the server answers every /chat with 503 ai_chat_off (pytest proves the server side).
  await page.route('**/chat', (r) => r.fulfill({ status: 503, json: { error: 'ai_chat_off' } }));
  await page.goto('/#/datos/will');
  await expect(page.getByText('La charla con los personajes no está disponible por ahora. Puede seguir con sus lecciones.')).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);                                  // calm text, not an error
  await page.getByRole('button', { name: 'Volver al mapa' }).click();
  await expect(page).toHaveURL(/#\/aprender/);
  const start = page.getByRole('link', { name: 'Empezar' });
  await expect(start).toHaveAttribute('href', '#/leccion/will');
  await start.click();
  await expect(page).toHaveURL(/#\/leccion\/will/);
});

const SETTINGS = {
  availability: { hours: { mon: [['09:00', '17:00']] }, slot_minutes: { signing: 60, consultation: 30 } },
  holidays: ['2026-12-25'],
  retention: { unpaid_personal_data_days: 365 },
  switches: { voice_recording: true, ai_chat: true, extension: true },
  lessons_per_day: 1,
};

async function admin(page: Page, role: 'attorney' | 'paralegal') {
  const user = { id: role, role, name: role === 'attorney' ? 'Pankaj Raval' : 'Rosa Paralegal', email: `${role}@example.com` };
  await page.addInitScript((u) => { localStorage.setItem('carbon_token', 'tok'); localStorage.setItem('carbon_user', JSON.stringify(u)); }, user);
  await page.route('https://carbon-law.onrender.com/**', (r) => r.fulfill({ json: [] }));
  await page.route('**/auth/me', (r) => r.fulfill({ json: user }));
  const puts: Request[] = [];
  await page.route(/\/staff\/firm-settings$/, (r) => {
    if (r.request().method() === 'GET') return r.fulfill({ json: SETTINGS });
    puts.push(r.request());
    return r.fulfill({ json: { ...SETTINGS, switches: { ...SETTINGS.switches, ai_chat: false } } });
  });
  const holidays: Request[] = [];
  await page.route(/\/staff\/holidays$/, (r) => { holidays.push(r.request()); return r.fulfill({ json: { holidays: [] } }); });
  await page.goto(`${ADMIN}/admin.html#firm`);
  return { puts, holidays };
}

test('the admin turns AI chat off and adds a holiday through its own route', async ({ page }) => {
  const { puts, holidays } = await admin(page, 'attorney');
  const ai = page.getByLabel('AI chat');
  await expect(ai).toBeChecked();
  await expect(page.getByLabel('Lessons per day')).toHaveValue('1');
  await expect(page.getByLabel("Delete unpaid clients' data after (days)")).toHaveValue('365');
  await ai.uncheck();
  await page.getByRole('button', { name: 'Save settings' }).click();
  await expect.poll(() => puts.length).toBe(1);
  const sent = puts[0].postDataJSON();
  expect(puts[0].method()).toBe('PUT');
  expect(sent.switches.ai_chat).toBe(false);
  expect(Object.keys(sent).sort()).toEqual(['switches']);                               // only what changed
  await page.getByLabel('Holiday', { exact: true }).fill('2026-12-24');
  await page.getByRole('button', { name: 'Add holiday' }).click();
  await expect.poll(() => holidays.length).toBe(1);
  expect(holidays[0].method()).toBe('PUT');
  expect([...holidays[0].postDataJSON().dates].sort()).toEqual(['2026-12-24', '2026-12-25']);
  expect(puts.length).toBe(1);                                                           // holidays never go to firm-settings
});

test('a paralegal sees the firm settings but cannot change them', async ({ page }) => {
  await admin(page, 'paralegal');
  await expect(page.getByLabel('AI chat')).toBeDisabled();
  await expect(page.getByLabel('Chrome extension')).toBeDisabled();
  await expect(page.getByLabel('Lessons per day')).toBeDisabled();
  await expect(page.getByText('Only the attorney or an admin can change these settings.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save settings' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Add holiday' })).toBeEnabled();     // holidays stay editable, as today
});
