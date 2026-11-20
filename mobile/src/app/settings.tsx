import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native';

import { Button, Card, Chip, Section, ui } from '@/components/ui';
import { api, configureApi, guessServer } from '@/lib/api';
import { useApp } from '@/lib/app-context';
import { getJSON, KEYS } from '@/lib/storage';
import { colors, font, space } from '@/lib/theme';
import type { Settings, Status } from '@/lib/types';

const LIMITS = [0, 20, 30, 45, 60, 90];
const BREAKS = [0, 10, 15, 20, 30];

function Toggle({ label, sub, value, onChange, testID }: { label: string; sub?: string; value: boolean; onChange: (v: boolean) => void; testID?: string }) {
  return (
    <View style={styles.toggle}>
      <View style={{ flex: 1 }}>
        <Text style={ui.text}>{label}</Text>
        {sub ? <Text style={ui.muted}>{sub}</Text> : null}
      </View>
      <Switch value={value} onValueChange={onChange} trackColor={{ true: colors.accent, false: colors.surface2 }} testID={testID} />
    </View>
  );
}

export default function SettingsScreen() {
  const app = useApp();
  const [server, setServer] = useState(app.server);
  const [token, setToken] = useState('');
  const [status, setStatus] = useState<Status | null>(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const s = app.settings;

  useEffect(() => {
    getJSON<string>(KEYS.token, '').then(setToken);
    api.status().then(setStatus).catch(() => setStatus(null));
  }, [app.online]);

  const set = (patch: Partial<Settings>) => app.updateSettings(patch).catch(() => setMsg('No se pudo guardar'));

  return (
    <ScrollView style={ui.screen} contentContainerStyle={ui.content} keyboardShouldPersistTaps="handled">
      {s ? (
        <>
          <Section title="Límite diario">
            <Text style={ui.muted}>Cuando lo alcances, MyFeed te propone parar (puedes pedir 10 minutos más).</Text>
            <View style={styles.chips}>
              {LIMITS.map((m) => (
                <Chip key={m} label={m ? `${m} min` : 'Sin límite'} on={s.daily_limit_minutes === m}
                  onPress={() => set({ daily_limit_minutes: m })} testID={`limit-${m}`} />
              ))}
            </View>
          </Section>
          <Section title="Pausa consciente">
            <View style={styles.chips}>
              {BREAKS.map((m) => (
                <Chip key={m} label={m ? `Cada ${m} min` : 'Nunca'} on={s.break_every_minutes === m} onPress={() => set({ break_every_minutes: m })} />
              ))}
            </View>
          </Section>
          <Card>
            <Toggle label="¿Qué quieres aprender hoy?" sub="Pregunta de intención al abrir la app cada día" value={s.purpose_prompt} onChange={(v) => set({ purpose_prompt: v })} />
            <Toggle label="Mostrar «por qué veo esto»" value={s.show_reasons} onChange={(v) => set({ show_reasons: v })} />
            <Toggle label="Huecos de exploración" sub="De vez en cuando, algo distinto para no encerrarte en una burbuja" value={s.exploration} onChange={(v) => set({ exploration: v })} />
          </Card>
        </>
      ) : null}

      <Section title="Servidor">
        <Text style={ui.muted}>La dirección de tu PC con MyFeed (puerto 8000). Debe estar en la misma wifi que el iPhone.</Text>
        <TextInput value={server} onChangeText={setServer} autoCapitalize="none" autoCorrect={false} style={ui.input}
          placeholder={guessServer()} placeholderTextColor={colors.faint} testID="server-input" />
        <TextInput value={token} onChangeText={setToken} autoCapitalize="none" autoCorrect={false} style={ui.input}
          placeholder="Token de la app (opcional)" placeholderTextColor={colors.faint} secureTextEntry />
        <Button label="Conectar" busy={busy} testID="server-save" onPress={async () => {
          setBusy(true);
          await configureApi(server || guessServer(), token);
          const ok = await app.reconnect();
          setMsg(ok ? '✓ Conectado' : '✗ No responde. ¿Está encendido docker compose?');
          app.bumpFeed();
          setBusy(false);
        }} />
        {msg ? <Text style={{ color: msg.startsWith('✓') ? colors.accent : colors.danger }}>{msg}</Text> : null}
      </Section>

      {status ? (
        <Section title="Estado">
          <Card>
            <Text style={ui.text}>🤖 Claude: {status.claude.enabled ? `activo (${status.claude.model})` : 'sin clave · modo reglas'}</Text>
            <Text style={ui.text}>▶️ YouTube API: {status.youtube_api ? 'activa' : 'sin clave · solo RSS de tus canales'}</Text>
            <Text style={ui.text}>🗄️ Base de datos: {status.database}{status.redis ? ' + Redis' : ''}</Text>
            <Text style={ui.text}>📚 {status.items_total} contenidos · {status.creators.approved ?? 0} creadores · {status.sources} fuentes</Text>
            <Text style={[ui.muted, { marginTop: space(1) }]}>Las claves se ponen en el archivo .env del servidor (ver README).</Text>
          </Card>
        </Section>
      ) : null}
      <Text style={[ui.muted, { textAlign: 'center' }]}>MyFeed · hecho para aprender, no para engancharte.</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: space(2) },
  toggle: { flexDirection: 'row', alignItems: 'center', gap: space(3), paddingVertical: space(1) },
  h: { color: colors.text, ...font.h3 },
});
