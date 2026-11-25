import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import { LoadFailed, problemOf, type LoadProblem } from '../LoadFailed';
import './datos.css';
import './pago.css';

const money = (cents: number) => `$${Math.floor(cents / 100).toLocaleString('en-US')}`;

/** Day 5: the server's total, then Stripe's own page. The app never sees a card number. */
export function Pago() {
  const [state, setState] = useState<{ may: boolean; paid: boolean; total: number; mode: string } | null>(null);
  const [problem, setProblem] = useState<LoadProblem | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const load = async () => {
    setProblem(null);
    const get = async (path: string) => {
      const r = await apiFetch(path).catch(() => null);
      if (r?.ok) return r.json();
      setProblem(problemOf(r));
      return null;
    };
    const j = await get('/journey');
    if (!j) return;
    const codes = j.documents.confirmed.join(',');
    const quote = codes ? await get(`/payments/quote?codes=${codes}`) : { total: 0 };
    const config = quote && await get('/payments/config');
    if (config) setState({ may: j.gates.may_pay, paid: !!j.facts.paid, total: quote.total, mode: config.mode });
  };
  useEffect(() => { void load(); }, []);
  const pay = async () => {
    setBusy(true); setFailed(false);
    const r = await apiFetch('/payments/checkout', { method: 'POST' }).catch(() => null);
    if (r?.ok) { location.assign((await r.json()).url); return; }
    setFailed(true); setBusy(false);
  };
  if (problem) return h(LoadFailed, { title: 'pago.title', problem, retry: () => void load() });
  if (!state) return h('section', { class: 'screen datos-page' }, h('h1', null, t('pago.title')));
  if (state.paid) return h(Paid, null);
  return h('section', { class: 'screen datos-page' },
    h('h1', null, t('pago.title')),
    state.mode === 'test' ? h('p', { class: 'test-banner', role: 'note' }, t('pago.test')) : null,
    state.may ? [
      h('p', { key: 't', class: 'pay-total' }, t('pago.total', { total: money(state.total) })),
      h('p', { key: 'n' }, t('pago.note')),
      failed ? h('p', { key: 'e', class: 'gate-error', role: 'alert' }, t('pago.error')) : null,
      h('button', { key: 'b', class: 'btn', type: 'button', disabled: busy, onClick: () => void pay() }, t('pago.button'))]
      : [h('p', { key: 'l' }, t('pago.locked')), h('a', { key: 'a', class: 'btn', href: '#/acuerdo' }, t('pago.toAgreement'))]);
}

/** Back from Stripe: only the webhook records a payment, so this page waits for it (up to a minute). */
export function PagoListo() {
  const [paid, setPaid] = useState(false);
  useEffect(() => {
    const sid = new URLSearchParams(location.hash.split('?')[1] ?? '').get('session_id') ?? '';
    const until = Date.now() + 60_000;
    let timer = 0;
    const tick = async () => {
      const r = await apiFetch(`/payments/return?session_id=${encodeURIComponent(sid)}`).catch(() => null);
      if (r?.ok && (await r.json()).paid) { setPaid(true); return; }
      if (Date.now() < until) timer = window.setTimeout(() => void tick(), 2000);
    };
    void tick();
    return () => clearTimeout(timer);
  }, []);
  return paid ? h(Paid, null) : h('section', { class: 'screen datos-page' }, h('h1', null, t('pago.title')), h('p', { role: 'status' }, t('pago.waiting')));
}

/** Paid: nothing more to pay, and the way on to the plan. */
function Paid() {
  return h('section', { class: 'screen datos-page' },
    h('h1', null, t('pago.paid.title')),
    h('p', { class: 'confirmed', role: 'status' }, t('pago.done')),
    h('a', { class: 'btn', href: '#/plan' }, t('plan.title')));
}
