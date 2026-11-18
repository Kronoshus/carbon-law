import { h } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import type { CharacterEngine } from '../core/character/engine';
import type { CharacterState } from '../core/character/states';
import { t } from '../core/i18n';

export interface CharacterStageProps {
  character?: string;
  state?: CharacterState;
}

const BASE = import.meta.env.BASE_URL;

export function CharacterStage(props: CharacterStageProps) {
  const character = props.character || 'calavera';
  const [state, setState] = useState<CharacterState>(props.state || 'idle');
  const [fallback, setFallback] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<CharacterEngine | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const mod = await import('../core/character/engine');
      if (cancelled) return;
      const eng = new mod.CharacterEngine(character);
      engineRef.current = eng;
      const canvas = canvasRef.current;
      if (canvas) {
        eng.mount(canvas).then((ok) => { if (!ok && !cancelled) setFallback(true); }).catch(() => { if (!cancelled) setFallback(true); });
      }
    })();
    return () => { cancelled = true; const eng = engineRef.current; if (eng) eng.unmount(); };
  }, [character]);

  useEffect(() => { engineRef.current?.setState(state); }, [state]);

  const label = t('character.aiLabel');

  return h('div', { class: 'character-stage', 'aria-label': `${character} — ${label}` },
    h('div', { class: 'character-backdrop' },
      h('img', { src: `${BASE}characters/${character}-bg.jpg`, alt: '', 'aria-hidden': 'true' })),
    fallback
      ? h('img', { class: 'character-fallback', src: `${BASE}characters/${character}.png`, alt: character })
      : h('canvas', { ref: canvasRef, class: 'character-canvas', width: 256, height: 256 }),
    h('div', { class: 'character-label', role: 'status' }, label),
    h('div', { class: 'character-controls' },
      (['idle','talking','thinking','listening','celebrating','comforting','waving','dancing'] as CharacterState[]).map((s) =>
        h('button', { key: s, onClick: () => setState(s), 'aria-pressed': state === s }, s)),
      h('button', { onClick: () => { const eng = engineRef.current; if (eng) void eng.speak('Hola, soy un programa de inteligencia artificial.', 'es'); } }, 'decir'),
    ),
  );
}
