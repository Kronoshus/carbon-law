import { h } from 'preact';
import { t } from '../../core/i18n';
import { useState } from 'preact/hooks';

interface Item { id: string; kind: string; prompt?: string; say?: string; options?: string[]; story?: string }

export function ListenExercise({ item, choice, setChoice, locked, correct, onCheck }: {
  item: Item; choice: number | null; setChoice: (v: unknown) => void; locked: boolean; correct: boolean | null; onCheck: () => void;
}) {
  const [show, setShow] = useState(false);
  const say = item.say ?? '';
  const play = () => {
    try {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        const u = new SpeechSynthesisUtterance(say);
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(u);
      }
    } catch { /* noop */ }
  };
  const options = item.options ?? [];
  const rows = options.map((o, i) => {
    const picked = choice === i;
    const mark = locked && picked ? (correct ? ' correct' : ' wrong') : '';
    return h('label', { class: `option${mark}`, key: String(i) },
      h('input', { type: 'radio', name: `r-${item.id}`, checked: picked, onChange: () => setChoice(i) }),
      h('span', { class: 'key', 'aria-hidden': 'true' }, String.fromCharCode(65 + i)), ' ', o
    );
  });
  return h('section', { class: 'q' },
    h('span', { class: 'kind' }, t('leccion.kind.listen')),
    item.story ? h('p', { class: 'story' }, item.story) : null,
    h('h1', null, item.prompt),
    h('div', { style: 'display:flex;gap:var(--s2);flex-wrap:wrap;' },
      h('button', { type: 'button', class: 'btn secondary', onClick: play, style: 'min-block-size:48px;' }, t('leccion.play')),
      h('button', { type: 'button', class: 'btn secondary', onClick: () => setShow((s) => !s), style: 'min-block-size:48px;' }, t('leccion.showText'))
    ),
    show ? h('p', { class: 'story' }, say) : null,
    h('fieldset', { disabled: locked, style: 'border:0;padding:0;margin:0;display:grid;gap:var(--s2);' }, rows),
    locked ? null : h('button', { class: 'btn', type: 'button', disabled: choice === null, onClick: onCheck }, t('leccion.check'))
  );
}
