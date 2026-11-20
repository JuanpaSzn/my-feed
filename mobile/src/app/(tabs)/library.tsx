import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Chip, Empty, H1, ItemRow, Loading, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { colors, radius, space } from '@/lib/theme';
import type { Item } from '@/lib/types';

type Tab = 'saved' | 'liked' | 'notes' | 'history';
const TABS: { key: Tab; label: string }[] = [
  { key: 'saved', label: 'Guardados' },
  { key: 'liked', label: 'Me gusta' },
  { key: 'notes', label: 'Aprendizajes' },
  { key: 'history', label: 'Historial' },
];

export default function LibraryScreen() {
  const insets = useSafeAreaInsets();
  const [tab, setTab] = useState<Tab>('saved');
  const [items, setItems] = useState<Item[] | null>(null);
  const [collections, setCollections] = useState<{ name: string; key: string; count: number }[]>([]);
  const [collection, setCollection] = useState<string | undefined>();

  const load = useCallback(async () => {
    setItems(null);
    try {
      if (tab === 'saved') {
        const [s, c] = await Promise.all([api.saved(collection), api.collections()]);
        setItems(s);
        setCollections(c);
      } else if (tab === 'liked') setItems(await api.liked());
      else if (tab === 'notes') setItems(await api.notes());
      else setItems(await api.history());
    } catch {
      setItems([]);
    }
  }, [tab, collection]);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const empty = {
    saved: ['🔖', 'Nada guardado todavía', 'Toca el marcador en un vídeo para verlo después.'],
    liked: ['❤️', 'Aún no hay me gusta', 'Tus me gusta enseñan al algoritmo qué te interesa.'],
    notes: ['✍️', 'Sin aprendizajes', 'Toca «Aprendí» en un vídeo y escribe una idea. Así se queda contigo.'],
    history: ['🕒', 'Historial vacío', 'Lo que veas aparecerá aquí.'],
  }[tab];

  return (
    <View style={[ui.screen, { paddingTop: insets.top + space(4) }]}>
      <View style={{ paddingHorizontal: space(4), gap: space(3) }}>
        <H1>Biblioteca</H1>
        <View style={styles.tabs}>
          {TABS.map((t) => (
            <Pressable key={t.key} onPress={() => { setTab(t.key); setCollection(undefined); }} style={[styles.tab, tab === t.key && styles.tabOn]}
              testID={`lib-${t.key}`}>
              <Text style={[styles.tabText, tab === t.key && { color: colors.bg }]}>{t.label}</Text>
            </Pressable>
          ))}
        </View>
        {tab === 'saved' && collections.length > 1 ? (
          <View style={styles.cols}>
            <Chip label="Todo" on={!collection} onPress={() => setCollection(undefined)} />
            {collections.map((c) => (
              <Chip key={c.key || '_'} label={`${c.name} (${c.count})`} on={collection === c.key && !!c.key}
                onPress={() => setCollection(c.key || undefined)} />
            ))}
          </View>
        ) : null}
        {tab === 'history' && items?.length ? (
          <Pressable onPress={async () => { await api.clearHistory(); load(); }}>
            <Text style={{ color: colors.muted, fontSize: 12 }}>Volver a ver todo en el feed (limpiar historial)</Text>
          </Pressable>
        ) : null}
      </View>
      {items === null ? <Loading /> : (
        <FlatList
          data={items}
          keyExtractor={(i) => String(i.id)}
          contentContainerStyle={{ padding: space(4), gap: space(4), paddingBottom: space(16) }}
          renderItem={({ item }) => <ItemRow item={item} />}
          ListEmptyComponent={<Empty emoji={empty[0]} title={empty[1]} text={empty[2]} />}
          initialNumToRender={10}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  tabs: { flexDirection: 'row', backgroundColor: colors.surface, borderRadius: radius.pill, padding: 3 },
  tab: { flex: 1, alignItems: 'center', paddingVertical: space(2), borderRadius: radius.pill },
  tabOn: { backgroundColor: colors.accent },
  tabText: { color: colors.text, fontWeight: '700', fontSize: 12 },
  cols: { flexDirection: 'row', flexWrap: 'wrap', gap: space(2) },
});
