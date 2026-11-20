export interface PlayerProps {
  kind: 'youtube' | 'embed';
  videoId?: string;
  embedUrl?: string;
  width: number;
  height: number;
  playing: boolean;
  muted: boolean;
  onError?: (reason: string) => void;
  onEnded?: () => void;
}
