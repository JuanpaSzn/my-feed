import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Card, H1, Section, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { useApp } from '@/lib/app-context';
import { minutes } from '@/lib/format';
import { colors, font, radius, space } from '@/lib/theme';
import type { Stats } from '@/lib/types';

const DAYS = ['D', 'L', 'M', 'X', 'J', 'V', 'S'];

function Link({ icon, label, sub, to, testID }: { icon: keyof typeof Ionicons.glyphMap; label: string; sub?: string; to: string; testID?: string }) {
  return (
    <Pressable style={styles.link} onPress={() => router.push(to as never)} testID={testID}>
      <Ionicons name={icon} size={20} color={colors.accent} />
      <View style={{ flex: 1 }}>
        <Text style={styles.linkText}>{label}</Text>
        {sub ? <Text style={ui.muted}>{sub}</Text> : null}
      </View>
      <Ionicons name="chevron-forward" size={18} color={colors.faint} />
    </Pressable>
  );
}

export default function MeScreen() {
  const insets = useSafeAreaInsets();
  const app = useApp();
  const [stats, setStats] = useState<Stats | null>(null);

  const load = useCallback(async () => {
    try {
      setStats(await api.stats(7));
      app.setUsage(await api.usage());
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const u = app.usage;
  const pct = u && u.limit_seconds ? Math.min(1, u.seconds / u.limit_seconds) : 0;
  const maxDay = Math.max(1, ...(stats?.days.map((d) => d.minutes) ?? [1]));
  const maxCat = Math.max(1, ...(stats?.by_category.map((c) => c.minutes) ?? [1]));

  return (
    <ScrollView style={ui.screen} contentContainerStyle={[ui.content, { paddingTop: insets.top + space(4) }]}
      refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor={colors.accent} />}>
      <H1>Tu tiempo, tu aprendizaje</H1>

      <Card>
        <Text style={ui.muted}>Hoy</Text>
        <Text style={styles.big} testID="today-minutes">{minutes(u?.seconds ?? 0)}</Text>
        {u?.limit_seconds ? (
          <>
            <View style={styles.track}><View style={[styles.fill, { width: `${pct * 100}%`, backgroundColor: pct >= 1 ? colors.warning : colors.accent }]} /></View>
            <Text style={ui.muted}>
              {u.exceeded ? 'Objetivo cumplido por hoy' : `Te quedan ${minutes(u.remaining_seconds ?? 0)} de tu límite de ${minutes(u.limit_seconds)}`}
            </Text>
          </>
        ) : <Text style={ui.muted}>Sin límite diario</Text>}
        {stats ? (
          <View style={styles.statsRow}>
            <View style={styles.stat}><Text style={styles.statNum}>🔥 {stats.streak_days}</Text><Text style={ui.muted}>días de racha</Text></View>
            <View style={styles.stat}><Text style={styles.statNum}>{stats.saved}</Text><Text style={ui.muted}>guardados</Text></View>
            <View style={styles.stat}><Text style={styles.statNum}>{stats.notes}</Text><Text style={ui.muted}>aprendizajes</Text></View>
          </View>
        ) : null}
      </Card>

      {stats ? (
        <Section title="Últimos 7 días">
          <View style={styles.bars}>
            {stats.days.map((d) => (
              <View key={d.day} style={styles.barCol}>
                <View style={[styles.bar, { height: Math.max(3, (d.minutes / maxDay) * 90) }]} />
                <Text style={styles.barLabel}>{DAYS[new Date(`${d.day}T12:00:00`).getDay()]}</Text>
              </View>
            ))}
          </View>
          <Text style={ui.muted}>Promedio: {stats.avg_minutes} min/día · Total: {stats.total_minutes} min</Text>
          {stats.by_category.length ? (
            <View style={{ gap: space(2) }}>
              {stats.by_category.map((c) => (
                <View key={c.slug} style={styles.catRow}>
                  <Text style={styles.catName} numberOfLines={1}>{c.emoji} {c.name}</Text>
                  <View style={styles.catTrack}><View style={[styles.catFill, { width: `${(c.minutes / maxCat) * 100}%`, backgroundColor: c.color }]} /></View>
                  <Text style={styles.catMin}>{c.minutes}m</Text>
                </View>
              ))}
            </View>
          ) : null}
        </Section>
      ) : null}

      <View style={{ gap: space(2) }}>
        <Link icon="school" label="Repaso" sub="Tarjetas con las ideas clave de lo que guardaste" to="/review" testID="open-review" />
        <Link icon="analytics" label="Lo que aprendí de ti" sub="Tus gustos según tus likes, guardados y descartes" to="/preferences" testID="open-prefs" />
        <Link icon="people" label="Creadores y fuentes" sub="Aprueba o descarta las sugerencias de la IA" to="/creators" />
        <Link icon="hardware-chip" label="Agentes" sub="Qué están haciendo el explorador, el analista y el curador" to="/agents" />
        <Link icon="settings" label="Ajustes" sub="Límite diario, pausas, servidor" to="/settings" testID="open-settings" />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  big: { color: colors.text, fontSize: 40, fontWeight: '900', letterSpacing: -1 },
  track: { height: 10, borderRadius: 5, backgroundColor: colors.surface2, overflow: 'hidden' },
  fill: { height: 10, borderRadius: 5 },
  statsRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: space(2) },
  stat: { alignItems: 'center', flex: 1 },
  statNum: { color: colors.text, ...font.h2 },
  bars: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', height: 110, paddingHorizontal: space(2) },
  barCol: { alignItems: 'center', gap: space(1), flex: 1 },
  bar: { width: 18, borderRadius: 6, backgroundColor: colors.accent },
  barLabel: { color: colors.muted, fontSize: 11 },
  catRow: { flexDirection: 'row', alignItems: 'center', gap: space(2) },
  catName: { color: colors.text, width: 150, ...font.small },
  catTrack: { flex: 1, height: 8, backgroundColor: colors.surface2, borderRadius: 4, overflow: 'hidden' },
  catFill: { height: 8, borderRadius: 4 },
  catMin: { color: colors.muted, width: 40, textAlign: 'right', fontSize: 12 },
  link: { flexDirection: 'row', alignItems: 'center', gap: space(3), backgroundColor: colors.surface, padding: space(4), borderRadius: radius.md, borderWidth: 1, borderColor: colors.border },
  linkText: { color: colors.text, fontWeight: '700', fontSize: 15 },
});
