// Archivo: /app/frontend/app/onboarding/index.tsx
// Onboarding de 4 slides — funciona en web y móvil

import React, { useRef, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  Animated, StatusBar, Image, ScrollView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';

// ─── Datos de cada slide ─────────────────────────────────────────────────────
const SLIDES = [
  {
    id: '1',
    useLogo: true,
    tag: 'LIGA MX · QUINIELA · ONCE',
    title: 'La quiniela\nde tus cuates',
    subtitle: 'No la de todos.\nTu grupo, tus reglas, tu liga privada.',
    bg: '#0A0A0A',
    accent: '#E63946',
  },
  {
    id: '2',
    emoji: '🏟️',
    tag: 'ASÍ DE FÁCIL',
    title: '3 pasos y\nya estás jugando',
    subtitle: null,
    steps: [
      { icon: '1️⃣', text: 'Crea tu liga en 30 segundos' },
      { icon: '2️⃣', text: 'Comparte el código con tus amigos' },
      { icon: '3️⃣', text: 'Predice y compite cada jornada' },
    ],
    bg: '#0A0A0A',
    accent: '#1D88E5',
  },
  {
    id: '3',
    emoji: '🎮',
    tag: 'DOS MODOS DE JUEGO',
    title: 'Elige cómo\nquieres ganar',
    subtitle: null,
    modes: [
      {
        icon: '📝',
        name: 'QUINIELA',
        desc: 'Predice resultados de cada partido. 1 acierto = 1 punto.',
        color: '#E63946',
      },
      {
        icon: '⚽',
        name: 'ONCE IDEAL',
        desc: 'Arma tu once ideal con jugadores reales. Ganas puntos con sus stats.',
        color: '#1D88E5',
      },
    ],
    bg: '#0A0A0A',
    accent: '#2A9D8F',
  },
  {
    id: '4',
    emoji: '🎉',
    tag: 'SIN LETRA CHICA',
    title: '100% gratis.\nSiempre.',
    subtitle: null,
    perks: [
      { icon: '✅', text: 'Quiniela y ONCE sin costo' },
      { icon: '✅', text: 'Crea tu liga con hasta 25 amigos' },
      { icon: '✅', text: 'Únete a ligas ilimitadas' },
      { icon: '✅', text: 'Rankings, logros y rachas' },
      { icon: '✅', text: 'Sin anuncios, sin pagos ocultos' },
    ],
    bg: '#0A0A0A',
    accent: '#E63946',
    isFinal: true,
  },
];

// ─── Componente de un slide ──────────────────────────────────────────────────
const Slide = ({ item }: { item: typeof SLIDES[0] }) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  React.useEffect(() => {
    fadeAnim.setValue(0);
    slideAnim.setValue(30);
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 500, delay: 100, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 500, delay: 100, useNativeDriver: true }),
    ]).start();
  }, [item.id]);

  return (
    <ScrollView
      style={{ flex: 1 }}
      contentContainerStyle={slide.container}
      showsVerticalScrollIndicator={false}
    >
      <Animated.View style={[slide.tagRow, { opacity: fadeAnim }]}>
        <View style={[slide.tagPill, { borderColor: `${item.accent}55` }]}>
          <Text style={[slide.tagText, { color: item.accent }]}>{item.tag}</Text>
        </View>
      </Animated.View>

      {item.useLogo ? (
        <Animated.View style={[slide.logoContainer, {
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }],
        }]}>
          <Image
            source={require('../../assets/images/FuchoMX.png')}
            style={slide.logoImage}
            resizeMode="contain"
          />
        </Animated.View>
      ) : (
        <Animated.Text style={[slide.bigEmoji, {
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }],
        }]}>
          {item.emoji}
        </Animated.Text>
      )}

      <Animated.Text style={[slide.title, {
        opacity: fadeAnim,
        transform: [{ translateY: slideAnim }],
      }]}>
        {item.title}
      </Animated.Text>

      {item.subtitle && (
        <Animated.Text style={[slide.subtitle, { opacity: fadeAnim }]}>
          {item.subtitle}
        </Animated.Text>
      )}

      {item.steps && (
        <Animated.View style={[slide.stepsBox, { opacity: fadeAnim }]}>
          {item.steps.map((step, i) => (
            <View key={i} style={slide.stepRow}>
              <Text style={slide.stepIcon}>{step.icon}</Text>
              <Text style={slide.stepText}>{step.text}</Text>
            </View>
          ))}
        </Animated.View>
      )}

      {item.modes && (
        <Animated.View style={[slide.modesBox, { opacity: fadeAnim }]}>
          {item.modes.map((mode, i) => (
            <View key={i} style={[slide.modeCard, { borderColor: `${mode.color}44` }]}>
              <Text style={slide.modeIcon}>{mode.icon}</Text>
              <View style={slide.modeInfo}>
                <Text style={[slide.modeName, { color: mode.color }]}>{mode.name}</Text>
                <Text style={slide.modeDesc}>{mode.desc}</Text>
              </View>
            </View>
          ))}
          <View style={slide.orBadge}>
            <Text style={slide.orText}>¡O juega los DOS al mismo tiempo! 🔥</Text>
          </View>
        </Animated.View>
      )}

      {item.perks && (
        <Animated.View style={[slide.perksBox, { opacity: fadeAnim }]}>
          {item.perks.map((perk, i) => (
            <View key={i} style={slide.perkRow}>
              <Text style={slide.perkIcon}>{perk.icon}</Text>
              <Text style={slide.perkText}>{perk.text}</Text>
            </View>
          ))}
        </Animated.View>
      )}
    </ScrollView>
  );
};

// ─── Pantalla principal ──────────────────────────────────────────────────────
export default function OnboardingScreen() {
  const router = useRouter();
  const [currentIndex, setCurrentIndex] = useState(0);

  const handleNext = () => {
    if (currentIndex < SLIDES.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const handleFinish = async () => {
    await AsyncStorage.setItem('onboarding_completed', 'true');
    router.replace('/(auth)/register');
  };

  const handleSkip = async () => {
    await AsyncStorage.setItem('onboarding_completed', 'true');
    router.replace('/(auth)/login');
  };

  const isLast = currentIndex === SLIDES.length - 1;
  const currentSlide = SLIDES[currentIndex];
  const accent = currentSlide.accent;

  return (
    <SafeAreaView style={[s.container, { backgroundColor: currentSlide.bg }]}>
      <StatusBar barStyle="light-content" backgroundColor="#0A0A0A" />

      {!isLast && (
        <TouchableOpacity style={s.skipBtn} onPress={handleSkip}>
          <Text style={s.skipText}>Omitir</Text>
        </TouchableOpacity>
      )}

      <Slide item={currentSlide} />

      <View style={s.dotsRow}>
        {SLIDES.map((_, i) => (
          <View
            key={i}
            style={[
              s.dot,
              {
                width: i === currentIndex ? 24 : 8,
                opacity: i === currentIndex ? 1 : 0.3,
                backgroundColor: accent,
              },
            ]}
          />
        ))}
      </View>

      <View style={s.btnRow}>
        {isLast ? (
          <>
            <TouchableOpacity
              style={[s.btnPrimary, { backgroundColor: accent }]}
              onPress={handleFinish}
              activeOpacity={0.85}
            >
              <Text style={s.btnPrimaryText}>🚀 CREAR MI CUENTA</Text>
            </TouchableOpacity>
            <TouchableOpacity style={s.btnSecondary} onPress={handleSkip}>
              <Text style={s.btnSecondaryText}>Ya tengo cuenta → Iniciar sesión</Text>
            </TouchableOpacity>
          </>
        ) : (
          <TouchableOpacity
            style={[s.btnPrimary, { backgroundColor: accent }]}
            onPress={handleNext}
            activeOpacity={0.85}
          >
            <Text style={s.btnPrimaryText}>Siguiente →</Text>
          </TouchableOpacity>
        )}
      </View>
    </SafeAreaView>
  );
}

const slide = StyleSheet.create({
  container:     { alignItems: 'center', paddingHorizontal: 28, paddingTop: 20, paddingBottom: 20, flexGrow: 1 },
  tagRow:        { marginBottom: 20 },
  tagPill:       { borderWidth: 1, borderRadius: 20, paddingHorizontal: 14, paddingVertical: 5 },
  tagText:       { fontSize: 10, fontWeight: '800', letterSpacing: 2 },
  bigEmoji:      { fontSize: 80, marginBottom: 20, textAlign: 'center' },
  logoContainer: { marginBottom: 20, alignItems: 'center', justifyContent: 'center' },
  logoImage:     { width: 140, height: 140 },
  title:         { fontSize: 34, fontWeight: '900', color: '#FFFFFF', textAlign: 'center', lineHeight: 40, marginBottom: 16, letterSpacing: -0.5 },
  subtitle:      { fontSize: 16, color: '#888', textAlign: 'center', lineHeight: 24 },
  stepsBox:      { width: '100%', marginTop: 8 },
  stepRow:       { flexDirection: 'row', alignItems: 'center', backgroundColor: '#111', borderRadius: 14, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: '#1E1E1E' },
  stepIcon:      { fontSize: 24, marginRight: 14 },
  stepText:      { color: '#DDD', fontSize: 15, fontWeight: '600', flex: 1 },
  modesBox:      { width: '100%', marginTop: 8 },
  modeCard:      { flexDirection: 'row', alignItems: 'center', backgroundColor: '#111', borderRadius: 14, padding: 16, marginBottom: 12, borderWidth: 1 },
  modeIcon:      { fontSize: 30, marginRight: 14 },
  modeInfo:      { flex: 1 },
  modeName:      { fontSize: 13, fontWeight: '900', letterSpacing: 1, marginBottom: 3 },
  modeDesc:      { color: '#777', fontSize: 12, lineHeight: 17 },
  orBadge:       { backgroundColor: '#1A1A1A', borderRadius: 12, padding: 12, alignItems: 'center', borderWidth: 1, borderColor: '#2A2A2A' },
  orText:        { color: '#AAA', fontSize: 13, fontWeight: '600' },
  perksBox:      { width: '100%', marginTop: 8 },
  perkRow:       { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  perkIcon:      { fontSize: 20, width: 28, textAlign: 'center', marginRight: 12 },
  perkText:      { color: '#DDD', fontSize: 15, fontWeight: '500' },
});

const s = StyleSheet.create({
  container:        { flex: 1, backgroundColor: '#0A0A0A' },
  skipBtn:          { position: 'absolute', top: 52, right: 20, zIndex: 10, padding: 8 },
  skipText:         { color: '#555', fontSize: 14 },
  dotsRow:          { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginBottom: 20 },
  dot:              { height: 8, borderRadius: 4, marginHorizontal: 3 },
  btnRow:           { paddingHorizontal: 24, paddingBottom: 24 },
  btnPrimary:       { borderRadius: 16, paddingVertical: 17, alignItems: 'center', marginBottom: 10 },
  btnPrimaryText:   { color: '#FFF', fontSize: 16, fontWeight: '900', letterSpacing: 0.5 },
  btnSecondary:     { alignItems: 'center', paddingVertical: 10 },
  btnSecondaryText: { color: '#555', fontSize: 14 },
});
