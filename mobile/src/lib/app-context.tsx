import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { AppState } from 'react-native';

import { api, initApi } from './api';
import type { Settings, Usage } from './types';

interface AppCtx {
  ready: boolean;
  online: boolean;
  server: string;
  settings: Settings | null;
  usage: Usage | null;
  /** Cambia cuando algo afecta al feed (categorías, comando, ajustes): el feed se recarga. */
  feedVersion: number;
  bumpFeed: () => void;
  reconnect: () => Promise<boolean>;
  updateSettings: (s: Partial<Settings>) => Promise<void>;
  /** Suma tiempo de visionado (se envía al servidor en lotes de 30 s). */
  track: (seconds: number, category: string | null, viewed?: number) => void;
  setUsage: (u: Usage | null) => void;
  breakDue: boolean;
  dismissBreak: () => void;
  extend: (minutes: number) => Promise<void>;
}

const Ctx = createContext<AppCtx | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [online, setOnline] = useState(false);
  const [server, setServer] = useState('');
  const [settings, setSettings] = useState<Settings | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [feedVersion, setFeedVersion] = useState(0);
  const [breakDue, setBreakDue] = useState(false);
  const pending = useRef({ seconds: 0, viewed: 0, byCat: {} as Record<string, number> });
  const sinceBreak = useRef(0);

  const reconnect = useCallback(async () => {
    const cfg = await initApi();
    setServer(cfg.server);
    try {
      await api.health();
      const [s, u] = await Promise.all([api.settings(), api.usage()]);
      setSettings(s);
      setUsage(u);
      setOnline(true);
      return true;
    } catch {
      setOnline(false);
      return false;
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    reconnect();
  }, [reconnect]);

  const flush = useCallback(async () => {
    const p = pending.current;
    if (p.seconds < 1 && p.viewed === 0) return;
    pending.current = { seconds: 0, viewed: 0, byCat: {} };
    // Un latido por categoría; normalmente es solo una.
    const entries = Object.entries(p.byCat);
    try {
      let last: Usage | null = null;
      if (!entries.length) last = await api.heartbeat(p.seconds, null, p.viewed);
      for (const [i, [cat, secs]] of entries.entries()) {
        last = await api.heartbeat(Math.min(600, secs), cat === '_' ? null : cat, i === 0 ? p.viewed : 0);
      }
      if (last) setUsage(last);
    } catch {
      // sin conexión: se pierde poco, y no queremos acumular infinito
    }
  }, []);

  useEffect(() => {
    const t = setInterval(flush, 30000);
    const sub = AppState.addEventListener('change', (st) => {
      if (st !== 'active') flush();
    });
    return () => {
      clearInterval(t);
      sub.remove();
    };
  }, [flush]);

  const track = useCallback(
    (seconds: number, category: string | null, viewed = 0) => {
      if (seconds <= 0 && !viewed) return;
      const p = pending.current;
      p.seconds += seconds;
      p.viewed += viewed;
      const k = category ?? '_';
      p.byCat[k] = (p.byCat[k] ?? 0) + seconds;
      // Estimación local para que el aviso de límite sea inmediato.
      setUsage((u) => (u ? { ...u, seconds: u.seconds + seconds, exceeded: !!u.limit_seconds && u.seconds + seconds >= u.limit_seconds } : u));
      sinceBreak.current += seconds;
      const every = (settings?.break_every_minutes ?? 0) * 60;
      if (every && sinceBreak.current >= every) setBreakDue(true);
    },
    [settings?.break_every_minutes],
  );

  const dismissBreak = useCallback(() => {
    sinceBreak.current = 0;
    setBreakDue(false);
  }, []);

  const updateSettings = useCallback(async (patch: Partial<Settings>) => {
    const s = await api.patchSettings(patch);
    setSettings(s);
    setUsage(await api.usage());
  }, []);

  const extend = useCallback(async (minutes: number) => {
    await flush();
    setUsage(await api.extend(minutes));
  }, [flush]);

  const value = useMemo<AppCtx>(
    () => ({
      ready, online, server, settings, usage, feedVersion,
      bumpFeed: () => setFeedVersion((v) => v + 1),
      reconnect, updateSettings, track, setUsage, breakDue, dismissBreak, extend,
    }),
    [ready, online, server, settings, usage, feedVersion, reconnect, updateSettings, track, breakDue, dismissBreak, extend],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useApp fuera de AppProvider');
  return c;
}
