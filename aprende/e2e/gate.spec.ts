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

const axeClean = async (page: Page) => {
  const axe = await new AxeBuilder({ page }).exclude('canvas').analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
};

async function journey(page: Page) {
  return page.evaluate(async () => {
    const tok = localStorage.getItem('aprende_token');
    return (await fetch('/journey', { headers: { Authorization: `Bearer ${tok}` } })).json();
  });
}

async function answer(page: Page, text: string) {
  await page.getByLabel('Su respuesta, con sus palabras').fill(text);
  await page.getByRole('button', { name: 'Responder' }).click();
}

async function toConsent(page: Page) {
  await signUp(page);
  await expect(page.getByText('No soy el abogado ni una persona', { exact: false })).toBeVisible();
  await axeClean(page);
  await page.getByRole('button', { name: 'Entendido' }).click();
  await expect(page.getByRole('heading', { name: '¿Podemos guardar lo que conversemos?' })).toBeVisible();
  await axeClean(page);
}

test('a clear yes leads to the names, and the names to a neutral wait', async ({ page }) => {
  await toConsent(page);
  await answer(page, 'Sí, acepto');
  await expect(page.getByRole('heading', { name: '¿Quiénes son las personas de su familia?' })).toBeVisible();
  await page.getByLabel('Nombre completo 1').fill('Ana Torres');
  await page.getByRole('button', { name: 'Agregar otro nombre' }).click();
  await page.getByLabel('Nombre completo 2').fill('Roberto Mendes');      // close to a name on the seed's list
  await axeClean(page);
  await page.getByRole('button', { name: 'Continuar' }).click();
  await expect(page.getByText('La oficina está revisando los nombres', { exact: false })).toBeVisible();   // a hold looks like any wait
  const j = await journey(page);
  expect(j.facts.consent_answer).toBe('yes');
  expect(Object.keys(j.facts)).toContain('names_submitted');
  expect(JSON.stringify(j)).not.toMatch(/possible|M[eé]ndez|Mendes|no_list/);
});

test('"No, no acepto" is a refusal: learning only, and it can be changed', async ({ page }) => {
  await toConsent(page);
  await answer(page, 'No, no acepto');
  await expect(page.getByRole('heading', { name: 'Está bien. No guardamos nada.' })).toBeVisible();
  expect((await journey(page)).facts.consent_answer).toBe('no');
  await axeClean(page);
  await page.getByRole('button', { name: 'Cambiar mi respuesta' }).click();
  await page.getByRole('button', { name: 'Sí, acepto' }).click();
  await expect(page.getByRole('heading', { name: '¿Quiénes son las personas de su familia?' })).toBeVisible();
});

test('an unclear answer is asked once more, and unclear twice counts as no', async ({ page }) => {
  await toConsent(page);
  await answer(page, 'mmm');
  await expect(page.getByText('Perdone, no le entendí', { exact: false })).toBeVisible();
  expect((await journey(page)).facts.consent).toBeUndefined();          // nothing recorded yet
  await answer(page, 'tal vez');
  await expect(page.getByRole('heading', { name: 'Está bien. No guardamos nada.' })).toBeVisible();
  expect((await journey(page)).facts.consent_answer).toBe('no');
  await page.getByRole('button', { name: 'Ir a las lecciones' }).click();
  await expect(page).toHaveURL(/#\/aprender/);
});
