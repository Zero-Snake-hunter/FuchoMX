import { useEffect } from 'react';
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

import api from '../app/lib/api';

const STORAGE_KEY = 'expo_push_token_sent';

export function usePushNotifications(authToken: string | null) {
  useEffect(() => {
    if (!authToken || Platform.OS === 'web') return;

    (async () => {
      try {
        const alreadySent = await AsyncStorage.getItem(STORAGE_KEY);
        if (alreadySent) return;

        const { status } = await Notifications.requestPermissionsAsync();
        if (status !== 'granted') return;

        const projectId =
          Constants.expoConfig?.extra?.eas?.projectId ?? undefined;
        const { data: pushToken } = await Notifications.getExpoPushTokenAsync({
          projectId,
        });

        await api.post('/api/auth/push-token', { token: pushToken });
        await AsyncStorage.setItem(STORAGE_KEY, pushToken);
      } catch (err) {
        // Push notifications are best-effort — never throw
        console.warn('[usePushNotifications]', err);
      }
    })();
  }, [authToken]);
}
