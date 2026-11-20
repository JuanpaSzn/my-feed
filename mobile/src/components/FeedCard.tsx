import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { memo, useRef } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ago, duration, PLATFORM_LABEL } from '@/lib/format';
import { catMeta, colors, font, radius, space } from '@/lib/theme';
import type { Item } from '@/lib/types';
import Player from './players/Player';

export type CardAction = 'like' | 'save' | 'note' | 'share' | 'open' | 'why' | 'detail' | 'more' | 'broken' | 'ended';

interface Props {
  item: Item;
  active: boolean;
  width: number;
  height: number;
  muted: boolean;
  showReasons: boolean;
  onAction: (item: Item, action: CardAction) => void;
}

function ActionButton({ icon, label, color, onPress, testID }: {
  icon: keyof typeof Ionicons.glyphMap; label?: string; color?: string; onPress: () => void; testID?: string;
}) {
  return (
    <Pressable onPress={onPress} hitSlop={8} style={styles.action} accessibilityRole="button" accessibilityLabel={label} testID={testID}>
      <View style={styles.actionCircle}>
        <Ionicons name={icon} size={26} color={color ?? colors.text} />
      </View>
      {label ? <Text style={styles.actionLabel}>{label}</Text> : null}
    </Pressable>
  );
}

function FeedCard({ item, active, width, height, muted, showReasons, onAction }: Props) {
  const meta = catMeta(item.category);
  const lastTap = useRef(0);
  const isVideo = item.platform === 'youtube' || item.platform === 'tiktok' || item.platform === 'instagram' || item.platform === 'vimeo';
  const vertical = item.format === 'short' || item.platform === 'tiktok' || item.platform === 'instagram';
  const playerW = width;
  const playerH = vertical ? Math.min(height * 0.74, (width * 16) / 9) : Math.round((width * 9) / 16);

  const doubleTap = () => {
    const now = Date.now();
    if (now - lastTap.current < 300) onAction(item, 'like');
    lastTap.current = now;
  };

  const header = (
    <View style={styles.topRow}>
      <View style={[styles.chip, { borderColor: meta.color }]}>
        <Text style={styles.chipText}>{meta.emoji} {meta.name}</Text>
      </View>
      {item.is_news ? <View style={[styles.chip, styles.newsChip]}><Text style={styles.chipText}>Novedad</Text></View> : null}
    </View>
  );

  let media: React.ReactNode;
  if (item.platform === 'myfeed') {
    media = (
      <Pressable onPress={doubleTap} style={[styles.lesson, { borderColor: meta.color }]}>
        <Text style={[styles.lessonKicker, { color: meta.color }]}>MICROLECCIÓN · 1 MIN</Text>
        <Text style={styles.lessonTitle}>{item.title}</Text>
        <ScrollView style={{ maxHeight: height * 0.32 }} showsVerticalScrollIndicator={false}>
          <Text style={styles.lessonBody}>{item.description}</Text>
        </ScrollView>
        {item.key_points.length ? (
          <View style={styles.points}>
            {item.key_points.map((p) => (
              <View key={p} style={styles.pointRow}>
                <View style={[styles.dot, { backgroundColor: meta.color }]} />
                <Text style={styles.pointText}>{p}</Text>
              </View>
            ))}
          </View>
        ) : null}
      </Pressable>
    );
  } else if (item.platform === 'article') {
    media = (
      <Pressable onPress={doubleTap} style={styles.article}>
        {item.thumbnail_url ? (
          <Image source={{ uri: item.thumbnail_url }} style={styles.articleImg} contentFit="cover" transition={150} />
        ) : (
          <View style={[styles.articleImg, styles.articlePlaceholder, { backgroundColor: meta.color + '22' }]}>
            <Text style={{ fontSize: 56 }}>{meta.emoji}</Text>
          </View>
        )}
        <Text style={styles.articleTitle} numberOfLines={4}>{item.title}</Text>
        <Text style={styles.articleBody} numberOfLines={7}>{item.summary || item.description}</Text>
        <Pressable onPress={() => onAction(item, 'open')} style={styles.readBtn} testID="read-source">
          <Ionicons name="open-outline" size={18} color={colors.bg} />
          <Text style={styles.readBtnText}>Leer en {item.author_name || 'la fuente'}</Text>
        </Pressable>
      </Pressable>
    );
  } else if (isVideo) {
    media = active ? (
      <Player
        kind={item.platform === 'youtube' ? 'youtube' : 'embed'}
        videoId={item.platform === 'youtube' ? item.external_id : undefined}
        embedUrl={item.embed_url}
        width={playerW}
        height={playerH}
        playing={active}
        muted={muted}
        onError={() => onAction(item, 'broken')}
        onEnded={() => onAction(item, 'ended')}
      />
    ) : (
      <View style={{ width: playerW, height: playerH, justifyContent: 'center', alignItems: 'center' }}>
        {item.thumbnail_url ? (
          <Image source={{ uri: item.thumbnail_url }} style={StyleSheet.absoluteFill} contentFit="cover" />
        ) : null}
        <Ionicons name="play-circle" size={64} color="rgba(255,255,255,0.85)" />
      </View>
    );
  }

  const metaLine = [item.creator?.name || item.author_name, duration(item.duration_sec), ago(item.published_at), PLATFORM_LABEL[item.platform]]
    .filter(Boolean)
    .join(' · ');

  return (
    <View style={[styles.card, { width, height }]} testID={`card-${item.id}`}>
      {item.thumbnail_url && item.platform !== 'myfeed' ? (
        <Image source={{ uri: item.thumbnail_url }} style={StyleSheet.absoluteFill} blurRadius={40} contentFit="cover" />
      ) : null}
      <View style={[StyleSheet.absoluteFill, { backgroundColor: item.platform === 'myfeed' ? meta.color + '14' : colors.overlay }]} />

      <View style={[styles.mediaWrap, vertical && isVideo ? { justifyContent: 'flex-start', paddingTop: space(14) } : null]}>
        {media}
      </View>

      <View style={styles.bottom} pointerEvents="box-none">
        {header}
        {item.platform !== 'myfeed' && item.platform !== 'article' ? (
          <Pressable onPress={() => onAction(item, 'detail')}>
            <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
          </Pressable>
        ) : null}
        <Text style={styles.meta} numberOfLines={1}>{metaLine}</Text>
        {item.summary && isVideo ? (
          <Pressable onPress={() => onAction(item, 'detail')}>
            <Text style={styles.summary} numberOfLines={2}>{item.summary}</Text>
          </Pressable>
        ) : null}
        {showReasons && item.score?.reasons?.length ? (
          <Pressable onPress={() => onAction(item, 'why')} style={styles.why} testID="why-button">
            <Ionicons name="sparkles" size={14} color={colors.accent} />
            <Text style={styles.whyText} numberOfLines={1}>{item.score.reasons[0]}</Text>
            <Text style={styles.whyMore}>¿Por qué?</Text>
          </Pressable>
        ) : null}
      </View>

      <View style={styles.actions}>
        <ActionButton icon={item.state.liked ? 'heart' : 'heart-outline'} color={item.state.liked ? colors.like : undefined}
          label="Me gusta" onPress={() => onAction(item, 'like')} testID="like-button" />
        <ActionButton icon={item.state.saved ? 'bookmark' : 'bookmark-outline'} color={item.state.saved ? colors.save : undefined}
          label="Guardar" onPress={() => onAction(item, 'save')} testID="save-button" />
        <ActionButton icon={item.state.note ? 'create' : 'create-outline'} label="Aprendí" onPress={() => onAction(item, 'note')} testID="note-button" />
        <ActionButton icon="share-social-outline" label="Compartir" onPress={() => onAction(item, 'share')} />
        <ActionButton icon="ellipsis-horizontal" onPress={() => onAction(item, 'more')} testID="more-button" />
      </View>
    </View>
  );
}

export default memo(FeedCard, (a, b) =>
  a.item === b.item && a.active === b.active && a.height === b.height && a.width === b.width && a.muted === b.muted &&
  a.showReasons === b.showReasons);

const styles = StyleSheet.create({
  card: { backgroundColor: colors.bg, overflow: 'hidden' },
  mediaWrap: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingBottom: space(36) },
  bottom: { position: 'absolute', left: space(4), right: space(20), bottom: space(6), gap: space(1.5) },
  topRow: { flexDirection: 'row', gap: space(2) },
  chip: { borderWidth: 1, borderRadius: radius.pill, paddingHorizontal: space(2.5), paddingVertical: space(1), backgroundColor: 'rgba(10,13,20,0.6)' },
  newsChip: { borderColor: colors.warning },
  chipText: { color: colors.text, ...font.tiny },
  title: { color: colors.text, ...font.h2, textShadowColor: 'rgba(0,0,0,0.6)', textShadowRadius: 6 },
  meta: { color: colors.muted, ...font.small },
  summary: { color: colors.text, opacity: 0.85, ...font.small },
  why: { flexDirection: 'row', alignItems: 'center', gap: space(1.5), alignSelf: 'flex-start', backgroundColor: 'rgba(46,230,166,0.12)', borderRadius: radius.pill, paddingHorizontal: space(3), paddingVertical: space(1.5), maxWidth: '100%' },
  whyText: { color: colors.text, ...font.small, flexShrink: 1 },
  whyMore: { color: colors.accent, ...font.small, fontWeight: '700' },
  actions: { position: 'absolute', right: space(2), bottom: space(8), alignItems: 'center', gap: space(3.5) },
  action: { alignItems: 'center', width: 64 },
  actionCircle: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(10,13,20,0.55)' },
  actionLabel: { color: colors.text, fontSize: 10, marginTop: 2, fontWeight: '600' },
  lesson: { marginHorizontal: space(5), marginRight: space(20), padding: space(5), borderRadius: radius.lg, borderWidth: 1, backgroundColor: colors.surface, gap: space(3) },
  lessonKicker: { ...font.tiny, letterSpacing: 1.2 },
  lessonTitle: { color: colors.text, ...font.h1, fontSize: 24 },
  lessonBody: { color: colors.text, ...font.body, opacity: 0.9 },
  points: { gap: space(2), marginTop: space(1) },
  pointRow: { flexDirection: 'row', gap: space(2), alignItems: 'flex-start' },
  dot: { width: 8, height: 8, borderRadius: 4, marginTop: 6 },
  pointText: { color: colors.text, ...font.small, flex: 1, fontWeight: '600' },
  article: { marginHorizontal: space(5), marginRight: space(20), gap: space(3) },
  articleImg: { width: '100%', aspectRatio: 16 / 9, borderRadius: radius.md },
  articlePlaceholder: { alignItems: 'center', justifyContent: 'center' },
  articleTitle: { color: colors.text, ...font.h2 },
  articleBody: { color: colors.text, opacity: 0.85, ...font.body },
  readBtn: { flexDirection: 'row', gap: space(2), alignItems: 'center', alignSelf: 'flex-start', backgroundColor: colors.accent, paddingHorizontal: space(4), paddingVertical: space(2.5), borderRadius: radius.pill },
  readBtnText: { color: colors.bg, fontWeight: '700' },
});
