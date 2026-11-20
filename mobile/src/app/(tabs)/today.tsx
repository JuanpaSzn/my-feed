import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Button, Card, Empty, H1, ItemRow, Loading, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { getJSON, KEYS, setJSON } from '@/lib/storage';
import { colors, font, space } from '@/lib/theme';
import type { Highlights } from '@/lib/types';

/** «Hoy»: la selección diaria de destacados que complementa el feed continuo. */
export default function TodayScreen() {
  const insets = useSafeAreaInsets();
  const [data, setData] = useState<Highlights | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [offline, setOffline] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const h = await api.highlights();
      setData(h);
      setOffline(false);
      setJSON(KEYS.highlightsCache, h);
    } catch {
      setOffline(true);
      setData(await getJSON<Highlights | null>(KEYS.highlightsCache, null));
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const dayLabel = data ? new Date(`${data.day}T12:00:00`).toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' }) : '';

  return (
    <ScrollView style={ui.screen} contentContainerStyle={[ui.content, { paddingTop: insets.top + space(4) }]}
      refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor={colors.accent} />}>
      <View style={{ gap: space(1) }}>
        <Text style={ui.muted}>{dayLabel}</Text>
        <H1>Lo importante hoy</H1>
      </View>
      {offline ? <Text style={{ color: colors.warning }}>Sin conexión: mostrando la última selección.</Text> : null}
      {loading && !data ? <Loading /> : null}
      {data ? (
        <>
          {data.headline ? (
            <Card style={{ borderColor: colors.accent2 }}>
              <Text style={styles.kicker}>{data.generator === 'claude' ? 'RESUMEN CON IA' : 'RESUMEN'}</Text>
              <Text style={styles.headline}>{data.headline}</Text>
              {data.summary ? <Text style={styles.summary}>{data.summary}</Text> : null}
            </Card>
          ) : null}
          {data.items.length ? (
            <View style={{ gap: space(4) }} testID="highlights-list">
              {data.items.map((it, i) => (
                <View key={it.id} style={{ gap: space(1) }}>
                  <Text style={styles.rank}>#{i + 1} · {it.score?.reasons?.[0] ?? ''}</Text>
                  <ItemRow item={it} />
                </View>
              ))}
            </View>
          ) : (
            <Empty emoji="🌤️" title="Aún no hay destacados" text="Los agentes los preparan cada mañana." />
          )}
          <Button label="Recalcular destacados" kind="ghost" icon="refresh" busy={busy} onPress={async () => {
            setBusy(true);
            try { await api.rebuildHighlights(); await load(); } catch {} finally { setBusy(false); }
          }} />
        </>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  kicker: { color: colors.accent2, ...font.tiny, letterSpacing: 1 },
  headline: { color: colors.text, ...font.h2 },
  summary: { color: colors.text, opacity: 0.9, ...font.body },
  rank: { color: colors.muted, ...font.tiny },
});
