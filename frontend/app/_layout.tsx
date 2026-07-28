import { Stack } from 'expo-router';
import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { FantasyProvider } from './context/FantasyContext';
import { ToastProvider, useToast } from './context/ToastContext';
import * as SplashScreen from 'expo-splash-screen';
import { usePushNotifications } from '../hooks/usePushNotifications';

SplashScreen.preventAutoHideAsync();

function PushNotificationRegistrar() {
  const { token } = useAuth();
  usePushNotifications(token);
  return null;
}

function AuthErrorToast() {
  const { authError, clearAuthError } = useAuth();
  const { showToast } = useToast();

  React.useEffect(() => {
    if (authError) {
      showToast('error', authError);
      clearAuthError();
    }
  }, [authError]);

  return null;
}

export default function RootLayout() {
  console.log('🏗️ [RootLayout] Montando aplicación...');

  React.useEffect(() => {
    const timer = setTimeout(() => {
      SplashScreen.hideAsync();
      console.log('✅ [RootLayout] SplashScreen oculto');
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <AuthProvider>
      <FantasyProvider>
        <ToastProvider>
          <PushNotificationRegistrar />
          <AuthErrorToast />
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="index" />
            <Stack.Screen name="onboarding" />
            <Stack.Screen name="(auth)" />
            <Stack.Screen name="(tabs)" />
          </Stack>
        </ToastProvider>
      </FantasyProvider>
    </AuthProvider>
  );
}