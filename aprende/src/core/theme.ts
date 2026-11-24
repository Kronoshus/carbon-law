import { signal } from '@preact/signals';

/** The look of the app. Día de Muertos is the default (no attribute); the others re-point the role tokens (src/ui/themes.css). */
export const THEMES = ['muertos', 'vela', 'codice'] as const;
export type Theme = (typeof THEMES)[number];

const KEY = 'aprende_theme';
const BAR: Record<Theme, string> = { muertos: '#2A1145', vela: '#0F0A06', codice: '#F3EADA' };   // the browser bar, from each paper

function stored(): Theme {
  try {
    const v = localStorage.getItem(KEY);
    if ((THEMES as readonly string[]).includes(v ?? '')) return v as Theme;
  } catch { /* storage blocked: the default */ }
  return 'muertos';
}

function apply(t: Theme): void {
  if (typeof document === 'undefined') return;
  if (t === 'muertos') delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = t;
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', BAR[t]);
}

export const theme = signal<Theme>(stored());
apply(theme.value);

export function setTheme(t: Theme): void {
  theme.value = t;
  try { localStorage.setItem(KEY, t); } catch { /* the choice lasts this visit */ }
  apply(t);
}
