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

const doc = (id: string, name: string) => ({ id, name, version: 1, decision: null as string | null,
  content: '# LAST WILL\n\n## ARTICLE ONE\n\nDeclarations.\n\n<script>window.__pwned = 1</script><img src=x onerror="window.__pwned=2">',
  summary: [{ article: 1, text: 'Quién es usted, dónde vive y quiénes son su familia.' }, { article: 2, text: 'Lo que significan algunas palabras.' }] });

test('the client reads the summary, approves one document and asks a change on the other; nothing in a document runs', async ({ page }) => {
  await signUp(page);
  const docs = [doc('d1', 'Last will and testament'), doc('d2', 'Advance health care directive')];
  const posts: { id: string; body: Record<string, string> }[] = [];
  await page.route('**/review/documents?*', (r) => r.fulfill({ json: { documents: docs } }));
  await page.route(/\/review\/documents\/d[12]$/, async (r) => {
    const id = r.request().url().split('/').pop()!;
    const body = r.request().postDataJSON();
    posts.push({ id, body });
    docs.find((d) => d.id === id)!.decision = body.decision;
    await r.fulfill({ json: { ok: true } });
  });
  await page.goto('/#/revisar');
  await expect(page.getByRole('heading', { name: 'Revise sus documentos' })).toBeVisible();
  await expect(page.getByText('Quién es usted, dónde vive y quiénes son su familia.').first()).toBeVisible();
  const axe = await new AxeBuilder({ page }).exclude('canvas').analyze();
  expect(axe.violations.map((v) => v.id)).toEqual([]);

  const will = page.getByRole('region', { name: 'Last will and testament' });
  await will.getByText('Ver el documento completo').click();
  await expect(will.getByText('<script>window.__pwned = 1</script>', { exact: false })).toBeVisible();   // shown as text
  expect(await page.evaluate(() => (window as unknown as { __pwned?: number }).__pwned)).toBeUndefined();
  await will.getByRole('button', { name: 'Está bien' }).click();
  await expect(will.getByText('Usted dijo que está bien.')).toBeVisible();

  const ahcd = page.getByRole('region', { name: 'Advance health care directive' });
  await ahcd.getByRole('button', { name: 'Quiero un cambio' }).click();
  await ahcd.getByLabel('¿Qué quiere cambiar?').selectOption({ label: 'Quién está a cargo (albacea, fiduciario, agente)' });
  await ahcd.getByLabel('Cuéntenos el cambio con sus palabras').fill('Quiero que mi hija sea la agente.');
  await ahcd.getByRole('button', { name: 'Enviar el cambio al abogado' }).click();
  await expect(ahcd.getByText('Pidió un cambio.', { exact: false })).toBeVisible();
  expect(posts).toEqual([{ id: 'd1', body: { decision: 'ok' } },
    { id: 'd2', body: { decision: 'change', change_type: 'Fiduciary change', note: 'Quiero que mi hija sea la agente.' } }]);
});
