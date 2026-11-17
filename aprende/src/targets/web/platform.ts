import type { Platform } from '../../platform';

export const webPlatform: Platform = {
  storage: {
    async get(key) { return localStorage.getItem(key); },
    async set(key, value) { localStorage.setItem(key, value); },
    async remove(key) { localStorage.removeItem(key); },
  },
  async getMicrophone() {
    try { return await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch { return null; }
  },
  async notify(title, body) {
    if ('Notification' in window && Notification.permission === 'granted') new Notification(title, { body });
  },
  openUrl(url) { window.open(url, '_blank', 'noopener'); },
  async scheduleReminder(when, message) {
    // Web target: best-effort via setTimeout for the session.
    const delay = typeof when === 'number' ? when - Date.now() : when.getTime() - Date.now();
    if (delay > 0) setTimeout(() => { void this.notify('Recordatorio', message); }, delay);
  },
};
