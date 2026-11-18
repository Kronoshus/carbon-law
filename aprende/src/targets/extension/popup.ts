import '@fontsource/work-sans/400.css';
import '@fontsource/work-sans/700.css';
import '@fontsource/league-spartan/800.css';
import '../../ui/tokens.css';
import './popup.css';
import { h, render } from 'preact';
import { setPlatform } from '../../platform';
import { extensionPlatform } from './platform';
import { Popup } from './Popup';

setPlatform(extensionPlatform);
render(h(Popup, null), document.getElementById('app')!);
