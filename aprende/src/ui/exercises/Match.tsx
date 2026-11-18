import { h } from 'preact';
import { useState } from 'preact/hooks';
import { t } from '../../core/i18n';

type Tile = { key: string; text: string };
export type Pairs = Record<string, string>;      // left key -> right key: exactly the answer the server grades

/** Pair or unpair: choosing a left tile and then a right tile pairs them; choosing a paired tile undoes its pair. */
const without = (pairs: Pairs, left: string): Pairs => Object.fromEntries(Object.entries(pairs).filter(([l]) => l !== left));

export function toggle(pairs: Pairs, left: string | null, right: string | null): { pairs: Pairs; pending: string | null } {
  if (left && left in pairs) return { pairs: without(pairs, left), pending: null };
  if (right) {
    const owner = Object.keys(pairs).find((l) => pairs[l] === right);
    if (owner) return { pairs: without(pairs, owner), pending: left };
    if (left) return { pairs: { ...pairs, [left]: right }, pending: null };
  }
  return { pairs, pending: left };
}

export function MatchExercise({ item, onAnswer, locked, onCheck }: {
  item: { id: string; prompt?: string; left?: Tile[]; right?: Tile[] }; onAnswer: (a: Pairs | null) => void; locked: boolean; onCheck: () => void;
}) {
  const left = item.left ?? [], right = item.right ?? [];
  const [pairs, setPairs] = useState<Pairs>({});
  const [pending, setPending] = useState<string | null>(null);
  const order = left.filter((l) => l.key in pairs).map((l) => l.key);       // pair numbers follow the left column
  const number = (leftKey: string | undefined) => (leftKey ? order.indexOf(leftKey) + 1 : 0);
  const choose = (l: string | null, r: string | null) => {
    const next = toggle(pairs, l ?? pending, r);
    setPairs(next.pairs); setPending(next.pending);
    onAnswer(Object.keys(next.pairs).length === left.length ? next.pairs : null);
  };
  const tile = (tl: Tile, n: number, pressed: boolean, onClick: () => void) =>
    h('button', { type: 'button', class: 'tile', 'data-pair': n || undefined, 'aria-pressed': pressed, disabled: locked, onClick, key: tl.key },
      n ? h('span', { class: 'pair-no', 'aria-label': t('leccion.pairNo', { n }) }, String(n)) : null, tl.text);
  return h('section', { class: 'q', 'aria-labelledby': `q-${item.id}` },
    h('span', { class: 'kind' }, t('leccion.kind.match')),
    h('h1', { id: `q-${item.id}` }, item.prompt),
    h('div', { class: 'match' },
      h('div', { class: 'match-col' }, left.map((l) => tile(l, number(l.key in pairs ? l.key : undefined), pending === l.key || l.key in pairs, () => choose(l.key, null)))),
      h('div', { class: 'match-col' }, right.map((r) => {
        const owner = Object.keys(pairs).find((k) => pairs[k] === r.key);
        return tile(r, number(owner), !!owner, () => choose(null, r.key));
      }))),
    locked ? null : h('button', { class: 'btn', type: 'button', disabled: Object.keys(pairs).length !== left.length, onClick: onCheck }, t('leccion.check')));
}
