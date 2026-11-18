export type ConsentResult = 'yes' | 'no' | null;

function rx(phrases: string[]): RegExp {
  const parts = [...phrases].sort((a, b) => b.length - a.length).map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return new RegExp('(?<!\\w)(?:' + parts.join('|') + ')(?!\\w)', 'iu');
}

const REFUSAL_PHRASES = [
  'no acepto', 'no quiero', 'prefiero que no', 'mejor no',
  'no estoy de acuerdo', 'claro que no', 'no me grabe', 'no me graben',
  'nunca', 'no gracias', 'no thanks', "i don't agree", 'i do not consent',
  'not okay', 'rather not', 'never', 'nope', 'nah',
];

const UNCERTAIN_PHRASES = [
  'no sé', 'no se', 'no entiendo', 'tal vez', 'a lo mejor', 'depende',
  'déjeme pensarlo', 'dejeme pensarlo', 'maybe', "i don't know", 'let me think',
];

const NO_PROBLEM_PHRASES = [
  'no hay problema', 'no me molesta', 'no problem', "i don't mind",
];

const YES_WORDS = [
  'sí', 'si', 'acepto', 'claro', 'de acuerdo', 'por supuesto', 'está bien',
  'esta bien', 'yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'i agree',
];

const REFUSAL_RE = rx(REFUSAL_PHRASES);
const UNCERTAIN_RE = rx(UNCERTAIN_PHRASES);
const NO_PROBLEM_RE = rx(NO_PROBLEM_PHRASES);
const YES_RE = rx(YES_WORDS);
const NO_RE = /(?<!\w)no(?!\w)/iu;

export function classifyConsent(text: string): ConsentResult {
  const t = text == null ? '' : String(text);
  if (REFUSAL_RE.test(t)) return 'no';
  if (t.includes('?') || UNCERTAIN_RE.test(t)) return null;
  if (NO_PROBLEM_RE.test(t)) return 'yes';
  const hasYes = YES_RE.test(t);
  const hasNo = NO_RE.test(t);
  if (hasYes && !hasNo) return 'yes';
  if (hasNo && !hasYes) return 'no';
  return null;
}
