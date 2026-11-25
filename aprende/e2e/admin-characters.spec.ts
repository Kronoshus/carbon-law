import { test, expect, type Page, type Request } from '@playwright/test';

// T7-03 acceptance (Opus, t7-tests): web/admin.html#personajes against docs/tickets/T7-03.md; the API is played back.
const ADMIN = `http://127.0.0.1:${process.env.E2E_ADMIN_PORT || '5174'}`;
const CHARACTERS = [
  { id: 'calavera', name_key: 'character.calavera.name', enabled: true, units: ['will', 'trust', 'intake', 'final'], voice_es: null, voice_en: null },
  { id: 'oso', name_key: 'character.oso.name', enabled: true, units: ['ahcd', 'sensitive'], voice_es: null, voice_en: null },
  { id: 'pinata', name_key: 'character.pinata.name', enabled: true, units: ['games'], voice_es: null, voice_en: null },
  { id: 'tortuga', name_key: 'character.tortuga.name', enabled: true, units: [], voice_es: null, voice_en: null },
];

async function open(page: Page) {
  const user = { id: 'par', role: 'paralegal', name: 'Rosa Paralegal', email: 'p@example.com' };
  await page.addInitScript((u) => {
    localStorage.setItem('carbon_token', 'tok'); localStorage.setItem('carbon_user', JSON.stringify(u));
    const spoken: { text: string; lang: string; pitch: number; rate: number }[] = [];
    (window as unknown as { __spoken: typeof spoken }).__spoken = spoken;
    window.speechSynthesis.speak = (utt: SpeechSynthesisUtterance) => { spoken.push({ text: utt.text, lang: utt.lang, pitch: utt.pitch, rate: utt.rate }); };
  }, user);
  const calls: Request[] = [];
  page.on('request', (r) => { if (r.url().startsWith('https://carbon-law.onrender.com')) calls.push(r); });
  await page.route('https://carbon-law.onrender.com/**', (r) => r.fulfill({ json: [] }));
  await page.route('**/auth/me', (r) => r.fulfill({ json: user }));
  await page.route(/\/staff\/characters$/, (r) => r.fulfill({ json: CHARACTERS }));
  const patches: Request[] = [];
  await page.route(/\/characters\/(calavera|oso|pinata)$/, (r) => { patches.push(r.request()); return r.fulfill({ json: {} }); });
  await page.goto(`${ADMIN}/admin.html#personajes`);
  return { calls, patches };
}

const card = (page: Page, name: string) => page.locator('#personajes').locator('article, .card, fieldset')
  .filter({ has: page.getByRole('heading', { name, exact: true }) });

test('the voice preview speaks the line in the browser and calls no server', async ({ page }) => {
  const { calls } = await open(page);
  const oso = card(page, 'El Oso');
  await expect(oso.getByLabel('Frase para escuchar')).toHaveValue(/El Oso/);
  await oso.getByLabel('Frase para escuchar').fill('No hay respuestas buenas ni malas.');
  const before = calls.length;
  await oso.getByRole('button', { name: 'Escuchar voz' }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { __spoken: unknown[] }).__spoken.length)).toBe(1);
  const spoken = await page.evaluate(() => (window as unknown as { __spoken: { text: string; lang: string }[] }).__spoken[0]);
  expect(spoken.text).toBe('No hay respuestas buenas ni malas.');
  expect(spoken.lang).toBe('es-MX');
  expect(calls.slice(before).map((r) => r.url())).toEqual([]);                           // no server voice (F-003)
  await oso.getByLabel('Idioma').selectOption('en');
  await oso.getByRole('button', { name: 'Escuchar voz' }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { __spoken: { lang: string }[] }).__spoken[1]?.lang)).toBe('en-US');
});

test('a theme host is previewed in its own voice: Doña Tortuga lower and slower', async ({ page }) => {
  await open(page);
  const tortuga = card(page, 'Doña Tortuga');
  await expect(tortuga.getByLabel('Frase para escuchar')).toHaveValue(/Doña Tortuga/);
  await tortuga.getByRole('button', { name: 'Escuchar voz' }).click();
  await expect.poll(() => page.evaluate(() => (window as unknown as { __spoken: unknown[] }).__spoken.length)).toBe(1);
  const spoken = await page.evaluate(() => (window as unknown as { __spoken: { lang: string; pitch: number; rate: number }[] }).__spoken[0]);
  expect(spoken.lang).toMatch(/^es-/);
  expect(spoken.pitch).toBeLessThan(1);
  expect(spoken.rate).toBeLessThan(1);
});

test('turning Piñata off and La Calavera cannot be turned off', async ({ page }) => {
  const { patches } = await open(page);
  await expect(card(page, 'La Calavera').getByLabel('Activo')).toBeDisabled();
  await expect(card(page, 'La Calavera').getByText('La Calavera no se puede desactivar.')).toBeVisible();
  const pinata = card(page, 'Piñata');
  await pinata.getByLabel('Activo').uncheck();
  await pinata.getByRole('button', { name: 'Guardar' }).click();
  await expect.poll(() => patches.length).toBe(1);
  expect(patches[0].method()).toBe('PATCH');
  expect(patches[0].url()).toMatch(/\/characters\/pinata$/);
  expect(patches[0].postDataJSON()).toEqual({ enabled: false, units: ['games'] });
});

test('assigning a unit sends the new list', async ({ page }) => {
  const { patches } = await open(page);
  const oso = card(page, 'El Oso');
  await expect(oso.getByLabel('La directiva de salud')).toBeChecked();
  await oso.getByLabel('El poder notarial').check();
  await oso.getByRole('button', { name: 'Guardar' }).click();
  await expect.poll(() => patches.length).toBe(1);
  expect(patches[0].url()).toMatch(/\/characters\/oso$/);
  const sent = patches[0].postDataJSON();
  expect(sent.enabled).toBe(true);
  expect([...sent.units].sort()).toEqual(['ahcd', 'poa', 'sensitive']);
});
