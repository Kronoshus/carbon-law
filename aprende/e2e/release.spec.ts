import { test, expect, type BrowserContext, type Page } from '@playwright/test';
import {
  asClient, asStaff, addDays, attorneyApproves, dbCounts, disclosureAndConsent, FAKES, giveNames, journey, laTime, modelCalls,
  moveTo, nextWeekday, openAdminReview, releaseJourney, serverNow, signUp, type ClientApp,
} from './journey-steps';

// T8-06 (Opus): the release criteria of brief section 5, end to end, on a phone, in Spanish, on the fake clock.
// Runs in the "release" project: after every other test, one test at a time (the clock is the whole backend's).
test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'es-US', timezoneId: 'America/Los_Angeles' });

async function phone(page: Page, context: BrowserContext): Promise<ClientApp> {
  await context.clock.install({ time: await serverNow() });
  return { page, context, go: async (hash) => { await page.goto(`/#${hash}`); },
    token: async () => (await page.evaluate(() => localStorage.getItem('aprende_token')))! };
}

for (const [weekday, label] of [[3, 'Wednesday'], [4, 'Thursday']] as const) {
  test(`a new client who starts on a ${label} goes through the whole journey, each step on its planned day`, async ({ page, context }) => {
    const c = await phone(page, context);
    const start = await nextWeekday(weekday);
    await releaseJourney(c, start);
  });
}

test('a late attorney review raises the staff alert once, and the client only reads a calm sentence', async ({ page, context }) => {
  const c = await phone(page, context);
  const start = await nextWeekday(3);
  let jid = '';
  await test.step('Mateo signs up, clears the checks, and signs his letter (the steps before payment, mostly by fixture)', async () => {
    await moveTo(c, laTime(start));
    await signUp(c, 'Mateo Torres');
    await disclosureAndConsent(c, 'Sí, acepto');
    await giveNames(c, ['Mateo Torres']);
    jid = (await journey(c)).id;
    await asClient(c, 'POST', '/journey/events', { type: 'documents_confirmed', payload: { codes: ['will'] } });
    await asStaff('paralegal', 'POST', `/conflicts/${jid}/decision`, { result: 'cleared' });
    await asStaff('attorney', 'POST', `/staff/journeys/${jid}/scope-approval`);
    const letter = (await asClient(c, 'GET', '/engagement')).body;
    expect((await asClient(c, 'POST', '/engagement/sign', { name: 'Mateo Torres', accept: true, sha256: letter.sha256 })).status).toBe(200);
    await asStaff('attorney', 'POST', `/staff/journeys/${jid}/engagement/countersign`);
  });
  await test.step('Mateo pays on day 5; the drafts reach the queue', async () => {
    await moveTo(c, laTime(addDays(start, 4)));
    const { url } = (await asClient(c, 'POST', '/payments/checkout')).body;
    await page.goto(url);
    await page.getByRole('button', { name: 'Pagar (prueba)' }).click();
    await expect(page.getByText('¡Pago recibido!', { exact: false })).toBeVisible();
    await expect.poll(async () => ((await asStaff('attorney', 'GET', '/staff/review-queue')).body as { journey_id: string }[])
      .some((r) => r.journey_id === jid), { timeout: 60_000 }).toBe(true);
  });
  const due = (await journey(c)).timeline.find((s) => s.step === 'attorney_review')!.due!;
  await test.step(`On the due date (${due}) the review is not late yet`, async () => {
    await moveTo(c, laTime(due, 16));
    await page.waitForTimeout(3000);                                     // the worker runs the hourly check within a second or two
    expect((await asStaff('paralegal', 'GET', `/staff/journeys/${jid}`)).body.late).toEqual([]);
  });
  await test.step('The next morning, with no approval, staff get the alert: a flag on the dashboard and in the review queue', async () => {
    await moveTo(c, laTime(addDays(due, 1), 9));
    await expect.poll(async () => (await asStaff('paralegal', 'GET', `/staff/journeys/${jid}`)).body.late, { timeout: 30_000 })
      .toEqual(['attorney_review']);
    expect(dbCounts(jid).timeline_alerts).toBe(1);
    const admin = await openAdminReview(context);
    await expect(admin.getByRole('row').filter({ has: admin.getByRole('button', { name: 'Mateo Torres', exact: true }) })).toContainText('⚠');
    await admin.close();
  });
  await test.step('An hour later the check runs again, and the alert is not sent twice', async () => {
    await moveTo(c, laTime(addDays(due, 1), 11));
    await page.waitForTimeout(3000);
    expect(dbCounts(jid).timeline_alerts).toBe(1);
  });
  await test.step('Mateo sees "the office is a little behind", with no alarm', async () => {
    await c.go('/plan');
    await expect(page.getByText('La oficina va un poco atrasada con este paso.', { exact: false })).toBeVisible();
    await expect(page.getByText(/atrasad[oa]/i)).toHaveCount(1);
  });
});

test('a refusal to record keeps nothing, and the lessons still work', async ({ page, context }) => {
  const c = await phone(page, context);
  await moveTo(c, laTime(await nextWeekday(3)));
  const calls = await modelCalls();
  await signUp(c, 'Luis Torres');
  await disclosureAndConsent(c, 'No, no acepto');
  await expect(page.getByRole('heading', { name: 'Está bien. No guardamos nada.' })).toBeVisible();
  const jid = (await journey(c)).id;
  await test.step('The server refuses names, details and chat', async () => {
    expect((await asClient(c, 'POST', '/journey/events', { type: 'names_submitted', payload: { names: ['Luis Torres'] } })).status).toBe(409);
    expect((await asClient(c, 'PUT', '/datos/nombre', { answer: 'Luis Torres' })).status).toBe(409);
    expect((await asClient(c, 'POST', '/chat', { mode: 'intake', character: 'calavera', group: 'will', messages: [] })).status).toBe(409);
  });
  await test.step('The database holds nothing about Luis but the two answers he gave', async () => {
    const db = dbCounts(jid);
    expect(db.events).toEqual(['ai_disclosed', 'consent']);
    for (const table of ['conflict_checks', 'conflict_names', 'datos_answers', 'datos_audit', 'attorney_questions', 'legacy_matters', 'legacy_documents']) {
      expect(db[table] ?? 0, table).toBe(0);
    }
    expect(await modelCalls(), 'no model call').toBe(calls);
  });
  await test.step('The will lesson still opens in learning-only mode', async () => {
    await c.go('/leccion/will');
    await expect(page.locator('.bubble')).toContainText('Un testamento no es solo para quien tiene mucho');
  });
});

test('a possible conflict stops the flow without saying why', async ({ page, context }) => {
  const c = await phone(page, context);
  await moveTo(c, laTime(await nextWeekday(3)));
  const calls = await modelCalls();
  await signUp(c, 'Sofía Torres');
  await disclosureAndConsent(c, 'Sí, acepto');
  await giveNames(c, ['Sofía Torres', 'Roberto Mendes']);                // close to a name on the seed's conflict list
  await test.step('Sofía reads the same neutral wait as any client, with no reason and no name', async () => {
    await expect(page.getByText('La oficina está revisando los nombres', { exact: false })).toBeVisible();
    expect(JSON.stringify(await journey(c))).not.toMatch(/possible|M[eé]nde[sz]|conflict_auto_result/);
  });
  await test.step('Details, chat and the letter stay closed, and no model is called', async () => {
    expect((await asClient(c, 'GET', '/datos')).status).toBe(409);
    expect((await asClient(c, 'POST', '/chat', { mode: 'intake', character: 'calavera', group: 'will', messages: [] })).status).toBe(409);
    expect((await asClient(c, 'GET', '/engagement')).status).toBe(409);
    expect((await asClient(c, 'POST', '/payments/checkout')).status).toBe(409);
    expect(await modelCalls()).toBe(calls);
  });
  await test.step('Staff see the hold in the conflict queue', async () => {
    const queue = JSON.stringify((await asStaff('paralegal', 'GET', '/conflicts/queue')).body);
    expect(queue).toContain((await journey(c)).id);
  });
  await test.step('The lessons stay readable', async () => {
    await c.go('/leccion/will');
    await expect(page.locator('.bubble')).toContainText('Un testamento no es solo para quien tiene mucho');
  });
});

test('no payment before the firm clears the conflict and the attorney countersigns', async ({ page, context }) => {
  const c = await phone(page, context);
  await moveTo(c, laTime(await nextWeekday(3)));
  await signUp(c, 'Ana Torres');
  await disclosureAndConsent(c, 'Sí, acepto');
  await giveNames(c, ['Ana Torres']);
  const jid = (await journey(c)).id;
  await asClient(c, 'POST', '/journey/events', { type: 'documents_confirmed', payload: { codes: ['will'] } });
  const early = async () => {
    expect((await asClient(c, 'POST', '/payments/checkout')).status).toBe(409);
    const r = await (await page.request.post(`${FAKES}/webhook`, { data: { journey_id: jid, amount_total: 250000, session_id: `cs_early_${Date.now()}` } })).json();
    expect(r.status).toBe(200);                                         // Stripe gets its 200, and nothing is recorded
    expect(dbCounts(jid).payments).toBe(0);
    expect(Object.keys((await journey(c)).facts)).not.toContain('paid');
  };
  await test.step('Before the firm clears the conflict: no checkout, and a signed webhook records nothing', early);
  await test.step('After clearance, scope and her signature, but before the countersignature: still nothing', async () => {
    await asStaff('paralegal', 'POST', `/conflicts/${jid}/decision`, { result: 'cleared' });
    await asStaff('attorney', 'POST', `/staff/journeys/${jid}/scope-approval`);
    const letter = (await asClient(c, 'GET', '/engagement')).body;
    expect((await asClient(c, 'POST', '/engagement/sign', { name: 'Ana Torres', accept: true, sha256: letter.sha256 })).status).toBe(200);
    await early();
    await c.go('/pago');
    await expect(page.getByText('Podrá pagar cuando usted y el abogado Raval hayan firmado el acuerdo.')).toBeVisible();
  });
  await test.step('After the countersignature, checkout opens', async () => {
    await asStaff('attorney', 'POST', `/staff/journeys/${jid}/engagement/countersign`);
    expect((await asClient(c, 'POST', '/payments/checkout')).status).toBe(200);
  });
});

test('no draft is visible to the client before the attorney approves it', async ({ page, context }) => {
  const c = await phone(page, context);
  await moveTo(c, laTime(await nextWeekday(3)));
  await signUp(c, 'Ana Torres');
  await disclosureAndConsent(c, 'Sí, acepto');
  await giveNames(c, ['Ana Torres']);
  const j = await journey(c);
  await asClient(c, 'POST', '/journey/events', { type: 'documents_confirmed', payload: { codes: ['will'] } });
  await asStaff('paralegal', 'POST', `/conflicts/${j.id}/decision`, { result: 'cleared' });
  await asStaff('attorney', 'POST', `/staff/journeys/${j.id}/scope-approval`);
  const letter = (await asClient(c, 'GET', '/engagement')).body;
  await asClient(c, 'POST', '/engagement/sign', { name: 'Ana Torres', accept: true, sha256: letter.sha256 });
  await asStaff('attorney', 'POST', `/staff/journeys/${j.id}/engagement/countersign`);
  await page.goto((await asClient(c, 'POST', '/payments/checkout')).body.url);
  await page.getByRole('button', { name: 'Pagar (prueba)' }).click();
  await test.step('The draft is written and waits in the attorney queue', async () => {
    await expect.poll(async () => ((await asStaff('attorney', 'GET', '/staff/review-queue')).body as { journey_id: string }[])
      .some((r) => r.journey_id === j.id), { timeout: 60_000 }).toBe(true);
  });
  await test.step('Ana sees only "your documents will appear here", and the API gives her nothing', async () => {
    await c.go('/revisar');
    await expect(page.getByText('Sus documentos aparecerán aquí cuando el abogado Raval los apruebe.')).toBeVisible();
    await expect(page.getByText('LAST WILL', { exact: false })).toHaveCount(0);
    expect((await asClient(c, 'GET', '/review/documents')).status).toBe(409);
    expect((await asClient(c, 'GET', '/documents')).body).toEqual([]);
    const mine = (await asClient(c, 'GET', `/staff/drafts/${'x'}`)).status;
    expect([401, 403]).toContain(mine);                                 // the staff route refuses a client
  });
  await test.step('After the attorney approves, the document appears', async () => {
    const mid = j.matter_id || (await journey(c)).matter_id;
    const attorneyId = (await asStaff('attorney', 'GET', '/auth/me')).body.id;
    await asStaff('paralegal', 'PATCH', `/matters/${mid}`, { attorney_reviewer: attorneyId });
    await attorneyApproves(context, 'Ana Torres');
    await c.go('/revisar');
    await expect(page.getByRole('heading', { name: 'Revise sus documentos' })).toBeVisible();
  });
});
