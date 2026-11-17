import { getPlatform } from '../platform';

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

export async function apiFetch(path: string, options: ApiOptions = {}): Promise<Response> {
  const { json, headers, ...rest } = options;
  const token = await getToken();
  const h = new Headers(headers);
  if (json !== undefined) h.set('Content-Type', 'application/json');
  if (token) h.set('Authorization', `Bearer ${token}`);
  const body = json !== undefined ? JSON.stringify(json) : (options as RequestInit).body;
  return fetch(path, { ...rest, headers: h, body });
}

export const api = apiFetch;
export const request = apiFetch;

export default apiFetch;
