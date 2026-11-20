export type Format = 'all' | 'short' | 'long' | 'article';

export interface ItemState {
  liked: boolean;
  saved: boolean;
  hidden: boolean;
  note: string;
  collection: string;
  seen_count: number;
}

export interface Score {
  total: number;
  parts: Record<string, number>;
  reasons: string[];
}

export interface Item {
  id: number;
  platform: 'youtube' | 'tiktok' | 'instagram' | 'vimeo' | 'article' | 'myfeed';
  external_id: string;
  url: string;
  embed_url: string;
  title: string;
  description: string;
  summary: string;
  key_points: string[];
  author_name: string;
  creator: { id: number; name: string } | null;
  thumbnail_url: string;
  duration_sec: number | null;
  format: 'short' | 'long' | 'article';
  language: string;
  category: string | null;
  subtopic: string | null;
  tags: string[];
  published_at: string | null;
  discovered_at: string | null;
  quality: number;
  credibility: number;
  is_news: boolean;
  analysis: string;
  state: ItemState;
  score: Score | null;
}

export interface Usage {
  day: string;
  seconds: number;
  limit_seconds: number;
  remaining_seconds: number | null;
  exceeded: boolean;
  break_every_minutes: number;
  extra_minutes: number;
}

export interface FeedCommand {
  id: number;
  label: string;
  categories: string[];
  subtopics: string[];
  keywords: string[];
  format: Format;
  max_age_days: number | null;
}

export interface FeedPage {
  session: string;
  offset: number;
  items: Item[];
  has_more: boolean;
  command: FeedCommand | null;
  usage: Usage | null;
}

export interface Category {
  slug: string;
  name: string;
  emoji: string;
  color: string;
  description: string;
  weight: number;
  enabled: boolean;
  items: number;
  subtopics: { slug: string; name: string; enabled: boolean }[];
}

export interface Creator {
  id: number;
  platform: string;
  external_id: string;
  name: string;
  handle: string;
  url: string;
  category: string | null;
  language: string;
  status: 'approved' | 'suggested' | 'rejected' | 'muted' | 'error';
  origin: string;
  reason: string;
  credibility: number;
  items: number;
}

export interface Settings {
  daily_limit_minutes: number;
  break_every_minutes: number;
  autoplay: boolean;
  muted_start: boolean;
  show_reasons: boolean;
  exploration: boolean;
  language: string;
  purpose_prompt: boolean;
  quiet_hours: { enabled: boolean; start: string; end: string };
  onboarded: boolean;
}

export interface Highlights {
  day: string;
  headline: string;
  summary: string;
  generator: string;
  items: Item[];
}

export interface Stats {
  days: { day: string; minutes: number; items: number; extra_minutes: number }[];
  total_minutes: number;
  avg_minutes: number;
  by_category: { slug: string; name: string; emoji: string; color: string; minutes: number }[];
  streak_days: number;
  events: Record<string, number>;
  notes: number;
  saved: number;
}

export interface Status {
  version: string;
  claude: { enabled: boolean; model: string | null };
  youtube_api: boolean;
  redis: boolean;
  database: string;
  items: Record<string, number>;
  items_total: number;
  pending_analysis: number;
  creators: Record<string, number>;
  sources: number;
  auth: boolean;
}
