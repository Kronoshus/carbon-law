import type { ComponentChildren } from 'preact';
import { route, navigate } from '../core/router';
import { t } from '../core/i18n';
import type { I18nKey } from '../core/i18n-keys';
import { clearToken } from '../core/api';
import './shell.css';

const TABS: { path: string; key: I18nKey }[] = [
  { path: '/aprender', key: 'nav.aprender' },
  { path: '/plan', key: 'nav.plan' },
  { path: '/preguntas', key: 'nav.preguntas' },
  { path: '/perfil', key: 'nav.perfil' },
];

function isActive(tabPath: string): boolean {
  const r = route.value;
  if (r === tabPath || r.startsWith(tabPath + '/')) return true;
  if (tabPath === '/aprender' && (r.startsWith('/inicio') || r.startsWith('/leccion'))) return true;
  if (tabPath === '/plan' && r.startsWith('/plan')) return true;
  return false;
}

export function Shell({ children }: { children: ComponentChildren }) {
  async function signOut() {
    await clearToken();
    navigate('/entrar');
  }
  return (
    <div class="shell">
      <header class="topbar">
        <span class="topbar-title">{t('top.title')}</span>
        <button type="button" class="topbar-signout" onClick={() => void signOut()}>
          {t('top.signout')}
        </button>
      </header>
      <div class="shell-body">
        <nav class="rail" aria-label={t('top.title')}>
          {TABS.map((tab) => (
            <a
              key={tab.path}
              href={'#' + tab.path}
              class="rail-link"
              aria-current={isActive(tab.path) ? 'page' : 'false'}
            >
              {t(tab.key)}
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
            aria-current={isActive(tab.path) ? 'page' : 'false'}
          >
            {t(tab.key)}
          </a>
        ))}
      </nav>
    </div>
  );
}
