// Archivo: /app/frontend/app/components/StreakWidget.tsx
// Widget de racha para la pantalla de inicio (home.tsx)

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

interface StreakWidgetProps {
  quinielaStreak: number;
  winStreak:      number;
  correctStreak:  number;
  onPress:        () => void;
}

export function StreakWidget({ quinielaStreak, winStreak, correctStreak, onPress }: StreakWidgetProps) {
  // Si todas las rachas son 0, no mostrar
  if (quinielaStreak === 0 && winStreak === 0 && correctStreak === 0) {
    return (
      <TouchableOpacity style={sw.containerEmpty} onPress={onPress} activeOpacity={0.8}>
        <Text style={sw.emptyEmoji}>🔥</Text>
        <Text style={sw.emptyText}>¡Juega tu primera quiniela para empezar una racha!</Text>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity style={sw.container} onPress={onPress} activeOpacity={0.85}>
      <View style={sw.header}>
        <Text style={sw.headerTitle}>🔥 Tus Rachas</Text>
        <Text style={sw.headerLink}>Ver logros →</Text>
      </View>

      <View style={sw.row}>
        {/* Racha de participación */}
        {quinielaStreak > 0 && (
          <View style={[sw.pill, { borderColor: '#E6394644' }]}>
            <Text style={sw.pillEmoji}>📅</Text>
            <View>
              <Text style={[sw.pillNum, { color: '#E63946' }]}>{quinielaStreak}</Text>
              <Text style={sw.pillLabel}>jornadas</Text>
            </View>
          </View>
        )}

        {/* Racha de victorias */}
        {winStreak > 0 && (
          <View style={[sw.pill, { borderColor: '#F4A26144' }]}>
            <Text style={sw.pillEmoji}>🏆</Text>
            <View>
              <Text style={[sw.pillNum, { color: '#F4A261' }]}>{winStreak}</Text>
              <Text style={sw.pillLabel}>victorias</Text>
            </View>
          </View>
        )}

        {/* Racha de predicciones */}
        {correctStreak > 0 && (
          <View style={[sw.pill, { borderColor: '#2A9D8F44' }]}>
            <Text style={sw.pillEmoji}>🎯</Text>
            <View>
              <Text style={[sw.pillNum, { color: '#2A9D8F' }]}>{correctStreak}</Text>
              <Text style={sw.pillLabel}>correctas</Text>
            </View>
          </View>
        )}
      </View>

      {/* Mensaje motivacional */}
      <Text style={sw.motivation}>
        {quinielaStreak >= 5
          ? `🔥 ¡${quinielaStreak} jornadas seguidas! ¡Imparable!`
          : quinielaStreak >= 3
          ? `⚡ ¡${quinielaStreak} seguidas! No rompas la racha`
          : quinielaStreak >= 1
          ? `💪 ¡${quinielaStreak} jornada(s)! Sigue así`
          : winStreak >= 1
          ? `🏆 ¡${winStreak} victoria(s) seguidas!`
          : '¡Sigue jugando!'}
      </Text>
    </TouchableOpacity>
  );
}

const sw = StyleSheet.create({
  container:      { backgroundColor: '#111', borderRadius: 16, padding: 16, marginHorizontal: 16, marginVertical: 8, borderWidth: 1, borderColor: '#1E1E1E' },
  containerEmpty: { backgroundColor: '#0D0D0D', borderRadius: 14, padding: 14, marginHorizontal: 16, marginVertical: 6, borderWidth: 1, borderColor: '#1A1A1A', flexDirection: 'row', alignItems: 'center', gap: 10 },
  emptyEmoji:     { fontSize: 24 },
  emptyText:      { color: '#444', fontSize: 12, flex: 1 },
  header:         { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  headerTitle:    { color: '#FFF', fontSize: 15, fontWeight: '700' },
  headerLink:     { color: '#E63946', fontSize: 12 },
  row:            { flexDirection: 'row', gap: 10, marginBottom: 10 },
  pill:           { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#1A1A1A', borderRadius: 12, paddingHorizontal: 12, paddingVertical: 8, borderWidth: 1, flex: 1, justifyContent: 'center' },
  pillEmoji:      { fontSize: 18 },
  pillNum:        { fontSize: 22, fontWeight: '800' },
  pillLabel:      { color: '#555', fontSize: 10 },
  motivation:     { color: '#666', fontSize: 12, textAlign: 'center' },
});
