export type CharacterState =
  | 'idle' | 'talking' | 'thinking' | 'listening' | 'celebrating' | 'comforting' | 'waving' | 'dancing';

export const STATES: CharacterState[] = [
  'idle', 'talking', 'thinking', 'listening', 'celebrating', 'comforting', 'waving', 'dancing',
];

export type Costume = null | 'glasses' | 'pen';

export type OptionalKey = 'celebrate' | 'think' | 'wave' | 'waveSwing' | 'comfort' | 'glasses' | 'pen';
