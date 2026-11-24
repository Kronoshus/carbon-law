import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch, extensionOff, getToken } from '../../core/api';
import { NoDisponible } from '../../ui/screens/NoDisponible';

type Journey = { day: number; gates: Record<string, boolean>; };
type Lesson = { id: string; day: number | null; unit: string; title: { es: string; en: string }; status: string };
type MapUnit = { id: string; lessons: Lesson[] };

type Gate =
  | 'may_disclose' | 'may_consent' | 'may_name' | 'may_collect_details' | 'may_chat'
  | 'may_sign_engagement' | 'may_pay' | 'may_see_documents' | 'may_book_signing' | 'may_take_final_lesson';

const GATE_ORDER: Gate[] = [
  'may_disclose', 'may_consent', 'may_name', 'may_collect_details', 'may_chat',
  'may_sign_engagement', 'may_pay', 'may_see_documents', 'may_book_signing', 'may_take_final_lesson',
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
  for (const g of GATE_ORDER) if (gates[g] === false) return g;
  return 'complete';
}

function availableLesson(units: MapUnit[] | undefined): Lesson | undefined {
  if (!units) return undefined;
  const wanted = new Set(['will', 'trust', 'ahcd', 'poa', 'final']);
  const candidates = units.flatMap((u) => u.lessons ?? []).filter((l) => l.status === 'available' && wanted.has(l.unit));
  if (!candidates.length) return undefined;
  candidates.sort((a, b) => (a.day ?? 999) - (b.day ?? 999));
  return candidates[0];
}

export function Popup() {
  const [signedOut, setSignedOut] = useState(false);
  const [off, setOff] = useState(false);
  const [day, setDay] = useState<number>(1);
  const [streak, setStreak] = useState<number>(0);
  const [lessonTitle, setLessonTitle] = useState<string | null>(null);
  const [gate, setGate] = useState<Gate | 'complete'>('may_disclose');
  const [opening, setOpening] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await apiFetch('/settings/public').catch(() => null);
      if (extensionOff.value) { if (!cancelled) setOff(true); return; }
      const token = await getToken();
      if (!token) { if (!cancelled) setSignedOut(true); return; }
      let journey: Journey | null = null;
      try {
        const res = await apiFetch('/journey');
        if (res.ok) journey = (await res.json()) as Journey;
      } catch { /* ignore */ }
      if (cancelled) return;
      if (journey) {
        setDay(journey.day ?? 1);
        const gates = journey.gates;
        const allThree = gates?.may_disclose === true && gates?.may_consent === true && gates?.may_name === true;
        let title: string | null = null;
        if (allThree) {
          try {
            const res = await apiFetch('/learn/map');
            if (res.ok) {
              const m = (await res.json()) as { units?: MapUnit[] };
              const l = availableLesson(m.units);
              if (l) title = l.title[lang.value] ?? l.title.es;
            }
          } catch { /* ignore */ }
        }
        if (cancelled) return;
        if (title) setLessonTitle(title); else { setLessonTitle(null); setGate(firstOpenGate(gates)); }
      }
      try {
        const res = await apiFetch('/progress');
        if (res.ok) {
          const p = (await res.json()) as { streak?: { count?: number } };
          if (!cancelled) setStreak(p?.streak?.count ?? 0);
        }
      } catch {
        if (!cancelled) setStreak(0);
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

  if (off) return h(NoDisponible, null);

  if (signedOut) {
    return (
      <main class="popup">
        <div class="popup-head">
          <img src="img/calavera-face.png" alt="" width="56" height="56" />
        </div>
        <h1 class="visually-hidden">{t('top.title')}</h1>
        <p class="popup-signedout">{t('popup.signedOut')}</p>
        <button class="btn" onClick={openSidePanel} disabled={opening} type="button">
          {t('popup.open')}
        </button>
      </main>
    );
  }

  const stepLabel = lessonTitle ?? (gate === 'complete' ? t('popup.complete') : t(GATE_LABEL[gate]));

  return (
    <main class="popup">
      <h1 class="visually-hidden">{t('top.title')}</h1>
      <div class="popup-head">
        <img src="img/calavera-face.png" alt="" width="56" height="56" />
        <span class="chip">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2c2 3 3 4.5 3 6.5a3 3 0 0 1-6 0C9 6.5 10 5 12 2Z" style={{ fill: 'var(--icon-warm)' }} stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" /><rect x="8.5" y="12" width="7" height="10" rx="1.5" style={{ fill: 'var(--icon-paper)' }} stroke="currentColor" stroke-width="1.8" /></svg>
          {t('popup.streak', { count: streak })}
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
