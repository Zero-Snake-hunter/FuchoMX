import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';

// ── Types ──────────────────────────────────────────────────────────────────
interface BreakdownItem {
  label: string;
  points: number;
}
interface PlayerResult {
  player_id: string;
  player_name: string;
  position: string;
  position_slot: string;
  points: number;
  breakdown: Record<string, BreakdownItem>;
  is_mvp: boolean;
  minutes: number;
  goals: number;
  assists: number;
  team_shield: string;
  team_name: string;
}
interface ResultsData {
  has_lineup: boolean;
  team_name: string;
  total_points: number;
  players: PlayerResult[];
  processed: boolean;
}

// ── Constants ──────────────────────────────────────────────────────────────
const POS_COLOR: Record<string, string> = {
  POR: '#FFC107',
  DEF: '#4CAF50',
  MED: '#2196F3',
  DEL: '#E63946',
};
const POS_LABEL: Record<string, string> = {
  POR: 'POR',
  DEF: 'DEF',
  MED: 'MED',
  DEL: 'DEL',
};
const BREAKDOWN_EMOJI: Record<string, string> = {
  minutes: '⏱',
  goals: '⚽',
  assists: '🎯',
  yellow_cards: '🟨',
  red_cards: '🟥',
  saves: '🧤',
  clean_sheet: '🛡',
  own_goals: '😬',
  penalty_saved: '🦸',
  penalty_missed: '❌',
  mvp: '🏆',
  doblete: '🔥',
  hat_trick: '🎩',
};

// ── Player Card ────────────────────────────────────────────────────────────
function PlayerCard({ player }: { player: PlayerResult }) {
  const [expanded, setExpanded] = useState(false);
  const posColor = POS_COLOR[player.position] ?? '#888';
  const hasBonus = player.points >= 8;

  return (
    <TouchableOpacity
      style={[s.card, hasBonus && s.cardBonus]}
      onPress={() => setExpanded(e => !e)}
      activeOpacity={0.85}
    >
      {/* Header row */}
      <View style={s.cardHeader}>
        {/* Shield + name */}
        <View style={s.playerLeft}>
          {player.team_shield ? (
            <Image source={{ uri: player.team_shield }} style={s.shield} />
          ) : (
            <View style={[s.shieldPh, { backgroundColor: posColor + '40' }]} />
          )}
          <View style={s.nameSide}>
            <View style={s.nameLine}>
              <Text style={s.playerName} numberOfLines={1}>
                {player.player_name}
              </Text>
              {player.is_mvp && (
                <Text style={s.mvpBadge}>⭐ MVP</Text>
              )}
            </View>
            <View style={s.tagRow}>
              <View style={[s.posBadge, { backgroundColor: posColor + '22', borderColor: posColor }]}>
                <Text style={[s.posBadgeText, { color: posColor }]}>
                  {POS_LABEL[player.position] ?? player.position}
                </Text>
              </View>
              <Text style={s.teamName}>{player.team_name}</Text>
            </View>
          </View>
        </View>

        {/* Points + chevron */}
        <View style={s.ptsSide}>
          <Text style={[s.ptsNum, player.points >= 10 && s.ptsHigh]}>
            {player.points}
          </Text>
          <Text style={s.ptsSub}>pts</Text>
          <Ionicons
            name={expanded ? 'chevron-up' : 'chevron-down'}
            size={14}
            color="#555"
            style={{ marginTop: 2 }}
          />
        </View>
      </View>

      {/* Breakdown (collapsible) */}
      {expanded && (
        <View style={s.breakdown}>
          {Object.entries(player.breakdown).map(([key, item]) => {
            if (!item || item.points === 0) return null;
            const emoji = BREAKDOWN_EMOJI[key] ?? '•';
            const positive = item.points > 0;
            return (
              <View key={key} style={s.bRow}>
                <Text style={s.bEmoji}>{emoji}</Text>
                <Text style={s.bLabel}>{item.label}</Text>
                <Text style={[s.bPoints, positive ? s.bPos : s.bNeg]}>
                  {positive ? '+' : ''}{item.points}
                </Text>
              </View>
            );
          })}
        </View>
      )}
    </TouchableOpacity>
  );
}

// ── Main Screen ────────────────────────────────────────────────────────────
export default function FantasyResultsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ jornada_id?: string }>();
  const [data, setData] = useState<ResultsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [jornadaId, setJornadaId] = useState<string | null>(params.jornada_id ?? null);

  useEffect(() => {
    const load = async () => {
      try {
        let jid = jornadaId;
        if (!jid) {
          const curr = await api.get('/api/jornadas/current');
          jid = curr.data?.jornada?.id;
          setJornadaId(jid ?? null);
        }
        if (!jid) return;
        const res = await api.get(`/api/fantasy/results/${jid}`);
        setData(res.data);
      } catch {
        setData({ has_lineup: false, team_name: '', total_points: 0, players: [], processed: false });
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [jornadaId]);

  const grouped: Record<string, PlayerResult[]> = {};
  (data?.players ?? []).forEach(p => {
    grouped[p.position] = [...(grouped[p.position] ?? []), p];
  });
  const ORDER = ['POR', 'DEF', 'MED', 'DEL'];

  return (
    <SafeAreaView style={s.safe} edges={['top', 'bottom']}>
      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="arrow-back" size={24} color="#FFF" />
        </TouchableOpacity>
        <Text style={s.headerTitle}>RESULTADOS ONCEMX</Text>
        <View style={{ width: 24 }} />
      </View>

      {loading ? (
        <View style={s.center}>
          <ActivityIndicator size="large" color="#E63946" />
          <Text style={s.loadingText}>Calculando puntos...</Text>
        </View>
      ) : !data?.has_lineup ? (
        <View style={s.center}>
          <Text style={s.emptyEmoji}>📋</Text>
          <Text style={s.emptyTitle}>Sin alineación</Text>
          <Text style={s.emptyMsg}>
            {data?.processed
              ? 'No enviaste alineación para esta jornada.'
              : 'Los resultados estarán disponibles cuando termine la jornada.'}
          </Text>
          <TouchableOpacity style={s.backBtn} onPress={() => router.back()}>
            <Text style={s.backBtnText}>← Volver</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={s.scroll}
          showsVerticalScrollIndicator={false}
        >
          {/* Total banner */}
          <View style={s.totalBanner}>
            <View>
              <Text style={s.bannerTeam}>{data.team_name ?? 'Mi Equipo'}</Text>
              <Text style={s.bannerSub}>Jornada completa</Text>
            </View>
            <View style={s.bannerPts}>
              <Text style={s.bannerNum}>{data.total_points}</Text>
              <Text style={s.bannerPtsSub}>PUNTOS</Text>
            </View>
          </View>

          {/* Status badge */}
          {!data.processed && (
            <View style={s.pendingBadge}>
              <Ionicons name="time-outline" size={14} color="#FFC107" />
              <Text style={s.pendingText}> Jornada en curso — puntos provisionales</Text>
            </View>
          )}

          {/* Players by position */}
          {ORDER.filter(pos => grouped[pos]?.length > 0).map(pos => (
            <View key={pos} style={s.section}>
              <View style={[s.sectionHeader, { borderLeftColor: POS_COLOR[pos] }]}>
                <Text style={[s.sectionTitle, { color: POS_COLOR[pos] }]}>
                  {POS_LABEL[pos]}
                </Text>
                <Text style={s.sectionCount}>
                  {grouped[pos].length} jugador{grouped[pos].length !== 1 ? 'es' : ''}
                </Text>
              </View>
              {grouped[pos].map(p => (
                <PlayerCard key={p.player_id} player={p} />
              ))}
            </View>
          ))}

          <View style={{ height: 32 }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────
const s = StyleSheet.create({
  safe:         { flex: 1, backgroundColor: '#090909' },
  header:       { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#1A1A1A' },
  headerTitle:  { color: '#FFF', fontSize: 15, fontWeight: '800', letterSpacing: 1 },
  center:       { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  loadingText:  { color: '#555', marginTop: 12, fontSize: 14 },
  emptyEmoji:   { fontSize: 48, marginBottom: 12 },
  emptyTitle:   { color: '#FFF', fontSize: 18, fontWeight: '700', marginBottom: 8 },
  emptyMsg:     { color: '#666', fontSize: 14, textAlign: 'center', lineHeight: 20 },
  backBtn:      { marginTop: 20, backgroundColor: '#111', borderRadius: 10, paddingHorizontal: 20, paddingVertical: 10, borderWidth: 1, borderColor: '#E63946' },
  backBtnText:  { color: '#E63946', fontWeight: '700' },
  scroll:       { padding: 16, gap: 8 },
  totalBanner:  { backgroundColor: '#E63946', borderRadius: 14, padding: 18, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  bannerTeam:   { color: '#FFF', fontSize: 16, fontWeight: '800' },
  bannerSub:    { color: 'rgba(255,255,255,0.75)', fontSize: 12, marginTop: 2 },
  bannerPts:    { alignItems: 'flex-end' },
  bannerNum:    { color: '#FFF', fontSize: 40, fontWeight: '900', lineHeight: 44 },
  bannerPtsSub: { color: 'rgba(255,255,255,0.75)', fontSize: 10, fontWeight: '700', letterSpacing: 1.2 },
  pendingBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1A1500', borderRadius: 8, padding: 8, marginBottom: 8, borderWidth: 1, borderColor: '#FFC10740' },
  pendingText:  { color: '#FFC107', fontSize: 12, fontWeight: '600' },
  section:      { gap: 6 },
  sectionHeader:{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingLeft: 10, borderLeftWidth: 3, marginBottom: 2 },
  sectionTitle: { fontSize: 12, fontWeight: '900', letterSpacing: 1.5 },
  sectionCount: { color: '#555', fontSize: 11 },
  card:         { backgroundColor: '#111', borderRadius: 12, padding: 12, borderWidth: 1, borderColor: '#1E1E1E' },
  cardBonus:    { borderColor: '#E63946' + '50' },
  cardHeader:   { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  playerLeft:   { flexDirection: 'row', alignItems: 'center', flex: 1, gap: 10 },
  shield:       { width: 32, height: 32, borderRadius: 6 },
  shieldPh:     { width: 32, height: 32, borderRadius: 6 },
  nameSide:     { flex: 1, gap: 3 },
  nameLine:     { flexDirection: 'row', alignItems: 'center', gap: 6 },
  playerName:   { color: '#FFF', fontSize: 13, fontWeight: '700', flex: 1 },
  mvpBadge:     { backgroundColor: '#FFD70022', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2 },
  tagRow:       { flexDirection: 'row', alignItems: 'center', gap: 6 },
  posBadge:     { borderRadius: 4, paddingHorizontal: 5, paddingVertical: 1, borderWidth: 1 },
  posBadgeText: { fontSize: 10, fontWeight: '700', letterSpacing: 0.5 },
  teamName:     { color: '#555', fontSize: 11 },
  ptsSide:      { alignItems: 'center', minWidth: 40 },
  ptsNum:       { color: '#FFF', fontSize: 22, fontWeight: '900' },
  ptsHigh:      { color: '#E63946' },
  ptsSub:       { color: '#555', fontSize: 10, fontWeight: '600', letterSpacing: 0.5 },
  breakdown:    { marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: '#1E1E1E', gap: 5 },
  bRow:         { flexDirection: 'row', alignItems: 'center', gap: 8 },
  bEmoji:       { fontSize: 14, width: 20, textAlign: 'center' },
  bLabel:       { color: '#AAA', fontSize: 12, flex: 1 },
  bPoints:      { fontSize: 12, fontWeight: '700', minWidth: 32, textAlign: 'right' },
  bPos:         { color: '#4CAF50' },
  bNeg:         { color: '#E63946' },
});
