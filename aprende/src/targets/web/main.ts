import { h, render } from 'preact';
import { setPlatform } from '../../platform';
import { webPlatform } from './platform';
import { App } from '../../ui/App';

setPlatform(webPlatform);
render(h(App, null), document.getElementById('app')!);
