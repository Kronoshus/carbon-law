import '../../ui/fonts';
import '../../ui/tokens.css';
import '../../ui/themes.css';
import '../../core/theme';
import './popup.css';
import { h, render } from 'preact';
import { setPlatform } from '../../platform';
import { extensionPlatform } from './platform';
import { Popup } from './Popup';

setPlatform(extensionPlatform);
render(h(Popup, null), document.getElementById('app')!);
