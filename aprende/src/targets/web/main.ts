import { h, render } from 'preact';
import { setPlatform } from '../../platform';
import { webPlatform } from './platform';
import { App } from '../../ui/App';
import { installPrompt } from '../../core/pwa';

setPlatform(webPlatform);
render(h(App, null), document.getElementById('app')!);

if ('serviceWorker' in navigator) {
  const BASE = (import.meta.env.BASE_URL as string) || '/';
  navigator.serviceWorker.register(BASE + 'sw.js', { type: 'module', scope: BASE }).catch(() => {});
}

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  installPrompt.value = e;
});
