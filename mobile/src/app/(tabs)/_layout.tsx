import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors } from '@/lib/theme';

type IconName = keyof typeof Ionicons.glyphMap;
const icon = (on: IconName, off: IconName) =>
  ({ focused, color, size }: { focused: boolean; color: unknown; size: number }) => (
    <Ionicons name={focused ? on : off} size={size} color={color as string} />
  );

export default function TabsLayout() {
  const insets = useSafeAreaInsets();
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: {
          backgroundColor: colors.bg, borderTopColor: colors.border,
          height: 64 + insets.bottom, paddingBottom: Math.max(insets.bottom, 10), paddingTop: 6,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600', lineHeight: 14 },
      }}>
      <Tabs.Screen name="index" options={{ title: 'Inicio', tabBarIcon: icon('home', 'home-outline') }} />
      <Tabs.Screen name="today" options={{ title: 'Hoy', tabBarIcon: icon('sunny', 'sunny-outline') }} />
      <Tabs.Screen name="explore" options={{ title: 'Explorar', tabBarIcon: icon('compass', 'compass-outline') }} />
      <Tabs.Screen name="library" options={{ title: 'Biblioteca', tabBarIcon: icon('bookmarks', 'bookmarks-outline') }} />
      <Tabs.Screen name="me" options={{ title: 'Yo', tabBarIcon: icon('person-circle', 'person-circle-outline') }} />
    </Tabs>
  );
}
