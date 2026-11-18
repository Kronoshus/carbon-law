import './tokens.css';
import { t } from '../core/i18n';

export function App() {
  return (
    <main>
      <h1>{t('app.title')}</h1>
      <p>{t('app.welcome')}</p>
    </main>
  );
}
