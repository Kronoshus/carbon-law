import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setPlatform } from '../src/platform';
import { apiFetch, TOKEN_KEY } from '../src/core/api';

describe('apiFetch', () => {
  beforeEach(() => {
    const store: Record<string, string> = { [TOKEN_KEY]: 'tok123' };
    setPlatform({
      storage: {
        get: async (k: string) => store[k] ?? null,
        set: async (k: string, v: string) => { store[k] = v; },
        remove: async (k: string) => { delete store[k]; },
      },
      getMicrophone: async () => null,
      notify: async () => {},
      openUrl: () => {},
      scheduleReminder: async () => {},
    } as unknown as Parameters<typeof setPlatform>[0]);
    (globalThis as unknown as { fetch: unknown }).fetch = vi.fn(async () => new Response('{}', { status: 200 }));
  });

  it('sends Authorization header when token exists', async () => {
    await apiFetch('/x');
    const f = (globalThis as unknown as { fetch: ReturnType<typeof vi.fn> }).fetch;
    const headers = f.mock.calls[0][1].headers;
    expect(headers.get('Authorization')).toBe('Bearer tok123');
  });

  it('sets JSON body and content-type', async () => {
    await apiFetch('/x', { method: 'POST', json: { a: 1 } });
    const f = (globalThis as unknown as { fetch: ReturnType<typeof vi.fn> }).fetch;
    const init = f.mock.calls[0][1];
    expect(init.body).toBe(JSON.stringify({ a: 1 }));
    expect(init.headers.get('Content-Type')).toBe('application/json');
  });

  it('clears token on 401', async () => {
    (globalThis as unknown as { fetch: unknown }).fetch = vi.fn(async () => new Response('', { status: 401 }));
    await apiFetch('/x');
    const platform = (await import('../src/platform')).getPlatform();
    expect(await platform.storage.get(TOKEN_KEY)).toBeNull();
  });
});
