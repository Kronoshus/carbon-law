import { t } from '../../core/i18n';

export function Bienvenida() {
  return (
    <main class="screen bienvenida">
      <h1>{t('bienvenida.title')}</h1>
      <section class="host" aria-label={t('bienvenida.host')}>
        <img src={`${import.meta.env.BASE_URL}img/calavera-face.png`} alt="" width="72" height="72" />
        <p class="bubble">{t('bienvenida.what.body')}</p>
      </section>
      <div class="actions">
        <a href="#/cuenta-nueva" class="btn">{t('bienvenida.signup')}</a>
        <a href="#/entrar" class="btn secondary">{t('bienvenida.signin')}</a>
      </div>
      <p class="note">{t('bienvenida.note')}</p>
    </main>
  );
}
