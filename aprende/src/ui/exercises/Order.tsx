import { h } from 'preact';
import { useEffect, useState } from 'preact/hooks';
import { t } from '../../core/i18n';

type Step = { key: string; text: string };

export function move(keys: string[], index: number, by: -1 | 1): string[] {
  const to = index + by;
  if (to < 0 || to >= keys.length) return keys;
  const next = keys.slice();
  [next[index], next[to]] = [next[to], next[index]];
  return next;
}

/** Put the steps in order with Subir / Bajar on each row (keyboard and switch access; no drag needed). The order as
 *  served is already an answer, so the client may check it without moving anything. */
export function OrderExercise({ item, onAnswer, locked, onCheck }: {
  item: { id: string; prompt?: string; steps?: Step[] }; onAnswer: (a: string[]) => void; locked: boolean; onCheck: () => void;
}) {
  const steps = item.steps ?? [];
  const [keys, setKeys] = useState(() => steps.map((s) => s.key));
  useEffect(() => onAnswer(keys), [keys]);
  const text = new Map(steps.map((s) => [s.key, s.text]));
  return h('section', { class: 'q', 'aria-labelledby': `q-${item.id}` },
    h('span', { class: 'kind' }, t('leccion.kind.order')),
    h('h1', { id: `q-${item.id}` }, item.prompt),
    h('ol', { class: 'order' }, keys.map((k, i) => h('li', { class: 'order-row', key: k },
      h('span', { class: 'order-no', 'aria-hidden': 'true' }, String(i + 1)),
      h('span', { class: 'order-text' }, text.get(k)),
      h('button', { type: 'button', class: 'icon-btn', 'aria-label': t('leccion.up', { step: text.get(k) ?? '' }), disabled: locked || i === 0, onClick: () => setKeys(move(keys, i, -1)) }, '↑'),
      h('button', { type: 'button', class: 'icon-btn', 'aria-label': t('leccion.down', { step: text.get(k) ?? '' }), disabled: locked || i === keys.length - 1, onClick: () => setKeys(move(keys, i, 1)) }, '↓')))),
    locked ? null : h('button', { class: 'btn', type: 'button', onClick: onCheck }, t('leccion.check')));
}
