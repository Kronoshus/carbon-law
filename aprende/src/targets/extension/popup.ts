import { h, render } from 'preact';
import { setPlatform } from '../../platform';
import { extensionPlatform } from './platform';
import { Popup } from './Popup';

setPlatform(extensionPlatform);
render(h(Popup, null), document.getElementById('app')!);
