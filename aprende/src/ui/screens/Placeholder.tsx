import { t } from '../../core/i18n';

export function Placeholder() {
  return (
    <section class="screen placeholder">
      <h1>{t('placeholder.title')}</h1>
    </section>
  );
}
