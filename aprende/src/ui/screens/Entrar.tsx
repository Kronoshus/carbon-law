import { useState } from 'preact/hooks';
import { navigate } from '../../core/router';
import { t } from '../../core/i18n';
import { setToken } from '../../core/api';
import { apiFetch } from '../../core/api';

export function Entrar() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: Event) {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const res = await apiFetch('/auth/login', {
        method: 'POST',
        json: { email, password },
      });
      if (!res.ok) { setError(t('error.invalid')); return; }
      const data = await res.json();
      await setToken(data.token as string);
      // decide landing via journey
      try {
        const jr = await apiFetch('/journey');
        if (jr.ok) {
          const j = await jr.json();
          const facts = j.facts || {};
          if (!facts.ai_disclosed) { navigate('/inicio/ia'); return; }
        }
      } catch { /* fall through */ }
      navigate('/aprender');
    } catch {
      setError(t('error.invalid'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main class="screen entrar">
      <h1>{t('entrar.title')}</h1>
      <form onSubmit={onSubmit} autocomplete="on">
        <label>
          {t('entrar.email')}
          <input type="email" name="email" autocomplete="username" value={email} onInput={(e) => setEmail((e.target as HTMLInputElement).value)} required aria-invalid={!!error} aria-describedby={error ? "signin-error" : undefined} />
        </label>
        <label>
          {t('entrar.password')}
          <input type="password" name="password" autocomplete="current-password" value={password} onInput={(e) => setPassword((e.target as HTMLInputElement).value)} required aria-invalid={!!error} aria-describedby={error ? "signin-error" : undefined} />
        </label>
        {error ? <p id="signin-error" role="alert">{error}</p> : null}
        <button type="submit" disabled={submitting}>{t('entrar.submit')}</button>
      </form>
    </main>
  );
}
