import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const ATTORNEY = { email: 'attorney-e2e@example.com', password: 'attorney-e2e-password' };   // seeded by scripts/seed-e2e-content.py

async function signUp(page: Page) {
  await page.goto('/#/cuenta-nueva');
  await page.getByLabel(/Nombre/i).fill('Ana Torres');
  await page.getByLabel(/Correo/i).fill(`ana-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`);
  await page.getByLabel(/Contraseña/i).fill('long-secure-password');
  await page.getByLabel(/mayor de 18/i).check();
  await page.getByRole('button', { name: /Crear cuenta/i }).click();
  await expect(page).toHaveURL(/#\/inicio\/ia/);
}

/** Runs in the page: the client's own calls with her token, and the attorney's calls with his. */
async function firmSteps(page: Page, steps: string[]) {
  await page.evaluate(async ([s, att]) => {
    const tok = localStorage.getItem('aprende_token');
    const json = (t: string | null) => ({ Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' });
    const me = async (type: string, payload: object) => fetch('/journey/events', { method: 'POST', headers: json(tok), body: JSON.stringify({ type, payload }) });
    const a = (await (await fetch('/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(att) })).json()).token;
    const jid = (await (await fetch('/journey', { headers: json(tok) })).json()).id;
    for (const step of s as string[]) {
      if (step === 'ready') {
        await me('ai_disclosed', {}); await me('consent', { answer: 'yes' }); await me('names_submitted', { names: ['Ana Torres'] });
        await fetch(`/conflicts/${jid}/decision`, { method: 'POST', headers: json(a), body: JSON.stringify({ result: 'cleared' }) });
        await me('documents_confirmed', { codes: ['will'] });
        await fetch(`/staff/journeys/${jid}/scope-approval`, { method: 'POST', headers: json(a) });
      }
      if (step === 'countersign') await fetch(`/staff/journeys/${jid}/engagement/countersign`, { method: 'POST', headers: json(a) });
    }
  }, [steps, ATTORNEY] as const);
}

test('the client reads and signs the agreement; the copy comes after the attorney signs', async ({ page }) => {
  await signUp(page);
  await page.goto('/#/acuerdo');
  await expect(page.getByText('Su acuerdo estará listo cuando el abogado Raval apruebe sus documentos', { exact: false })).toBeVisible();

  await firmSteps(page, ['ready']);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Su acuerdo con la oficina' })).toBeVisible();
  await expect(page.locator('.letter')).toContainText('Ana Torres');
  await expect(page.locator('.letter')).toContainText('Testamento');
  const axe = await new AxeBuilder({ page }).exclude('canvas').analyze();
  expect(axe.violations.map((v) => v.id)).toEqual([]);

  const sign = page.getByRole('button', { name: 'Firmar' });
  await expect(sign).toBeDisabled();
  await page.getByLabel('Escriba su nombre completo').fill('Ana Torres');
  await expect(sign).toBeDisabled();
  await page.getByLabel('Leí este acuerdo y lo acepto').check();
  await sign.click();
  await expect(page.getByText('Usted firmó el acuerdo', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Descargar mi copia (PDF)' })).toHaveCount(0);   // § 6148: a copy signed by both

  await firmSteps(page, ['countersign']);
  await page.reload();
  await expect(page.getByText('Firmado por usted y por el abogado Raval.')).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Descargar mi copia (PDF)' }).click();
  expect((await download).suggestedFilename()).toMatch(/\.pdf$/);
  await expect(page.getByRole('button', { name: 'Ir a pagar' })).toBeVisible();
});
