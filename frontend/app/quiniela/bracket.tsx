import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  Image, StatusBar, ActivityIndicator, Alert, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { captureRef } from 'react-native-view-shot';
import * as Sharing from 'expo-sharing';
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
        <Text style={ts.emptyText}> </Text>
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
  const [sharing, setSharing] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [bracketData, setBracketData] = useState<any>(null);
  const [picks, setPicks] = useState<BracketPicks>(EMPTY);
  const [byPos, setByPos] = useState<Record<number, TeamInfo>>({});
  const shareCardRef = useRef<View>(null);

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
        setSaved(true); // Ya tenía predicción guardada
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
    setSaveError('');
    setSaving(true);
    try {
      await api.post('/api/liguilla/bracket/submit', {
        cuartos_picks: [picks.qL1?.id, picks.qL2?.id, picks.qR1?.id, picks.qR2?.id].filter(Boolean),
        semis_picks:   [picks.sfL?.id, picks.sfR?.id].filter(Boolean),
        champion:      picks.champion?.id,
      });
      setSaved(true);
    } catch {
      setSaveError('No se pudo guardar el bracket. Intenta de nuevo.');
    } finally {
      setSaving(false);
    }
  };

  const handleShare = async () => {
    if (!picks.champion) return;
    setSharing(true);
    try {
      const uri = await captureRef(shareCardRef, {
        format: 'png',
        quality: 0.92,
        result: 'tmpfile',
      });
      const shareText =
        `Mi bracket del Clausura 2026 🏆\nMi campeón: ${picks.champion.name}\n¿Quién ganará? Haz tu predicción en FuchoMX\n#FuchoMX #LigaMX #Clausura2026`;

      const isAvailable = await Sharing.isAvailableAsync();
      if (isAvailable) {
        await Sharing.shareAsync(uri, {
          mimeType: 'image/png',
          dialogTitle: 'Mi Bracket del Clausura 2026',
          UTI: 'public.png',
        });
      } else {
        // Web fallback: show the text to copy
        Alert.alert(
          '📤 Tu bracket',
          shareText,
          [{ text: 'OK' }]
        );
      }
    } catch (e) {
      Alert.alert('Error', 'No se pudo generar la imagen del bracket. Intenta de nuevo.');
    } finally {
      setSharing(false);
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

      {/* Submit / Share bar */}
      {picks.champion && (
        <View style={s.submitBar}>
          {saved && (
            <Text style={s.savedText}>✓ Bracket guardado — ¡comparte tu predicción!</Text>
          )}
          {saveError ? <Text style={s.saveErrorText}>{saveError}</Text> : null}

          {/* Save button — always visible when champion is picked */}
          <TouchableOpacity
            style={s.submitBtn}
            onPress={saveBracket}
            disabled={saving}
            activeOpacity={0.8}
          >
            {saving
              ? <ActivityIndicator color="#FFF" />
              : <Text style={s.submitText}>{saved ? 'ACTUALIZAR BRACKET' : 'GUARDAR MI BRACKET'}</Text>}
          </TouchableOpacity>

          {/* Share button — visible after saving */}
          {saved && (
            <TouchableOpacity
              style={s.shareBtn}
              onPress={handleShare}
              disabled={sharing}
              activeOpacity={0.8}
            >
              {sharing
                ? <ActivityIndicator color="#E63946" size="small" />
                : <Text style={s.shareText}>📤 Compartir mi bracket</Text>}
            </TouchableOpacity>
          )}
        </View>
      )}

      {/* Off-screen share card (for captureRef) */}
      {picks.champion && (
        <View
          ref={shareCardRef}
          collapsable={false}
          style={sc.cardWrapper}
        >
          {/* Header */}
          <View style={sc.header}>
            <Text style={sc.headerEmoji}>🏆</Text>
            <Text style={sc.headerTitle}>LIGUILLA CLAUSURA 2026</Text>
            <Text style={sc.headerSub}>FuchoMX</Text>
          </View>

          {/* Cuartos de Final */}
          <Text style={sc.sectionLabel}>CUARTOS DE FINAL</Text>
          <View style={sc.cuartosGrid}>
            {[
              { pos: 1, match: '1° vs 8°', pick: picks.qL1 },
              { pos: 2, match: '4° vs 5°', pick: picks.qL2 },
              { pos: 3, match: '2° vs 7°', pick: picks.qR1 },
              { pos: 4, match: '3° vs 6°', pick: picks.qR2 },
            ].map(({ pos, match, pick }) => (
              <View key={pos} style={sc.cuartoRow}>
                <Text style={sc.matchLabel}>{match}</Text>
                <View style={[sc.pickRow, !!pick && sc.pickRowActive]}>
                  {pick?.shield_url
                    ? <Image source={{ uri: pick.shield_url }} style={sc.shield} />
                    : <View style={sc.shieldPlaceholder} />
                  }
                  <Text style={[sc.pickName, !!pick && sc.pickNameActive]}>
                    {pick ? pick.short_name : '?'}
                  </Text>
                  {pick && <Text style={sc.checkmark}>✓</Text>}
                </View>
              </View>
            ))}
          </View>

          {/* Semis */}
          <Text style={sc.sectionLabel}>SEMIFINALES</Text>
          <View style={sc.semisRow}>
            {[picks.sfL, picks.sfR].map((team, i) => (
              <View key={i} style={[sc.semiCard, !!team && sc.semiCardActive]}>
                {team?.shield_url
                  ? <Image source={{ uri: team.shield_url }} style={sc.semiShield} />
                  : <View style={sc.semiShieldPh} />
                }
                <Text style={[sc.semiName, !!team && sc.semiNameActive]}>
                  {team ? team.short_name : '?'}
                </Text>
              </View>
            ))}
          </View>

          {/* Campeón */}
          <View style={sc.champSection}>
            <Text style={sc.champLabel}>🏆 MI CAMPEÓN</Text>
            <View style={sc.champCard}>
              {picks.champion?.shield_url
                ? <Image source={{ uri: picks.champion.shield_url }} style={sc.champShield} />
                : null
              }
              <Text style={sc.champName}>{picks.champion?.name ?? '?'}</Text>
            </View>
          </View>

          {/* Footer */}
          <Text style={sc.footer}>fucho.com.mx  •  #FuchoMX #LigaMX #Clausura2026</Text>
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
  submitBar:    { paddingHorizontal: 16, paddingBottom: 16, paddingTop: 8, backgroundColor: '#090909', borderTopWidth: 1, borderTopColor: '#1A1A1A', gap: 10 },
  submitBtn:    { backgroundColor: '#E63946', borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  submitText:   { color: '#FFF', fontSize: 15, fontWeight: '800', letterSpacing: 1 },
  shareBtn:     { backgroundColor: '#111', borderRadius: 12, paddingVertical: 13, alignItems: 'center', borderWidth: 1, borderColor: '#E63946' },
  shareText:    { color: '#E63946', fontSize: 15, fontWeight: '700', letterSpacing: 0.5 },
  savedText:    { color: '#00A551', fontSize: 13, fontWeight: '600', textAlign: 'center' },
  saveErrorText: { color: '#E63946', fontSize: 13, textAlign: 'center' },
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

// ── Share Card Styles (off-screen capture target) ─────────────────────────
const sc = StyleSheet.create({
  cardWrapper: {
    position: 'absolute',
    top: -2000,          // Off-screen but rendered
    left: 0,
    width: 360,
    backgroundColor: '#090909',
    paddingBottom: 20,
  },
  header: {
    backgroundColor: '#E63946',
    paddingVertical: 16,
    paddingHorizontal: 20,
    alignItems: 'center',
  },
  headerEmoji:  { fontSize: 32, marginBottom: 4 },
  headerTitle:  { color: '#FFF', fontSize: 17, fontWeight: '900', letterSpacing: 1 },
  headerSub:    { color: 'rgba(255,255,255,0.8)', fontSize: 12, fontWeight: '600', marginTop: 2 },
  sectionLabel: { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 1.2, textAlign: 'center', paddingTop: 14, paddingBottom: 6 },
  cuartosGrid:  { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: 12, gap: 8 },
  cuartoRow:    { width: '47%', backgroundColor: '#111', borderRadius: 8, padding: 8 },
  matchLabel:   { color: '#555', fontSize: 10, fontWeight: '600', marginBottom: 4 },
  pickRow:      { flexDirection: 'row', alignItems: 'center', gap: 6 },
  pickRowActive: { backgroundColor: '#E6394614', borderRadius: 4, paddingHorizontal: 4 },
  shield:       { width: 22, height: 22, borderRadius: 3 },
  shieldPlaceholder: { width: 22, height: 22, borderRadius: 3, backgroundColor: '#222' },
  pickName:     { color: '#666', fontSize: 12, fontWeight: '600', flex: 1 },
  pickNameActive: { color: '#FFF', fontWeight: '800' },
  checkmark:    { color: '#E63946', fontSize: 13, fontWeight: '900' },
  semisRow:     { flexDirection: 'row', justifyContent: 'center', gap: 16, paddingHorizontal: 20 },
  semiCard:     { flex: 1, backgroundColor: '#111', borderRadius: 10, padding: 10, alignItems: 'center', gap: 6 },
  semiCardActive: { borderWidth: 1, borderColor: '#E63946' },
  semiShield:   { width: 36, height: 36, borderRadius: 6 },
  semiShieldPh: { width: 36, height: 36, borderRadius: 6, backgroundColor: '#222' },
  semiName:     { color: '#555', fontSize: 13, fontWeight: '700' },
  semiNameActive: { color: '#FFF' },
  champSection: { alignItems: 'center', paddingHorizontal: 40, paddingTop: 8 },
  champLabel:   { color: '#FFC300', fontSize: 13, fontWeight: '800', letterSpacing: 0.5, marginBottom: 8 },
  champCard:    { backgroundColor: '#E63946', borderRadius: 12, padding: 14, alignItems: 'center', width: '100%', gap: 8 },
  champShield:  { width: 52, height: 52, borderRadius: 8 },
  champName:    { color: '#FFF', fontSize: 16, fontWeight: '900', letterSpacing: 0.5 },
  footer:       { color: '#333', fontSize: 11, textAlign: 'center', paddingTop: 14, paddingHorizontal: 12 },
});
