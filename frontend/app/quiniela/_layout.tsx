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
      <Stack.Screen
        name="index"
        options={{
          title: 'Quiniela Tradicional',
        }}
      />
      <Stack.Screen
        name="history"
        options={{
          title: 'Mis Quinielas',
        }}
      />
      <Stack.Screen
        name="rankings"
        options={{
          title: 'Rankings',
        }}
      />
    </Stack>
  );
}
