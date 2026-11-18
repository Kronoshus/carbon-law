import { h } from 'preact';
import { navigate } from '../../core/router';
import { t } from '../../core/i18n';

export function InicioEspera() {
  return h('section', { class: 'screen gate' },
    h('h1', null, t('gate.wait.title')),
    h('p', null, t('gate.wait.body')),
    h('button', { class: 'btn', onClick: () => navigate('/aprender') }, t('gate.wait.learn')),
  );
}
