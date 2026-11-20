import { DarkTheme, Stack, ThemeProvider } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AppProvider } from '@/lib/app-context';
import { colors } from '@/lib/theme';

const theme = {
  ...DarkTheme,
  colors: { ...DarkTheme.colors, background: colors.bg, card: colors.bg, text: colors.text, border: colors.border, primary: colors.accent },
};

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ThemeProvider value={theme}>
        <AppProvider>
          <StatusBar style="light" />
          <Stack
            screenOptions={{
              headerStyle: { backgroundColor: colors.bg },
              headerTintColor: colors.text,
              headerTitleStyle: { fontWeight: '700' },
              contentStyle: { backgroundColor: colors.bg },
              headerBackTitle: 'Atrás',
            }}>
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="item/[id]" options={{ title: 'Detalle', presentation: 'modal' }} />
            <Stack.Screen name="creators" options={{ title: 'Creadores y fuentes' }} />
            <Stack.Screen name="settings" options={{ title: 'Ajustes' }} />
            <Stack.Screen name="preferences" options={{ title: 'Lo que aprendí de ti' }} />
            <Stack.Screen name="review" options={{ title: 'Repaso', presentation: 'modal' }} />
            <Stack.Screen name="add" options={{ title: 'Añadir enlace', presentation: 'modal' }} />
            <Stack.Screen name="agents" options={{ title: 'Agentes' }} />
          </Stack>
        </AppProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
