import { h } from 'preact';
import { useState } from 'preact/hooks';
import type { CharacterEngine } from '../core/character/engine';
import { STATES, type CharacterState, type Costume } from '../core/character/states';
import { CharacterStage } from './CharacterStage';

/* Dev-only (npm run dev, #/dev/personaje): every character, state and costume, for visual review. Not translated on purpose. */
export function DevCharacter() {
  const [character, setCharacter] = useState<'calavera' | 'pinata' | 'oso'>('calavera');
  const [state, setState] = useState<CharacterState>('idle');
  const [costume, setCostume] = useState<Costume | null>(null);
  const [engine, setEngine] = useState<CharacterEngine | null>(null);
  return h('main', { class: 'screen' },
    h(CharacterStage, { key: character, character, state, costume, onEngine: setEngine }),
    h('div', { class: 'actions' },
      (['calavera', 'pinata', 'oso'] as const).map((c) => h('button', { class: 'btn secondary', onClick: () => setCharacter(c), 'aria-pressed': c === character }, c)),
      STATES.map((s) => h('button', { class: 'btn secondary', onClick: () => setState(s), 'aria-pressed': s === state }, s)),
      ([null, 'glasses', 'pen'] as (Costume | null)[]).map((k) => h('button', { class: 'btn secondary', onClick: () => setCostume(k) }, k ?? 'no costume')),
      h('button', { class: 'btn', onClick: () => engine && void engine.speak('Hola, soy un programa de inteligencia artificial, no el abogado.', 'es') }, 'decir'),
    ));
}
