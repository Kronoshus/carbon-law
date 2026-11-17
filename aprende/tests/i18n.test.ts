
import { describe, it, expect } from 'vitest';
import { t, setLang, getLang } from '../src/core/i18n';

describe('i18n', () => {
  it('precio formats money', () => {
    setLang('es');
    expect(t('precio', { cents: 280000 })).toBe('$2,800');
    setLang('en');
    expect(t('precio', { cents: 280000 })).toBe('$2,800');
  });
  it('html lang follows', () => {
    setLang('es');
    expect(document.documentElement.lang).toBe('es');
    setLang('en');
    expect(document.documentElement.lang).toBe('en');
  });
});
