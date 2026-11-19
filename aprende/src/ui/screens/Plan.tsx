import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';
import { PriceCard } from '../PriceCard';
import { Icon } from '../Icons';
import './plan.css';

type Step = { step: string; day: number; date: string; status: 'done' | 'today' | 'next' | 'waiting' | 'late'; shifted_days: number; reason_key: 'weekend' | 'holiday' | null };

/** "Mi plan" (spec 6.3): every step of the journey with its calendar date. A late firm step is said calmly, never in red. */
export function Plan() {
  const [steps, setSteps] = useState<Step[]>([]);
  useEffect(() => { void apiFetch('/journey').then(async (r) => { if (r.ok) setSteps((await r.json()).timeline); }); }, []);
  const date = (iso: string) => new Intl.DateTimeFormat(lang.value, { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' })
    .format(new Date(`${iso}T12:00:00Z`));
  return h('section', { class: 'screen plan' },
    h('h1', null, t('plan.title')),
    h('p', null, t('plan.intro')),
    h('ol', { class: 'plan-list' }, steps.map((s) => h('li', { key: s.step, class: `plan-step ${s.status}` },
      h('span', { class: 'plan-mark', 'aria-hidden': 'true' }, s.status === 'done' ? h(Icon, { name: 'check' }) : null),
      h('div', { class: 'plan-text' },
        h('p', { class: 'plan-day' }, t('plan.day', { day: s.day, date: date(s.date) })),
        h('p', { class: 'plan-name' }, t(`plan.step.${s.step}` as I18nKey)),
        s.status === 'late' ? h('p', { class: 'plan-note' }, t('plan.late')) : null,
        s.shifted_days > 0 && s.reason_key ? h('p', { class: 'plan-note' }, t(`plan.shifted.${s.reason_key}` as I18nKey, { count: s.shifted_days, n: s.shifted_days })) : null),
      s.status === 'late' ? null : h('span', { class: 'chip' }, t(`plan.status.${s.status}` as I18nKey))))),
    h(PriceCard, { codes: ['will'] }));
}
