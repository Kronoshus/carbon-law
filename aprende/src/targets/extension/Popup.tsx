import { useEffect, useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';

type Journey = {
  day: number;
  gates: Record<string, boolean>;
};

type Gate =
  | 'may_disclose'
  | 'may_consent'
  | 'may_name'
  | 'may_collect_details'
  | 'may_chat'
  | 'may_sign_engagement'
  | 'may_pay'
  | 'may_see_documents'
  | 'may_book_signing'
  | 'may_take_final_lesson';

const GATE_ORDER: Gate[] = [
  'may_disclose',
  'may_consent',
  'may_name',
  'may_collect_details',
  'may_chat',
  'may_sign_engagement',
  'may_pay',
  'may_see_documents',
  'may_book_signing',
  'may_take_final_lesson',
];

const GATE_LABEL: Record<Gate, I18nKey> = {
  may_disclose: 'popup.gate.may_disclose',
  may_consent: 'popup.gate.may_consent',
  may_name: 'popup.gate.may_name',
  may_collect_details: 'popup.gate.may_collect_details',
  may_chat: 'popup.gate.may_chat',
  may_sign_engagement: 'popup.gate.may_sign_engagement',
  may_pay: 'popup.gate.may_pay',
  may_see_documents: 'popup.gate.may_see_documents',
  may_book_signing: 'popup.gate.may_book_signing',
  may_take_final_lesson: 'popup.gate.may_take_final_lesson',
};

function firstOpenGate(gates: Record<string, boolean> | undefined): Gate | 'complete' {
  if (!gates) return 'may_disclose';
  for (const g of GATE_ORDER) {
    if (gates[g] === false) return g;
  }
  return 'complete';
}

export function Popup() {
  const [day, setDay] = useState<number>(1);
  const [step, setStep] = useState<Gate | 'complete'>('may_disclose');
  const [opening, setOpening] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch('/journey');
        if (!res.ok) return;
        const j = (await res.json()) as Journey;
        if (cancelled) return;
        setDay(j.day ?? 1);
        setStep(firstOpenGate(j.gates));
      } catch {
        // offline / no token: keep defaults
      }
    })();
    return () => { cancelled = true; };
  }, []);

  async function openSidePanel() {
    setOpening(true);
    try {
      const win = await chrome.windows.getCurrent();
      if (win.id === undefined) return;
      await chrome.sidePanel.open({ windowId: win.id });
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('sidePanel.open failed', e);
    } finally {
      setOpening(false);
    }
  }

  const stepLabel = step === 'complete'
    ? t('popup.complete')
    : t(GATE_LABEL[step]);

  return (
    <main style={{ width: '360px', minHeight: '480px', padding: 'var(--s4)' }}>
      <div class="chip" style={{ marginBottom: 'var(--s3)' }}>
        <span aria-hidden="true">🕯️</span>
        <strong>{t('popup.streak', { count: 0 })}</strong>
      </div>
      <p style={{ marginBottom: 'var(--s4)' }}>{t('popup.today', { step: `${day} · ${stepLabel}` })}</p>
      <button class="btn" onClick={openSidePanel} disabled={opening} type="button">
        {t('popup.open')}
      </button>
    </main>
  );
}
