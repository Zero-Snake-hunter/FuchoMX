// Archivo: /app/frontend/app/components/AchievementToast.tsx
// Toast que aparece cuando el usuario desbloquea un logro

import React, { useEffect, useRef } from 'react';
import { Animated, View, Text, StyleSheet } from 'react-native';

interface Props {
  visible: boolean;
  emoji:   string;
  title:   string;
  description: string;
  onHide:  () => void;
}

export function AchievementToast({ visible, emoji, title, description, onHide }: Props) {
  const translateY = useRef(new Animated.Value(-130)).current;
  const opacity    = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!visible) return;

    // Entrar
    Animated.parallel([
      Animated.spring(translateY, { toValue: 0, tension: 65, friction: 10, useNativeDriver: true }),
      Animated.timing(opacity,    { toValue: 1, duration: 200, useNativeDriver: true }),
    ]).start();

    // Salir después de 3.5s
    const t = setTimeout(() => {
      Animated.parallel([
        Animated.timing(translateY, { toValue: -130, duration: 280, useNativeDriver: true }),
        Animated.timing(opacity,    { toValue: 0,    duration: 280, useNativeDriver: true }),
      ]).start(() => onHide());
    }, 3500);

    return () => clearTimeout(t);
  }, [visible]);

  if (!visible) return null;

  return (
    <Animated.View style={[ts.container, { transform: [{ translateY }], opacity }]}>
      <View style={ts.glowBar} />
      <Text style={ts.emoji}>{emoji}</Text>
      <View style={ts.content}>
        <Text style={ts.label}>🏅 LOGRO DESBLOQUEADO</Text>
        <Text style={ts.title}>{title}</Text>
        <Text style={ts.desc} numberOfLines={1}>{description}</Text>
      </View>
    </Animated.View>
  );
}

const ts = StyleSheet.create({
  container: {
    position: 'absolute', top: 52, left: 12, right: 12,
    backgroundColor: '#111', borderRadius: 16, padding: 14,
    flexDirection: 'row', alignItems: 'center', gap: 12,
    borderWidth: 1.5, borderColor: '#E63946',
    zIndex: 9999,
  },
  glowBar:  { position: 'absolute', top: 0, left: 0, right: 0, height: 3, backgroundColor: '#E63946', borderTopLeftRadius: 16, borderTopRightRadius: 16 },
  emoji:    { fontSize: 38 },
  content:  { flex: 1 },
  label:    { color: '#E63946', fontSize: 9, fontWeight: '800', letterSpacing: 1.5 },
  title:    { color: '#FFF', fontSize: 15, fontWeight: '800', marginTop: 1 },
  desc:     { color: '#777', fontSize: 12, marginTop: 2 },
});
