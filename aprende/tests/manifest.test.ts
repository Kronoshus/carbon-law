import { describe, it, expect } from 'vitest';
import { makeManifest } from '../src/targets/extension/manifest';

describe('makeManifest', () => {
  // T8-02 (Opus, p8-tests): only the permissions the code uses (Store review). offscreen went with the microphone (F-003);
  // alarms and notifications have no caller: the reminders come from the web app (T8-03).
  it('produces MV3 manifest with 2 perms and one host permission', () => {
    const m = makeManifest('https://carbon-law.onrender.com');
    expect(m.manifest_version).toBe(3);
    expect(m.permissions).toEqual(['sidePanel', 'storage']);
    expect(m.host_permissions).toEqual(['https://carbon-law.onrender.com/*']);
  });
});
