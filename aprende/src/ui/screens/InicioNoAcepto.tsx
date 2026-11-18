import { h } from 'preact';
import { navigate } from '../../core/router';
import { t } from '../../core/i18n';

export function InicioNoAcepto() {
  return h('section', { class: 'screen gate' },
    h('h1', null, t('gate.refused.title')),
    h('p', null, t('gate.refused.body')),
    h('div', { class: 'row' },
      h('button', { class: 'btn', onClick: () => navigate('/aprender') }, t('gate.refused.learn')),
      h('button', { class: 'btn', onClick: () => navigate('/inicio/consentimiento') }, t('gate.refused.change')),
    ),
  );
}
