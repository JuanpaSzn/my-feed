import AsyncStorage from '@react-native-async-storage/async-storage';

export async function getJSON<T>(key: string, fallback: T): Promise<T> {
  try {
    const raw = await AsyncStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export async function setJSON(key: string, value: unknown): Promise<void> {
  try {
    await AsyncStorage.setItem(key, JSON.stringify(value));
  } catch {
    // almacenamiento lleno o no disponible: la caché es opcional
  }
}

export const KEYS = {
  server: 'myfeed.server',
  token: 'myfeed.token',
  feedCache: 'myfeed.cache.feed',
  highlightsCache: 'myfeed.cache.highlights',
  purposeDay: 'myfeed.purpose.day',
  muted: 'myfeed.muted',
};
