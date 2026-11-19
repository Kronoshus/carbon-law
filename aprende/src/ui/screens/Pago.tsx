import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import './datos.css';
import './pago.css';

const money = (cents: number) => `$${Math.floor(cents / 100).toLocaleString('en-US')}`;

/** Day 5: the server's total, then Stripe's own page. The app never sees a card number. */
export function Pago() {
  const [state, setState] = useState<{ may: boolean; total: number; mode: string } | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { void (async () => {
    const j = await (await apiFetch('/journey')).json();
    const codes = j.documents.confirmed.join(',');
    const total = codes ? (await (await apiFetch(`/payments/quote?codes=${codes}`)).json()).total : 0;
    const { mode } = await (await apiFetch('/payments/config')).json();
    setState({ may: j.gates.may_pay, total, mode });
  })(); }, []);
  const pay = async () => {
    setBusy(true); setFailed(false);
    const r = await apiFetch('/payments/checkout', { method: 'POST' }).catch(() => null);
    if (r?.ok) { location.assign((await r.json()).url); return; }
    setFailed(true); setBusy(false);
  };
  if (!state) return h('section', { class: 'screen datos-page' }, h('h1', null, t('pago.title')));
  return h('section', { class: 'screen datos-page' },
    h('h1', null, t('pago.title')),
    state.mode === 'test' ? h('p', { class: 'test-banner', role: 'note' }, t('pago.test')) : null,
    state.may ? [
      h('p', { key: 't', class: 'pay-total' }, t('pago.total', { total: money(state.total) })),
      h('p', { key: 'n' }, t('pago.note')),
      failed ? h('p', { key: 'e', class: 'gate-error', role: 'alert' }, t('pago.error')) : null,
      h('button', { key: 'b', class: 'btn', type: 'button', disabled: busy, onClick: () => void pay() }, t('pago.button'))]
      : h('p', null, t('pago.locked')));
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
  return h('section', { class: 'screen datos-page' },
    h('h1', null, t('pago.title')),
    paid ? [h('p', { key: 'd', class: 'confirmed', role: 'status' }, t('pago.done')),
            h('a', { key: 'l', class: 'btn', href: '#/plan' }, t('plan.title'))]
      : h('p', { role: 'status' }, t('pago.waiting')));
}
