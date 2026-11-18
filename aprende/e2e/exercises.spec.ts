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

test('match pairs (Piñata), by click', async ({ page }) => {
  await signUp(page);
  await page.evaluate(() => localStorage.setItem('aprende.lesson.will', JSON.stringify({ step: 1, item: 'will.2.5' })));
  await page.goto('/#/leccion/will');
  await expect(page.getByRole('heading', { name: 'Una cada palabra con su significado' })).toBeVisible();
  const check = page.getByRole('button', { name: 'Comprobar' });
  await expect(check).toBeDisabled();
  const pairs: [string, string][] = [['Albacea', 'Cumple el testamento'], ['Testigo', 'Ve cómo usted firma'],
    ['Beneficiario', 'Recibe sus bienes'], ['Resto', 'Lo que queda después de los regalos']];
  await page.getByRole('button', { name: 'Albacea' }).click();
  await page.getByRole('button', { name: 'Recibe sus bienes' }).click();                 // a wrong pair...
  await page.getByRole('button', { name: /Recibe sus bienes/ }).click();                 // ...undone
  for (const [a, b] of pairs) {
    await page.getByRole('button', { name: new RegExp(`^(pareja \\d )?${a}$`) }).click();
    await page.getByRole('button', { name: new RegExp(`^(pareja \\d )?${b}$`) }).click();
  }
  await axeClean(page);
  await check.click();
  await expect(page.locator('.feedback')).toContainText('¡Muy bien!');
});

test('put the steps in order, by keyboard only', async ({ page }) => {
  await signUp(page);
  await page.evaluate(() => localStorage.setItem('aprende.lesson.will', JSON.stringify({ step: 4, item: 'will.5.7' })));
  await page.goto('/#/leccion/will');
  await expect(page.getByRole('heading', { name: 'Ordene los pasos para hacer un testamento' })).toBeVisible();
  const want = ['Pensar a quién dejar sus bienes', 'Elegir a su albacea y al tutor', 'Firmar con dos testigos', 'Guardar el original en un lugar seguro'];
  for (let target = 0; target < want.length; target++) {             // selection sort with the keyboard
    for (;;) {
      const rows = await page.locator('.order-text').allTextContents();
      const at = rows.indexOf(want[target]);
      if (at === target) break;
      await page.getByRole('button', { name: `Subir «${want[target]}»` }).focus();
      await page.keyboard.press('Enter');
    }
  }
  await expect(page.locator('.order-text')).toHaveText(want);
  await axeClean(page);
  await page.getByRole('button', { name: 'Comprobar' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.feedback')).toContainText('¡Muy bien!');
});
