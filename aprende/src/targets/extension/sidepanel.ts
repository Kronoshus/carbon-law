import { h, render } from 'preact';
import { setPlatform } from '../../platform';
import { extensionPlatform } from './platform';
import { App } from '../../ui/App';
import { apiFetch } from '../../core/api';

setPlatform(extensionPlatform);
void (async () => {
  await apiFetch('/settings/public');
})();
render(h(App, null), document.getElementById('app')!);
