import { h } from 'preact';
import { useState } from 'preact/hooks';
import { t } from '../../core/i18n';

/** The character says a sentence; the client answers a choice about it. The text is always one tap away. */
export function ListenExercise({ item, onAnswer, answer, locked, correct, onCheck, onPlay }: {
  item: { id: string; prompt?: string; say?: string; options?: string[] }; answer: number | null; onAnswer: (a: number) => void;
  locked: boolean; correct: boolean | null; onCheck: () => void; onPlay: () => void;
}) {
  const [shown, setShown] = useState(false);
  return h('form', { class: 'q', 'aria-labelledby': `q-${item.id}`, onSubmit: (e: Event) => { e.preventDefault(); onCheck(); } },
    h('span', { class: 'kind' }, t('leccion.kind.listen')),
    h('h1', { id: `q-${item.id}` }, item.prompt),
    h('div', { class: 'listen-actions' },
      h('button', { type: 'button', class: 'btn secondary', onClick: onPlay }, t('leccion.play')),
      h('button', { type: 'button', class: 'btn secondary', 'aria-expanded': shown, onClick: () => setShown(!shown) }, t('leccion.showText'))),
    shown ? h('p', { class: 'story' }, item.say) : null,
    h('fieldset', { disabled: locked },
      h('legend', { class: 'visually-hidden' }, item.prompt),
      (item.options ?? []).map((o, i) => h('label', { class: `option${locked && answer === i ? (correct ? ' correct' : ' wrong') : ''}`, key: i },
        h('input', { type: 'radio', name: `r-${item.id}`, checked: answer === i, onChange: () => onAnswer(i) }),
        h('span', { class: 'key', 'aria-hidden': 'true' }, String.fromCharCode(65 + i)), o))),
    locked ? null : h('button', { class: 'btn', type: 'submit', disabled: answer === null }, t('leccion.check')));
}
