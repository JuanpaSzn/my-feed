import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button, Empty, Section, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { useApp } from '@/lib/app-context';
import { colors, space } from '@/lib/theme';

type P = { key: string; label: string; score: number };

export default function PreferencesScreen() {
  const app = useApp();
  const [data, setData] = useState<{ likes: P[]; dislikes: P[] } | null>(null);
  const load = useCallback(() => api.preferences().then(setData).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);

  const Row = ({ p, good }: { p: P; good: boolean }) => (
    <View style={styles.row}>
      <Text style={[ui.text, { flex: 1 }]} numberOfLines={1}>{p.label}</Text>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${Math.min(100, Math.abs(p.score) * 33)}%`, backgroundColor: good ? colors.accent : colors.danger }]} />
      </View>
      <Pressable onPress={async () => { await api.forgetPreference(p.key); load(); app.bumpFeed(); }} hitSlop={8}>
        <Text style={{ color: colors.muted }}>Olvidar</Text>
      </Pressable>
    </View>
  );

  return (
    <ScrollView style={ui.screen} contentContainerStyle={ui.content}>
      <Text style={ui.muted}>
        MyFeed aprende de tus me gusta, guardados, notas, lo que ves completo y lo que saltas. Los gustos se desvanecen
        poco a poco si dejas de mostrar interés. Puedes borrar cualquier cosa.
      </Text>
      {!data ? null : !data.likes.length && !data.dislikes.length ? (
        <Empty emoji="🌱" title="Aún estoy aprendiendo" text="Interactúa con unos cuantos vídeos y vuelve." />
      ) : (
        <>
          <Section title="Te interesa">{data.likes.map((p) => <Row key={p.key} p={p} good />)}</Section>
          {data.dislikes.length ? <Section title="Prefieres menos">{data.dislikes.map((p) => <Row key={p.key} p={p} good={false} />)}</Section> : null}
          <Button label="Empezar de cero" kind="danger" onPress={async () => { await api.resetPreferences(); load(); app.bumpFeed(); }} />
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: space(3) },
  track: { width: 90, height: 8, borderRadius: 4, backgroundColor: colors.surface2, overflow: 'hidden' },
  fill: { height: 8, borderRadius: 4 },
});
