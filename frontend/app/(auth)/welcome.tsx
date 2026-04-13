import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function WelcomeScreen() {
  const router = useRouter();
  const { name } = useLocalSearchParams<{ name: string }>();

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      <View style={styles.content}>
        {/* Logo */}
        <View style={styles.logoContainer}>
          <Image
            source={require('../../assets/images/FuchoMX.png')}
            style={styles.logo}
            resizeMode="contain"
          />
        </View>

        {/* Confetti / Celebration icon */}
        <Text style={styles.confetti}>🎉</Text>

        {/* Welcome message */}
        <Text style={styles.title}>¡Bienvenido a FuchoMX,</Text>
        <Text style={styles.nameText}>{name || 'Campeón'}!</Text>

        <Text style={styles.subtitle}>
          Ya eres parte de la quiniela de tus cuates.{'\n'}
          ¿Cómo quieres empezar?
        </Text>

        {/* Primary Actions */}
        <View style={styles.actionsContainer}>
          <TouchableOpacity
            style={styles.primaryButton}
            onPress={() => router.replace('/quiniela/create-league')}
            activeOpacity={0.85}
          >
            <View style={styles.buttonIconContainer}>
              <Ionicons name="add-circle" size={28} color="#FFFFFF" />
            </View>
            <View style={styles.buttonTextContainer}>
              <Text style={styles.primaryButtonTitle}>Crear mi liga</Text>
              <Text style={styles.primaryButtonSubtitle}>
                Invita a tus cuates con un código
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={22} color="rgba(255,255,255,0.6)" />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => router.replace('/quiniela/join-league')}
            activeOpacity={0.85}
          >
            <View style={[styles.buttonIconContainer, styles.secondaryIconContainer]}>
              <Ionicons name="enter-outline" size={28} color="#0047AB" />
            </View>
            <View style={styles.buttonTextContainer}>
              <Text style={styles.secondaryButtonTitle}>Unirme a una liga</Text>
              <Text style={styles.secondaryButtonSubtitle}>
                Tengo un código de 6 caracteres
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={22} color="#666" />
          </TouchableOpacity>
        </View>

        {/* Skip link */}
        <TouchableOpacity
          style={styles.skipLink}
          onPress={() => router.replace('/(tabs)/home')}
          activeOpacity={0.7}
        >
          <Text style={styles.skipText}>Explorar primero</Text>
          <Ionicons name="arrow-forward" size={14} color="#666" />
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
    paddingBottom: 32,
  },
  logoContainer: {
    marginBottom: 8,
  },
  logo: {
    width: 80,
    height: 80,
  },
  confetti: {
    fontSize: 52,
    marginBottom: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#FFFFFF',
    textAlign: 'center',
    lineHeight: 30,
  },
  nameText: {
    fontSize: 28,
    fontWeight: '900',
    color: '#DC143C',
    textAlign: 'center',
    marginBottom: 16,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 40,
  },
  actionsContainer: {
    width: '100%',
    gap: 12,
    marginBottom: 32,
  },
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#DC143C',
    borderRadius: 16,
    padding: 16,
    gap: 12,
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  buttonIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(255,255,255,0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  secondaryIconContainer: {
    backgroundColor: 'rgba(0,71,171,0.15)',
  },
  buttonTextContainer: {
    flex: 1,
  },
  primaryButtonTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 2,
  },
  primaryButtonSubtitle: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.7)',
  },
  secondaryButtonTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
    marginBottom: 2,
  },
  secondaryButtonSubtitle: {
    fontSize: 12,
    color: '#666',
  },
  skipLink: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  skipText: {
    fontSize: 14,
    color: '#666',
  },
});
