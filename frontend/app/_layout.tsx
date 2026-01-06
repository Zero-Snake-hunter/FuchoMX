import { Stack } from 'expo-router';
import { useEffect } from 'react';
import { AuthProvider } from './context/AuthContext';
import { FantasyProvider } from './context/FantasyContext';
import * as SplashScreen from 'expo-splash-screen';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  useEffect(() => {
    setTimeout(() => {
      SplashScreen.hideAsync();
    }, 1000);
  }, []);

  return (
    <AuthProvider>
      <FantasyProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(tabs)" />
        </Stack>
      </FantasyProvider>
    </AuthProvider>
  );
}