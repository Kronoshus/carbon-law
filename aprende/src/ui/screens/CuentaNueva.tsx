import { useState } from 'preact/hooks';
import { navigate } from '../../core/router';
import { t, lang, setLang } from '../../core/i18n';
import { apiFetch, setToken } from '../../core/api';

export function CuentaNueva() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [adult, setAdult] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: Event) {
    e.preventDefault();
    if (!adult) { setError(t('error.adult')); return; }
    setSubmitting(true);
    setError('');
    try {
      const res = await apiFetch('/auth/signup', {
        method: 'POST',
        json: { name, email, password, source: 'aprende', adult: true },
      });
      if (!res.ok) {
        let msg = t('error.invalid');
        try {
          const body = await res.json();
          if (typeof body?.detail === 'string') msg = body.detail;
        } catch { /* ignore */ }
        setError(msg);
        return;
      }
      const data = await res.json();
      const token = data.token as string;
      await setToken(token);
      navigate('/inicio/ia');
    } catch {
      setError(t('error.invalid'));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main class="screen cuenta">
      <h1>{t('cuenta.title')}</h1>
      <form onSubmit={onSubmit} autocomplete="on">
        <label>
          {t('cuenta.name')}
          <input name="name" autocomplete="name" value={name} onInput={(e) => setName((e.target as HTMLInputElement).value)} required aria-invalid={!!error} aria-describedby={error ? "signup-error" : undefined} />
        </label>
        <label>
          {t('cuenta.email')}
          <input type="email" name="email" autocomplete="email" value={email} onInput={(e) => setEmail((e.target as HTMLInputElement).value)} required aria-invalid={!!error} aria-describedby={error ? "signup-error" : undefined} />
        </label>
        <label>
          {t('cuenta.password')}
          <input type="password" name="password" autocomplete="new-password" value={password} onInput={(e) => setPassword((e.target as HTMLInputElement).value)} required aria-invalid={!!error} aria-describedby={error ? "signup-error" : undefined} />
        </label>
        <label>
          <input type="checkbox" name="adult" checked={adult} onChange={(e) => setAdult((e.target as HTMLInputElement).checked)} />
          {t('cuenta.adult')}
        </label>
        <label>
          {t('cuenta.lang')}
          <select value={lang.value} onChange={(e) => setLang((e.target as HTMLSelectElement).value as 'es' | 'en')}>
            <option value="es">{'Español'}</option>
            <option value="en">{'English'}</option>
          </select>
        </label>
        {error ? <p id="signup-error" role="alert">{error}</p> : null}
        <button type="submit" disabled={submitting || !adult}>{t('cuenta.submit')}</button>
      </form>
    </main>
  );
}
