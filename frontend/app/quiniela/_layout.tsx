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
      <Stack.Screen name="leagues" options={{ headerShown: false }} />
      <Stack.Screen name="create-league" options={{ title: 'Crear Liga' }} />
      <Stack.Screen name="join-league" options={{ title: 'Unirse a Liga' }} />
      <Stack.Screen name="league-detail" options={{ headerShown: false }} />
      <Stack.Screen name="league-results" options={{ title: 'Resultados' }} />
      <Stack.Screen name="history" options={{ title: 'Mis Quinielas' }} />
      <Stack.Screen name="bracket" options={{ headerShown: false }} />
      <Stack.Screen name="bracket-results" options={{ headerShown: false }} />
      <Stack.Screen name="rankings" options={{ title: 'Rankings' }} />
    </Stack>
  );
}
