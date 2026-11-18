import { h } from 'preact';
import { t } from '../../core/i18n';
import { useState } from 'preact/hooks';

export interface MatchPair { leftKey: string; rightKey: string }

export function pairsToAnswer(pairs: MatchPair[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const p of pairs) out[p.leftKey] = p.rightKey;
  return out;
}

const COLORS = ['#c9a227', '#7c5cff', '#2e8b57', '#c45a8a', '#3a7ca5', '#b07d2a'];

interface Item { id: string; kind: string; prompt?: string; left?: { key: string; text: string }[]; right?: { key: string; text: string }[] }

export function MatchExercise({ item, choice, setChoice, locked, onCheck }: {
  item: Item; choice: Record<string, string> | null; setChoice: (v: unknown) => void; locked: boolean; correct: boolean | null; onCheck: () => void;
}) {
  const left = item.left ?? [];
  const right = item.right ?? [];
  const [pairs, setPairs] = useState<Record<string, string>>(() => (choice && typeof choice === 'object' ? { ...choice } : {}));
  const [selectedLeft, setSelectedLeft] = useState<string | null>(null);

  const sync = (next: Record<string, string>) => {
    setPairs(next);
    setChoice(Object.keys(next).length ? next : null);
  };

  const isPairedLeft = (k: string) => k in pairs;
  const isPairedRight = (k: string) => Object.values(pairs).includes(k);

  const onLeft = (k: string) => {
    if (locked) return;
    if (isPairedLeft(k)) { const rest = Object.fromEntries(Object.entries(pairs).filter(([kk]) => kk !== k)); sync(rest); setSelectedLeft(null); return; }
    setSelectedLeft(k);
  };
  const onRight = (k: string) => {
    if (locked) return;
    if (isPairedRight(k)) {
      const leftKey = Object.keys(pairs).find((l) => pairs[l] === k);
      if (leftKey) { const rest = Object.fromEntries(Object.entries(pairs).filter(([kk]) => kk !== leftKey)); sync(rest); }
      return;
    }
    if (selectedLeft) {
      const next = { ...pairs, [selectedLeft]: k };
      sync(next);
      setSelectedLeft(null);
    }
  };

  const pairedLefts = left.filter((l) => isPairedLeft(l.key)).map((l) => l.key);
  const pairNo = (leftKey: string) => pairedLefts.indexOf(leftKey);

  const allPaired = left.every((l) => isPairedLeft(l.key));

  const leftTiles = left.map((l) => {
    const pi = isPairedLeft(l.key) ? pairNo(l.key) : -1;
    const sel = selectedLeft === l.key;
    const style = pi >= 0 ? `background:${COLORS[pi % COLORS.length]}22;border-color:${COLORS[pi % COLORS.length]}` : '';
    return h('button', {
      type: 'button', class: 'btn secondary', key: l.key, disabled: locked,
      'aria-pressed': sel || isPairedLeft(l.key),
      onClick: () => onLeft(l.key),
      style: `${style};min-block-size:48px`,
    }, (pi >= 0 ? `${pi + 1}. ` : '') + l.text);
  });

  const rightTiles = right.map((r) => {
    const lk = Object.keys(pairs).find((l) => pairs[l] === r.key);
    const pi = lk ? pairNo(lk) : -1;
    const style = pi >= 0 ? `background:${COLORS[pi % COLORS.length]}22;border-color:${COLORS[pi % COLORS.length]}` : '';
    return h('button', {
      type: 'button', class: 'btn secondary', key: r.key, disabled: locked,
      onClick: () => onRight(r.key),
      style: `${style};min-block-size:48px`,
    }, (pi >= 0 ? `${pi + 1}. ` : '') + r.text);
  });

  return h('section', { class: 'q' },
    h('span', { class: 'kind' }, t('leccion.kind.match')),
    h('h1', null, item.prompt),
    h('div', { class: 'match-grid', style: 'display:grid;grid-template-columns:1fr 1fr;gap:var(--s2);' },
      h('div', { class: 'match-col' }, leftTiles),
      h('div', { class: 'match-col' }, rightTiles)
    ),
    locked ? null : h('button', { class: 'btn', type: 'button', disabled: !allPaired, onClick: onCheck }, t('leccion.check'))
  );
}
