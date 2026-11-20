import { Image } from 'expo-image';
import { useLocalSearchParams } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, useWindowDimensions, View } from 'react-native';

import Player from '@/components/players/Player';
import { Button, Card, Loading, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { ago, duration, PLATFORM_LABEL } from '@/lib/format';
import { catMeta, colors, font, space } from '@/lib/theme';
import type { Item } from '@/lib/types';

export default function ItemScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { width } = useWindowDimensions();
  const [item, setItem] = useState<Item | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [play, setPlay] = useState(false);

  useEffect(() => {
    api.item(Number(id)).then((it) => {
      setItem(it);
      setNote(it.state.note);
    }).catch(() => setMsg('No se pudo cargar'));
  }, [id]);

  if (!item) return msg ? <Text style={[ui.text, { padding: 20 }]}>{msg}</Text> : <Loading />;
  const meta = catMeta(item.category);
  const isVideo = ['youtube', 'tiktok', 'instagram', 'vimeo'].includes(item.platform);
  const w = Math.min(width, 700) - space(8);
  const vertical = item.format === 'short' && item.platform !== 'youtube';

  const toggle = async (kind: 'like' | 'unlike' | 'save' | 'unsave') => {
    setItem(await api.event(item.id, kind));
  };

  return (
    <ScrollView style={ui.screen} contentContainerStyle={ui.content} keyboardShouldPersistTaps="handled">
      {isVideo && play ? (
        <Player kind={item.platform === 'youtube' ? 'youtube' : 'embed'} videoId={item.external_id} embedUrl={item.embed_url}
          width={w} height={vertical ? w * 1.6 : (w * 9) / 16} playing muted={false} />
      ) : item.thumbnail_url ? (
        <Image source={{ uri: item.thumbnail_url }} style={{ width: w, height: (w * 9) / 16, borderRadius: 12 }} contentFit="cover" />
      ) : null}
      {isVideo && !play ? <Button label="Reproducir aquí" icon="play" onPress={() => setPlay(true)} /> : null}

      <View style={{ gap: space(2) }}>
        <Text style={[font.tiny, { color: meta.color }]}>{meta.emoji} {meta.name.toUpperCase()}{item.subtopic ? ` · ${item.subtopic}` : ''}</Text>
        <Text style={styles.title}>{item.title}</Text>
        <Text style={ui.muted}>
          {[item.creator?.name || item.author_name, duration(item.duration_sec), PLATFORM_LABEL[item.platform], ago(item.published_at)].filter(Boolean).join(' · ')}
        </Text>
      </View>

      <View style={styles.row}>
        <Button label={item.state.liked ? 'Te gusta' : 'Me gusta'} kind={item.state.liked ? 'primary' : 'ghost'} icon={item.state.liked ? 'heart' : 'heart-outline'}
          onPress={() => toggle(item.state.liked ? 'unlike' : 'like')} />
        <Button label={item.state.saved ? 'Guardado' : 'Guardar'} kind={item.state.saved ? 'primary' : 'ghost'} icon={item.state.saved ? 'bookmark' : 'bookmark-outline'}
          onPress={() => toggle(item.state.saved ? 'unsave' : 'save')} />
      </View>

      {item.summary || item.key_points.length ? (
        <Card>
          <Text style={styles.kicker}>{item.analysis === 'claude' ? 'RESUMEN CON IA' : 'DE QUÉ VA'}</Text>
          {item.summary ? <Text style={ui.text}>{item.summary}</Text> : null}
          {item.key_points.map((p) => <Text key={p} style={styles.point}>• {p}</Text>)}
        </Card>
      ) : null}

      {item.score?.reasons?.length ? (
        <Card>
          <Text style={styles.kicker}>POR QUÉ LO VES</Text>
          {item.score.reasons.map((r) => <Text key={r} style={ui.text}>✦ {r}</Text>)}
        </Card>
      ) : null}

      <Card>
        <Text style={styles.kicker}>MI APRENDIZAJE</Text>
        <TextInput value={note} onChangeText={setNote} multiline placeholder="¿Qué te llevas de esto?" placeholderTextColor={colors.faint}
          style={[ui.input, { minHeight: 90, textAlignVertical: 'top' }]} testID="detail-note" />
        <Button label="Guardar nota" busy={busy} onPress={async () => {
          setBusy(true);
          try { setItem(await api.note(item.id, note)); setMsg('Nota guardada'); } finally { setBusy(false); }
        }} />
        {msg ? <Text style={{ color: colors.accent }}>{msg}</Text> : null}
      </Card>

      {item.description && item.platform !== 'myfeed' ? (
        <View style={{ gap: space(2) }}>
          <Text style={styles.kicker}>DESCRIPCIÓN ORIGINAL</Text>
          <Text style={ui.muted}>{item.description}</Text>
        </View>
      ) : null}

      <View style={styles.scoreRow}>
        <Text style={ui.muted}>Calidad {Math.round(item.quality * 100)}/100</Text>
        <Text style={ui.muted}>Credibilidad {Math.round(item.credibility * 100)}/100</Text>
      </View>
      {item.url ? (
        <Button label={`Abrir en ${PLATFORM_LABEL[item.platform] ?? 'la fuente'}`} kind="ghost" icon="open-outline"
          onPress={() => { api.event(item.id, 'open_source').catch(() => {}); WebBrowser.openBrowserAsync(item.url); }} />
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  title: { color: colors.text, ...font.h1, fontSize: 24 },
  kicker: { color: colors.accent, ...font.tiny, letterSpacing: 1 },
  point: { color: colors.text, ...font.body, fontWeight: '600' },
  row: { flexDirection: 'row', gap: space(3) },
  scoreRow: { flexDirection: 'row', justifyContent: 'space-between' },
});
