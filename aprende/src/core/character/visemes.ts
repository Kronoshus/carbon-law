// Port of VIS table + vis() + viseme() from avatar-intake/index.html.
// Jaw smoothing and blink timing live in engine.ts; this module is pure data/logic.

export type Viseme = [number, number]; // [mouthOpen, mouthRound]

export const VIS: Record<string, Viseme> = {
  a: [1, 0],
  e: [0.65, 0],
  i: [0.4, 0],
  o: [0.7, 0.8],
  u: [0.35, 1],
  w: [0.3, 1],
  m: [0, 0.2],
  b: [0, 0.2],
  p: [0, 0.2],
  f: [0.15, 0],
  v: [0.15, 0],
};

export function vis(ch?: string | null): Viseme {
  const c = (ch || ' ').normalize('NFD')[0].toLowerCase();
  const found = VIS[c];
  if (found) return found;
  if (/[a-z]/.test(c)) return [0.45, 0.1];
  return [0, 0];
}

export interface Alignment {
  characters: string[];
  character_start_times_seconds: number[];
}

export function viseme(al: Alignment | null | undefined, tm: number): Viseme {
  if (!al) return [1, 0];
  const s = al.character_start_times_seconds;
  let i = 0;
  while (i < s.length - 1 && s[i + 1] <= tm) i++;
  return vis(al.characters[i]);
}

// server audio shape accepted by speak()
export interface ServerAudio {
  audio_base64: string;
  mime?: string;
  alignment?: Alignment | null;
}
