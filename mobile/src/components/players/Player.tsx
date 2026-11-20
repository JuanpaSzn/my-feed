import { useCallback } from 'react';
import { StyleSheet, View } from 'react-native';
import { WebView } from 'react-native-webview';
import YoutubePlayer from 'react-native-youtube-iframe';

import type { PlayerProps } from './types';

/** Reproductores oficiales: IFrame de YouTube y los embeds de TikTok/Instagram/Vimeo.
 *  Nada se descarga ni se vuelve a alojar. */
export default function Player({ kind, videoId, embedUrl, width, height, playing, muted, onError, onEnded }: PlayerProps) {
  const onState = useCallback((s: string) => {
    if (s === 'ended') onEnded?.();
  }, [onEnded]);

  if (kind === 'youtube' && videoId) {
    return (
      <View style={{ width, height }} pointerEvents="box-none">
        <YoutubePlayer
          height={height}
          width={width}
          videoId={videoId}
          play={playing}
          mute={muted}
          onChangeState={onState}
          onError={(e: string) => onError?.(e)}
          initialPlayerParams={{ controls: true, rel: false, iv_load_policy: 3, playerLang: 'es', cc_lang_pref: 'es' }}
          webViewProps={{
            allowsInlineMediaPlayback: true,
            mediaPlaybackRequiresUserAction: false,
            allowsFullscreenVideo: true,
            style: { backgroundColor: 'transparent' },
          }}
        />
      </View>
    );
  }
  if (!embedUrl) return null;
  return (
    <View style={[styles.embed, { width, height }]}>
      <WebView
        source={{ uri: embedUrl }}
        style={{ backgroundColor: 'transparent' }}
        allowsInlineMediaPlayback
        mediaPlaybackRequiresUserAction={false}
        allowsFullscreenVideo
        javaScriptEnabled
        // Evita que el embed nos saque de la app al tocar enlaces.
        setSupportMultipleWindows={false}
        onError={() => onError?.('embed_error')}
        onHttpError={(e) => e.nativeEvent.statusCode >= 400 && onError?.('embed_http_error')}
      />
    </View>
  );
}

const styles = StyleSheet.create({ embed: { overflow: 'hidden', borderRadius: 12 } });
