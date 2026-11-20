import { test, expect } from '@playwright/test';

// T7-06 acceptance (Opus, t7-tests): web/admin.html#analitica (docs/tickets/T7-06.md); the API is played back.
const ADMIN = `http://127.0.0.1:${process.env.E2E_ADMIN_PORT || '5174'}`;

test('the dashboard shows completion, drop-off, accuracy, conversion and on-time completion', async ({ page }) => {
  const user = { id: 'par', role: 'paralegal', name: 'Rosa Paralegal', email: 'p@example.com' };
  await page.addInitScript((u) => { localStorage.setItem('carbon_token', 'tok'); localStorage.setItem('carbon_user', JSON.stringify(u)); }, user);
  await page.route('https://carbon-law.onrender.com/**', (r) => r.fulfill({ json: [] }));
  await page.route('**/auth/me', (r) => r.fulfill({ json: user }));
  await page.route(/\/staff\/analytics(\?.*)?$/, (r) => r.fulfill({ json: {
    lessons: [{ lesson_id: 'will', started: 12, completed: 9, completion_rate: 0.75, dropped_before_first_item: 1 }],
    items: [{ item_id: 'will.2.3', lesson_id: 'will', answered: 11, first_try_correct: 4, accuracy: 0.364, drop_off: 2 },
      { item_id: 'will.2.4', lesson_id: 'will', answered: 0, first_try_correct: 0, accuracy: null, drop_off: 0 }],
    conversion: { journeys: 12, paid: 3, rate: 0.25 },
    on_time: { finished: 2, on_time: 1, rate: 0.5 } } }));
  await page.goto(`${ADMIN}/admin.html#analitica`);
  const s = page.locator('#analitica');
  await expect(s.getByRole('heading', { name: 'Analítica' })).toBeVisible();
  for (const h of ['Lección', 'Empezaron', 'Terminaron', '% terminaron', 'Dejaron antes de empezar',
    'Pregunta', 'Respondieron', 'Acertaron a la primera', '% acierto', 'Dejaron aquí']) {
    await expect(s.getByRole('columnheader', { name: h, exact: true })).toBeVisible();
  }
  const lesson = s.getByRole('row').filter({ hasText: 'will' }).first();
  await expect(lesson).toContainText('12');
  await expect(lesson).toContainText('75');
  const confusing = s.getByRole('row').filter({ hasText: 'will.2.3' });
  await expect(confusing).toContainText('36');
  await expect(confusing.getByRole('cell').last()).toHaveText('2');
  await expect(s.getByRole('row').filter({ hasText: 'will.2.4' })).toContainText('—');
  await expect(s.getByText('Pagaron: 3 de 12 (25 %)')).toBeVisible();
  await expect(s.getByText('Terminaron a tiempo: 1 de 2 (50 %)')).toBeVisible();
});
