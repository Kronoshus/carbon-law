import { describe, it, expect } from 'vitest';
import { setTheme, theme } from '../src/core/theme';
import { cast } from '../src/core/character/cast';

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
  it('each theme has its own host; La Calavera only hosts Día de Muertos, Piñata and El Oso keep their parts', () => {
    const hosts = { muertos: 'calavera', sol: 'girasol', huerto: 'colibri', vela: 'velita', codice: 'tortuga' } as const;
    for (const [t, id] of Object.entries(hosts)) {
      setTheme(t as keyof typeof hosts);
      expect(cast('calavera')).toBe(id);
      expect(cast('oso')).toBe('oso');
      expect(cast('pinata')).toBe('pinata');
    }
    setTheme('muertos');
  });
});
