
import es from '../../i18n/es.json';
import en from '../../i18n/en.json';

export type Lang = 'es' | 'en';

const messages: Record<Lang, Record<string, string>> = {
  es: es as Record<string, string>,
  en: en as Record<string, string>,
};

let currentLang: Lang = 'es';

export function getLang(): Lang {
  return currentLang;
}

export function getLocale(lang: Lang = currentLang): string {
  return lang === 'es' ? 'es-US' : 'en-US';
}

export function setLang(lang: Lang): void {
  currentLang = lang;
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lang;
  }
}

export function setLanguage(lang: Lang): void {
  setLang(lang);
}

export const lang = {
  get value(): Lang {
    return currentLang;
  },
  set value(v: Lang) {
    setLang(v);
  },
};

export function useLang(): Lang {
  return currentLang;
}

function formatMoney(cents: number, lang: Lang = currentLang): string {
  const n = Number(cents) / 100;
  return new Intl.NumberFormat(getLocale(lang), {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
  }).format(n);
}

export function plural(count: number, lang: Lang = currentLang): string {
  return new Intl.PluralRules(getLocale(lang)).select(count);
}

export function formatDate(date: Date | string | number, lang: Lang = currentLang): string {
  const d = date instanceof Date ? date : new Date(date);
  return new Intl.DateTimeFormat(getLocale(lang)).format(d);
}

export function formatNumber(value: number, lang: Lang = currentLang): string {
  return new Intl.NumberFormat(getLocale(lang)).format(value);
}

export function t(key: string, vars?: Record<string, unknown>): string {
  const lang = currentLang;
  const table = messages[lang] || messages.es;
  let msg = Object.prototype.hasOwnProperty.call(table, key) ? table[key] : key;
  const v = vars || {};
  if (typeof v.cents === 'number') {
    const money = formatMoney(v.cents as number, lang);
    msg = msg.replace(/\{cents\}/g, money).replace(/\{money\}/g, money).replace(/\{amount\}/g, money);
  }
  for (const [k, val] of Object.entries(v)) {
    if (k === 'cents') continue;
    msg = msg.replace(new RegExp('\\{' + k + '\\}', 'g'), String(val));
  }
  if (typeof v.count === 'number' && msg.includes('{plural}')) {
    msg = msg.replace(/\{plural\}/g, new Intl.PluralRules(getLocale(lang)).select(v.count as number));
  }
  return msg;
}

setLang('es');

export default { t, setLang, getLang, setLanguage, lang, plural, formatDate, formatNumber, formatMoney };
