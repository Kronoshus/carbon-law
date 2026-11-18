import { signal } from '@preact/signals';

function normalize(hash: string): string {
  const h = (hash || '').replace(/^#/, '');
  return h === '' ? '/bienvenida' : h;
}

export const route = signal<string>(typeof window !== 'undefined' ? normalize(window.location.hash) : '/bienvenida');

if (typeof window !== 'undefined') {
  window.addEventListener('hashchange', () => {
    route.value = normalize(window.location.hash);
  });
}

export function navigate(to: string): void {
  if (typeof window !== 'undefined') {
    window.location.hash = '#' + to;
  } else {
    route.value = to;
  }
}
