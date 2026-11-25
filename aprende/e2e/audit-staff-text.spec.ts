import { test, expect } from '@playwright/test';

// Audit (guardrail 7): every value the staff pages show comes from clients or staff, so each is rendered as text.
// web/admin.html calls the production API base; every answer is played back, each string field carrying markup.
const ADMIN = `http://127.0.0.1:${process.env.E2E_ADMIN_PORT || '5174'}`;
const X = (field: string) => `${field}<img src="x" class="pwn" onerror="window.__pwned = '${field}'"><script>window.__pwned = '${field}'</script>`;

const record = (i: string) => ({
  id: `id-${i}`, client_name: X('client_name'), related_names: [X('related_name')], stage: 'attorney_review',
  documents_requested: [X('document_requested')], staff_review_note: X('staff_review_note'),
  drafts: { [X('draft_name')]: { content: X('draft_content'), version: 1, status: 'Attorney Review' } },
  matter_id: X('matter_id'), owner: X('owner'), attorney_reviewer: null, risk_level: 'Low', priority: 'Normal',
  due_date: '2026-12-09', next_action: X('next_action'), change_type: X('change_type'), requested_by: X('requested_by'),
  status: 'Open', impact: X('impact'), resolution: X('resolution'), kind: X('kind'), note: X('note'),
  scheduled_at: '2026-12-09T17:00:00Z', name: X('name'), version: 1, content: X('content'), title: X('title'),
  blocker: X('blocker'), email: X('email'), phone: X('phone'), service: X('service'), message: X('message'),
  created_at: '2026-11-19T10:00:00', direction: X('direction'), channel: X('channel'), summary: X('summary'),
  visibility: 'internal', actor: X('actor'), action: X('action'), entity: X('entity'), entity_id: X('entity_id'),
  detail: X('detail'), time: '2026-11-19T10:00:00', role: 'attorney',
});

test('no client or staff text runs as markup on the staff pages', async ({ page }) => {
  const user = { id: 'att', role: 'admin', name: 'Pankaj Raval', email: 'a@example.com' };
  await page.addInitScript((u) => { localStorage.setItem('carbon_token', 'tok'); localStorage.setItem('carbon_user', JSON.stringify(u)); }, user);
  await page.route('https://carbon-law.onrender.com/**', (r) => {
    const path = new URL(r.request().url()).pathname;
    if (path === '/auth/me') return r.fulfill({ json: user });
    if (path === '/stages') return r.fulfill({ json: ['1 Intake', X('stage')] });
    if (path === '/reports/friday') return r.fulfill({ json: { total: 1, by_stage: { [X('by_stage')]: 1 } } });
    if (path === '/reports/capacity') return r.fulfill({ json: { by_owner: { [X('by_owner')]: { matters: 1, high_risk: 0, urgent: 0, overdue: 0 } } } });
    if (path === '/reports/bottlenecks') return r.fulfill({ json: { waiting_on_client: 0, blocked_matters: 0, open_change_requests: 0, top_stages: [[X('top_stage'), 1]] } });
    if (path === '/staff/review-queue') return r.fulfill({ json: [{ journey_id: 'j1', client_name: X('queue_client'), due: X('due'), late: true, note: X('review_note'), documents: [{ id: 'd1', name: X('doc_name'), version: 1 }] }] });
    if (path === '/staff/drafts/d1') return r.fulfill({ json: { id: 'd1', name: X('doc_name'), version: 1, content: `# ${X('title')}\n\n${X('draft_line')} [ATTORNEY TO CONFIRM - ${X('mark')}]` } });
    if (path.endsWith('/history')) return r.fulfill({ json: { stages: [{ stage: X('hist_stage'), time: '2026-11-19T10:00:00' }], tasks: [{ title: X('hist_task') }], changes: [{ change_type: X('hist_change'), status: 'Open' }], comms: [{ summary: X('hist_comm'), created_at: '2026-11-19T10:00:00' }] } });
    if (/^\/(prompts|templates)\/./.test(path)) return r.fulfill({ json: { name: X('file'), content: X('file_content') } });
    if (path === '/my-workflow' || /^\/(matters|change-requests|appointments|documents|tasks|contacts|communications|audit|staff|prompts|templates)$/.test(path))
      return r.fulfill({ json: [record('1'), { ...record('2'), stage: 'conflict_review' }] });
    return r.fulfill({ json: [] });
  });
  await page.goto(`${ADMIN}/admin.html#review`);
  await expect(page.locator('#workflowRows')).toContainText('client_name<img', { timeout: 20000 });
  await expect(page.locator('#reviewQueueRows')).toContainText('queue_client<img');
  await page.locator('#reviewQueueRows button').first().click();
  await expect(page.locator('#reviewDetail')).toContainText('draft_line<img');
  await page.getByRole('link', { name: 'Matters', exact: true }).click();
  await page.locator('[data-history]').first().click();
  await expect(page.locator('#historyContent')).toContainText('hist_comm<img');
  await page.keyboard.press('Escape');
  await page.getByRole('link', { name: 'Today', exact: true }).click();
  await page.locator('[data-review]').first().click();
  await expect(page.locator('#reviewDocuments')).toContainText('draft_content<img');
  await expect(page.locator('#contactRows')).toContainText('message<img');
  await expect(page.locator('#auditRows')).toContainText('detail<img');
  await expect(page.locator('img.pwn')).toHaveCount(0);
  await expect(page.locator('script:not([src])')).toHaveCount(1);                 // admin.html's own inline script only
  expect(await page.evaluate(() => (window as unknown as { __pwned?: string }).__pwned)).toBeUndefined();
});
