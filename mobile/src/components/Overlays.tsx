import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { api } from '@/lib/api';
import { minutes } from '@/lib/format';
import { colors, font, radius, space } from '@/lib/theme';
import type { Usage } from '@/lib/types';
import Sheet from './Sheet';
import { sheetStyles } from './Sheets';

export const COMMAND_EXAMPLES = [
  'Muéstrame los últimos avances en agentes autónomos',
  'Quiero vídeos sobre cómo mejorar mi aceleración en fútbol sala',
  'Enséñame proyectos interesantes de ciberseguridad',
  'Los descubrimientos científicos más importantes de esta semana',
  'Algo de filosofía estoica para pensar',
  'Proyectos open source sorprendentes en Python',
];

/** Límite diario alcanzado: la app propone cerrar en vez de engancharte. */
export function LimitOverlay({ usage, onExtend, onReview }: {
  usage: Usage; onExtend: (m: number) => void; onReview: () => void;
}) {
  return (
    <View style={styles.full} testID="limit-overlay">
      <Text style={styles.big}>🌙</Text>
      <Text style={styles.h1}>Suficiente por hoy</Text>
      <Text style={styles.p}>
        Llevas {minutes(usage.seconds)} aprendiendo. Ese era tu objetivo: tu yo de mañana te lo agradece.
      </Text>
      <Pressable style={styles.primary} onPress={onReview}>
        <Text style={styles.primaryText}>Repasar lo que aprendí</Text>
      </Pressable>
      <Pressable style={styles.ghost} onPress={() => onExtend(10)} testID="extend-10">
        <Text style={styles.ghostText}>Dame 10 minutos más</Text>
      </Pressable>
      <Text style={styles.small}>Puedes cambiar el límite en Yo → Ajustes.</Text>
    </View>
  );
}

/** Pausa consciente cada N minutos. */
export function BreakOverlay({ every, onContinue, onReview }: { every: number; onContinue: () => void; onReview: () => void }) {
  return (
    <View style={[styles.full, { backgroundColor: 'rgba(10,13,20,0.94)' }]} testID="break-overlay">
      <Text style={styles.big}>🫁</Text>
      <Text style={styles.h1}>Pausa de {every} minutos</Text>
      <Text style={styles.p}>Respira hondo tres veces, mira algo lejano y estira el cuello. ¿Con qué idea te quedas de lo que viste?</Text>
      <Pressable style={styles.primary} onPress={onContinue} testID="break-continue">
        <Text style={styles.primaryText}>Seguir aprendiendo</Text>
      </Pressable>
      <Pressable style={styles.ghost} onPress={onReview}>
        <Text style={styles.ghostText}>Hacer un repaso rápido</Text>
      </Pressable>
    </View>
  );
}

/** Comando escrito: «muéstrame…». Cambia temporalmente el feed. */
export function CommandSheet({ visible, onClose, onDone }: {
  visible: boolean; onClose: () => void; onDone: (label: string) => void;
}) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [recent, setRecent] = useState<{ id: number; text: string }[]>([]);
  useEffect(() => {
    if (visible) {
      setError('');
      api.commands().then((r) => setRecent(r.slice(0, 4))).catch(() => setRecent([]));
    }
  }, [visible]);

  const run = async (t: string) => {
    if (t.trim().length < 3) return;
    setBusy(true);
    setError('');
    try {
      const r = await api.command(t.trim());
      setText('');
      onDone(String((r.parsed as { label?: string }).label ?? t));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Algo falló');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet visible={visible} onClose={onClose} title="¿Qué quieres ver ahora?">
      <TextInput
        value={text}
        onChangeText={setText}
        placeholder="Muéstrame…"
        placeholderTextColor={colors.faint}
        style={[sheetStyles.input, { minHeight: 64 }]}
        multiline
        autoFocus
        onSubmitEditing={() => run(text)}
        testID="command-input"
      />
      <Pressable style={sheetStyles.primary} onPress={() => run(text)} disabled={busy} testID="command-submit">
        {busy ? <ActivityIndicator color={colors.bg} /> : <Text style={sheetStyles.primaryText}>Ajustar mi feed</Text>}
      </Pressable>
      {error ? <Text style={{ color: colors.danger }}>{error}</Text> : null}
      <Text style={styles.label}>Ideas</Text>
      <View style={styles.chips}>
        {COMMAND_EXAMPLES.slice(0, 4).map((e) => (
          <Pressable key={e} onPress={() => run(e)} style={styles.chip} disabled={busy}>
            <Text style={styles.chipText} numberOfLines={1}>{e}</Text>
          </Pressable>
        ))}
      </View>
      {recent.length ? (
        <>
          <Text style={styles.label}>Recientes</Text>
          {recent.map((r) => (
            <Pressable key={r.id} onPress={() => run(r.text)} disabled={busy}>
              <Text style={styles.recent} numberOfLines={1}>↺ {r.text}</Text>
            </Pressable>
          ))}
        </>
      ) : null}
    </Sheet>
  );
}

/** «¿Qué quieres aprender hoy?» al abrir la app: empezar con intención, no por inercia. */
export function PurposeSheet({ visible, onClose, onPick }: { visible: boolean; onClose: () => void; onPick: (t: string) => void }) {
  return (
    <Sheet visible={visible} onClose={onClose} title="¿Qué quieres aprender hoy?">
      <Text style={{ color: colors.muted, ...font.small }}>Elige una intención o simplemente explora tu feed equilibrado.</Text>
      <View style={styles.chips}>
        {COMMAND_EXAMPLES.map((e) => (
          <Pressable key={e} onPress={() => onPick(e)} style={styles.chip}>
            <Text style={styles.chipText}>{e}</Text>
          </Pressable>
        ))}
      </View>
      <Pressable style={sheetStyles.primary} onPress={onClose} testID="purpose-explore">
        <Text style={sheetStyles.primaryText}>Solo explorar</Text>
      </Pressable>
    </Sheet>
  );
}

const styles = StyleSheet.create({
  full: { ...StyleSheet.absoluteFill, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center', padding: space(8), gap: space(4), zIndex: 50 },
  big: { fontSize: 56 },
  h1: { color: colors.text, ...font.h1, textAlign: 'center' },
  p: { color: colors.muted, ...font.body, textAlign: 'center' },
  small: { color: colors.faint, ...font.small },
  primary: { backgroundColor: colors.accent, borderRadius: radius.pill, paddingVertical: space(3.5), paddingHorizontal: space(8), marginTop: space(2) },
  primaryText: { color: colors.bg, fontWeight: '800', fontSize: 16 },
  ghost: { paddingVertical: space(2) },
  ghostText: { color: colors.text, fontWeight: '600' },
  label: { color: colors.muted, ...font.tiny, textTransform: 'uppercase', marginTop: space(1) },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: space(2) },
  chip: { backgroundColor: colors.surface2, borderRadius: radius.pill, paddingHorizontal: space(3), paddingVertical: space(2), maxWidth: '100%' },
  chipText: { color: colors.text, ...font.small },
  recent: { color: colors.text, ...font.body, paddingVertical: space(1) },
});
