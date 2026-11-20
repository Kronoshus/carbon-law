import { h, render } from 'preact';
import { setPlatform } from '../../platform';
import { extensionPlatform } from './platform';
import { App } from '../../ui/App';
import { extensionOff } from '../../core/api';

setPlatform(extensionPlatform);
void (async () => {
  try {
    const res = await fetch('/settings/public');
    if (res.status === 503) {
      const j = await res.json().catch(() => ({}));
      if (j && j.error === 'extension_off') extensionOff.value = true;
    }
  } catch { /* ignore */ }
})();
render(h(App, null), document.getElementById('app')!);
