import { Stack } from 'expo-router';

export default function FantasyLayout() {
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
      <Stack.Screen
        name="index"
        options={{
          title: 'Fantasy Fútbol',
        }}
      />
      <Stack.Screen
        name="create-team"
        options={{
          title: 'Crear Equipo',
        }}
      />
      <Stack.Screen
        name="lineup"
        options={{
          title: 'Armar Alineación',
        }}
      />
      <Stack.Screen
        name="rankings"
        options={{
          title: 'Rankings Fantasy',
        }}
      />
    </Stack>
  );
}
