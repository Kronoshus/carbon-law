import { h, render } from 'preact';
import { setPlatform } from '../../platform';
import { extensionPlatform } from './platform';
import { App } from '../../ui/App';

setPlatform(extensionPlatform);
render(h(App, null), document.getElementById('app')!);
