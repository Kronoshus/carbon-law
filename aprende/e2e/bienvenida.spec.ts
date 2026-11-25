import { test, expect } from '@playwright/test';

// APP-01: the welcome page is the app's front door. The theme's host stands on its stage, large, and the promise and both
// ways in are on the first screen, on a phone and on a laptop.
for (const [w, h] of [[390, 844], [1280, 800]]) {
  for (const [theme, host] of [['muertos', 'La Calavera'], ['sol', 'Girasol']]) {
    test(`${theme} at ${w}px: the host on a large stage, the promise and both actions on the first screen`, async ({ page }) => {
      await page.addInitScript((t) => localStorage.setItem('aprende_theme', t), theme);
      await page.setViewportSize({ width: w, height: h });
      await page.goto('/#/bienvenida');
      const stage = page.getByRole('figure', { name: new RegExp(`^${host},`) });
      await expect(stage).toBeInViewport({ ratio: 1 });
      expect((await stage.boundingBox())!.width).toBeGreaterThan(w < 600 ? 300 : 400);
      await expect(page.getByRole('heading', { level: 1, name: 'Entienda su plan patrimonial, lección por lección.' })).toBeInViewport();
      for (const name of ['Crear cuenta', 'Iniciar sesión']) await expect(page.getByRole('link', { name })).toBeInViewport({ ratio: 1 });
      await expect(page.getByText('Información general, no asesoría legal.', { exact: false })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Aviso de privacidad' })).toBeVisible();
    });
  }
}
