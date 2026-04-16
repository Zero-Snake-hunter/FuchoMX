import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';

export default function BracketResultsScreen() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/liguilla/bracket').then(res => setData(res.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const pred = data?.my_prediction;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={{ top:8,bottom:8,left:8,right:8 }}>
          <Ionicons name="arrow-back" size={24} color="#FFF" />
        </TouchableOpacity>
        <Text style={s.title}>🏆 Tu Bracket</Text>
        <View style={{ width: 32 }} />
      </View>

      {loading ? (
        <ActivityIndicator color="#E63946" size="large" style={{ flex: 1 }} />
      ) : !pred ? (
        <View style={s.emptyState}>
          <Text style={s.emptyEmoji}>📋</Text>
          <Text style={s.emptyTitle}>Sin predicción guardada</Text>
          <Text style={s.emptySub}>Ve al Bracket para hacer tus predicciones</Text>
          <TouchableOpacity style={s.goBtn} onPress={() => router.replace('/quiniela/bracket')}>
            <Text style={s.goBtnText}>Ir al Bracket</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: 20 }}>
          <View style={s.statusBanner}>
            <Text style={s.statusText}>⏳ Liguilla aún no ha comenzado</Text>
            <Text style={s.statusSub}>Los resultados se calcularán cuando termine la fase regular (J17)</Text>
          </View>

          <Text style={s.sectionTitle}>TUS PICKS GUARDADOS</Text>

          <View style={s.pickSection}>
            <Text style={s.pickRound}>🥊 Cuartos de Final</Text>
            {(pred.cuartos_picks || []).map((teamId: string, i: number) => {
              const team = data.teams?.find((t: any) => t.id === teamId);
              return (
                <View key={i} style={s.pickRow}>
                  <Text style={s.pickPos}>Q{i + 1}</Text>
                  <Text style={s.pickName}>{team?.name ?? teamId}</Text>
                </View>
              );
            })}
          </View>

          <View style={s.pickSection}>
            <Text style={s.pickRound}>⚔️ Semifinal</Text>
            {(pred.semis_picks || []).map((teamId: string, i: number) => {
              const team = data.teams?.find((t: any) => t.id === teamId);
              return (
                <View key={i} style={s.pickRow}>
                  <Text style={s.pickPos}>SF{i + 1}</Text>
                  <Text style={s.pickName}>{team?.name ?? teamId}</Text>
                </View>
              );
            })}
          </View>

          {pred.champion && (
            <View style={s.championCard}>
              <Text style={s.champEmoji}>🏆</Text>
              <Text style={s.champLabel}>TU CAMPEÓN</Text>
              <Text style={s.champName}>
                {data.teams?.find((t: any) => t.id === pred.champion)?.name ?? pred.champion}
              </Text>
            </View>
          )}

          <View style={s.scoringCard}>
            <Text style={s.scoringTitle}>Puntos posibles</Text>
            <Text style={s.scoringRow}>Cada equipo correcto en Cuartos: <Text style={s.pts}>5 pts</Text></Text>
            <Text style={s.scoringRow}>Cada equipo correcto en Semis: <Text style={s.pts}>10 pts</Text></Text>
            <Text style={s.scoringRow}>Campeón correcto: <Text style={s.pts}>25 pts</Text></Text>
            <Text style={s.scoringMax}>Máximo posible: <Text style={s.pts}>75 pts</Text></Text>
          </View>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container:    { flex: 1, backgroundColor: '#090909' },
  header:       { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#1A1A1A' },
  title:        { color: '#FFF', fontSize: 17, fontWeight: '800', flex: 1, textAlign: 'center' },
  emptyState:   { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  emptyEmoji:   { fontSize: 56, marginBottom: 16 },
  emptyTitle:   { color: '#FFF', fontSize: 20, fontWeight: '800', marginBottom: 8 },
  emptySub:     { color: '#666', fontSize: 14, textAlign: 'center', lineHeight: 20, marginBottom: 24 },
  goBtn:        { backgroundColor: '#E63946', borderRadius: 10, paddingHorizontal: 24, paddingVertical: 12 },
  goBtnText:    { color: '#FFF', fontWeight: '700', fontSize: 15 },
  statusBanner: { backgroundColor: '#111', borderRadius: 12, padding: 16, marginBottom: 20, borderWidth: 1, borderColor: '#1E1E1E' },
  statusText:   { color: '#FFC300', fontWeight: '700', marginBottom: 4 },
  statusSub:    { color: '#666', fontSize: 12, lineHeight: 18 },
  sectionTitle: { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 1, marginBottom: 12 },
  pickSection:  { backgroundColor: '#111', borderRadius: 12, padding: 16, marginBottom: 16, borderWidth: 1, borderColor: '#1A1A1A' },
  pickRound:    { color: '#FFF', fontWeight: '700', marginBottom: 12 },
  pickRow:      { flexDirection: 'row', alignItems: 'center', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: '#1A1A1A' },
  pickPos:      { color: '#E63946', fontWeight: '700', width: 32, fontSize: 12 },
  pickName:     { color: '#DDD', fontSize: 14 },
  championCard: { backgroundColor: '#E6394615', borderRadius: 16, padding: 20, alignItems: 'center', marginBottom: 16, borderWidth: 1, borderColor: '#E6394633' },
  champEmoji:   { fontSize: 40, marginBottom: 8 },
  champLabel:   { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 1, marginBottom: 6 },
  champName:    { color: '#FFF', fontSize: 20, fontWeight: '900' },
  scoringCard:  { backgroundColor: '#111', borderRadius: 12, padding: 16, borderWidth: 1, borderColor: '#1A1A1A' },
  scoringTitle: { color: '#FFF', fontWeight: '700', marginBottom: 10 },
  scoringRow:   { color: '#888', fontSize: 13, marginBottom: 6 },
  scoringMax:   { color: '#FFF', fontSize: 14, fontWeight: '700', marginTop: 8 },
  pts:          { color: '#E63946', fontWeight: '700' },
});
