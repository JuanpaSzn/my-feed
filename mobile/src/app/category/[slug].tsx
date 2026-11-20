import { Stack, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { FlatList } from 'react-native';

import { Empty, ItemRow, Loading, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { catMeta, space } from '@/lib/theme';
import type { Item } from '@/lib/types';

export default function CategoryScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const meta = catMeta(slug);
  const [items, setItems] = useState<Item[] | null>(null);
  useEffect(() => {
    api.feed({ category: slug, limit: 30 }).then((p) => setItems(p.items)).catch(() => setItems([]));
  }, [slug]);
  return (
    <>
      <Stack.Screen options={{ title: `${meta.emoji} ${meta.name}` }} />
      {items === null ? <Loading /> : (
        <FlatList style={ui.screen} data={items} keyExtractor={(i) => String(i.id)}
          contentContainerStyle={{ padding: space(4), gap: space(4) }}
          renderItem={({ item }) => <ItemRow item={item} />}
          ListEmptyComponent={<Empty emoji={meta.emoji} title="Nada nuevo aquí" text="Ya viste todo lo de esta categoría." />} />
      )}
    </>
  );
}
