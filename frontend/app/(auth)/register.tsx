import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  ActivityIndicator,
  Image,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';

export default function RegisterScreen() {
  const router = useRouter();
  const { register } = useAuth();
  const { joinCode, joinLeagueName } = useLocalSearchParams<{ joinCode?: string; joinLeagueName?: string }>();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleRegister = async () => {
    setErrorMsg('');
    if (!displayName.trim() || !email.trim() || !password || !confirmPassword) {
      setErrorMsg('Por favor completa todos los campos');
      return;
    }
    if (displayName.trim().length > 20) {
      setErrorMsg('Usa un apodo o nombre corto (máx. 20 caracteres).');
      return;
    }
    if (displayName.trim().length < 3) {
      setErrorMsg('Tu nombre debe tener al menos 3 caracteres.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMsg('Las contraseñas no coinciden');
      return;
    }
    if (password.length < 6) {
      setErrorMsg('La contraseña debe tener al menos 6 caracteres');
      return;
    }

    setLoading(true);
    try {
      await register(email.toLowerCase().trim(), password, displayName.trim());
      await joinPendingLeagueIfAny();
      router.replace({
        pathname: '/(auth)/welcome',
        params: { name: displayName.trim() },
      });
    } catch (error: any) {
      setErrorMsg(error.message || 'No se pudo crear la cuenta. Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  // Si el usuario llegó aquí desde un link de invitación (/leagues/join/[code]
  // guardó el código antes de mandarlo a registrarse), lo une a esa liga en
  // cuanto la cuenta nueva queda creada — sin que tenga que volver a pegar
  // el código a mano.
  const joinPendingLeagueIfAny = async () => {
    const pendingCode = await AsyncStorage.getItem('pending_league_code');
    if (!pendingCode) return;

    try {
      const res = await api.post('/api/leagues/join', { code: pendingCode });
      Alert.alert('¡Te uniste a la liga!', `Ya eres parte de "${res.data.league_name}"`);
    } catch (error: any) {
      // No bloqueamos el flujo de registro por esto — el código pudo haberse
      // llenado o vencido justo en este momento; el usuario ya puede unirse
      // a mano desde Mis Ligas si hace falta.
      console.log('No se pudo unir a la liga pendiente:', error.response?.data?.detail);
    } finally {
      await AsyncStorage.multiRemove(['pending_league_code', 'pending_league_name']);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      {/* Botón atrás FUERA del ScrollView para garantizar eventos touch en móvil */}
      <TouchableOpacity
        style={styles.backButton}
        onPress={() => router.replace('/(auth)/login')}
        activeOpacity={0.7}
      >
        <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
      </TouchableOpacity>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Image
            source={require('../../assets/images/FuchoMX.png')}
            style={styles.logo}
            resizeMode="contain"
          />
          <Text style={styles.title}>FUCHO MX</Text>
          <Text style={styles.subtitle}>Tu fut, con tus cuates</Text>
        </View>

        {joinCode ? (
          <View style={styles.joinBanner}>
            <Ionicons name="trophy" size={18} color="#DC143C" />
            <Text style={styles.joinBannerText}>
              Al crear tu cuenta te unirás a{' '}
              <Text style={styles.joinBannerBold}>{joinLeagueName || `la liga ${joinCode}`}</Text>
            </Text>
          </View>
        ) : null}

        <View style={styles.form}>
          <View style={styles.inputContainer}>
            <Ionicons name="person-outline" size={20} color="#666" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Apodo o nombre corto (máx. 20)"
              placeholderTextColor="#666"
              value={displayName}
              onChangeText={setDisplayName}
              autoCapitalize="words"
              maxLength={20}
            />
          </View>

          <View style={styles.inputContainer}>
            <Ionicons name="mail-outline" size={20} color="#666" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Correo electrónico"
              placeholderTextColor="#666"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          <View style={styles.inputContainer}>
            <Ionicons name="lock-closed-outline" size={20} color="#666" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Contraseña"
              placeholderTextColor="#666"
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!showPassword}
              autoCapitalize="none"
            />
            <TouchableOpacity
              onPress={() => setShowPassword(!showPassword)}
              style={styles.eyeIcon}
            >
              <Ionicons
                name={showPassword ? 'eye-outline' : 'eye-off-outline'}
                size={20}
                color="#666"
              />
            </TouchableOpacity>
          </View>

          <View style={styles.inputContainer}>
            <Ionicons name="lock-closed-outline" size={20} color="#666" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Confirmar contraseña"
              placeholderTextColor="#666"
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              secureTextEntry={!showPassword}
              autoCapitalize="none"
            />
          </View>

          {errorMsg ? <Text style={styles.errorText}>{errorMsg}</Text> : null}

          <TouchableOpacity
            style={[styles.registerButton, loading && styles.buttonDisabled]}
            onPress={handleRegister}
            disabled={loading}
            activeOpacity={0.85}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.registerButtonText}>CREAR CUENTA</Text>
            )}
          </TouchableOpacity>

          <View style={styles.loginContainer}>
            <Text style={styles.loginText}>¿Ya tienes cuenta? </Text>
            <TouchableOpacity onPress={() => router.replace('/(auth)/login')}>
              <Text style={styles.loginLink}>Inicia sesión</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  scrollContent: {
    flexGrow: 1,
    padding: 24,
    paddingTop: 60,
  },
  backButton: {
    position: 'absolute',
    top: 48,
    left: 24,
    zIndex: 10,
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
    marginTop: 20,
  },
  logo: {
    width: 120,
    height: 120,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginTop: 16,
    letterSpacing: 1,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
  },
  joinBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#DC143C44',
    padding: 12,
    marginBottom: 20,
    gap: 10,
  },
  joinBannerText: {
    flex: 1,
    color: '#CCCCCC',
    fontSize: 13,
    lineHeight: 18,
  },
  joinBannerBold: {
    color: '#FFFFFF',
    fontWeight: 'bold',
  },
  form: {
    width: '100%',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  inputIcon: {
    marginLeft: 16,
  },
  input: {
    flex: 1,
    height: 56,
    color: '#FFFFFF',
    fontSize: 16,
    paddingHorizontal: 16,
  },
  eyeIcon: {
    padding: 16,
  },
  registerButton: {
    backgroundColor: '#DC143C',
    height: 56,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 24,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  errorText: {
    color: '#DC143C',
    fontSize: 13,
    textAlign: 'center',
    marginBottom: 12,
  },
  registerButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  loginContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loginText: {
    color: '#999',
    fontSize: 14,
  },
  loginLink: {
    color: '#DC143C',
    fontSize: 14,
    fontWeight: 'bold',
  },
});
