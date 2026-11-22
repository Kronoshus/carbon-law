import { t } from '../../core/i18n';
const EMAIL = 'info@carbonlaw.com';

export function Privacidad() {
  return (
    <main class="screen privacidad">
      <h1>{t('privacy.title')}</h1>
      <p class="note" role="note">{t('privacy.draft')}</p>
      <p>{t('privacy.intro')}</p>
      <section>
        <h2>{t('privacy.collect.title')}</h2>
        <p>{t('privacy.collect.body')}</p>
      </section>
      <section>
        <h2>{t('privacy.not.title')}</h2>
        <p>{t('privacy.not.body')}</p>
      </section>
      <section>
        <h2>{t('privacy.ai.title')}</h2>
        <p>{t('privacy.ai.body')}</p>
      </section>
      <section>
        <h2>{t('privacy.who.title')}</h2>
        <p>{t('privacy.who.body')}</p>
      </section>
      <section>
        <h2>{t('privacy.keep.title')}</h2>
        <p>{t('privacy.keep.body')}</p>
      </section>
      <section>
        <h2>{t('privacy.ext.title')}</h2>
        <p>{t('privacy.ext.body')}</p>
      </section>
      <section>
        <h2>{t('privacy.rights.title')}</h2>
        <p>{t('privacy.rights.body')} <a href="mailto:info@carbonlaw.com">{EMAIL}</a>{'.'}</p>
      </section>
      <p class="note">{t('privacy.version')}</p>
    </main>
  );
}
