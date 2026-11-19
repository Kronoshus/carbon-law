import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';
import { navigate } from '../../core/router';

type Journey = { gates: { may_pay: boolean }; documents: { confirmed: string[] } };

export function Pago() {
  const [journey, setJourney] = useState<Journey | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [mode, setMode] = useState<string>('test');
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    (async () => {
      const j = await (await apiFetch('/journey')).json();
      setJourney(j);
      const codes = (j.documents?.confirmed?.length ? j.documents.confirmed : ['will']).join(',');
      const q = await (await apiFetch(`/payments/quote?codes=${codes}`)).json();
      setTotal(q.total);
      setMode(q.test_mode ? 'test' : (q.mode ?? 'test'));
      // also read config mode if available
      try {
        const cfg = await (await apiFetch('/payments/config')).json();
        if (cfg?.mode) setMode(cfg.mode);
      } catch { /* ignore */ }
    })();
  }, []);

  const mayPay = journey?.gates?.may_pay === true;

  const pay = async () => {
    setBusy(true); setFailed(false);
    try {
      const r = await apiFetch('/payments/checkout', { method: 'POST' });
      if (!r.ok) { setFailed(true); setBusy(false); return; }
      const data = await r.json();
      if (data?.url) location.assign(data.url);
      else { setFailed(true); setBusy(false); }
    } catch {
      setFailed(true); setBusy(false);
    }
  };

  const money = (cents: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(cents / 100);

  if (!journey) return h('section', { class: 'screen' }, h('p', null, '…'));

  if (!mayPay) {
    return h('section', { class: 'screen pago-page' },
      h('h1', null, t('pago.title')),
      h('p', { class: 'locked' }, t('pago.locked')));
  }

  return h('section', { class: 'screen pago-page' },
    h('h1', null, t('pago.title')),
    mode === 'test' ? h('p', { class: 'test-banner', role: 'status' }, t('pago.test')) : null,
    total !== null ? h('p', { class: 'total' }, t('pago.total', { total: money(total) })) : null,
    h('p', { class: 'note' }, t('pago.note')),
    failed ? h('p', { class: 'gate-error', role: 'alert' }, t('pago.error')) : null,
    h('button', { class: 'btn', type: 'button', disabled: busy, onClick: () => void pay() }, t('pago.button')));
}

export function PagoListo() {
  const [paid, setPaid] = useState(false);
  const [done, setDone] = useState(false);
  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.split('?')[1] || '');
    const sid = params.get('session_id') || '';
    let stopped = false;
    const tick = async () => {
      if (stopped) return;
      try {
        const r = await apiFetch(`/payments/return?session_id=${encodeURIComponent(sid)}`);
        const data = await r.json();
        if (data?.paid) { setPaid(true); setDone(true); stopped = true; return; }
      } catch { /* ignore */ }
      if (!stopped) setTimeout(tick, 2000);
    };
    void tick();
    const timeout = setTimeout(() => { stopped = true; }, 60000);
    return () => { stopped = true; clearTimeout(timeout); };
  }, []);
  return h('section', { class: 'screen pago-listo' },
    !paid ? h('p', { class: 'waiting' }, t('pago.waiting')) : null,
    paid ? h('div', null,
      h('p', { class: 'done' }, t('pago.done')),
      h('a', { href: '#/plan', onClick: (e: Event) => { e.preventDefault(); navigate('/plan'); } }, t('pago.done'))) : null);
}
