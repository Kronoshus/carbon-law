import { h } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { CharacterEngine } from '../core/character/engine';
import type { CharacterState } from '../core/character/states';
import { t } from '../core/i18n';

export interface CharacterStageProps {
  character?: string;
  state?: CharacterState;
}

export function CharacterStage(props: CharacterStageProps) {
  const character = props.character || 'calavera';
  const [state, setState] = useState<CharacterState>(props.state || 'idle');
  const [fallback, setFallback] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<CharacterEngine | null>(null);

  useEffect(() => {
    const eng = new CharacterEngine(character);
    engineRef.current = eng;
    const canvas = canvasRef.current;
    if (canvas) {
      eng.mount(canvas).then((ok) => {
        if (!ok) setFallback(true);
      }).catch(() => setFallback(true));
    }
    return () => { eng.unmount(); };
  }, [character]);

  useEffect(() => {
    engineRef.current?.setState(state);
  }, [state]);

  const label = t('character.aiLabel');

  return h('div', { class: 'character-stage', 'aria-label': `${character} — ${label}` },
    h('div', { class: 'character-backdrop' },
      h('img', { src: `/characters/${character}-bg.png`, alt: '', 'aria-hidden': 'true' })),
    fallback
      ? h('img', { class: 'character-fallback', src: `/characters/${character}.png`, alt: character })
      : h('canvas', { ref: canvasRef, class: 'character-canvas', width: 256, height: 256 }),
    h('div', { class: 'character-label', role: 'status' }, label),
    h('div', { class: 'character-controls' },
      (['idle','talking','thinking','listening','celebrating','comforting'] as CharacterState[]).map((s) =>
        h('button', { key: s, onClick: () => setState(s), 'aria-pressed': state === s }, s)),
      h('button', { onClick: () => { const eng = engineRef.current; if (eng) void eng.speak('Hola, soy un programa de inteligencia artificial.', 'es'); } }, 'decir'),
    ),
  );
}
