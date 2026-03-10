// Archivo: /app/frontend/app/index.tsx
// Lógica: onboarding (1ra vez) → login/home según token

import { useEffect } from 'react';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function Index() {
  const router = useRouter();

  useEffect(() => {
    checkAppState();
  }, []);

  const checkAppState = async () => {
    try {
      // 1. ¿Ya vio el onboarding?
      const onboardingDone = await AsyncStorage.getItem('onboarding_completed');

      if (!onboardingDone) {
        // Primera vez que abre la app → mostrar onboarding
        router.replace('/onboarding');
        return;
      }

      // 2. ¿Tiene sesión activa?
      const token = await AsyncStorage.getItem('auth_token');

      if (token) {
        // Usuario ya logueado → ir al home
        router.replace('/(tabs)/home');
      } else {
        // Ya vio onboarding pero no está logueado → login
        router.replace('/(auth)/login');
      }
    } catch (error) {
      // En caso de error, ir a login
      router.replace('/(auth)/login');
    }
  };

  return null; // Esta pantalla no renderiza nada, solo redirige
}
