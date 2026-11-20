import { useCallback, useEffect, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button, Card, Section, ui } from '@/components/ui';
import { api } from '@/lib/api';
import { ago } from '@/lib/format';
import { colors, font, space } from '@/lib/theme';

const NAMES: Record<string, string> = {
  explorer: '🛰️ Explorador + analista', analyst: '🔬 Analista', curator: '🗞️ Curador (destacados)', maintenance: '🧹 Mantenimiento',
};

type Run = Awaited<ReturnType<typeof api.agentRuns>>[number];

export default function AgentsScreen() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [msg, setMsg] = useState('');
  const load = useCallback(() => api.agentRuns().then(setRuns).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);

  return (
    <ScrollView style={ui.screen} contentContainerStyle={ui.content}
      refreshControl={<RefreshControl refreshing={false} onRefresh={load} tintColor={colors.accent} />}>
      <Text style={ui.muted}>
        El explorador revisa tus creadores y fuentes cada 90 minutos; el analista clasifica y puntúa lo nuevo; el curador
        prepara los destacados cada mañana. Todo corre en tu PC, en segundo plano y con muy poco consumo.
      </Text>
      <Button label="Buscar contenido nuevo ahora" icon="refresh" onPress={async () => {
        await api.runAgents('all', true);
        setMsg('En marcha. Desliza hacia abajo en un minuto para ver el resultado.');
      }} />
      {msg ? <Text style={{ color: colors.accent }}>{msg}</Text> : null}
      <Section title="Últimas ejecuciones">
        {runs.map((r) => (
          <Card key={r.id} style={{ borderColor: r.ok ? colors.border : colors.danger }}>
            <View style={styles.head}>
              <Text style={styles.name}>{NAMES[r.agent] ?? r.agent}</Text>
              <Text style={ui.muted}>{ago(r.started_at)}</Text>
            </View>
            <Text style={ui.muted} numberOfLines={3}>
              {r.ok ? summarize(r.stats) : `Error: ${r.error}`}
              {!r.finished_at ? ' · en curso…' : ''}
            </Text>
          </Card>
        ))}
      </Section>
    </ScrollView>
  );
}

function summarize(s: Record<string, unknown>): string {
  const parts: string[] = [];
  if (typeof s.new_items === 'number') parts.push(`${s.new_items} nuevos`);
  if (typeof s.creators === 'number') parts.push(`${s.creators} creadores revisados`);
  if (typeof s.sources === 'number') parts.push(`${s.sources} fuentes`);
  if (typeof s.searches === 'number' && s.searches) parts.push(`${s.searches} búsquedas`);
  const a = s.analyst as { heuristic?: number; claude?: number } | undefined;
  if (a) parts.push(`${a.heuristic ?? 0} analizados${a.claude ? ` (${a.claude} con IA)` : ''}`);
  if (typeof s.highlights === 'number') parts.push(`${s.highlights} destacados`);
  if (typeof s.decayed === 'number') parts.push(`${s.decayed} preferencias ajustadas`);
  return parts.join(' · ') || 'Sin cambios';
}

const styles = StyleSheet.create({
  head: { flexDirection: 'row', justifyContent: 'space-between' },
  name: { color: colors.text, ...font.h3 },
});
