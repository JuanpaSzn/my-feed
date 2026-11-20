import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { PART_LABEL } from '@/lib/format';
import { colors, font, radius, space } from '@/lib/theme';
import type { Item } from '@/lib/types';
import Sheet, { SheetButton } from './Sheet';

/** «¿Por qué veo esto?»: transparencia total del algoritmo. */
export function WhySheet({ item, onClose }: { item: Item | null; onClose: () => void }) {
  const s = item?.score;
  return (
    <Sheet visible={!!item} onClose={onClose} title="¿Por qué ves esto?">
      {s ? (
        <View style={{ gap: space(3) }}>
          {s.reasons.map((r) => (
            <Text key={r} style={styles.reason}>✦ {r}</Text>
          ))}
          <View style={{ gap: space(2), marginTop: space(2) }}>
            {Object.entries(s.parts).map(([k, v]) => (
              <View key={k} style={styles.barRow}>
                <Text style={styles.barLabel}>{PART_LABEL[k] ?? k}</Text>
                <View style={styles.barTrack}>
                  <View style={[styles.barFill, { width: `${Math.round(Math.max(0, Math.min(1, v)) * 100)}%` }]} />
                </View>
                <Text style={styles.barValue}>{Math.round(v * 100)}</Text>
              </View>
            ))}
          </View>
          <Text style={styles.hint}>
            Nada de esto mide la viralidad. Puedes cambiar el peso de cada categoría en Explorar, y lo que la app
            aprendió de ti en Yo → Preferencias.
          </Text>
        </View>
      ) : (
        <Text style={styles.hint}>Este contenido viene de tu biblioteca.</Text>
      )}
    </Sheet>
  );
}

const COLLECTIONS = ['Ver después', 'Aplicar', 'Entrenamiento', 'Ideas'];

/** «Aprendí...»: nota rápida y colección. Escribir lo aprendido es la mejor señal para el algoritmo. */
export function NoteSheet({ item, onClose, onSave }: {
  item: Item | null; onClose: () => void; onSave: (note: string, collection: string) => Promise<void>;
}) {
  const [note, setNote] = useState('');
  const [col, setCol] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setNote(item?.state.note ?? '');
    setCol(item?.state.collection ?? '');
  }, [item]);
  return (
    <Sheet visible={!!item} onClose={onClose} title="¿Qué aprendiste?">
      <TextInput
        value={note}
        onChangeText={setNote}
        placeholder="Una idea, un ejercicio para probar, algo que no sabías…"
        placeholderTextColor={colors.faint}
        multiline
        style={styles.input}
        autoFocus
        testID="note-input"
      />
      <View style={styles.pills}>
        {COLLECTIONS.map((c) => (
          <Pressable key={c} onPress={() => setCol(col === c ? '' : c)} style={[styles.pill, col === c && styles.pillOn]}>
            <Text style={[styles.pillText, col === c && { color: colors.bg }]}>{c}</Text>
          </Pressable>
        ))}
      </View>
      <Pressable
        style={styles.primary}
        disabled={busy}
        testID="note-save"
        onPress={async () => {
          setBusy(true);
          try {
            await onSave(note, col);
            onClose();
          } finally {
            setBusy(false);
          }
        }}>
        {busy ? <ActivityIndicator color={colors.bg} /> : <Text style={styles.primaryText}>Guardar nota</Text>}
      </Pressable>
    </Sheet>
  );
}

export function MoreSheet({ item, onClose, onChoose }: {
  item: Item | null; onClose: () => void;
  onChoose: (a: 'more_like_this' | 'less_like_this' | 'hide' | 'open' | 'detail' | 'mute_creator') => void;
}) {
  return (
    <Sheet visible={!!item} onClose={onClose} title={item?.title}>
      <SheetButton icon="👍" label="Más contenido como este" onPress={() => onChoose('more_like_this')} testID="more-like" />
      <SheetButton icon="👎" label="Menos contenido como este" onPress={() => onChoose('less_like_this')} testID="less-like" />
      <SheetButton icon="📄" label="Ver detalles e ideas clave" onPress={() => onChoose('detail')} />
      {item?.url ? <SheetButton icon="↗️" label="Abrir en la fuente original" onPress={() => onChoose('open')} /> : null}
      {item?.creator ? (
        <SheetButton icon="🔇" label={`Silenciar a ${item.creator.name}`} onPress={() => onChoose('mute_creator')} />
      ) : null}
      <SheetButton icon="🚫" label="No me interesa (ocultar)" danger onPress={() => onChoose('hide')} testID="hide-item" />
    </Sheet>
  );
}

export const sheetStyles = StyleSheet.create({
  input: { minHeight: 110, color: colors.text, backgroundColor: colors.surface2, borderRadius: radius.md, padding: space(3), textAlignVertical: 'top', ...font.body },
  primary: { backgroundColor: colors.accent, borderRadius: radius.pill, alignItems: 'center', paddingVertical: space(3.5) },
  primaryText: { color: colors.bg, fontWeight: '800', fontSize: 16 },
});

const styles = StyleSheet.create({
  ...sheetStyles,
  reason: { color: colors.text, ...font.body },
  barRow: { flexDirection: 'row', alignItems: 'center', gap: space(2) },
  barLabel: { color: colors.muted, width: 92, ...font.small },
  barTrack: { flex: 1, height: 8, borderRadius: 4, backgroundColor: colors.surface2, overflow: 'hidden' },
  barFill: { height: 8, borderRadius: 4, backgroundColor: colors.accent },
  barValue: { color: colors.text, width: 28, textAlign: 'right', ...font.small },
  hint: { color: colors.muted, ...font.small },
  pills: { flexDirection: 'row', flexWrap: 'wrap', gap: space(2) },
  pill: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.pill, paddingHorizontal: space(3), paddingVertical: space(1.5) },
  pillOn: { backgroundColor: colors.accent, borderColor: colors.accent },
  pillText: { color: colors.text, ...font.small, fontWeight: '600' },
});
