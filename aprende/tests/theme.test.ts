import { describe, it, expect } from 'vitest';
import { setTheme, theme } from '../src/core/theme';

describe('theme', () => {
  it('a chosen theme is on <html> and kept for the next visit', () => {
    setTheme('codice');
    expect(document.documentElement.dataset.theme).toBe('codice');
    expect(localStorage.getItem('aprende_theme')).toBe('codice');
    expect(theme.value).toBe('codice');
  });
  it('Día de Muertos is the page without a theme attribute', () => {
    setTheme('muertos');
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false);
  });
});
