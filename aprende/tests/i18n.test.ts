import { h } from 'preact';
import { render } from '@testing-library/preact';
import { describe, it, expect } from 'vitest';
import { t, setLang, lang, formatMoney } from '../src/core/i18n';

describe('i18n', () => {
  it('interpolates vars', () => {
    setLang('es');
    expect(t('price.now', { price: formatMoney(280000) })).toBe('$2,800');
  });
  it('money in both languages', () => {
    setLang('es');
    expect(t('price.now', { price: formatMoney(280000) })).toBe('$2,800');
    setLang('en');
    expect(t('price.now', { price: formatMoney(280000) })).toBe('$2,800');
  });
  it('plural one/other in both languages', () => {
    setLang('es');
    expect(t('lessons.done', { count: 1 })).toBe('1 lección completada');
    expect(t('lessons.done', { count: 3 })).toBe('3 lecciones completadas');
    setLang('en');
    expect(t('lessons.done', { count: 1 })).toBe('1 lesson completed');
    expect(t('lessons.done', { count: 3 })).toBe('3 lessons completed');
  });
  it('html lang updates', () => {
    setLang('es');
    expect(document.documentElement.lang).toBe('es');
    setLang('en');
    expect(document.documentElement.lang).toBe('en');
  });
  it('setLang re-renders component using t', () => {
    setLang('es');
    function Comp() {
      return h('div', null, t('app.title'), ' ', lang.value);
    }
    const { container } = render(h(Comp, null));
    expect(container.textContent).toContain('es');
    setLang('en');
    expect(container.textContent).toContain('en');
  });
});
