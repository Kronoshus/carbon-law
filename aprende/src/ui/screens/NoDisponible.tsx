import { h } from 'preact';
import { t } from '../../core/i18n';

export function NoDisponible() {
  return h('main', { class: 'no-disponible' },
    h('h1', null, t('unavailable.title')),
    h('p', null, t('unavailable.body')));
}
