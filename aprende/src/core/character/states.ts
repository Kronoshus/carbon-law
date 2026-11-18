// Character states. Each state may drive optional extra shape keys if the GLB has them
// (celebrate, think, wave, comfort); otherwise falls back to base keys.

export type CharacterState =
  | 'idle'
  | 'talking'
  | 'thinking'
  | 'listening'
  | 'celebrating'
  | 'comforting';

export const STATES: CharacterState[] = [
  'idle',
  'talking',
  'thinking',
  'listening',
  'celebrating',
  'comforting',
];

// Optional morph-target names a GLB may provide for states.
export const OPTIONAL_KEYS = ['celebrate', 'think', 'wave', 'comfort'] as const;
export type OptionalKey = (typeof OPTIONAL_KEYS)[number];

// Map state -> optional key it prefers (if present).
export const STATE_OPTIONAL_KEY: Partial<Record<CharacterState, OptionalKey>> = {
  thinking: 'think',
  celebrating: 'celebrate',
  comforting: 'comfort',
};

// Reduced-motion: caller checks; engine just exposes flags.
export interface StateInfluences {
  // base shape-key targets driven by state (added on top of frame() base)
  browUp?: number;
  headYaw?: number;
  headPitch?: number;
  headRoll?: number;
  lookX?: number;
  jawOpen?: number;
  // whether to add a bounce to body position
  bounce?: boolean;
}
