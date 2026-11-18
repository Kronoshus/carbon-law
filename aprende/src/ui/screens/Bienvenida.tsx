import { t } from '../../core/i18n';

export function Bienvenida() {
  return (
    <main class="screen bienvenida">
      <h1>{t('bienvenida.title')}</h1>
      <h2>{t('bienvenida.what')}</h2>
      <p>{t('bienvenida.what.body')}</p>
      <div class="actions">
        <a href="#/cuenta-nueva" class="btn">{t('bienvenida.signup')}</a>
        <a href="#/entrar" class="btn">{t('bienvenida.signin')}</a>
      </div>
    </main>
  );
}
