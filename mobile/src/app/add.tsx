import * as Clipboard from 'expo-clipboard';
import { router } from 'expo-router';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { Button, Chip, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { useApp } from '@/lib/app-context';
import { CATEGORY_META, colors, space } from '@/lib/theme';

/** Pega un enlace de TikTok, Instagram, YouTube, Vimeo o un artículo y queda en tu feed y en Guardados. */
export default function AddScreen() {
  const app = useApp();
  const [url, setUrl] = useState('');
  const [cat, setCat] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  return (
    <ScrollView style={ui.screen} contentContainerStyle={ui.content} keyboardShouldPersistTaps="handled">
      <Text style={ui.text}>
        ¿Viste algo bueno en TikTok, Instagram o YouTube? Comparte → Copiar enlace, y pégalo aquí. Se reproduce con el
        reproductor oficial; nada se descarga.
      </Text>
      <TextInput value={url} onChangeText={setUrl} placeholder="https://…" placeholderTextColor={colors.faint}
        autoCapitalize="none" autoCorrect={false} style={ui.input} testID="add-url" />
      <Button label="Pegar del portapapeles" kind="ghost" icon="clipboard-outline" onPress={async () => {
        try { setUrl(await Clipboard.getStringAsync()); } catch {}
      }} />
      <Text style={ui.muted}>Categoría (opcional, la IA la deduce si no eliges)</Text>
      <View style={styles.chips}>
        {Object.entries(CATEGORY_META).map(([slug, m]) => (
          <Chip key={slug} label={`${m.emoji} ${m.name}`} on={cat === slug} color={m.color} onPress={() => setCat(cat === slug ? undefined : slug)} />
        ))}
      </View>
      <Button label="Añadir a MyFeed" busy={busy} testID="add-submit" onPress={async () => {
        if (!url.trim()) return;
        setBusy(true);
        setMsg('');
        try {
          const it = await api.addLink(url.trim(), cat);
          app.bumpFeed();
          router.replace(`/item/${it.id}`);
        } catch (e) {
          setMsg(e instanceof Error ? e.message : 'No se pudo añadir');
        } finally {
          setBusy(false);
        }
      }} />
      {msg ? <Text style={{ color: colors.danger }}>{msg}</Text> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({ chips: { flexDirection: 'row', flexWrap: 'wrap', gap: space(2) } });
