import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { Button, Card, Chip, Empty, Section, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { useApp } from '@/lib/app-context';
import { catMeta, CATEGORY_META, colors, font, space } from '@/lib/theme';
import type { Creator } from '@/lib/types';

export default function CreatorsScreen() {
  const app = useApp();
  const [all, setAll] = useState<Creator[]>([]);
  const [url, setUrl] = useState('');
  const [cat, setCat] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [filter, setFilter] = useState<string | null>(null);

  const load = useCallback(() => api.creators().then(setAll).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);

  const setStatus = async (c: Creator, status: Creator['status']) => {
    setAll((prev) => prev.map((x) => (x.id === c.id ? { ...x, status } : x)));
    await api.patchCreator(c.id, { status }).catch(load);
    app.bumpFeed();
  };

  const suggested = all.filter((c) => c.status === 'suggested');
  const followed = all.filter((c) => c.status === 'approved' && (!filter || c.category === filter));
  const muted = all.filter((c) => c.status === 'muted' || c.status === 'rejected');

  return (
    <ScrollView style={ui.screen} contentContainerStyle={ui.content} keyboardShouldPersistTaps="handled">
      <Section title={`Sugerencias de la IA (${suggested.length})`}>
        <Text style={ui.muted}>El explorador propone creadores que aparecen con contenido de calidad. Tú decides.</Text>
        {suggested.length ? suggested.map((c) => (
          <Card key={c.id} style={{ borderColor: colors.accent2 }}>
            <Text style={styles.name}>{c.name}</Text>
            <Text style={ui.muted}>{catMeta(c.category).emoji} {catMeta(c.category).name} · {c.platform}</Text>
            {c.reason ? <Text style={ui.text}>{c.reason}</Text> : null}
            <View style={styles.row}>
              <Button label="Aprobar" icon="checkmark" onPress={() => setStatus(c, 'approved')} testID={`approve-${c.id}`} />
              <Button label="Descartar" kind="ghost" icon="close" onPress={() => setStatus(c, 'rejected')} testID={`reject-${c.id}`} />
            </View>
          </Card>
        )) : <Empty emoji="🧭" title="Sin sugerencias pendientes" text="Con la clave de YouTube, el explorador descubre creadores nuevos cada día." />}
      </Section>

      <Section title="Seguir a alguien">
        <TextInput value={url} onChangeText={setUrl} placeholder="URL del canal de YouTube, @usuario o enlace de TikTok"
          placeholderTextColor={colors.faint} autoCapitalize="none" autoCorrect={false} style={ui.input} testID="creator-url" />
        <View style={styles.chips}>
          {Object.entries(CATEGORY_META).map(([slug, m]) => (
            <Chip key={slug} label={`${m.emoji} ${m.name}`} on={cat === slug} color={m.color} onPress={() => setCat(cat === slug ? undefined : slug)} />
          ))}
        </View>
        <Button label="Seguir" busy={busy} onPress={async () => {
          if (!url.trim()) return;
          setBusy(true);
          setMsg('');
          try {
            const c = await api.addCreator(url.trim(), cat);
            setMsg(`✓ Ahora sigues a ${c.name}`);
            setUrl('');
            load();
            app.bumpFeed();
          } catch (e) {
            setMsg(e instanceof Error ? e.message : 'No se pudo añadir');
          } finally {
            setBusy(false);
          }
        }} />
        {msg ? <Text style={{ color: msg.startsWith('✓') ? colors.accent : colors.danger }}>{msg}</Text> : null}
      </Section>

      <Section title={`Sigues a ${all.filter((c) => c.status === 'approved').length}`}>
        <View style={styles.chips}>
          <Chip label="Todos" on={!filter} onPress={() => setFilter(null)} />
          {Object.entries(CATEGORY_META).map(([slug, m]) => (
            <Chip key={slug} label={m.emoji} on={filter === slug} color={m.color} onPress={() => setFilter(filter === slug ? null : slug)} />
          ))}
        </View>
        {followed.map((c) => (
          <View key={c.id} style={styles.item}>
            <View style={{ flex: 1 }}>
              <Text style={styles.itemName}>{c.name}</Text>
              <Text style={ui.muted}>{catMeta(c.category).emoji} {c.items} vídeos · fiabilidad {Math.round(c.credibility * 100)}</Text>
            </View>
            <Pressable onPress={() => setStatus(c, 'muted')}><Text style={styles.action}>Silenciar</Text></Pressable>
          </View>
        ))}
      </Section>

      {muted.length ? (
        <Section title="Silenciados y descartados">
          {muted.map((c) => (
            <View key={c.id} style={styles.item}>
              <Text style={[styles.itemName, { flex: 1, opacity: 0.6 }]}>{c.name}</Text>
              <Pressable onPress={() => setStatus(c, 'approved')}><Text style={styles.action}>Recuperar</Text></Pressable>
            </View>
          ))}
        </Section>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  name: { color: colors.text, ...font.h3 },
  row: { flexDirection: 'row', gap: space(3) },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: space(2) },
  item: { flexDirection: 'row', alignItems: 'center', gap: space(3), paddingVertical: space(2), borderBottomWidth: 1, borderBottomColor: colors.border },
  itemName: { color: colors.text, fontWeight: '700' },
  action: { color: colors.accent, fontWeight: '700' },
});
