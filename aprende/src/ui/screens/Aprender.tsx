import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t, lang, formatDate } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';
import { Icon, type IconName } from '../Icons';
import { PriceCard } from '../PriceCard';
import './map.css';

type Status = 'locked' | 'available' | 'done';
interface MapLesson { id: string; day: number | null; character: 'calavera' | 'pinata' | 'oso'; title: { es: string; en: string }; status: Status; unlock_at: string | null }
interface MapData { units: { id: string; lessons: MapLesson[] }[] }
interface Progress { petals: number; streak: { count: number } }

const UNIT_ICON: Record<string, IconName> = { will: 'testamento', trust: 'casa', ahcd: 'salud', poa: 'llave', final: 'caja', bonus: 'plan' };
const CHARACTER_NAME: Record<MapLesson['character'], I18nKey> = { calavera: 'character.calavera.name', pinata: 'character.pinata.name', oso: 'character.oso.name' };
const BASE = import.meta.env.BASE_URL;
const CORE = ['will', 'trust', 'ahcd', 'poa'];

/** The 14-day path after the lessons: firm steps the client waits for. Phase 6 links them to the timeline. */
const PAY = { key: 'map.node.pay', sub: 'map.node.pay.day', icon: 'pluma' } as const;
const REVIEW = { key: 'map.node.review', sub: 'map.node.review.day', icon: 'lupa' } as const;
const FINISH = [{ key: 'map.node.documents', sub: 'map.node.documents.day', icon: 'plan' }, { key: 'map.node.signing', sub: 'map.node.signing.day', icon: 'pluma' }] as const;
const step = (s: { key: I18nKey; sub: I18nKey; icon: IconName }) => {
  const isReview = s.key === 'map.node.review';
  const inner = [h('span', { class: 'disc', 'aria-hidden': 'true' }, h(Icon, { name: s.icon }), h('span', { class: 'badge' }, h(Icon, { name: 'candado' }))),
    h('span', { class: 'node-label' }, h('b', null, t(s.key)), h('span', null, t(s.sub)))];
  if (isReview) return h('li', { class: 'node-item', key: s.key }, h('a', { class: 'node available', href: '#/revisar' }, ...inner));
  return h('li', { class: 'node locked', key: s.key }, ...inner);
};

export function Aprender() {
  const [map, setMap] = useState<MapData | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [day, setDay] = useState<number | null>(null);
  const [tentative, setTentative] = useState<string[] | null>(null);
  const [failed, setFailed] = useState(false);
  const l = lang.value;

  useEffect(() => {
    (async () => {
      const [m, p, j] = await Promise.all([apiFetch('/learn/map'), apiFetch('/progress'), apiFetch('/journey')]);
      if (!m.ok) { setFailed(true); return; }
      setMap((await m.json()) as MapData);
      if (p.ok) setProgress((await p.json()) as Progress);
      if (j.ok) { const jd = await j.json() as { day: number; documents?: { tentative?: string[] } }; setDay(jd.day); setTentative(jd.documents?.tentative ?? []); }
    })();
  }, []);

  if (failed) return h('p', { role: 'alert' }, t('map.error'));
  if (!map) return h('p', { role: 'status' }, t('leccion.loading'));

  const lessons = map.units.flatMap((u) => u.lessons.map((ls) => ({ ...ls, unit: u.id })));
  const core = lessons.filter((ls) => CORE.includes(ls.unit)).sort((a, b) => (a.day ?? 0) - (b.day ?? 0));
  const final = lessons.find((ls) => ls.unit === 'final');
  const bonus = lessons.filter((ls) => ls.unit === 'bonus');
  const current = core.find((ls) => ls.status === 'available') ?? (final?.status === 'available' ? final : undefined);
  const title = (ls: MapLesson) => (l === 'en' ? ls.title.en : ls.title.es);

  const reason = (ls: MapLesson & { unit: string }) => {
    if (ls.status === 'done') return t('map.done', { day: ls.day ?? '' });
    if (ls.status === 'available') return ls.day ? t('map.dayN', { day: ls.day }) : t('map.open');
    if (ls.unlock_at) return t('map.opensOn', { date: formatDate(ls.unlock_at, { weekday: 'long', day: 'numeric', month: 'long' }) });
    if (ls.unit === 'final') return t('map.afterSigning');
    if (ls.unit === 'bonus') return t('map.afterFirst');
    return t('map.afterPrevious');
  };

  const node = (ls: MapLesson & { unit: string }) => {
    const badge = ls.status === 'done' ? h(Icon, { name: 'sello' }) : ls.status === 'locked' ? h(Icon, { name: 'candado' }) : null;
    const label = h('span', { class: 'node-label' }, h('b', null, title(ls)), h('span', null, reason(ls)));
    if (ls === current) {
      return h('li', { class: 'node current', key: ls.id },
        h('span', { class: 'disc pulse', 'aria-hidden': 'true' }, h('img', { src: `${BASE}img/${ls.character}-face.png`, alt: '' })),
        h('div', { class: 'card' }, h('span', { class: 'node-label' }, h('b', null, title(ls)),
          h('span', null, t('map.withCharacter', { day: ls.day ?? '', name: t(CHARACTER_NAME[ls.character]) }))),
          h('a', { class: 'btn', href: `#/leccion/${ls.id}` }, t(ls.status === 'done' ? 'map.review' : 'map.start'))));
    }
    const inner = [h('span', { class: 'disc', 'aria-hidden': 'true' }, h(Icon, { name: UNIT_ICON[ls.unit] ?? 'plan' }), badge ? h('span', { class: 'badge' }, badge) : null), label];
    return ls.status === 'locked'
      ? h('li', { class: 'node locked', key: ls.id }, ...inner)
      : h('li', { key: ls.id, class: 'node-item' }, h('a', { class: `node ${ls.status}`, href: `#/leccion/${ls.id}` }, ...inner));
  };

  const host = current ?? core[0];
  return h('div', { class: 'map' },
    h('div', { class: 'map-chips' },
      h('span', { class: 'chip', title: t('map.streak') }, h(Icon, { name: 'vela' }), String(progress?.streak.count ?? 0),
        h('span', { class: 'visually-hidden' }, t('map.streakSr'))),
      h('h1', { class: 'map-day' }, day ? t('map.dayOf', { day }) : t('nav.aprender')),
      h('span', { class: 'chip', title: t('map.petals') }, h(Icon, { name: 'petalo' }), String(progress?.petals ?? 0),
        h('span', { class: 'visually-hidden' }, t('map.petalsSr')))),
    host ? h('section', { class: 'host', 'aria-label': t('character.calavera.name') },
      h('img', { src: `${BASE}img/calavera-face.png`, alt: '' }),
      h('p', { class: 'bubble' }, current ? t('map.hostToday', { name: t(CHARACTER_NAME[current.character]), title: title(current) }) : t('map.hostDone'))) : null,
    h(PriceCard, { codes: ['will'] }),
    (tentative !== null && (tentative.length === 0) && core.some((ls) => ls.unit === 'trust' && ls.status === 'done'))
      ? h('a', { class: 'card docs-card', href: '#/documentos' }, h('strong', null, t('docs.title')), h('span', null, t('docs.body'))) : null,
    h('h2', { class: 'banner' }, t('map.learn'), h('small', null, t('map.learn.sub'))),
    h('ol', { class: 'path' }, core.map(node)),
    h('h2', { class: 'banner' }, t('map.step.pay'), h('small', null, t('map.step.pay.day'))),
    h('ol', { class: 'path' }, step(PAY)),
    h('h2', { class: 'banner' }, t('map.step.review'), h('small', null, t('map.step.review.day'))),
    h('ol', { class: 'path' }, step(REVIEW)),
    h('h2', { class: 'banner' }, t('map.step.finish'), h('small', null, t('map.step.finish.day'))),
    h('ol', { class: 'path' }, FINISH.map(step), final ? node(final) : null),
    bonus.length ? [h('h2', { class: 'banner', key: 'bonus' }, t('map.bonus'), h('small', null, t('map.bonus.sub'))), h('ol', { class: 'path', key: 'bonusp' }, bonus.map(node))] : null);
}
