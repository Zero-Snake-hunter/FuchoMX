import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { Alert, Platform } from 'react-native';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

console.log('🔧 API Instance creada con baseURL:', BACKEND_URL);

// Crear instancia de axios con configuración base
const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor de REQUEST - Agregar token automáticamente
api.interceptors.request.use(
  async (config) => {
    try {
      const token = await AsyncStorage.getItem('auth_token');
      
      console.log('🔐 Interceptor - Token desde AsyncStorage:', token ? token.substring(0, 30) + '...' : 'NULL');
      console.log('📡 Interceptor - Request:', config.method?.toUpperCase(), config.url);
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log('✅ Header Authorization agregado');
      } else {
        console.log('⚠️ No hay token en AsyncStorage para:', config.url);
      }
    } catch (error) {
      console.error('❌ Error obteniendo token de AsyncStorage:', error);
    }
    
    return config;
  },
  (error) => {
    console.error('❌ Error en request interceptor:', error);
    return Promise.reject(error);
  }
);

// Interceptor de RESPONSE - Manejar errores de autenticación
api.interceptors.response.use(
  (response) => {
    // Log solo en desarrollo
    if (__DEV__) {
      console.log('✅ Response:', response.status, response.config.url);
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // Log del error
    if (__DEV__) {
      console.log('❌ Error Response:', error.response?.status, error.config?.url);
      console.log('❌ Error Detail:', error.response?.data?.detail || error.message);
    }
    
    // Manejar error 401 (Unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      console.log('🔒 Sesión expirada o token inválido');
      
      // Limpiar datos de autenticación
      try {
        await AsyncStorage.removeItem('auth_token');
        await AsyncStorage.removeItem('user_data');
      } catch (e) {
        console.error('Error limpiando auth:', e);
      }
      
      // Mostrar alerta y redirigir (solo en mobile)
      if (Platform.OS !== 'web') {
        Alert.alert(
          'Sesión Expirada',
          'Tu sesión ha expirado. Por favor inicia sesión nuevamente.',
          [
            {
              text: 'OK',
              onPress: () => {
                try {
                  router.replace('/(auth)/login');
                } catch (e) {
                  console.error('Error redirigiendo:', e);
                }
              },
            },
          ]
        );
      } else {
        // En web, redirigir directamente
        try {
          router.replace('/(auth)/login');
        } catch (e) {
          console.error('Error redirigiendo:', e);
        }
      }
    }
    
    // Manejar error de red
    if (error.message === 'Network Error') {
      console.log('📵 Error de conexión de red');
    }
    
    return Promise.reject(error);
  }
);

export default api;
