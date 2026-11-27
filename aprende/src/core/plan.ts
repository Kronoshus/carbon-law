import { t } from './i18n';

/** The day in a header, "Day 3 of 14". The last day is the timeline's last step, which a change or a holiday moves;
 *  past it (or with no timeline yet) the header shows only the day. */
export function dayLabel(day: number, timeline: { day: number }[] | undefined, key: 'map.dayOf' | 'popup.today'): string {
  const total = timeline?.length ? Math.max(...timeline.map((s) => s.day)) : null;
  return total && day <= total ? t(key, { day, total }) : t('map.dayN', { day });
}
