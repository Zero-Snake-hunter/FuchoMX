import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../lib/api';

interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_base64: string | null;
  total_points: number;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  isReady: boolean;
  authError: string | null;
  clearAuthError: () => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isReady, setIsReady] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const clearAuthError = () => setAuthError(null);

  useEffect(() => {
    loadStoredAuth();
  }, []);

  const loadStoredAuth = async () => {
    console.log('🔄 [AuthContext] Bootstrap: Cargando sesión almacenada...');
    try {
      const storedToken = await AsyncStorage.getItem('auth_token');
      const storedUser = await AsyncStorage.getItem('user_data');

      console.log('🔄 [AuthContext] Bootstrap: Token encontrado:', storedToken ? storedToken.substring(0, 30) + '...' : 'NULL');
      console.log('🔄 [AuthContext] Bootstrap: User data encontrada:', storedUser ? 'SÍ' : 'NULL');

      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
        console.log('✅ [AuthContext] Bootstrap: Sesión restaurada exitosamente');
      } else {
        console.log('ℹ️ [AuthContext] Bootstrap: No hay sesión almacenada');
      }
    } catch (error) {
      console.error('❌ [AuthContext] Bootstrap: Error cargando auth:', error);
    } finally {
      setLoading(false);
      setIsReady(true);
      console.log('✅ [AuthContext] Bootstrap: Completado. loading=false, isReady=true');
    }
  };

  const login = async (email: string, password: string) => {
    console.log('🔐 [AuthContext] Login: Iniciando para', email);
    try {
      const response = await api.post('/api/auth/login', {
        email,
        password,
      });

      const { access_token, user: userData } = response.data;

      console.log('🔐 [AuthContext] Login: Token recibido:', access_token ? access_token.substring(0, 30) + '...' : 'NULL');

      // Guardar token en AsyncStorage
      await AsyncStorage.setItem('auth_token', access_token);
      console.log('✅ [AuthContext] Login: Token guardado en AsyncStorage');

      // Verificar que se guardó correctamente
      const verifyToken = await AsyncStorage.getItem('auth_token');
      console.log('🔍 [AuthContext] Login: Verificación - Token en storage:', verifyToken ? verifyToken.substring(0, 30) + '...' : 'NULL');

      await AsyncStorage.setItem('user_data', JSON.stringify(userData));
      console.log('✅ [AuthContext] Login: User data guardada en AsyncStorage');

      setToken(access_token);
      setUser(userData);
      console.log('✅ [AuthContext] Login: Estado actualizado. Login completo.');
    } catch (error: any) {
      console.error('❌ [AuthContext] Login error:', error);
      let message = 'Error al iniciar sesión';
      if (error.response?.data?.detail) {
        message = error.response.data.detail;
      } else if (error.message === 'Network Error') {
        message = 'Error de conexión. Verifica tu internet.';
      } else if (error.code === 'ECONNABORTED') {
        message = 'Tiempo de espera agotado. Intenta de nuevo.';
      }
      throw new Error(message);
    }
  };

  const register = async (email: string, password: string, displayName: string) => {
    console.log('📝 [AuthContext] Register: Iniciando para', email);
    try {
      const response = await api.post('/api/auth/register', {
        email,
        password,
        display_name: displayName,
      });

      const { access_token, user: userData } = response.data;

      console.log('📝 [AuthContext] Register: Token recibido:', access_token ? access_token.substring(0, 30) + '...' : 'NULL');

      await AsyncStorage.setItem('auth_token', access_token);
      console.log('✅ [AuthContext] Register: Token guardado en AsyncStorage');

      const verifyToken = await AsyncStorage.getItem('auth_token');
      console.log('🔍 [AuthContext] Register: Verificación - Token en storage:', verifyToken ? verifyToken.substring(0, 30) + '...' : 'NULL');

      await AsyncStorage.setItem('user_data', JSON.stringify(userData));
      console.log('✅ [AuthContext] Register: User data guardada');

      setToken(access_token);
      setUser(userData);
      console.log('✅ [AuthContext] Register: Estado actualizado. Registro completo.');
    } catch (error: any) {
      console.error('❌ [AuthContext] Register error:', error);
      let message = 'Error al registrarse';
      if (error.response?.data?.detail) {
        message = error.response.data.detail;
      } else if (error.message === 'Network Error') {
        message = 'Error de conexión. Verifica tu internet.';
      } else if (error.code === 'ECONNABORTED') {
        message = 'Tiempo de espera agotado. Intenta de nuevo.';
      }
      throw new Error(message);
    }
  };

  const logout = async () => {
    console.log('🚪 [AuthContext] Logout: Cerrando sesión...');
    try {
      await AsyncStorage.removeItem('auth_token');
      await AsyncStorage.removeItem('user_data');
      setToken(null);
      setUser(null);
      console.log('✅ [AuthContext] Logout: Sesión cerrada');
    } catch (error) {
      console.error('❌ [AuthContext] Logout error:', error);
    }
  };

  const refreshUser = async () => {
    if (!token) {
      console.log('⚠️ [AuthContext] RefreshUser: No hay token, saltando');
      return;
    }

    console.log('🔄 [AuthContext] RefreshUser: Actualizando datos de usuario...');
    try {
      // Usa la instancia api centralizada - el interceptor agrega el token automáticamente
      const response = await api.get('/api/auth/me');

      const userData = response.data;
      await AsyncStorage.setItem('user_data', JSON.stringify(userData));
      setUser(userData);
      console.log('✅ [AuthContext] RefreshUser: Datos actualizados');
    } catch (error) {
      console.error('❌ [AuthContext] RefreshUser error:', error);
      setAuthError('No se pudo actualizar tu sesión. Vuelve a iniciar sesión.');
      await logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isReady,
        authError,
        clearAuthError,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
