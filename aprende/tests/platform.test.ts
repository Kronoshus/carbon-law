import { describe, it, expect, vi } from 'vitest';
import { setPlatform, platform } from '../src/platform';

describe('platform proxy', () => {
  it('binds scheduleReminder this', async () => {
    vi.useFakeTimers();
    const notify = vi.fn();
    const impl = {
      storage: { get: async () => null, set: async () => {}, remove: async () => {} },
      getMicrophone: async () => null,
      notify,
      openUrl: () => {},
      async scheduleReminder(this: { notify: typeof notify }, when: number, message: string) {
        await this.notify('Recordatorio', message);
      },
    };
    setPlatform(impl as unknown as Parameters<typeof setPlatform>[0]);
    const p = platform as unknown as { scheduleReminder: (w: number, m: string) => Promise<void> };
    await p.scheduleReminder(Date.now() + 10, 'hi');
    vi.useRealTimers();
    expect(true).toBe(true);
  });
});
