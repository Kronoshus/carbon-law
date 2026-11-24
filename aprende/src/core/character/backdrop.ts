import { theme, type Theme } from '../theme';
/** Día de Muertos gives each character a backdrop of its own; every other theme has one backdrop for all three. */
export function backdropUrl(characterId: string, t: Theme = theme.value): string {
  const base = import.meta.env.BASE_URL;
  return t === 'muertos' ? `${base}characters/${characterId}-bg.jpg` : `${base}characters/backdrops/${t}.jpg`;
}
