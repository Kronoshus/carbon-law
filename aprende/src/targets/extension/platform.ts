import type { Platform } from '../../platform';

export const extensionPlatform: Platform = {
  storage: {
    async get(key) { const r = await chrome.storage.session.get(key); return (r[key] as string) ?? null; },
    async set(key, value) { await chrome.storage.session.set({ [key]: value }); },
    async remove(key) { await chrome.storage.session.remove(key); },
  },
  async getMicrophone() {
    try { return await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch { return null; }
  },
  async notify(title, body) { await chrome.notifications.create({ type: 'basic', iconUrl: 'icon.png', title, message: body }); },
  openUrl(url) { chrome.tabs.create({ url }); },
  async scheduleReminder(when, message) {
    const whenMs = typeof when === 'number' ? when : when.getTime();
    await chrome.alarms.create(message, { when: whenMs });
  },
};
