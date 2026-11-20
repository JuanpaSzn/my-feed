import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Button, Empty, Loading, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { catMeta, colors, font, radius, space } from '@/lib/theme';

type Card = { item_id: number; title: string; category: string; points: string[]; note: string };

/** Repaso espaciado: recordar es lo que convierte ver en aprender. */
export default function ReviewScreen() {
  const [cards, setCards] = useState<Card[] | null>(null);
  const [i, setI] = useState(0);
  const [shown, setShown] = useState(false);

  useEffect(() => { api.review(8).then(setCards).catch(() => setCards([])); }, []);
  if (!cards) return <Loading />;
  if (!cards.length) {
    return (
      <View style={[ui.screen, { justifyContent: 'center' }]}>
        <Empty emoji="🧠" title="Aún no hay nada que repasar" text="Guarda vídeos o escribe lo que aprendiste y volverán aquí como tarjetas." />
      </View>
    );
  }
  if (i >= cards.length) {
    return (
      <View style={[ui.screen, styles.center]}>
        <Text style={{ fontSize: 48 }}>🎉</Text>
        <Text style={styles.title}>Repaso completado</Text>
        <Text style={ui.muted}>{cards.length} ideas refrescadas. Mañana habrá más.</Text>
        <Button label="Terminar" onPress={() => router.back()} />
      </View>
    );
  }
  const c = cards[i];
  const meta = catMeta(c.category);
  return (
    <View style={[ui.screen, { padding: space(5), gap: space(5) }]}>
      <Text style={ui.muted}>{i + 1} / {cards.length}</Text>
      <Pressable style={[styles.card, { borderColor: meta.color }]} onPress={() => setShown(true)} testID="review-card">
        <Text style={[font.tiny, { color: meta.color }]}>{meta.emoji} {meta.name.toUpperCase()}</Text>
        <Text style={styles.title}>{c.title}</Text>
        {!shown ? (
          <Text style={ui.muted}>¿Recuerdas la idea principal? Piensa un momento y toca para ver.</Text>
        ) : (
          <View style={{ gap: space(2) }}>
            {c.points.map((p) => <Text key={p} style={styles.point}>• {p}</Text>)}
            {c.note ? <Text style={styles.note}>Tu nota: {c.note}</Text> : null}
          </View>
        )}
      </Pressable>
      {shown ? (
        <View style={{ flexDirection: 'row', gap: space(3), justifyContent: 'center' }}>
          <Button label="Lo recordaba" onPress={() => { setShown(false); setI(i + 1); }} testID="review-next" />
          <Button label="Ver de nuevo" kind="ghost" onPress={() => router.push(`/item/${c.item_id}`)} />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center', justifyContent: 'center', gap: space(3) },
  card: { backgroundColor: colors.surface, borderWidth: 1, borderRadius: radius.lg, padding: space(5), gap: space(4), minHeight: 260 },
  title: { color: colors.text, ...font.h2 },
  point: { color: colors.text, ...font.body, fontWeight: '600' },
  note: { color: colors.accent, ...font.body },
});
