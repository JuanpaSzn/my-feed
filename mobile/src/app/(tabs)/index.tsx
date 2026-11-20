import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { router, useFocusEffect } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, AppState, FlatList, Platform, Pressable, Share, StyleSheet, Text, View,
  type LayoutChangeEvent, type ListViewToken,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import FeedCard, { type CardAction } from '@/components/FeedCard';
import { BreakOverlay, CommandSheet, LimitOverlay, PurposeSheet } from '@/components/Overlays';
import { MoreSheet, NoteSheet, WhySheet } from '@/components/Sheets';
import { api } from '@/lib/api';
import { useApp } from '@/lib/app-context';
import { getJSON, KEYS, setJSON } from '@/lib/storage';
import { colors, font, radius, space } from '@/lib/theme';
import type { FeedCommand, Format, Item } from '@/lib/types';

const FORMATS: { key: Format; label: string }[] = [
  { key: 'all', label: 'Todo' },
  { key: 'short', label: 'Cortos' },
  { key: 'long', label: 'Largos' },
  { key: 'article', label: 'Leer' },
];
const PAGE = 8;

const haptic = () => {
  if (Platform.OS !== 'web') Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
};

export default function FeedScreen() {
  const insets = useSafeAreaInsets();
  const app = useApp();
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [items, setItems] = useState<Item[]>([]);
  const [session, setSession] = useState<string | undefined>();
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [offline, setOffline] = useState(false);
  const [format, setFormat] = useState<Format>('all');
  const [command, setCommand] = useState<FeedCommand | null>(null);
  const [active, setActive] = useState(0);
  const [focused, setFocused] = useState(true);
  const [muted, setMuted] = useState(Platform.OS === 'web');
  const [why, setWhy] = useState<Item | null>(null);
  const [noteFor, setNoteFor] = useState<Item | null>(null);
  const [moreFor, setMoreFor] = useState<Item | null>(null);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [purposeOpen, setPurposeOpen] = useState(false);
  const [toast, setToast] = useState('');
  const listRef = useRef<FlatList<Item>>(null);
  const viewStart = useRef<{ id: number; cat: string | null; t: number } | null>(null);
  const loadingRef = useRef(false);

  const flash = (t: string) => {
    setToast(t);
    setTimeout(() => setToast(''), 2200);
  };

  // --- registro de visionado: segundos en pantalla por ítem --------------------------
  const closeView = useCallback(() => {
    const v = viewStart.current;
    if (!v) return;
    viewStart.current = null;
    const secs = Math.min(3600, (Date.now() - v.t) / 1000);
    if (secs < 0.8) return;
    app.track(secs, v.cat, 1);
    api.event(v.id, 'view', secs).catch(() => {});
  }, [app]);

  const openView = useCallback((it: Item | undefined) => {
    closeView();
    if (it) viewStart.current = { id: it.id, cat: it.category, t: Date.now() };
  }, [closeView]);

  useFocusEffect(
    useCallback(() => {
      setFocused(true);
      return () => {
        setFocused(false);
        closeView();
      };
    }, [closeView]),
  );

  useEffect(() => {
    const sub = AppState.addEventListener('change', (s) => {
      if (s !== 'active') closeView();
      else if (items[active]) openView(items[active]);
    });
    return () => sub.remove();
  }, [items, active, closeView, openView]);

  // --- carga del feed --------------------------------------------------------------
  const load = useCallback(async (reset: boolean) => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setLoading(true);
    try {
      const page = await api.feed({
        session: reset ? undefined : session,
        offset: reset ? 0 : items.length,
        limit: PAGE,
        format,
      });
      setOffline(false);
      setSession(page.session);
      setHasMore(page.has_more);
      setCommand(page.command);
      if (page.usage) app.setUsage(page.usage);
      setItems((prev) => {
        if (reset) return page.items;
        const seen = new Set(prev.map((i) => i.id));
        return [...prev, ...page.items.filter((i) => !seen.has(i.id))];
      });
      if (reset) {
        setActive(0);
        listRef.current?.scrollToOffset({ offset: 0, animated: false });
        if (format === 'all' && page.items.length) setJSON(KEYS.feedCache, page.items);
      }
    } catch {
      setOffline(true);
      if (reset) {
        const cached = await getJSON<Item[]>(KEYS.feedCache, []);
        if (cached.length) setItems(cached);
        setHasMore(false);
      }
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [session, items.length, format, app]);

  useEffect(() => {
    if (app.ready) load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [app.ready, app.online, format, app.feedVersion]);

  // Pregunta de intención, una vez al día.
  useEffect(() => {
    if (!app.online || !app.settings?.purpose_prompt) return;
    const today = new Date().toISOString().slice(0, 10);
    getJSON<string>(KEYS.purposeDay, '').then((d) => {
      if (d !== today) {
        setPurposeOpen(true);
        setJSON(KEYS.purposeDay, today);
      }
    });
  }, [app.online, app.settings?.purpose_prompt]);

  // Ítem activo -> empieza a contar su tiempo.
  useEffect(() => {
    if (focused && items[active]) openView(items[active]);
  }, [active, items.length, focused]); // eslint-disable-line react-hooks/exhaustive-deps

  const onViewable = useRef(({ viewableItems }: { viewableItems: ListViewToken[] }) => {
    const first = viewableItems.find((v) => v.isViewable);
    if (first?.index != null) setActive(first.index);
  }).current;

  const replace = (it: Item) => setItems((prev) => prev.map((p) => (p.id === it.id ? { ...it, score: p.score } : p)));
  const remove = (id: number) => setItems((prev) => prev.filter((p) => p.id !== id));
  const next = () => {
    if (active + 1 < items.length) listRef.current?.scrollToIndex({ index: active + 1, animated: true });
  };

  const onAction = useCallback(async (it: Item, a: CardAction) => {
    try {
      switch (a) {
        case 'like': {
          haptic();
          const liked = !it.state.liked;
          replace({ ...it, state: { ...it.state, liked } });
          replace(await api.event(it.id, liked ? 'like' : 'unlike'));
          break;
        }
        case 'save': {
          haptic();
          const saved = !it.state.saved;
          replace({ ...it, state: { ...it.state, saved } });
          replace(await api.event(it.id, saved ? 'save' : 'unsave'));
          if (saved) flash('Guardado en tu biblioteca');
          break;
        }
        case 'note': setNoteFor(it); break;
        case 'why': setWhy(it); break;
        case 'more': setMoreFor(it); break;
        case 'detail': router.push(`/item/${it.id}`); break;
        case 'share':
          await Share.share({ message: `${it.title}\n${it.url}` });
          api.event(it.id, 'share').catch(() => {});
          break;
        case 'open':
          api.event(it.id, 'open_source').catch(() => {});
          await WebBrowser.openBrowserAsync(it.url);
          break;
        case 'broken':
          api.broken(it.id).catch(() => {});
          remove(it.id);
          break;
        case 'ended': next(); break;
      }
    } catch {
      flash('Sin conexión con tu servidor');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, items.length]);

  const onMore = async (a: 'more_like_this' | 'less_like_this' | 'hide' | 'open' | 'detail' | 'mute_creator') => {
    const it = moreFor;
    setMoreFor(null);
    if (!it) return;
    try {
      if (a === 'open') return onAction(it, 'open');
      if (a === 'detail') return onAction(it, 'detail');
      if (a === 'mute_creator' && it.creator) {
        await api.patchCreator(it.creator.id, { status: 'muted' });
        setItems((prev) => prev.filter((p) => p.creator?.id !== it.creator?.id || p.id === items[active]?.id));
        flash(`${it.creator.name} silenciado`);
        return;
      }
      await api.event(it.id, a as 'hide' | 'less_like_this' | 'more_like_this');
      if (a === 'hide') {
        remove(it.id);
        flash('Entendido, no verás más esto');
      } else flash(a === 'more_like_this' ? 'Verás más contenido así' : 'Verás menos contenido así');
    } catch {
      flash('Sin conexión con tu servidor');
    }
  };

  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    if (width !== size.w || height !== size.h) setSize({ w: width, h: height });
  };

  const usage = app.usage;
  const showLimit = !!usage?.exceeded;

  if (app.ready && !app.online && !items.length && !loading) {
    return (
      <View style={[styles.center, { paddingTop: insets.top }]}>
        <Text style={{ fontSize: 48 }}>📡</Text>
        <Text style={styles.h1}>No encuentro tu servidor</Text>
        <Text style={styles.p}>Comprueba que MyFeed está encendido en tu PC (docker compose up) y que el iPhone está en la misma wifi.</Text>
        <Text style={[styles.p, { color: colors.faint }]}>{app.server}</Text>
        <Pressable style={styles.primary} onPress={() => app.reconnect()}>
          <Text style={styles.primaryText}>Reintentar</Text>
        </Pressable>
        <Pressable onPress={() => router.push('/settings')}>
          <Text style={{ color: colors.accent, fontWeight: '700' }}>Cambiar la dirección del servidor</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.root} onLayout={onLayout} testID="feed-screen">
      {size.h > 0 ? (
        <FlatList
          ref={listRef}
          data={items}
          keyExtractor={(i) => String(i.id)}
          renderItem={({ item, index }) => (
            <FeedCard
              item={item}
              active={focused && index === active && !showLimit && !app.breakDue}
              width={size.w}
              height={size.h}
              muted={muted}
              showReasons={app.settings?.show_reasons ?? true}
              onAction={onAction}
            />
          )}
          pagingEnabled
          snapToInterval={size.h}
          snapToAlignment="start"
          decelerationRate="fast"
          showsVerticalScrollIndicator={false}
          getItemLayout={(_, index) => ({ length: size.h, offset: size.h * index, index })}
          onViewableItemsChanged={onViewable}
          viewabilityConfig={{ itemVisiblePercentThreshold: 60 }}
          onEndReached={() => hasMore && !loading && load(false)}
          onEndReachedThreshold={2}
          // Rendimiento: muy pocas tarjetas montadas a la vez.
          windowSize={3}
          initialNumToRender={2}
          maxToRenderPerBatch={2}
          removeClippedSubviews={Platform.OS !== 'web'}
          ListEmptyComponent={
            loading ? undefined : (
              <View style={[styles.center, { height: size.h }]}>
                <Text style={{ fontSize: 44 }}>🌱</Text>
                <Text style={styles.h1}>{command ? 'Nada aún para esa búsqueda' : 'Tu feed está al día'}</Text>
                <Text style={styles.p}>
                  {command ? 'Prueba otra frase o quita el filtro.' : 'Ya viste todo lo nuevo. Los agentes buscarán más contenido pronto.'}
                </Text>
                <Pressable style={styles.primary} onPress={() => api.runAgents('explorer').then(() => flash('Buscando contenido nuevo…'))}>
                  <Text style={styles.primaryText}>Buscar contenido nuevo</Text>
                </Pressable>
              </View>
            )
          }
          ListFooterComponent={loading && items.length ? <ActivityIndicator style={{ margin: 20 }} color={colors.accent} /> : undefined}
        />
      ) : null}

      {loading && !items.length ? (
        <View style={StyleSheet.absoluteFill} pointerEvents="none">
          <View style={styles.center}><ActivityIndicator size="large" color={colors.accent} /></View>
        </View>
      ) : null}

      {/* Barra superior */}
      <View style={[styles.top, { paddingTop: insets.top + space(1) }]} pointerEvents="box-none">
        <View style={styles.topRow}>
          <Text style={styles.brand}>My<Text style={{ color: colors.accent }}>Feed</Text></Text>
          <View style={styles.segment}>
            {FORMATS.map((f) => (
              <Pressable key={f.key} onPress={() => setFormat(f.key)} style={[styles.segBtn, format === f.key && styles.segOn]} testID={`format-${f.key}`}>
                <Text style={[styles.segText, format === f.key && { color: colors.bg }]}>{f.label}</Text>
              </Pressable>
            ))}
          </View>
          <Pressable onPress={() => setMuted((m) => !m)} hitSlop={10} accessibilityLabel={muted ? 'Activar sonido' : 'Silenciar'}>
            <Ionicons name={muted ? 'volume-mute' : 'volume-high'} size={22} color={colors.text} />
          </Pressable>
        </View>
        {command ? (
          <Pressable style={styles.focusBanner} onPress={async () => { await api.clearCommand(); app.bumpFeed(); }} testID="command-banner">
            <Ionicons name="locate" size={14} color={colors.accent2} />
            <Text style={styles.focusText} numberOfLines={1}>Enfoque: {command.label}</Text>
            <Ionicons name="close-circle" size={16} color={colors.muted} />
          </Pressable>
        ) : (
          <Pressable style={styles.askPill} onPress={() => setCmdOpen(true)} testID="command-open">
            <Ionicons name="sparkles" size={14} color={colors.accent2} />
            <Text style={styles.askText}>Pide algo: «muéstrame…»</Text>
          </Pressable>
        )}
        {offline ? <Text style={styles.offline}>Sin conexión · mostrando lo último guardado</Text> : null}
      </View>

      {toast ? <View style={[styles.toast, { top: insets.top + 104 }]}><Text style={styles.toastText}>{toast}</Text></View> : null}

      {showLimit && usage ? (
        <LimitOverlay usage={usage} onExtend={(m) => app.extend(m)} onReview={() => router.push('/review')} />
      ) : app.breakDue ? (
        <BreakOverlay every={app.settings?.break_every_minutes ?? 20} onContinue={app.dismissBreak}
          onReview={() => { app.dismissBreak(); router.push('/review'); }} />
      ) : null}

      <WhySheet item={why} onClose={() => setWhy(null)} />
      <NoteSheet item={noteFor} onClose={() => setNoteFor(null)} onSave={async (n, c) => {
        if (!noteFor) return;
        replace(await api.note(noteFor.id, n, c));
        flash('Nota guardada');
      }} />
      <MoreSheet item={moreFor} onClose={() => setMoreFor(null)} onChoose={onMore} />
      <CommandSheet visible={cmdOpen} onClose={() => setCmdOpen(false)} onDone={(label) => {
        setCmdOpen(false);
        flash(`Feed ajustado: ${label}`);
        app.bumpFeed();
      }} />
      <PurposeSheet visible={purposeOpen} onClose={() => setPurposeOpen(false)} onPick={async (t) => {
        setPurposeOpen(false);
        try {
          await api.command(t);
          app.bumpFeed();
        } catch {
          flash('No pude aplicar ese enfoque');
        }
      }} />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: space(8), gap: space(3), backgroundColor: colors.bg },
  h1: { color: colors.text, ...font.h2, textAlign: 'center' },
  p: { color: colors.muted, ...font.body, textAlign: 'center' },
  primary: { backgroundColor: colors.accent, borderRadius: radius.pill, paddingVertical: space(3), paddingHorizontal: space(6), marginTop: space(2) },
  primaryText: { color: colors.bg, fontWeight: '800' },
  top: { position: 'absolute', left: 0, right: 0, top: 0, paddingHorizontal: space(4), gap: space(2) },
  topRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: space(2) },
  brand: { color: colors.text, fontSize: 20, fontWeight: '900', letterSpacing: -0.5 },
  segment: { flexDirection: 'row', backgroundColor: 'rgba(18,24,38,0.85)', borderRadius: radius.pill, padding: 3 },
  segBtn: { paddingHorizontal: space(2.5), paddingVertical: space(1.2), borderRadius: radius.pill },
  segOn: { backgroundColor: colors.accent },
  segText: { color: colors.text, fontSize: 12, fontWeight: '700' },
  askPill: { flexDirection: 'row', alignItems: 'center', gap: space(2), alignSelf: 'flex-start', backgroundColor: 'rgba(18,24,38,0.85)', borderRadius: radius.pill, paddingHorizontal: space(3), paddingVertical: space(2), borderWidth: 1, borderColor: colors.border },
  askText: { color: colors.muted, ...font.small },
  focusBanner: { flexDirection: 'row', alignItems: 'center', gap: space(2), alignSelf: 'flex-start', backgroundColor: 'rgba(139,124,255,0.18)', borderRadius: radius.pill, paddingHorizontal: space(3), paddingVertical: space(2), maxWidth: '100%' },
  focusText: { color: colors.text, ...font.small, fontWeight: '700', flexShrink: 1 },
  offline: { color: colors.warning, ...font.small },
  toast: { position: 'absolute', alignSelf: 'center', maxWidth: '86%', backgroundColor: 'rgba(18,24,38,0.95)', paddingHorizontal: space(4), paddingVertical: space(3), borderRadius: radius.pill },
  toastText: { color: colors.text, fontWeight: '700' },
});
