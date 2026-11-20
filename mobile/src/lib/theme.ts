// Identidad visual propia de MyFeed: noche profunda + acentos menta y violeta.
export const colors = {
  bg: '#0A0D14',
  surface: '#121826',
  surface2: '#1A2233',
  border: '#263046',
  text: '#F3F5F9',
  muted: '#9AA3B5',
  faint: '#5E687D',
  accent: '#2EE6A6', // menta: acciones principales
  accent2: '#8B7CFF', // violeta: IA y comandos
  danger: '#FF5C7A',
  warning: '#FFC857',
  like: '#FF4D6D',
  save: '#FFC857',
  overlay: 'rgba(5,8,14,0.55)',
};

export const space = (n: number) => n * 4;
export const radius = { sm: 8, md: 14, lg: 22, pill: 999 };

export const font = {
  h1: { fontSize: 28, fontWeight: '800' as const, letterSpacing: -0.5 },
  h2: { fontSize: 20, fontWeight: '700' as const, letterSpacing: -0.2 },
  h3: { fontSize: 16, fontWeight: '700' as const },
  body: { fontSize: 15, lineHeight: 21 },
  small: { fontSize: 13, lineHeight: 18 },
  tiny: { fontSize: 11, fontWeight: '600' as const, letterSpacing: 0.3 },
};

export const CATEGORY_META: Record<string, { emoji: string; color: string; name: string }> = {
  deporte: { emoji: '⚽', color: '#22C55E', name: 'Fútbol y rendimiento' },
  ciberseguridad: { emoji: '🛡️', color: '#EF4444', name: 'Ciberseguridad' },
  ia: { emoji: '🤖', color: '#A855F7', name: 'Inteligencia artificial' },
  programacion: { emoji: '💻', color: '#3B82F6', name: 'Programación y tecnología' },
  mente: { emoji: '🧠', color: '#F59E0B', name: 'Psicología y filosofía' },
  ciencia: { emoji: '🔭', color: '#06B6D4', name: 'Ciencia y descubrimientos' },
};

export const catMeta = (slug?: string | null) =>
  (slug && CATEGORY_META[slug]) || { emoji: '✨', color: colors.accent, name: 'General' };
