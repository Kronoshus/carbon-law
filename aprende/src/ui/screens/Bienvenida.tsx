import { t } from '../../core/i18n';
import { host, nameKey } from '../../core/character/cast';
import { CharacterStage } from '../CharacterStage';
import './bienvenida.css';

/** The front door: the theme's host on its stage, one promise, and the two ways in. */
export function Bienvenida() {
  return (
    <div class="shell welcome-shell">
      <header class="topbar"><span class="topbar-title">{t('bienvenida.title')}</span></header>
      <main class="welcome">
        <div class="welcome-stage">
          <CharacterStage character={host()} />
        </div>
        <h1 class="welcome-promise">{t('bienvenida.promise')}</h1>
        <section class="welcome-say" aria-label={t('bienvenida.host', { name: t(nameKey(host())) })}>
          <p class="bubble">{t('bienvenida.what.body')}</p>
        </section>
        <div class="welcome-actions">
          <a href="#/cuenta-nueva" class="btn">{t('bienvenida.signup')}</a>
          <a href="#/entrar" class="btn secondary">{t('bienvenida.signin')}</a>
        </div>
        <footer class="welcome-foot">
          <p class="note">{t('bienvenida.note')}</p>
          <p class="note"><a href="#/privacidad">{t('privacy.link')}</a></p>
        </footer>
      </main>
    </div>
  );
}
