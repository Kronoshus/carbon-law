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
      console.error('sidePanel.open failed', e);
    } finally {
      setOpening(false);
    }
  }

  const stepLabel = step === 'complete'
    ? t('popup.complete')
    : t(GATE_LABEL[step]);

  return (
    <main class="popup">
      <div class="popup-head">
        <img src="img/calavera-face.png" alt="" width="56" height="56" />
        <span class="chip">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2c2 3 3 4.5 3 6.5a3 3 0 0 1-6 0C9 6.5 10 5 12 2Z" fill="#FFB627" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" /><rect x="8.5" y="12" width="7" height="10" rx="1.5" fill="#FFF7E6" stroke="currentColor" stroke-width="1.8" /></svg>
          {t('popup.streak', { count: 0 })}
        </span>
      </div>
      <p class="popup-day">{t('popup.today', { day })}</p>
      <p class="popup-step">{stepLabel}</p>
      <button class="btn" onClick={openSidePanel} disabled={opening} type="button">
        {t('popup.open')}
      </button>
    </main>
  );
}
