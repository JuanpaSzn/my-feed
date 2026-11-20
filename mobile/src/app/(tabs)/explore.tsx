import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Card, Chip, Empty, H1, ItemRow, Section, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { useApp } from '@/lib/app-context';
import { colors, font, radius, space } from '@/lib/theme';
import type { Category, Item } from '@/lib/types';

const LEVELS = [
  { w: 0.5, label: 'Poco' },
  { w: 1, label: 'Normal' },
  { w: 1.5, label: 'Más' },
  { w: 2, label: 'Prioridad' },
];

export default function ExploreScreen() {
  const insets = useSafeAreaInsets();
  const app = useApp();
  const [cats, setCats] = useState<Category[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Item[] | null>(null);
  const [suggested, setSuggested] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([api.categories(), api.creators('suggested')]);
      setCats(c);
      setSuggested(s.length);
    } catch {}
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (q.trim().length < 2) {
      setResults(null);
      return;
    }
    timer.current = setTimeout(() => {
      api.search(q.trim()).then(setResults).catch(() => setResults([]));
    }, 350);
  }, [q]);

  const patch = async (slug: string, body: { weight?: number; enabled?: boolean }) => {
    setCats((prev) => prev.map((c) => (c.slug === slug ? { ...c, ...body } : c)));
    try {
      await api.patchCategory(slug, body);
      app.bumpFeed();
    } catch {
      load();
    }
  };

  return (
    <ScrollView style={ui.screen} contentContainerStyle={[ui.content, { paddingTop: insets.top + space(4) }]} keyboardShouldPersistTaps="handled">
      <H1>Explorar</H1>
      <View style={styles.search}>
        <Ionicons name="search" size={18} color={colors.muted} />
        <TextInput value={q} onChangeText={setQ} placeholder="Busca en todo lo descubierto…" placeholderTextColor={colors.faint}
          style={styles.searchInput} returnKeyType="search" testID="search-input" />
        {q ? <Pressable onPress={() => setQ('')}><Ionicons name="close-circle" size={18} color={colors.muted} /></Pressable> : null}
      </View>

      {results ? (
        <Section title={`Resultados (${results.length})`}>
          {results.length ? results.map((it) => <ItemRow key={it.id} item={it} />) : (
            <Empty emoji="🔎" title="Sin resultados" text="Prueba a pedirlo desde Inicio con «muéstrame…» para que los agentes lo busquen." />
          )}
        </Section>
      ) : (
        <>
          <View style={styles.quick}>
            <Pressable style={styles.quickBtn} onPress={() => router.push('/creators')} testID="open-creators">
              <Ionicons name="people" size={20} color={colors.accent} />
              <Text style={styles.quickText}>Creadores</Text>
              {suggested ? <View style={styles.badge}><Text style={styles.badgeText}>{suggested}</Text></View> : null}
            </Pressable>
            <Pressable style={styles.quickBtn} onPress={() => router.push('/add')} testID="open-add">
              <Ionicons name="link" size={20} color={colors.accent} />
              <Text style={styles.quickText}>Añadir enlace</Text>
            </Pressable>
          </View>

          <Section title="Tus 6 áreas">
            <Text style={ui.muted}>Decide cuánto espacio ocupa cada tema en tu feed. Nada entra sin tu permiso.</Text>
            {cats.map((c) => (
              <Card key={c.slug} style={{ borderColor: c.enabled ? c.color + '66' : colors.border, opacity: c.enabled ? 1 : 0.6 }}>
                <View style={styles.catHead}>
                  <Pressable style={{ flex: 1 }} onPress={() => router.push(`/category/${c.slug}`)} testID={`cat-${c.slug}`}>
                    <Text style={styles.catName}>{c.emoji} {c.name}</Text>
                    <Text style={ui.muted}>{c.items} contenidos · {c.description}</Text>
                  </Pressable>
                  <Switch value={c.enabled} onValueChange={(v) => patch(c.slug, { enabled: v })}
                    trackColor={{ true: c.color, false: colors.surface2 }} testID={`toggle-${c.slug}`} />
                </View>
                {c.enabled ? (
                  <View style={styles.levels}>
                    {LEVELS.map((l) => (
                      <Chip key={l.w} label={l.label} on={Math.abs(c.weight - l.w) < 0.01} color={c.color}
                        onPress={() => patch(c.slug, { weight: l.w })} testID={`weight-${c.slug}-${l.w}`} />
                    ))}
                  </View>
                ) : null}
                <Pressable onPress={() => setOpen(open === c.slug ? null : c.slug)}>
                  <Text style={styles.subToggle}>{open === c.slug ? 'Ocultar subtemas' : 'Subtemas'}</Text>
                </Pressable>
                {open === c.slug ? (
                  <View style={styles.levels}>
                    {c.subtopics.map((s) => (
                      <Chip key={s.slug} label={s.name} on={s.enabled} color={c.color} onPress={async () => {
                        setCats((prev) => prev.map((x) => x.slug !== c.slug ? x : {
                          ...x, subtopics: x.subtopics.map((y) => (y.slug === s.slug ? { ...y, enabled: !y.enabled } : y)),
                        }));
                        await api.patchSubtopic(s.slug, !s.enabled).catch(() => {});
                      }} />
                    ))}
                  </View>
                ) : null}
              </Card>
            ))}
          </Section>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  search: { flexDirection: 'row', alignItems: 'center', gap: space(2), backgroundColor: colors.surface, borderRadius: radius.pill, paddingHorizontal: space(4), borderWidth: 1, borderColor: colors.border },
  searchInput: { flex: 1, color: colors.text, paddingVertical: space(3), ...font.body },
  quick: { flexDirection: 'row', gap: space(3) },
  quickBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: space(2), backgroundColor: colors.surface, borderRadius: radius.md, padding: space(4), borderWidth: 1, borderColor: colors.border },
  quickText: { color: colors.text, fontWeight: '700' },
  badge: { backgroundColor: colors.accent2, borderRadius: 10, minWidth: 20, height: 20, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 6 },
  badgeText: { color: colors.bg, fontSize: 11, fontWeight: '800' },
  catHead: { flexDirection: 'row', alignItems: 'center', gap: space(3) },
  catName: { color: colors.text, ...font.h3 },
  levels: { flexDirection: 'row', flexWrap: 'wrap', gap: space(2) },
  subToggle: { color: colors.accent, ...font.small, fontWeight: '700' },
});
