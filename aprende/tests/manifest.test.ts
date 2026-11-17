import { describe, it, expect } from 'vitest';
import { makeManifest } from '../src/targets/extension/manifest';

describe('makeManifest', () => {
  it('produces MV3 manifest with 5 perms and one host permission', () => {
    const m = makeManifest('https://carbon-law.onrender.com');
    expect(m.manifest_version).toBe(3);
    expect(m.permissions).toEqual(['sidePanel','storage','alarms','notifications','offscreen']);
    expect(m.host_permissions).toEqual(['https://carbon-law.onrender.com/*']);
  });
});
