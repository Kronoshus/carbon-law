import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import { PriceCard } from '../PriceCard';
import './plan.css';

type Step = { step: string; day: number; date: string; due: string | null; status: string; shifted_days: number; reason_key: string | null };

export function Plan() {
  const [timeline, setTimeline] = useState<Step[]>([]);
  const l = lang.value;
  useEffect(() => {
    (async () => {
      const r = await apiFetch('/journey');
      if (!r.ok) return;
      const j = await r.json();
      setTimeline((j.timeline || []) as Step[]);
    })();
  }, []);
  const fmtDate = (iso: string) => {
    const d = new Date(iso + 'T12:00:00Z');
    return new Intl.DateTimeFormat(l === 'es' ? 'es' : 'en', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'America/Los_Angeles' }).format(d);
  };
  return h('section', { class: 'plan' },
    h('h1', null, t('plan.title' as any)),
    h('p', { class: 'plan-intro' }, t('plan.intro' as any)),
    h('ol', { class: 'plan-list' },
      timeline.map((s) => {
        const isLate = s.status === 'late';
        const isDone = s.status === 'done';
        const isNext = s.status === 'next';
        const classes = ['plan-step'];
        if (isNext) classes.push('plan-step--next');
        if (isDone) classes.push('plan-step--done');
        return h('li', { class: classes.join(' '), key: s.step },
          h('span', { class: 'plan-day' }, t('plan.day' as any, { day: s.day, date: fmtDate(s.date) })),
          h('span', { class: 'plan-step-name' }, t(`plan.step.${s.step}` as any)),
          isDone ? h('span', { class: 'plan-check', 'aria-hidden': 'true' }, '✓') : null,
          !isLate ? h('span', { class: `plan-chip plan-chip--${s.status}` }, t(`plan.status.${s.status}` as any)) : null,
          isLate ? h('p', { class: 'plan-late' }, t('plan.late' as any)) : null,
          (s.shifted_days > 0 && s.reason_key)
            ? h('p', { class: 'plan-shifted' }, t(`plan.shifted.${s.reason_key}` as any, { count: s.shifted_days, n: s.shifted_days }))
            : null,
        );
      })
    ),
    h(PriceCard, { codes: ['will'] })
  );
}
