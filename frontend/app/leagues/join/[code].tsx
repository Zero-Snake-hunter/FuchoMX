import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, Image } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../context/AuthContext';
import api from '../../lib/api';

type ScreenState = 'loading' | 'invalid' | 'joining' | 'joined' | 'error';

export default function JoinLeagueScreen() {
  const router = useRouter();
  const { code } = useLocalSearchParams<{ code: string }>();
  const { token, isReady } = useAuth();

  const [state, setState] = useState<ScreenState>('loading');
  const [leagueName, setLeagueName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (!code || !isReady) return;
    validateAndJoin();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, isReady]);

  const validateAndJoin = async () => {
    let name = '';
    try {
      const res = await api.get(`/api/leagues/validate/${code}`);
      name = res.data.name;
      setLeagueName(name);
    } catch (error: any) {
      setErrorMsg(error.response?.data?.detail || 'Este link de liga ya no es válido');
      setState('invalid');
      return;
    }

    if (!token) {
      // Sin sesión: guardamos el código y mandamos a registro — al terminar,
      // register.tsx lo lee de AsyncStorage y se une automáticamente.
      await AsyncStorage.setItem('pending_league_code', code);
      await AsyncStorage.setItem('pending_league_name', name);
      router.replace({
        pathname: '/(auth)/register',
        params: { joinCode: code, joinLeagueName: name },
      });
      return;
    }

    setState('joining');
    try {
      const joinRes = await api.post('/api/leagues/join', { code });
      setLeagueName(joinRes.data.league_name || name);
      setState('joined');
      setTimeout(() => router.replace('/quiniela/leagues'), 1600);
    } catch (error: any) {
      const detail: string = error.response?.data?.detail || '';
      if (detail.includes('Ya eres miembro')) {
        // No es un error real — el usuario ya pertenece a la liga.
        setState('joined');
        setTimeout(() => router.replace('/quiniela/leagues'), 1600);
        return;
      }
      setErrorMsg(detail || 'No se pudo completar la unión a la liga');
      setState('error');
    }
  };

  return (
    <View style={styles.container}>
      <Image
        source={require('../../../assets/images/FuchoMX.png')}
        style={styles.logo}
        resizeMode="contain"
      />

      {(state === 'loading' || state === 'joining') && (
        <>
          <ActivityIndicator size="large" color="#DC143C" style={styles.spinner} />
          <Text style={styles.statusText}>
            {state === 'loading' ? 'Verificando invitación...' : 'Uniéndote a la liga...'}
          </Text>
        </>
      )}

      {state === 'joined' && (
        <>
          <Ionicons name="checkmark-circle" size={64} color="#00A551" style={styles.icon} />
          <Text style={styles.title}>¡Te uniste a {leagueName}!</Text>
          <Text style={styles.subtitle}>Te llevamos a Mis Ligas...</Text>
        </>
      )}

      {(state === 'invalid' || state === 'error') && (
        <>
          <Ionicons name="alert-circle" size={64} color="#DC143C" style={styles.icon} />
          <Text style={styles.title}>
            {state === 'invalid' ? 'Link inválido' : 'No se pudo unir a la liga'}
          </Text>
          <Text style={styles.subtitle}>{errorMsg}</Text>
          <TouchableOpacity
            style={styles.button}
            onPress={() => router.replace('/quiniela/leagues')}
            activeOpacity={0.85}
          >
            <Text style={styles.buttonText}>IR A MIS LIGAS</Text>
          </TouchableOpacity>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  logo: {
    width: 96,
    height: 96,
    marginBottom: 32,
  },
  spinner: {
    marginBottom: 16,
  },
  icon: {
    marginBottom: 16,
  },
  statusText: {
    color: '#999',
    fontSize: 15,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    color: '#999',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 24,
  },
  button: {
    backgroundColor: '#DC143C',
    height: 52,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
});
