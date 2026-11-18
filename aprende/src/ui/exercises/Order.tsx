import { h } from 'preact';
import { t } from '../../core/i18n';
import { useState } from 'preact/hooks';

export function orderToAnswer(keys: string[]): string[] {
  return [...keys];
}

interface Item { id: string; kind: string; prompt?: string; steps?: { key: string; text: string }[] }

export function OrderExercise({ item, choice, setChoice, locked, onCheck }: {
  item: Item; choice: string[] | null; setChoice: (v: unknown) => void; locked: boolean; correct: boolean | null; onCheck: () => void;
}) {
  const [order, setOrder] = useState<string[]>(() => (Array.isArray(choice) && choice.length ? [...choice] : (item.steps ?? []).map((s) => s.key)));

  const byKey = new Map((item.steps ?? []).map((s) => [s.key, s.text]));

  const move = (idx: number, dir: -1 | 1) => {
    if (locked) return;
    const next = [...order];
    const target = idx + dir;
    if (target < 0 || target >= next.length) return;
    [next[idx], next[target]] = [next[target], next[idx]];
    setOrder(next);
    setChoice(next);
  };

  const rows = order.map((k, i) =>
    h('li', { key: k, class: 'card', style: 'display:flex;align-items:center;gap:var(--s2);min-block-size:48px;' },
      h('span', { style: 'flex:1;' }, byKey.get(k) ?? k),
      h('button', { type: 'button', class: 'btn secondary', 'aria-label': t('leccion.up'), disabled: locked || i === 0, onClick: () => move(i, -1), style: 'min-block-size:48px;min-inline-size:48px;' }, '↑'),
      h('button', { type: 'button', class: 'btn secondary', 'aria-label': t('leccion.down'), disabled: locked || i === order.length - 1, onClick: () => move(i, 1), style: 'min-block-size:48px;min-inline-size:48px;' }, '↓')
    )
  );

  return h('section', { class: 'q' },
    h('span', { class: 'kind' }, t('leccion.kind.order')),
    h('h1', null, item.prompt),
    h('ol', { style: 'list-style:none;padding:0;margin:0;display:grid;gap:var(--s2);' }, rows),
    locked ? null : h('button', { class: 'btn', type: 'button', onClick: onCheck }, t('leccion.check'))
  );
}
