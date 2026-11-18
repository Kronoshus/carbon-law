import { useEffect, useState } from 'preact/hooks';
import { t } from '../../core/i18n';
import { apiFetch } from '../../core/api';

type Journey = {
  day: number;
  gates: Record<string, boolean>;
};

const GATE_ORDER = [
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

function firstOpenGate(gates: Record<string, boolean> | undefined): string {
  if (!gates) return 'may_disclose';
  for (const g of GATE_ORDER) {
    if (gates[g] === false) return g;
  }
  return 'complete';
}

export function Popup() {
  const [day, setDay] = useState<number>(1);
  const [step, setStep] = useState<string>('may_disclose');
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
    : t(`popup.gate.${step}` as unknown as Parameters<typeof t>[0]);

  return (
    <main style={{ padding: '12px', minWidth: '220px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span aria-label={t('popup.streak', { count: 0 })} role="img">🕯️</span>
        <strong>{t('popup.streak', { count: 0 })}</strong>
      </div>
      <p style={{ margin: '4px 0 12px' }}>{t('popup.today', { step: `${day} · ${stepLabel}` })}</p>
      <button onClick={openSidePanel} disabled={opening} type="button">
        {t('popup.open')}
      </button>
    </main>
  );
}
