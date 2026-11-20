import type { ReactNode } from 'react';
import { KeyboardAvoidingView, Modal, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, font, radius, space } from '@/lib/theme';

export default function Sheet({ visible, onClose, title, children }: {
  visible: boolean; onClose: () => void; title?: string; children: ReactNode;
}) {
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.root}>
        <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel="Cerrar" />
        <View style={[styles.sheet, { paddingBottom: insets.bottom + space(4) }]}>
          <View style={styles.handle} />
          {title ? <Text style={styles.title}>{title}</Text> : null}
          {children}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

export function SheetButton({ icon, label, onPress, danger, testID }: {
  icon?: string; label: string; onPress: () => void; danger?: boolean; testID?: string;
}) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.btn, pressed && { opacity: 0.6 }]} testID={testID}>
      {icon ? <Text style={styles.btnIcon}>{icon}</Text> : null}
      <Text style={[styles.btnText, danger && { color: colors.danger }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, justifyContent: 'flex-end' },
  backdrop: { ...StyleSheet.absoluteFill, backgroundColor: 'rgba(0,0,0,0.55)' },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: radius.lg, borderTopRightRadius: radius.lg, paddingHorizontal: space(5), paddingTop: space(3), gap: space(3), maxHeight: '85%' },
  handle: { alignSelf: 'center', width: 40, height: 4, borderRadius: 2, backgroundColor: colors.border, marginBottom: space(1) },
  title: { color: colors.text, ...font.h2 },
  btn: { flexDirection: 'row', alignItems: 'center', gap: space(3), paddingVertical: space(3) },
  btnIcon: { fontSize: 20, width: 28, textAlign: 'center' },
  btnText: { color: colors.text, ...font.body, fontWeight: '600' },
});
