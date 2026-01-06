import { Stack } from 'expo-router';

export default function QuinielaLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: {
          backgroundColor: '#000000',
        },
        headerTintColor: '#FFFFFF',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      }}
    >
      <Stack.Screen name="index" options={{ title: 'Quiniela Tradicional' }} />
      <Stack.Screen name="leagues" options={{ title: 'Mis Ligas' }} />
      <Stack.Screen name="create-league" options={{ title: 'Crear Liga' }} />
      <Stack.Screen name="join-league" options={{ title: 'Unirse a Liga' }} />
      <Stack.Screen name="league-detail" options={{ title: 'Detalle de Liga' }} />
      <Stack.Screen name="league-results" options={{ title: 'Resultados' }} />
      <Stack.Screen name="history" options={{ title: 'Mis Quinielas' }} />
      <Stack.Screen name="rankings" options={{ title: 'Rankings' }} />
    </Stack>
  );
}
