export function duration(sec: number | null | undefined): string {
  if (!sec) return '';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h) return `${h} h ${m} min`;
  if (m >= 10) return `${m} min`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function ago(iso: string | null | undefined): string {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 0) return '';
  if (diff < 3600) return `hace ${Math.max(1, Math.round(diff / 60))} min`;
  if (diff < 86400) return `hace ${Math.round(diff / 3600)} h`;
  const d = Math.round(diff / 86400);
  if (d < 30) return `hace ${d} ${d === 1 ? 'día' : 'días'}`;
  const mo = Math.round(d / 30);
  if (mo < 12) return `hace ${mo} ${mo === 1 ? 'mes' : 'meses'}`;
  const y = Math.round(d / 365);
  return `hace ${y} ${y === 1 ? 'año' : 'años'}`;
}

export function minutes(seconds: number): string {
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m} min`;
  return `${Math.floor(m / 60)} h ${m % 60} min`;
}

export const PLATFORM_LABEL: Record<string, string> = {
  youtube: 'YouTube', tiktok: 'TikTok', instagram: 'Instagram', vimeo: 'Vimeo', article: 'Artículo', myfeed: 'MyFeed',
};

export const PART_LABEL: Record<string, string> = {
  relevance: 'Relevancia', quality: 'Calidad', recency: 'Actualidad', credibility: 'Credibilidad', novelty: 'Diversidad',
  exploration: 'Exploración',
};
