import type { CharacterId } from './cast';

/** How a host sounds through the device's own speech (speechSynthesis): the device voices to look for, best first, and
 *  the pitch and rate that give the persona its character. A name matches any device voice whose name contains it
 *  (Apple "Paulina", Microsoft Edge "Microsoft Dalia Online (Natural) - Spanish (Mexico)", and so on). When none of the
 *  named voices is on the device, the best voice for the language is used, with the same pitch and rate.
 *  Characters without an entry keep the device's default voice. The staff Personajes page (web/characters.js) mirrors
 *  this table for its "Escuchar voz" preview. */
export interface Voice { es: string[]; en: string[]; pitch: number; rate: number }

export const VOICES: Partial<Record<CharacterId, Voice>> = {
  girasol: { es: ['Dalia', 'Paulina', 'Paloma', 'Google español de Estados Unidos'], en: ['Jenny', 'Samantha', 'Aria', 'Google US English'], pitch: 1.1, rate: 1.03 },
  colibri: { es: ['Alonso', 'Juan', 'Jorge', 'Raul'], en: ['Guy', 'Aaron', 'Alex', 'David'], pitch: 1.2, rate: 1.12 },
  velita: { es: ['Paloma', 'Paulina', 'Sabina', 'Dalia'], en: ['Aria', 'Samantha', 'Zira'], pitch: 1, rate: 0.9 },
  tortuga: { es: ['Dalia', 'Paulina', 'Sabina', 'Paloma'], en: ['Michelle', 'Samantha', 'Zira'], pitch: 0.85, rate: 0.84 },
};

/** es-US first, then es-MX, then any other Spanish (en-US, then any English). */
const LOCALES = { es: ['es-US', 'es-MX'], en: ['en-US'] };

function rank(v: SpeechSynthesisVoice, lang: 'es' | 'en'): number {
  const i = LOCALES[lang].indexOf(v.lang.replace('_', '-'));
  return i < 0 ? LOCALES[lang].length : i;
}

/** The device voice for this character and language, or null to let the browser choose by `lang`. */
export function pickVoice(voices: SpeechSynthesisVoice[], id: CharacterId, lang: 'es' | 'en'): SpeechSynthesisVoice | null {
  const want = VOICES[id];
  if (!want) return null;
  const ours = voices.filter((v) => v.lang.toLowerCase().startsWith(lang)).sort((a, b) => rank(a, lang) - rank(b, lang));
  for (const name of want[lang]) {
    const v = ours.find((o) => o.name.includes(name));
    if (v) return v;
  }
  return ours[0] ?? null;
}

/** An utterance in this character's voice. */
export function utterance(text: string, id: CharacterId, lang: 'es' | 'en'): SpeechSynthesisUtterance {
  const u = new SpeechSynthesisUtterance(text);
  u.lang = LOCALES[lang][0];
  const voice = pickVoice(window.speechSynthesis.getVoices(), id, lang);
  if (voice) { u.voice = voice; u.lang = voice.lang.replace('_', '-'); }
  const want = VOICES[id];
  if (want) { u.pitch = want.pitch; u.rate = want.rate; }
  return u;
}
