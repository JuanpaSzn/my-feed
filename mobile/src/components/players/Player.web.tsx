import { createElement, useMemo } from 'react';
import { View } from 'react-native';

import type { PlayerProps } from './types';

/** Versión web (navegador / pruebas): iframe oficial con los mismos parámetros. */
export default function Player({ kind, videoId, embedUrl, width, height, playing, muted }: PlayerProps) {
  const src = useMemo(() => {
    if (kind === 'youtube' && videoId) {
      const p = new URLSearchParams({
        autoplay: playing ? '1' : '0', mute: muted ? '1' : '0', playsinline: '1', rel: '0', iv_load_policy: '3',
        hl: 'es', cc_lang_pref: 'es',
      });
      return `https://www.youtube-nocookie.com/embed/${videoId}?${p.toString()}`;
    }
    return embedUrl ?? '';
  }, [kind, videoId, embedUrl, playing, muted]);
  if (!src || !playing) return <View style={{ width, height }} />;
  return (
    <View style={{ width, height }}>
      {createElement('iframe', {
        src,
        width,
        height,
        title: 'Reproductor',
        style: { border: 0, borderRadius: 12, backgroundColor: 'transparent' },
        allow: 'autoplay; encrypted-media; picture-in-picture; fullscreen',
        allowFullScreen: true,
      })}
    </View>
  );
}
