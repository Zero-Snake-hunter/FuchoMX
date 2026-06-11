import { useEffect } from 'react';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform, View } from 'react-native';
import LandingPage from './components/LandingPage';
import { useAuth } from './context/AuthContext';

export default function Index() {
  const router = useRouter();
  const { token, isReady } = useAuth();

  useEffect(() => {
    if (!isReady) return;

    if (Platform.OS === 'web') {
      if (token) {
        router.replace('/(tabs)/home');
      }
      // Sin token en web: el componente renderiza LandingPage abajo
      return;
    }

    handleMobileRouting();
  }, [isReady, token]);

  const handleMobileRouting = async () => {
    try {
      const onboardingDone = await AsyncStorage.getItem('onboarding_completed');
      if (!onboardingDone) {
        router.replace('/onboarding');
        return;
      }
      if (token) {
        router.replace('/(tabs)/home');
      } else {
        router.replace('/(auth)/login');
      }
    } catch {
      router.replace('/(auth)/login');
    }
  };

  // Mientras el estado de auth carga, mostrar pantalla negra para que
  // Expo Router no navegue a una ruta por defecto antes de que termine la verificación
  if (!isReady) {
    return <View style={{ flex: 1, backgroundColor: '#000' }} />;
  }

  // Web sin sesión → landing page
  if (Platform.OS === 'web' && !token) {
    return <LandingPage />;
  }

  return null;
}
