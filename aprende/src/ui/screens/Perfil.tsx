/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useState } from 'preact/hooks';
import { navigate } from '../../core/router';
import { t, lang, setLang } from '../../core/i18n';
import { apiFetch, clearToken } from '../../core/api';
import { installPrompt } from '../../core/pwa';
import { THEMES, theme, setTheme } from '../../core/theme';
import type { I18nKey } from '../../core/i18n-keys';

type Reminders = { enabled: boolean; local_time: string | null };

export function Perfil() {
  const [reminders, setReminders] = useState<Reminders>({ enabled: false, local_time: null });
  const [time, setTime] = useState('18:00');
  const [denied, setDenied] = useState(false);
  const [installed, setInstalled] = useState<'none' | 'installed' | 'cancelled'>('none');
  const [supported, setSupported] = useState(false);
  const [captured, setCaptured] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const res = await apiFetch('/progress');
      if (cancelled || !res.ok) return;
      const data = await res.json();
      const r = data.reminders as Reminders;
      setReminders(r);
      if (r.local_time) setTime(r.local_time);
    })();
    setSupported(typeof (Navigator.prototype as any).install === 'function' || !!installPrompt.value);
    const unsub = installPrompt.subscribe((v: any) => { if (v) setCaptured(true); });
    return () => { cancelled = true; unsub(); };
  }, []);

  const showInstall = supported || captured || !!installPrompt.value;

  async function toggleReminder(next: boolean) {
    if (next) {
      const res = await apiFetch('/progress/reminders', { method: 'PUT', json: { enabled: true, local_time: time } });
      if (!res.ok) return;
      const r = await res.json();
      setReminders(r);
      setDenied(false);
      const keyRes = await apiFetch('/progress/push-key');
      const keyData = keyRes.ok ? await keyRes.json() : { public_key: null };
      const pub = keyData.public_key;
      if (pub && 'PushManager' in window) {
        const perm = await Notification.requestPermission();
        if (perm === 'granted') {
          try {
            const reg = await (navigator as any).serviceWorker.ready;
            const sub = await reg.pushManager.subscribe({
              userVisibleOnly: true,
              applicationServerKey: urlBase64ToUint8Array(pub),
            });
            const json = sub.toJSON();
            await apiFetch('/progress/push', {
              method: 'PUT',
              json: { endpoint: json.endpoint, keys: json.keys, lang: lang.value },
            });
          } catch { /* ignore */ }
        } else {
          setDenied(true);
        }
      }
    } else {
      await apiFetch('/progress/reminders', { method: 'PUT', json: { enabled: false, local_time: time } });
      setReminders({ enabled: false, local_time: time });
      try {
        const reg = await (navigator as any).serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        await sub?.unsubscribe();
      } catch { /* ignore */ }
    }
  }

  async function onTimeChange(v: string) {
    setTime(v);
    if (reminders.enabled) {
      const res = await apiFetch('/progress/reminders', { method: 'PUT', json: { enabled: true, local_time: v } });
      if (res.ok) setReminders(await res.json());
    }
  }

  async function onInstall() {
    const nav = navigator as any;
    if (typeof nav.install === 'function') {
      try {
        await nav.install();
        setInstalled('installed');
      } catch (e: any) {
        if (e && e.name === 'AbortError') setInstalled('cancelled');
      }
      return;
    }
    const ev = installPrompt.value as any;
    if (ev) {
      installPrompt.value = null;
      setCaptured(false);
      try {
        await ev.prompt();
        const choice = await ev.userChoice;
        if (choice && choice.outcome === 'accepted') setInstalled('installed');
        else setInstalled('cancelled');
      } catch (e: any) {
        if (e && e.name === 'AbortError') setInstalled('cancelled');
      }
    }
  }

  async function onSignOut() {
    await clearToken();
    navigate('/entrar');
  }

  return (
    <div class="screen perfil">
      <h1>{t('perfil.title')}</h1>
      <section class="field">
        <label for="lang">{t('perfil.language')}</label>
        <select id="lang" value={lang.value} onChange={(e) => setLang((e.target as HTMLSelectElement).value as any)}>
          <option value="es">{'Español'}</option>
          <option value="en">{'English'}</option>
        </select>
      </section>
      <fieldset class="theme-choice">
        <legend>{t('perfil.theme')}</legend>
        {THEMES.map((k) => (
          <label class="option" key={k}>
            <input type="radio" name="theme" value={k} checked={theme.value === k} onChange={() => setTheme(k)} />
            <span>{t(`theme.${k}` as I18nKey)}<small>{t(`theme.${k}.note` as I18nKey)}</small></span>
          </label>
        ))}
      </fieldset>
      <section class="field">
        <label class="option">
          <input type="checkbox" role="switch" checked={reminders.enabled} onChange={(e) => toggleReminder((e.target as HTMLInputElement).checked)} />
          {t('perfil.reminder')}
        </label>
        <label class="field">
          {t('perfil.reminderTime')}
          <input type="time" value={time} onInput={(e) => onTimeChange((e.target as HTMLInputElement).value)} />
        </label>
        <p>{t('perfil.reminderNote')}</p>
        {denied ? <p role="status">{t('perfil.reminderDenied')}</p> : null}
      </section>
      {showInstall ? (
        <button class="btn secondary" type="button" onClick={() => void onInstall()}>{t('perfil.install')}</button>
      ) : null}
      {installed === 'installed' ? <p role="status">{t('perfil.installed')}</p> : null}
      {installed === 'cancelled' ? <p role="status">{t('perfil.installCancelled')}</p> : null}
      <button class="btn secondary" type="button" onClick={() => void onSignOut()}>{t('top.signout')}</button>
    </div>
  );
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
  return outputArray;
}
