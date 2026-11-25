import { describe, expect, it } from 'vitest';
import { pickVoice } from '../src/core/character/voice';

const v = (name: string, lang: string) => ({ name, lang }) as SpeechSynthesisVoice;
const MAC = [v('Mónica', 'es-ES'), v('Jorge', 'es-ES'), v('Paulina', 'es-MX'), v('Juan', 'es-MX'), v('Samantha', 'en-US'), v('Daniel', 'en-GB')];
const EDGE = [v('Microsoft Raul - Spanish (Mexico)', 'es-MX'), v('Microsoft Dalia Online (Natural) - Spanish (Mexico)', 'es-MX'),
  v('Microsoft Alonso Online (Natural) - Spanish (United States)', 'es-US'), v('Microsoft Paloma Online (Natural) - Spanish (United States)', 'es-US')];
const ANDROID = [v('español Estados Unidos', 'es_US'), v('español España', 'es_ES'), v('English United States', 'en_US')];

describe('each theme host has its own device voice', () => {
  it('picks the named voice for the persona', () => {
    expect(pickVoice(EDGE, 'girasol', 'es')?.name).toContain('Dalia');
    expect(pickVoice(EDGE, 'velita', 'es')?.name).toContain('Paloma');
    expect(pickVoice(EDGE, 'colibri', 'es')?.name).toContain('Alonso');
    expect(pickVoice(MAC, 'colibri', 'es')?.name).toBe('Juan');           // the Mexican Juan, not the Spanish Jorge after it
    expect(pickVoice(MAC, 'tortuga', 'en')?.name).toBe('Samantha');
  });

  it('without a named voice, takes the best one for the language: es-US, then es-MX', () => {
    expect(pickVoice(ANDROID, 'tortuga', 'es')?.name).toBe('español Estados Unidos');
    expect(pickVoice(ANDROID, 'girasol', 'en')?.name).toBe('English United States');
    expect(pickVoice([], 'velita', 'es')).toBeNull();
  });

  it('leaves the other characters on the device default', () => {
    expect(pickVoice(MAC, 'calavera', 'es')).toBeNull();
    expect(pickVoice(MAC, 'oso', 'es')).toBeNull();
  });
});
