// Archivo: /app/frontend/app/index.tsx
// En web: muestra landing page
// En móvil: onboarding (1ra vez) → login/home según token

import { useEffect, useState } from 'react';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import LandingPage from './components/LandingPage';

export default function Index() {
  const router = useRouter();
  const [showLanding, setShowLanding] = useState(false);

  useEffect(() => {
    checkAppState();
  }, []);

  const checkAppState = async () => {
    try {
      // En web: si no tiene token, mostrar landing
      if (Platform.OS === 'web') {
        const token = await AsyncStorage.getItem('auth_token');
        if (token) {
          router.replace('/(tabs)/home');
        } else {
          setShowLanding(true);
        }
        return;
      }

      // En móvil: flujo normal
      const onboardingDone = await AsyncStorage.getItem('onboarding_completed');
      if (!onboardingDone) {
        router.replace('/onboarding');
        return;
      }
      const token = await AsyncStorage.getItem('auth_token');
      if (token) {
        router.replace('/(tabs)/home');
      } else {
        router.replace('/(auth)/login');
      }
    } catch (error) {
      router.replace('/(auth)/login');
    }
  };

  if (showLanding) {
    return <LandingPage />;
  }

  return null;
}
