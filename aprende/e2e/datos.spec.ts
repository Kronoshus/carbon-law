import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

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

const api = (page: Page, path: string, init: object = {}) => page.evaluate(async ([p, i]) => {
  const tok = localStorage.getItem('aprende_token');
  const r = await fetch(p as string, { ...(i as object), headers: { Authorization: `Bearer ${tok}`, 'Content-Type': 'application/json' } });
  return r.json();
}, [path, init] as const);

const axeClean = async (page: Page) => {
  const axe = await new AxeBuilder({ page }).exclude('canvas').analyze();
  expect(axe.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
};

test('Tus datos: the character asks, the client answers or skips, one question at a time', async ({ page }) => {
  await cleared(page);
  const bodies: { messages: { role: string; content: string; question_id?: string }[]; group: string; mode: string }[] = [];
  const replies = [
    { text: 'Sobre el poder para finanzas: ¿a quién quiere nombrar como apoderado?', next: 'poder_agente' },
    { text: 'Gracias. ¿Quiere que pueda actuar desde que firme?', next: 'poder_inicio' },
    { text: '', next: null },
  ];
  await page.route('**/chat', async (route) => {          // no model call in tests: the server's reply is played back
    bodies.push(route.request().postDataJSON());
    const r = replies[Math.min(bodies.length - 1, replies.length - 1)];
    await route.fulfill({ json: { text: r.text, history: r.text, reasoning: null, covered: [], open: [], docs: [],
      attorney_question: false, next_question: r.next ? { id: r.next, text: '' } : null } });
  });
  await page.goto('/#/datos/poa');
  await expect(page.getByText('¿a quién quiere nombrar como apoderado?')).toBeVisible();
  await expect(page.getByText('Pregunta 1 de 4')).toBeVisible();
  expect(bodies[0]).toMatchObject({ mode: 'intake', group: 'poa' });
  await axeClean(page);

  await page.getByLabel('Su respuesta').fill('Mi hija Sofía Torres');
  await page.getByRole('button', { name: 'Enviar' }).click();
  await expect(page.getByText('¿Quiere que pueda actuar desde que firme?')).toBeVisible();
  await expect(page.getByText('Mi hija Sofía Torres')).toBeVisible();                     // the client's words stay on screen
  const sent = bodies[1].messages;
  expect(sent[sent.length - 1]).toMatchObject({ role: 'user', content: 'Mi hija Sofía Torres', question_id: 'poder_agente' });
  expect(sent.some((m) => m.role === 'assistant')).toBe(true);                          // the history goes back each turn

  const skip = page.waitForRequest((r) => r.url().endsWith('/datos/poder_inicio') && r.method() === 'PUT');
  await page.getByRole('button', { name: 'Saltar' }).click();
  expect((await skip).postDataJSON()).toEqual({ skipped: true });
  await expect(page.getByRole('heading', { name: '¡Listo! Ya tenemos sus respuestas de esta lección.' })).toBeVisible();
  const d = await api(page, '/datos');
  expect(d.questions.find((q: { id: string }) => q.id === 'poder_inicio').status).toBe('skipped');
});

test('document choice: "No sé todavía" means all four', async ({ page }) => {
  await cleared(page);
  await page.goto('/#/documentos');
  await expect(page.getByRole('heading', { name: '¿Qué documentos le interesan?' })).toBeVisible();
  await page.getByLabel('No sé todavía').check();
  await axeClean(page);
  await page.getByRole('button', { name: 'Guardar mi elección' }).click();
  await expect(page).toHaveURL(/#\/aprender/);
  expect([...(await api(page, '/journey')).documents.tentative].sort()).toEqual(['ahcd', 'poa', 'trust', 'will']);
});

test('the summary: answers by document, a correction, the gaps, and confirming', async ({ page }) => {
  await cleared(page);
  await api(page, '/journey/events', { method: 'POST', body: JSON.stringify({ type: 'documents_tentative', payload: { codes: ['will'] } }) });
  await api(page, '/datos/nombre', { method: 'PUT', body: JSON.stringify({ answer: 'Ana Torres' }) });
  await api(page, '/datos/nacimiento', { method: 'PUT', body: JSON.stringify({ skipped: true }) });
  await page.goto('/#/resumen');
  await expect(page.getByRole('heading', { name: 'Su resumen' })).toBeVisible();
  await expect(page.getByText('Ana Torres', { exact: true })).toBeVisible();
  await expect(page.getByText('La saltó')).toBeVisible();
  await expect(page.getByText(/Faltan \d+ respuestas\./)).toBeVisible();
  await axeClean(page);
  await page.getByRole('button', { name: /Corregir/ }).first().click();
  await page.getByRole('textbox').first().fill('Ana María Torres');
  await page.getByRole('button', { name: 'Guardar' }).click();
  await expect(page.getByText('Ana María Torres', { exact: true })).toBeVisible();
  expect((await api(page, '/datos')).questions.find((q: { id: string }) => q.id === 'nombre').answer).toBe('Ana María Torres');
  await page.getByRole('button', { name: 'Confirmar mis documentos' }).click();
  await expect(page.getByText('Documentos confirmados', { exact: false })).toBeVisible();
  expect((await api(page, '/journey')).documents.confirmed).toEqual(['will']);
});


test('after the character thanks her for an answer, the next question is on screen', async ({ page }) => {
  await cleared(page);
  let turn = 0;
  // As the persona asks (personas.yaml, intake mode): once the answer is complete the character only thanks the client and
  // tags [DONE]; it does not know the next question. The server's reply names the next question.
  await page.route('**/chat', async (route) => {
    turn += 1;
    const first = turn === 1;
    await route.fulfill({ json: { text: first ? '¿A quién quiere nombrar como apoderado?' : 'Gracias, lo anoté.',
      history: first ? '¿A quién quiere nombrar como apoderado?' : 'Gracias, lo anoté. [DONE: poder_agente]', reasoning: null,
      covered: first ? [] : ['poder_agente'], open: [], docs: [], attorney_question: false,
      next_question: first ? { id: 'poder_agente', text: 'texto del servidor 1' }
        : { id: 'poder_inicio', text: '¿Quiere que su apoderado pueda actuar desde que usted firme?' } } });
  });
  await page.goto('/#/datos/poa');
  await expect(page.getByText('¿A quién quiere nombrar como apoderado?')).toBeVisible();
  await page.getByLabel('Su respuesta').fill('Mi hija Sofía Torres');
  await page.getByRole('button', { name: 'Enviar' }).click();
  await expect(page.getByText('Gracias, lo anoté.')).toBeVisible();
  await expect(page.locator('.transcript li.them').last()).toHaveText('¿Quiere que su apoderado pueda actuar desde que usted firme?');
});
