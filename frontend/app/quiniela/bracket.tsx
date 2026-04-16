import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  Image, StatusBar, ActivityIndicator, Alert, Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';
import { SPONSORS } from '../config/sponsors';

type TeamInfo = {
  id: string;
  name: string;
  short_name: string;
  shield_url: string;
  position: number;
};

type BracketPicks = {
  qL1: TeamInfo | null;  // Ganador Q1: 1° vs 8°
  qL2: TeamInfo | null;  // Ganador Q2: 4° vs 5°
  qR1: TeamInfo | null;  // Ganador Q3: 2° vs 7°
  qR2: TeamInfo | null;  // Ganador Q4: 3° vs 6°
  sfL: TeamInfo | null;  // Semifinal izquierda
  sfR: TeamInfo | null;  // Semifinal derecha
  champion: TeamInfo | null;
};

const EMPTY: BracketPicks = { qL1:null, qL2:null, qR1:null, qR2:null, sfL:null, sfR:null, champion:null };

// ── Team Slot ──────────────────────────────────────────
const TeamSlot = ({
  team, isWinner, onPress, disabled = false, size = 'sm',
}: {
  team?: TeamInfo | null;
  isWinner?: boolean;
  onPress: () => void;
  disabled?: boolean;
  size?: 'sm' | 'md';
}) => {
  const h = size === 'md' ? 54 : 46;
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || !team}
      activeOpacity={0.65}
      style={[
        ts.slot,
        { minHeight: h },
        isWinner && ts.slotWinner,
        !team && ts.slotEmpty,
      ]}
    >
      {team ? (
        <>
          <Image source={{ uri: team.shield_url }} style={ts.shield} resizeMode="contain" />
          <Text style={[ts.name, isWinner && ts.nameWinner]} numberOfLines={1}>
            {team.short_name}
          </Text>
          {isWinner && <Text style={ts.check}>✓</Text>}
        </>
      ) : (
        <Text style={ts.emptyText}>?</Text>
      )}
    </TouchableOpacity>
  );
};

// ── Match Card (2 teams, tap to pick winner) ────────────
const MatchCard = ({
  label, homeTeam, awayTeam, winner, onPickHome, onPickAway,
}: {
  label: string;
  homeTeam?: TeamInfo | null;
  awayTeam?: TeamInfo | null;
  winner?: TeamInfo | null;
  onPickHome: () => void;
  onPickAway: () => void;
}) => (
  <View style={mc.card}>
    <Text style={mc.label}>{label}</Text>
    <TeamSlot
      team={homeTeam}
      isWinner={!!winner && winner.id === homeTeam?.id}
      onPress={onPickHome}
      disabled={!homeTeam || !awayTeam}
    />
    <View style={mc.vsRow}>
      <View style={mc.vsLine} />
      <Text style={mc.vsText}>vs</Text>
      <View style={mc.vsLine} />
    </View>
    <TeamSlot
      team={awayTeam}
      isWinner={!!winner && winner.id === awayTeam?.id}
      onPress={onPickAway}
      disabled={!homeTeam || !awayTeam}
    />
  </View>
);

// ── Main Screen ─────────────────────────────────────────
export default function BracketScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [bracketData, setBracketData] = useState<any>(null);
  const [picks, setPicks] = useState<BracketPicks>(EMPTY);
  const [byPos, setByPos] = useState<Record<number, TeamInfo>>({});

  useEffect(() => {
    api.get('/api/liguilla/bracket').then(res => {
      const data = res.data;
      setBracketData(data);
      const bp: Record<number, TeamInfo> = {};
      (data.teams || []).forEach((t: TeamInfo) => { bp[t.position] = t; });
      setByPos(bp);
      // Restore saved predictions
      if (data.my_prediction) {
        const mp = data.my_prediction;
        const findTeam = (id: string) =>
          (data.teams || []).find((t: TeamInfo) => t.id === id) ?? null;
        setPicks({
          qL1: findTeam(mp.cuartos_picks?.[0]),
          qL2: findTeam(mp.cuartos_picks?.[1]),
          qR1: findTeam(mp.cuartos_picks?.[2]),
          qR2: findTeam(mp.cuartos_picks?.[3]),
          sfL: findTeam(mp.semis_picks?.[0]),
          sfR: findTeam(mp.semis_picks?.[1]),
          champion: findTeam(mp.champion),
        });
      }
    }).catch(() => {
      Alert.alert('Error', 'No se pudo cargar el bracket');
    }).finally(() => setLoading(false));
  }, []);

  const pickQ = useCallback((key: keyof BracketPicks, team: TeamInfo | null) => {
    if (!team) return;
    setPicks(prev => {
      const next: BracketPicks = { ...prev, [key]: team };
      // Reset SF/Final si el cuarto cambia
      if (key === 'qL1' || key === 'qL2') {
        if (next.sfL && next.sfL.id !== next.qL1?.id && next.sfL.id !== next.qL2?.id)
          next.sfL = null;
      }
      if (key === 'qR1' || key === 'qR2') {
        if (next.sfR && next.sfR.id !== next.qR1?.id && next.sfR.id !== next.qR2?.id)
          next.sfR = null;
      }
      // Reset campeón si semi cambia
      if (next.champion && next.champion.id !== next.sfL?.id && next.champion.id !== next.sfR?.id)
        next.champion = null;
      return next;
    });
  }, []);

  const pickSF = useCallback((side: 'sfL' | 'sfR', team: TeamInfo | null) => {
    if (!team) return;
    setPicks(prev => {
      const next = { ...prev, [side]: team };
      if (next.champion && next.champion.id !== next.sfL?.id && next.champion.id !== next.sfR?.id)
        next.champion = null;
      return next;
    });
  }, []);

  const pickChampion = useCallback((team: TeamInfo | null) => {
    if (!team) return;
    setPicks(prev => ({ ...prev, champion: team }));
  }, []);

  const saveBracket = async () => {
    if (!picks.champion) return;
    setSaving(true);
    try {
      await api.post('/api/liguilla/bracket/submit', {
        cuartos_picks: [picks.qL1?.id, picks.qL2?.id, picks.qR1?.id, picks.qR2?.id].filter(Boolean),
        semis_picks:   [picks.sfL?.id, picks.sfR?.id].filter(Boolean),
        champion:      picks.champion?.id,
      });
      Alert.alert('✅ Bracket guardado', `Tu campeón: ${picks.champion.name}`);
    } catch {
      Alert.alert('Error', 'No se pudo guardar el bracket');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={s.container}>
        <ActivityIndicator color="#E63946" size="large" style={{ flex: 1 }} />
      </SafeAreaView>
    );
  }

  const isProvisional = bracketData?.is_provisional;

  return (
    <SafeAreaView style={s.container}>
      <StatusBar barStyle="light-content" />

      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={{ top:8,bottom:8,left:8,right:8 }}>
          <Ionicons name="arrow-back" size={24} color="#FFF" />
        </TouchableOpacity>
        <View style={{ alignItems: 'center', flex: 1 }}>
          <Text style={s.headerTitle}>🏆 LIGUILLA CLAUSURA 2026</Text>
          {SPONSORS.oro.torneo?.activo && (
            <Text style={s.sponsorSub}>Presentada por {SPONSORS.oro.torneo.marca}</Text>
          )}
        </View>
        <View style={{ width: 32 }} />
      </View>

      {isProvisional && (
        <View style={s.provBanner}>
          <Text style={s.provText}>⚠️  Tabla provisional — actualiza al terminar J17</Text>
        </View>
      )}

      {/* Scoring */}
      <View style={s.scoringRow}>
        <Text style={s.scoringItem}>Cuartos: <Text style={s.pts}>5 pts</Text></Text>
        <Text style={s.scoringItem}>Semis: <Text style={s.pts}>10 pts</Text></Text>
        <Text style={s.scoringItem}>Campeón: <Text style={s.pts}>25 pts</Text></Text>
      </View>

      {/* Bracket — horizontal scroll */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={s.bracketContent}
        style={{ flex: 1 }}
      >
        {/* ── LADO IZQUIERDO (cuartos) ── */}
        <View style={s.sideCol}>
          <Text style={s.roundLabel}>CUARTOS</Text>
          <MatchCard
            label={`1° vs 8°`}
            homeTeam={byPos[1]} awayTeam={byPos[8]}
            winner={picks.qL1}
            onPickHome={() => pickQ('qL1', byPos[1])}
            onPickAway={() => pickQ('qL1', byPos[8])}
          />
          <View style={{ height: 20 }} />
          <MatchCard
            label={`4° vs 5°`}
            homeTeam={byPos[4]} awayTeam={byPos[5]}
            winner={picks.qL2}
            onPickHome={() => pickQ('qL2', byPos[4])}
            onPickAway={() => pickQ('qL2', byPos[5])}
          />
        </View>

        {/* ── CONECTOR L ── */}
        <View style={s.connCol}>
          <View style={s.connLine} />
          <View style={mc.card}>
            <Text style={mc.label}>SEMI IZQ</Text>
            <TeamSlot
              team={picks.sfL}
              isWinner={!!picks.champion && picks.champion.id === picks.sfL?.id}
              onPress={() => {}} disabled={true}
            />
            <View style={mc.vsRow}>
              <View style={mc.vsLine} />
              <Text style={mc.vsText}>vs</Text>
              <View style={mc.vsLine} />
            </View>
            <TeamSlot
              team={picks.sfL ? null : (picks.qL1 && picks.qL2 ? picks.qL2 : null)}
              isWinner={false}
              onPress={() => {}} disabled={true}
            />
          </View>
          <View style={s.connLine} />
        </View>

        {/* ── CENTRO (semis + final) ── */}
        <View style={s.centerCol}>
          <Text style={s.roundLabel}>SEMIFINAL</Text>
          <MatchCard
            label="SF Izquierda"
            homeTeam={picks.qL1}
            awayTeam={picks.qL2}
            winner={picks.sfL}
            onPickHome={() => pickSF('sfL', picks.qL1)}
            onPickAway={() => pickSF('sfL', picks.qL2)}
          />
          <View style={s.trophyCenter}>
            <Text style={s.trophyEmoji}>🏆</Text>
            <Text style={s.finalLabel}>FINAL</Text>
          </View>
          <MatchCard
            label="SF Derecha"
            homeTeam={picks.qR1}
            awayTeam={picks.qR2}
            winner={picks.sfR}
            onPickHome={() => pickSF('sfR', picks.qR1)}
            onPickAway={() => pickSF('sfR', picks.qR2)}
          />

          {/* Final match */}
          <View style={{ marginTop: 12 }}>
            <MatchCard
              label="🏆 CAMPEÓN"
              homeTeam={picks.sfL}
              awayTeam={picks.sfR}
              winner={picks.champion}
              onPickHome={() => pickChampion(picks.sfL)}
              onPickAway={() => pickChampion(picks.sfR)}
            />
          </View>
        </View>

        {/* ── CONECTOR R ── */}
        <View style={s.connCol}>
          <View style={s.connLine} />
          <View style={mc.card}>
            <Text style={mc.label}>SEMI DER</Text>
            <TeamSlot
              team={picks.sfR}
              isWinner={!!picks.champion && picks.champion.id === picks.sfR?.id}
              onPress={() => {}} disabled={true}
            />
            <View style={mc.vsRow}>
              <View style={mc.vsLine} />
              <Text style={mc.vsText}>vs</Text>
              <View style={mc.vsLine} />
            </View>
            <TeamSlot
              team={null}
              isWinner={false}
              onPress={() => {}} disabled={true}
            />
          </View>
          <View style={s.connLine} />
        </View>

        {/* ── LADO DERECHO (cuartos) ── */}
        <View style={s.sideCol}>
          <Text style={s.roundLabel}>CUARTOS</Text>
          <MatchCard
            label={`2° vs 7°`}
            homeTeam={byPos[2]} awayTeam={byPos[7]}
            winner={picks.qR1}
            onPickHome={() => pickQ('qR1', byPos[2])}
            onPickAway={() => pickQ('qR1', byPos[7])}
          />
          <View style={{ height: 20 }} />
          <MatchCard
            label={`3° vs 6°`}
            homeTeam={byPos[3]} awayTeam={byPos[6]}
            winner={picks.qR2}
            onPickHome={() => pickQ('qR2', byPos[3])}
            onPickAway={() => pickQ('qR2', byPos[6])}
          />
        </View>
      </ScrollView>

      {/* Submit button */}
      {picks.champion && (
        <View style={s.submitBar}>
          <TouchableOpacity
            style={s.submitBtn}
            onPress={saveBracket}
            disabled={saving}
            activeOpacity={0.8}
          >
            {saving
              ? <ActivityIndicator color="#FFF" />
              : <Text style={s.submitText}>GUARDAR MI BRACKET</Text>}
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

// ── Styles ───────────────────────────────────────────────
const s = StyleSheet.create({
  container:    { flex: 1, backgroundColor: '#090909' },
  header:       { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#1A1A1A' },
  headerTitle:  { color: '#FFF', fontSize: 14, fontWeight: '800', letterSpacing: 0.5, textAlign: 'center' },
  sponsorSub:   { color: '#888', fontSize: 11, marginTop: 2 },
  provBanner:   { backgroundColor: '#1A1200', paddingVertical: 6, paddingHorizontal: 16, borderBottomWidth: 1, borderBottomColor: '#3A2E00' },
  provText:     { color: '#FFC300', fontSize: 11, textAlign: 'center' },
  scoringRow:   { flexDirection: 'row', justifyContent: 'space-around', paddingVertical: 8, backgroundColor: '#111', borderBottomWidth: 1, borderBottomColor: '#1A1A1A' },
  scoringItem:  { color: '#888', fontSize: 11 },
  pts:          { color: '#E63946', fontWeight: '700' },
  bracketContent: { paddingHorizontal: 12, paddingVertical: 16, alignItems: 'flex-start' },
  sideCol:      { width: 150, marginHorizontal: 6 },
  connCol:      { width: 10, alignItems: 'center', marginHorizontal: 2, justifyContent: 'center' },
  connLine:     { flex: 1, width: 2, backgroundColor: '#E6394655' },
  centerCol:    { width: 160, marginHorizontal: 6 },
  roundLabel:   { color: '#E63946', fontSize: 10, fontWeight: '800', letterSpacing: 1, textAlign: 'center', marginBottom: 8 },
  trophyCenter: { alignItems: 'center', paddingVertical: 12 },
  trophyEmoji:  { fontSize: 32 },
  finalLabel:   { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 2, marginTop: 4 },
  submitBar:    { paddingHorizontal: 16, paddingBottom: 16, paddingTop: 8, backgroundColor: '#090909', borderTopWidth: 1, borderTopColor: '#1A1A1A' },
  submitBtn:    { backgroundColor: '#E63946', borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  submitText:   { color: '#FFF', fontSize: 15, fontWeight: '800', letterSpacing: 1 },
});

const mc = StyleSheet.create({
  card:   { backgroundColor: '#111', borderRadius: 10, borderWidth: 1, borderColor: '#1E1E1E', overflow: 'hidden' },
  label:  { color: '#555', fontSize: 9, fontWeight: '700', letterSpacing: 0.8, textAlign: 'center', paddingVertical: 4, backgroundColor: '#0A0A0A' },
  vsRow:  { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8 },
  vsLine: { flex: 1, height: 1, backgroundColor: '#1E1E1E' },
  vsText: { color: '#333', fontSize: 9, fontWeight: '700', marginHorizontal: 6 },
});

const ts = StyleSheet.create({
  slot:       { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 8, gap: 8 },
  slotWinner: { backgroundColor: '#E6394618' },
  slotEmpty:  { backgroundColor: '#0D0D0D', justifyContent: 'center' },
  shield:     { width: 28, height: 28, borderRadius: 4 },
  name:       { color: '#AAA', fontSize: 12, fontWeight: '600', flex: 1 },
  nameWinner: { color: '#FFF', fontWeight: '800' },
  check:      { color: '#E63946', fontSize: 14, fontWeight: '900' },
  emptyText:  { color: '#333', fontSize: 18, flex: 1, textAlign: 'center' },
});
