import type { ComponentChildren } from 'preact';
import { route, navigate } from '../core/router';
import { t } from '../core/i18n';
import type { I18nKey } from '../core/i18n-keys';
import { clearToken } from '../core/api';
import { Icon, type IconName } from './Icons';

const TABS: { path: string; key: I18nKey; icon: IconName }[] = [
  { path: '/aprender', key: 'nav.aprender', icon: 'mapa' },
  { path: '/plan', key: 'nav.plan', icon: 'plan' },
  { path: '/preguntas', key: 'nav.preguntas', icon: 'pregunta' },
  { path: '/perfil', key: 'nav.perfil', icon: 'perfil' },
];

function isActive(tabPath: string): boolean {
  const r = route.value;
  if (r === tabPath || r.startsWith(tabPath + '/')) return true;
  if (tabPath === '/aprender' && (r.startsWith('/inicio') || r.startsWith('/leccion'))) return true;
  if (tabPath === '/plan' && r.startsWith('/plan')) return true;
  return false;
}

/** `bare`: the header only — for the day-1 gate, where the client does one thing at a time. */
export function Shell({ children, bare = false }: { children?: ComponentChildren; bare?: boolean }) {
  async function signOut() {
    await clearToken();
    navigate('/entrar');
  }
  return (
    <div class="shell">
      <header class="topbar">
        <span class="topbar-title">{t('top.title')}</span>
        {bare ? (
          <button type="button" class="topbar-signout" onClick={() => void signOut()}>
            {t('top.signout')}
          </button>
        ) : null}
      </header>
      {bare ? <main class="shell-main">{children}</main> : <>
      <div class="shell-body">
        <nav class="rail" aria-label={t('top.title')}>
          {TABS.map((tab) => (
            <a
              key={tab.path}
              href={'#' + tab.path}
              class="rail-link"
              aria-current={isActive(tab.path) ? 'page' : undefined}
            >
              <Icon name={tab.icon} />{t(tab.key)}
            </a>
          ))}
        </nav>
        <main class="shell-main">{children}</main>
      </div>
      <nav class="tabs" aria-label={t('top.title')}>
        {TABS.map((tab) => (
          <a
            key={tab.path}
            href={'#' + tab.path}
            class="tab-link"
            aria-current={isActive(tab.path) ? 'page' : undefined}
          >
            <Icon name={tab.icon} />{t(tab.key)}
          </a>
        ))}
      </nav>
      </>}
    </div>
  );
}
