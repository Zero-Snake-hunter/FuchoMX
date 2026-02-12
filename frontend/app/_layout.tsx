import { Stack } from 'expo-router';
import React, { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { AuthProvider, useAuth } from './context/AuthContext';
import { FantasyProvider } from './context/FantasyContext';
import * as SplashScreen from 'expo-splash-screen';

SplashScreen.preventAutoHideAsync();

function RootNavigator() {
  const { isReady, loading } = useAuth();

  useEffect(() => {
    console.log('🏗️ [RootNavigator] isReady:', isReady, 'loading:', loading);
    if (isReady) {
      SplashScreen.hideAsync();
      console.log('✅ [RootNavigator] SplashScreen oculto, app lista para navegar');
    }
  }, [isReady, loading]);

  // NO renderizar navegación hasta que el bootstrap de auth haya terminado
  // Esto previene la race condition donde se hacen requests antes de que el token esté disponible
  if (!isReady) {
    console.log('⏳ [RootNavigator] Esperando bootstrap de autenticación...');
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#DC143C" />
      </View>
    );
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="(auth)" />
      <Stack.Screen name="(tabs)" />
    </Stack>
  );
}

export default function RootLayout() {
  console.log('🏗️ [RootLayout] Montando aplicación...');

  return (
    <AuthProvider>
      <FantasyProvider>
        <RootNavigator />
      </FantasyProvider>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
  },
});