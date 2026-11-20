import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View, type ViewStyle } from 'react-native';

import { ago, duration, PLATFORM_LABEL } from '@/lib/format';
import { catMeta, colors, font, radius, space } from '@/lib/theme';
import type { Item } from '@/lib/types';

export function H1({ children }: { children: ReactNode }) {
  return <Text style={styles.h1}>{children}</Text>;
}

export function Section({ title, right, children }: { title: string; right?: ReactNode; children: ReactNode }) {
  return (
    <View style={{ gap: space(3) }}>
      <View style={styles.sectionHead}>
        <Text style={styles.sectionTitle}>{title}</Text>
        {right}
      </View>
      {children}
    </View>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Button({ label, onPress, kind = 'primary', busy, icon, testID }: {
  label: string; onPress: () => void; kind?: 'primary' | 'ghost' | 'danger'; busy?: boolean;
  icon?: keyof typeof Ionicons.glyphMap; testID?: string;
}) {
  const bg = kind === 'primary' ? colors.accent : kind === 'danger' ? 'rgba(255,92,122,0.15)' : colors.surface2;
  const fg = kind === 'primary' ? colors.bg : kind === 'danger' ? colors.danger : colors.text;
  return (
    <Pressable onPress={onPress} disabled={busy} testID={testID}
      style={({ pressed }) => [styles.button, { backgroundColor: bg, opacity: pressed ? 0.7 : 1 }]}>
      {busy ? <ActivityIndicator color={fg} /> : (
        <>
          {icon ? <Ionicons name={icon} size={18} color={fg} /> : null}
          <Text style={[styles.buttonText, { color: fg }]}>{label}</Text>
        </>
      )}
    </Pressable>
  );
}

export function Empty({ emoji, title, text }: { emoji: string; title: string; text?: string }) {
  return (
    <View style={styles.empty}>
      <Text style={{ fontSize: 40 }}>{emoji}</Text>
      <Text style={styles.emptyTitle}>{title}</Text>
      {text ? <Text style={styles.emptyText}>{text}</Text> : null}
    </View>
  );
}

export function Chip({ label, on, onPress, color, testID }: { label: string; on?: boolean; onPress?: () => void; color?: string; testID?: string }) {
  return (
    <Pressable onPress={onPress} testID={testID}
      style={[styles.chip, on && { backgroundColor: color ?? colors.accent, borderColor: color ?? colors.accent }]}>
      <Text style={[styles.chipText, on && { color: colors.bg }]}>{label}</Text>
    </Pressable>
  );
}

export function ItemRow({ item, right }: { item: Item; right?: ReactNode }) {
  const meta = catMeta(item.category);
  const sub = [item.creator?.name || item.author_name, duration(item.duration_sec), PLATFORM_LABEL[item.platform], ago(item.published_at)]
    .filter(Boolean).join(' · ');
  return (
    <Pressable onPress={() => router.push(`/item/${item.id}`)} style={({ pressed }) => [styles.row, pressed && { opacity: 0.7 }]}
      testID={`row-${item.id}`}>
      {item.thumbnail_url ? (
        <Image source={{ uri: item.thumbnail_url }} style={styles.thumb} contentFit="cover" transition={100} />
      ) : (
        <View style={[styles.thumb, { backgroundColor: meta.color + '22', alignItems: 'center', justifyContent: 'center' }]}>
          <Text style={{ fontSize: 26 }}>{meta.emoji}</Text>
        </View>
      )}
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={[styles.rowKicker, { color: meta.color }]} numberOfLines={1}>{meta.emoji} {meta.name}</Text>
        <Text style={styles.rowTitle} numberOfLines={2}>{item.title}</Text>
        <Text style={styles.rowSub} numberOfLines={1}>{sub}</Text>
        {item.state.note ? <Text style={styles.rowNote} numberOfLines={2}>✎ {item.state.note}</Text> : null}
      </View>
      {right}
    </Pressable>
  );
}

export function Loading() {
  return <View style={styles.empty}><ActivityIndicator color={colors.accent} size="large" /></View>;
}

export const ui = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: space(4), gap: space(6), paddingBottom: space(16) },
  muted: { color: colors.muted, ...font.small },
  text: { color: colors.text, ...font.body },
  input: { color: colors.text, backgroundColor: colors.surface2, borderRadius: radius.md, paddingHorizontal: space(3), paddingVertical: space(3), ...font.body },
});

const styles = StyleSheet.create({
  h1: { color: colors.text, ...font.h1 },
  sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sectionTitle: { color: colors.text, ...font.h2 },
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, padding: space(4), gap: space(3), borderWidth: 1, borderColor: colors.border },
  button: { flexDirection: 'row', gap: space(2), alignItems: 'center', justifyContent: 'center', borderRadius: radius.pill, paddingVertical: space(3), paddingHorizontal: space(5) },
  buttonText: { fontWeight: '800', fontSize: 15 },
  empty: { alignItems: 'center', justifyContent: 'center', padding: space(10), gap: space(2) },
  emptyTitle: { color: colors.text, ...font.h3, textAlign: 'center' },
  emptyText: { color: colors.muted, ...font.small, textAlign: 'center' },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.pill, paddingHorizontal: space(3), paddingVertical: space(1.5) },
  chipText: { color: colors.text, ...font.small, fontWeight: '600' },
  row: { flexDirection: 'row', gap: space(3), alignItems: 'center' },
  thumb: { width: 112, height: 64, borderRadius: radius.sm, backgroundColor: colors.surface2 },
  rowKicker: { ...font.tiny },
  rowTitle: { color: colors.text, fontWeight: '700', fontSize: 14, lineHeight: 19 },
  rowSub: { color: colors.muted, fontSize: 12 },
  rowNote: { color: colors.accent, fontSize: 12 },
});
