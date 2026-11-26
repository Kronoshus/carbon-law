import type { CharacterId } from './cast';
import hostVoices from '../../../../web/voices.json';

/** How a host sounds through the device's own speech (speechSynthesis): the device voices to look for, best first, and
 *  the pitch and rate that give the persona its character. A name matches any device voice whose name contains it
 *  (Apple "Paulina", Microsoft Edge "Microsoft Dalia Online (Natural) - Spanish (Mexico)", and so on). When none of the
 *  named voices is on the device, the best voice for the language is used, with the same pitch and rate.
 *  Characters without an entry keep the device's default voice. The table is web/voices.json, which the staff
 *  Personajes page (web/characters.js) also loads for its "Escuchar voz" preview, so the two always sound the same. */
export interface Voice { es: string[]; en: string[]; pitch: number; rate: number }

export const VOICES: Partial<Record<CharacterId, Voice>> = hostVoices;

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
