import { Stack } from 'expo-router';
import React from 'react';
import { AuthProvider } from './context/AuthContext';
import { FantasyProvider } from './context/FantasyContext';
import * as SplashScreen from 'expo-splash-screen';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  console.log('🏗️ [RootLayout] Montando aplicación...');

  // Ocultar splash después de 1 segundo
  React.useEffect(() => {
    const timer = setTimeout(() => {
      SplashScreen.hideAsync();
      console.log('✅ [RootLayout] SplashScreen oculto');
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  // IMPORTANTE: Siempre renderizar <Stack> para mantener el contexto de navegación de Expo Router.
  // La lógica de esperar auth se maneja en index.tsx (loading state + redirect).
  return (
    <AuthProvider>
      <FantasyProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="onboarding" />
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(tabs)" />
        </Stack>
      </FantasyProvider>
    </AuthProvider>
  );
}