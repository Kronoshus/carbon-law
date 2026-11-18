
import { signal } from '@preact/signals';
import type { I18nKey } from './i18n-keys';
import es from '../../i18n/es.json';
import en from '../../i18n/en.json';

export type Lang = 'es' | 'en';

const messages: Record<Lang, Record<string, string>> = {
  es: es as Record<string, string>,
  en: en as Record<string, string>,
};

export const lang = signal<Lang>('es');

export function setLang(l: Lang): void {
  lang.value = l;
  if (typeof document !== 'undefined') {
    document.documentElement.lang = l;
  }
}

export function getLocale(l: Lang = lang.value): string {
  return l === 'es' ? 'es-US' : 'en-US';
}

export function formatMoney(cents: number): string {
  const n = Number(cents) / 100;
  return new Intl.NumberFormat(getLocale(), {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
  }).format(n);
}

export function formatDate(date: Date | string | number, opts?: Intl.DateTimeFormatOptions): string {
  const d = date instanceof Date ? date : new Date(date);
  return new Intl.DateTimeFormat(getLocale(), opts).format(d);
}

const warned = new Set<string>();

export function t(key: I18nKey, vars?: Record<string, unknown>): string {
  const l = lang.value;
  const table = messages[l] || messages.es;
  const v = vars || {};

  // plural handling: if vars.count is a number and catalog has key.one / key.other
  let resolvedKey = String(key);
  if (typeof v.count === 'number') {
    const oneKey = `${resolvedKey}.one`;
    const otherKey = `${resolvedKey}.other`;
    if (Object.prototype.hasOwnProperty.call(table, oneKey) && Object.prototype.hasOwnProperty.call(table, otherKey)) {
      const cat = new Intl.PluralRules(getLocale(l)).select(v.count as number);
      const pick = cat === 'one' ? oneKey : otherKey;
      resolvedKey = pick;
    }
  }

  if (!Object.prototype.hasOwnProperty.call(table, resolvedKey)) {
    if (import.meta.env?.DEV && !warned.has(resolvedKey)) {
      warned.add(resolvedKey);
      console.warn(`Missing i18n key: ${resolvedKey}`);
    }
    return resolvedKey;
  }

  let msg = table[resolvedKey];
  msg = msg.replace(/\{(\w+)\}/g, (_m, name: string) => {
    if (Object.prototype.hasOwnProperty.call(v, name)) return String(v[name]);
    return `{${name}}`;
  });
  return msg;
}
