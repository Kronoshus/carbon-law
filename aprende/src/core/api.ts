import { getPlatform } from '../platform';
import { signal } from '@preact/signals';
import { navigate } from './router';

export const TOKEN_KEY = 'aprende_token';

export async function getToken(): Promise<string | null> {
  return getPlatform().storage.get(TOKEN_KEY);
}

export async function setToken(token: string): Promise<void> {
  await getPlatform().storage.set(TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await getPlatform().storage.remove(TOKEN_KEY);
}

export type ApiOptions = RequestInit & { json?: unknown };

const API_ORIGIN = (import.meta.env.VITE_API_ORIGIN as string | undefined) ?? '';

export async function apiFetch(path: string, options: ApiOptions = {}): Promise<Response> {
  const platform = getPlatform();
  const { json, headers, ...rest } = options;
  const token = await platform.storage.get(TOKEN_KEY);
  const h = new Headers(headers);
  if (json !== undefined) h.set('Content-Type', 'application/json');
  if (token) h.set('Authorization', `Bearer ${token}`);
  const body = json !== undefined ? JSON.stringify(json) : (options as RequestInit).body;
  const res = await fetch(`${API_ORIGIN}${path}`, { ...rest, headers: h, body });
  if (res.status === 503) {
    try {
      const clone = res.clone();
      const j = await clone.json();
      if (j && j.error === 'extension_off') extensionOff.value = true;
    } catch { /* ignore */ }
  }
  if (res.status === 401) {
    await platform.storage.remove(TOKEN_KEY);
    if (typeof window !== 'undefined' && !window.location.hash.startsWith('#/bienvenida') && !window.location.hash.startsWith('#/entrar') && !window.location.hash.startsWith('#/cuenta-nueva')) {
      navigate('/bienvenida');
    }
  }
  return res;
}

export const extensionOff = signal(false);
