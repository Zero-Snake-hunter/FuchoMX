import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { Alert, Platform } from 'react-native';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://fuchomx.onrender.com';

console.log('🔧 [API] Instancia creada con baseURL:', BACKEND_URL);

// Crear instancia de axios con configuración base
const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 8000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor de REQUEST - Agregar token automáticamente
api.interceptors.request.use(
  async (config) => {
    const fullUrl = `${config.baseURL || ''}${config.url || ''}`;
    console.log(`📡 [API Interceptor] >>> ${config.method?.toUpperCase()} ${fullUrl}`);
    
    try {
      const token = await AsyncStorage.getItem('auth_token');
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log(`🔐 [API Interceptor] Token adjuntado: ${token.substring(0, 20)}...`);
      } else {
        console.log('⚠️ [API Interceptor] Sin token en AsyncStorage');
      }
    } catch (error) {
      console.error('❌ [API Interceptor] Error leyendo token de AsyncStorage:', error);
    }
    
    // Log final del header Authorization
    console.log(`📋 [API Interceptor] Authorization header: ${config.headers.Authorization ? 'PRESENTE' : 'AUSENTE'}`);
    
    return config;
  },
  (error) => {
    console.error('❌ [API Interceptor] Error en request:', error);
    return Promise.reject(error);
  }
);

// Interceptor de RESPONSE - Manejar errores de autenticación
api.interceptors.response.use(
  (response) => {
    console.log(`✅ [API Response] <<< ${response.status} ${response.config.url}`);
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    const requestUrl = error.config?.url || '';
    
    console.log(`❌ [API Response] <<< ${error.response?.status || 'NETWORK_ERROR'} ${requestUrl}`);
    console.log(`❌ [API Response] Detail: ${error.response?.data?.detail || error.message}`);
    
    // Endpoints de auth que pueden retornar 401 legítimamente (credenciales incorrectas)
    const isAuthEndpoint = requestUrl.includes('/api/auth/login') || 
                           requestUrl.includes('/api/auth/register') ||
                           requestUrl.includes('/api/auth/recover');
    
    // Manejar error 401 (Unauthorized) - SOLO para endpoints protegidos, NO para login/register
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true;
      
      console.log('🔒 [API Response] 401 detectado - Limpiando sesión...');
      
      // Limpiar datos de autenticación
      try {
        await AsyncStorage.removeItem('auth_token');
        await AsyncStorage.removeItem('user_data');
        console.log('🔒 [API Response] Token y datos de usuario eliminados de AsyncStorage');
      } catch (e) {
        console.error('❌ [API Response] Error limpiando auth:', e);
      }
      
      // Mostrar alerta y redirigir
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
        try {
          router.replace('/(auth)/login');
        } catch (e) {
          console.error('Error redirigiendo:', e);
        }
      }
    }
    
    // Manejar error de red
    if (error.message === 'Network Error') {
      console.log('📵 [API Response] Error de conexión de red');
    }
    
    return Promise.reject(error);
  }
);

export default api;
