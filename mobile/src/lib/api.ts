import Constants from 'expo-constants';
import { Platform } from 'react-native';

import { getJSON, KEYS, setJSON } from './storage';
import type {
  Category, Creator, FeedPage, Format, Highlights, Item, Settings, Stats, Status, Usage,
} from './types';

let baseUrl = '';
let token = '';

/** Adivina dónde está el backend: en Expo Go, el mismo PC que sirve la app, puerto 8000. */
export function guessServer(): string {
  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location;
    // Servido por nginx junto a la API (docker compose --profile web): mismo origen.
    if (port === '' || port === '80' || port === '443' || port === '8080') return `${protocol}//${window.location.host}`;
    return `${protocol}//${hostname}:8000`;
  }
  const host =
    Constants.expoConfig?.hostUri ??
    (Constants as unknown as { expoGoConfig?: { debuggerHost?: string } }).expoGoConfig?.debuggerHost ??
    '';
  const ip = host.split(':')[0];
  return ip ? `http://${ip}:8000` : 'http://192.168.1.10:8000';
}

export async function initApi(): Promise<{ server: string; token: string }> {
  baseUrl = (await getJSON<string>(KEYS.server, '')) || guessServer();
  token = await getJSON<string>(KEYS.token, '');
  return { server: baseUrl, token };
}

export async function configureApi(server: string, newToken: string) {
  baseUrl = server.trim().replace(/\/+$/, '');
  if (!/^https?:\/\//.test(baseUrl)) baseUrl = `http://${baseUrl}`;
  token = newToken.trim();
  await setJSON(KEYS.server, baseUrl);
  await setJSON(KEYS.token, token);
}

export const getServer = () => baseUrl;

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, opts: { method?: string; body?: unknown; timeout?: number } = {}): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), opts.timeout ?? 15000);
  try {
    const res = await fetch(`${baseUrl}${path}`, {
      method: opts.method ?? 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'X-App-Token': token } : {}),
      },
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal: ctrl.signal,
    });
    if (!res.ok) {
      let msg = `Error ${res.status}`;
      try {
        const d = await res.json();
        msg = typeof d.detail === 'string' ? d.detail : msg;
      } catch {}
      throw new ApiError(res.status, msg);
    }
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError(0, 'No se pudo conectar con tu servidor de MyFeed');
  } finally {
    clearTimeout(timer);
  }
}

const qs = (p: Record<string, string | number | undefined | null>) =>
  Object.entries(p)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join('&');

export type EventKind =
  | 'like' | 'unlike' | 'save' | 'unsave' | 'hide' | 'view' | 'share' | 'open_source'
  | 'less_like_this' | 'more_like_this';

export const api = {
  health: () => request<{ ok: boolean }>('/health', { timeout: 5000 }),
  status: () => request<Status>('/api/status'),
  feed: (p: { session?: string; offset?: number; limit?: number; format?: Format; category?: string }) =>
    request<FeedPage>(`/api/feed?${qs(p)}`),
  item: (id: number) => request<Item>(`/api/items/${id}`),
  event: (id: number, kind: EventKind, value = 0) =>
    request<Item>(`/api/items/${id}/events`, { method: 'POST', body: { kind, value } }),
  broken: (id: number) => request(`/api/items/${id}/broken`, { method: 'POST' }),
  note: (id: number, note: string, collection?: string) =>
    request<Item>(`/api/items/${id}/note`, { method: 'PUT', body: { note, collection } }),
  addLink: (url: string, category?: string) =>
    request<Item>('/api/items', { method: 'POST', body: { url, category }, timeout: 25000 }),
  saved: (collection?: string) => request<Item[]>(`/api/saved?${qs({ collection })}`),
  collections: () => request<{ name: string; key: string; count: number }[]>('/api/collections'),
  liked: () => request<Item[]>('/api/liked'),
  history: () => request<Item[]>('/api/history'),
  clearHistory: () => request('/api/history', { method: 'DELETE' }),
  notes: () => request<Item[]>('/api/notes'),
  search: (q: string, category?: string) => request<Item[]>(`/api/search?${qs({ q, category })}`),
  categories: () => request<Category[]>('/api/categories'),
  patchCategory: (slug: string, body: { weight?: number; enabled?: boolean }) =>
    request<Category>(`/api/categories/${slug}`, { method: 'PATCH', body }),
  patchSubtopic: (slug: string, enabled: boolean) =>
    request(`/api/subtopics/${slug}`, { method: 'PATCH', body: { enabled } }),
  creators: (status?: string) => request<Creator[]>(`/api/creators?${qs({ status })}`),
  addCreator: (url: string, category?: string) =>
    request<Creator>('/api/creators', { method: 'POST', body: { url, category }, timeout: 25000 }),
  patchCreator: (id: number, body: { status?: string; category?: string }) =>
    request<Creator>(`/api/creators/${id}`, { method: 'PATCH', body }),
  preferences: () =>
    request<{ likes: { key: string; label: string; score: number }[]; dislikes: { key: string; label: string; score: number }[] }>(
      '/api/preferences',
    ),
  forgetPreference: (key: string) => request(`/api/preferences/${encodeURIComponent(key)}`, { method: 'DELETE' }),
  resetPreferences: () => request('/api/preferences', { method: 'DELETE' }),
  command: (text: string) =>
    request<{ id: number; parsed: Record<string, unknown>; parser: string; found_online: number }>('/api/commands', {
      method: 'POST', body: { text }, timeout: 40000,
    }),
  commands: () =>
    request<{ id: number; text: string; active: boolean; parser: string; created_at: string }[]>('/api/commands'),
  clearCommand: () => request('/api/commands/active', { method: 'DELETE' }),
  reactivateCommand: (id: number) => request(`/api/commands/${id}/reactivate`, { method: 'POST' }),
  highlights: () => request<Highlights>('/api/highlights', { timeout: 30000 }),
  rebuildHighlights: () => request('/api/highlights/rebuild', { method: 'POST', timeout: 60000 }),
  settings: () => request<Settings>('/api/settings'),
  patchSettings: (body: Partial<Settings>) => request<Settings>('/api/settings', { method: 'PATCH', body }),
  heartbeat: (seconds: number, category: string | null, items_viewed: number) =>
    request<Usage>('/api/usage/heartbeat', { method: 'POST', body: { seconds, category, items_viewed } }),
  usage: () => request<Usage>('/api/usage/today'),
  extend: (minutes: number) => request<Usage>('/api/usage/extend', { method: 'POST', body: { minutes } }),
  stats: (days = 7) => request<Stats>(`/api/stats?days=${days}`),
  review: (n = 8) =>
    request<{ item_id: number; title: string; category: string; points: string[]; note: string; thumbnail_url: string }[]>(
      `/api/review?n=${n}`,
    ),
  runAgents: (agent = 'all', force = true) =>
    request('/api/agents/run', { method: 'POST', body: { agent, force } }),
  agentRuns: () =>
    request<{ id: number; agent: string; started_at: string; finished_at: string | null; ok: boolean; stats: Record<string, unknown>; error: string }[]>(
      '/api/agents/runs',
    ),
};
