// Archivo: /app/frontend/app/profile/achievements.tsx

import React, { useEffect, useState, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet,
  TouchableOpacity, ActivityIndicator,
  Animated, Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import api from '../lib/api';
import { SPONSORS } from '../config/sponsors';
import ShareResultCard, { ShareResultData } from '../components/ShareResultCard';

const { width } = Dimensions.get('window');

// ─── Tipos ───────────────────────────────────────────────
interface Achievement {
  id: string; title: string; description: string;
  emoji: string; category: string; secret: boolean;
  unlocked: boolean; unlocked_at: string | null;
}
interface Streaks {
  quiniela_current: number; quiniela_best: number;
  win_current: number;      win_best: number;
  correct_current: number;  correct_best: number;
  fantasy_current: number;
}

// ─── Colores ─────────────────────────────────────────────
const CAT_COLOR: Record<string, string> = {
  quiniela: '#E63946', fantasy: '#1D88E5',
  social:   '#2A9D8F', general: '#F4A261',
};
const CAT_LABEL: Record<string, string> = {
  quiniela: 'Quiniela', fantasy: 'FuchoOnce',
  social: 'Social',     general: 'General',
};

// ─── Componente: una tarjeta de logro ────────────────────
const BadgeCard = ({
  item, index, onShare,
}: {
  item: Achievement; index: number; onShare: (a: Achievement) => void;
}) => {
  const fade  = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0.85)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fade,  { toValue: 1, duration: 280, delay: index * 35, useNativeDriver: true }),
      Animated.spring(scale, { toValue: 1, tension: 80, friction: 9, delay: index * 35, useNativeDriver: true }),
    ]).start();
  }, []);

  const color = CAT_COLOR[item.category] || '#666';

  return (
    <Animated.View style={{ opacity: fade, transform: [{ scale }], marginBottom: 10 }}>
      <View style={[s.card, { borderColor: item.unlocked ? color : '#222' }, !item.unlocked && s.cardLocked]}>

        {/* Línea superior de color */}
        {item.unlocked && <View style={[s.cardTopBar, { backgroundColor: color }]} />}

        <View style={s.cardInner}>
          {/* Ícono */}
          <View style={[s.iconCircle, { backgroundColor: item.unlocked ? `${color}22` : '#1A1A1A' }]}>
            <Text style={[s.iconEmoji, !item.unlocked && { opacity: 0.3 }]}>{item.emoji}</Text>
          </View>

          {/* Texto */}
          <View style={s.cardText}>
            <Text style={[s.cardTitle, !item.unlocked && { color: '#444' }]}>{item.title}</Text>
            <Text style={[s.cardDesc,  !item.unlocked && { color: '#333' }]} numberOfLines={2}>
              {item.description}
            </Text>
            {item.unlocked && item.unlocked_at ? (
              <Text style={[s.cardDate, { color: color }]}>
                ✓ {new Date(item.unlocked_at).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })}
              </Text>
            ) : (
              <Text style={s.cardPending}>Por desbloquear</Text>
            )}
          </View>

          {/* Derecha: chip + compartir */}
          <View style={{ alignItems: 'flex-end', gap: 6 }}>
            <View style={[s.catChip, { backgroundColor: item.unlocked ? `${color}22` : '#181818' }]}>
              <Text style={[s.catText, { color: item.unlocked ? color : '#444' }]}>
                {CAT_LABEL[item.category]}
              </Text>
            </View>
            {item.unlocked && (
              <TouchableOpacity
                style={s.shareBtn}
                onPress={() => onShare(item)}
                activeOpacity={0.7}
              >
                <Text style={s.shareBtnTxt}>📤</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
      </View>
    </Animated.View>
  );
};

// ─── Componente: tarjeta de racha ────────────────────────
const StreakCard = ({
  emoji, label, current, best, color, milestone,
}: {
  emoji: string; label: string; current: number;
  best: number;  color: string; milestone: number;
}) => {
  const pct = milestone > 0 ? Math.min((current / milestone) * 100, 100) : 0;
  const dots = Math.min(milestone, 10);

  return (
    <View style={[sc.card, { borderColor: `${color}44` }]}>
      <Text style={sc.emoji}>{emoji}</Text>
      <Text style={[sc.number, { color }]}>{current}</Text>
      <Text style={sc.label}>{label}</Text>
      <Text style={sc.best}>Mejor: {best}</Text>

      {/* Barra */}
      <View style={sc.barBg}>
        <View style={[sc.barFill, { backgroundColor: color, width: `${pct}%` }]} />
      </View>

      {/* Puntos */}
      <View style={sc.dots}>
        {Array.from({ length: dots }).map((_, i) => (
          <View key={i} style={[sc.dot, {
            backgroundColor: i < current ? color : '#1E1E1E',
            borderColor:     i < current ? color : '#2A2A2A',
          }]} />
        ))}
      </View>

      {/* Próxima meta */}
      {current < milestone && (
        <Text style={sc.next}>
          {milestone - current} más para {
            milestone === 3 ? '🔥' : milestone === 5 ? '⚡' : '👑'
          }
        </Text>
      )}
    </View>
  );
};

// ─── Pantalla principal ──────────────────────────────────
export default function AchievementsScreen() {
  const router   = useRouter();
  const [data,   setData]   = useState<any>(null);
  const [loading,setLoading]= useState(true);
  const [filter, setFilter] = useState('all');
  const [shareAchievement, setShareAchievement] = useState<ShareResultData | null>(null);

  useEffect(() => { load(); }, []);

  const load = async () => {
    try {
      const res = await api.get('/api/achievements/my');
      setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleShareAchievement = (item: Achievement) => {
    setShareAchievement({
      mode: 'achievement',
      userName: 'Jugador FuchoMX',
      achievementTitle: item.title,
      achievementEmoji: item.emoji,
      achievementDesc: item.description,
    });
  };

  const achievements: Achievement[] = data?.achievements ?? [];
  const streaks: Streaks = data?.streaks ?? {} as Streaks;
  const unlockedCount = data?.unlocked_count ?? 0;
  const total         = data?.total ?? 0;
  const pct = total > 0 ? (unlockedCount / total) * 100 : 0;

  const FILTERS = [
    { key: 'all',      label: 'Todos' },
    { key: 'unlocked', label: '✅ Desbloqueados' },
    { key: 'quiniela', label: '📝 Quiniela' },
    { key: 'fantasy',  label: '⚽ Fantasy' },
    { key: 'social',   label: '🤝 Social' },
    { key: 'general',  label: '🎖️ General' },
  ];

  const filtered = achievements.filter(a => {
    if (filter === 'all')      return true;
    if (filter === 'unlocked') return a.unlocked;
    return a.category === filter;
  });

  if (loading) {
    return (
      <SafeAreaView style={s.container}>
        <ActivityIndicator size="large" color="#E63946" style={{ flex: 1, marginTop: 60 }} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={s.container}>
      {/* ShareResultCard overlay */}
      {shareAchievement && (
        <ShareResultCard
          data={shareAchievement}
          onClose={() => setShareAchievement(null)}
        />
      )}

      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
          <Text style={s.backTxt}>← Atrás</Text>
        </TouchableOpacity>
        <Text style={s.headerTitle}>Logros y Rachas</Text>
        <View style={{ width: 70 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 50 }}>

        {/* ── Progreso ──────────────────────────── */}
        <View style={s.progressBox}>
          <View style={s.progressRow}>
            <Text style={s.progressTitle}>Tu colección</Text>
            <Text style={s.progressCount}>{unlockedCount} / {total}</Text>
          </View>
          <View style={s.progressBg}>
            <Animated.View style={[s.progressFill, { width: `${pct}%` }]} />
          </View>
          <Text style={s.progressSub}>
            {pct >= 100 ? '🎉 ¡Colección completa! Eres leyenda'
             : pct >= 50 ? '¡Más de la mitad! Sigue así 💪'
             : 'Juega más para desbloquear logros 🎯'}
          </Text>
        </View>

        {/* ── Rachas ────────────────────────────── */}
        <Text style={s.sectionTitle}>🔥 Tus Rachas</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}>

          <StreakCard
            emoji="📅" label="Jornadas seguidas"
            current={streaks.quiniela_current} best={streaks.quiniela_best}
            color="#E63946" milestone={10}
          />
          <StreakCard
            emoji="🏆" label="Jornadas ganadas"
            current={streaks.win_current} best={streaks.win_best}
            color="#F4A261" milestone={5}
          />
          <StreakCard
            emoji="🎯" label="Predicciones correctas"
            current={streaks.correct_current} best={streaks.correct_best}
            color="#2A9D8F" milestone={10}
          />
          <StreakCard
            emoji="⚽" label="ONCE seguidas"
            current={streaks.fantasy_current} best={streaks.fantasy_current || 5}
            color="#1D88E5" milestone={5}
          />
        </ScrollView>

        {/* ── Logros ────────────────────────────── */}
        <Text style={[s.sectionTitle, { marginTop: 24 }]}>🏅 Logros</Text>

        {/* Sponsor logros (si activo) */}
        {(SPONSORS.oro.logros.activo || SPONSORS.bronce.logros.activo) && (
          <View style={{ paddingHorizontal: 16, marginBottom: 4 }}>
            <Text style={{ color: '#555', fontSize: 11, letterSpacing: 0.5 }}>
              PATROCINADO POR{' '}
              <Text style={{ color: '#FFD700', fontWeight: '700' }}>
                {SPONSORS.oro.logros.activo ? SPONSORS.oro.logros.marca : SPONSORS.bronce.logros.marca}
              </Text>
            </Text>
          </View>
        )}

        {/* Filtros */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: 16, gap: 8, marginBottom: 12 }}>
          {FILTERS.map(f => (
            <TouchableOpacity key={f.key}
              style={[s.chip, filter === f.key && s.chipActive]}
              onPress={() => setFilter(f.key)}>
              <Text style={[s.chipTxt, filter === f.key && s.chipTxtActive]}>{f.label}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Lista */}
        <View style={{ paddingHorizontal: 16 }}>
          {filtered.length === 0 ? (
            <View style={s.empty}>
              <Text style={{ fontSize: 40 }}>🔍</Text>
              <Text style={s.emptyTxt}>Sin logros en esta categoría aún</Text>
            </View>
          ) : (
            filtered.map((item, i) => <BadgeCard key={item.id} item={item} index={i} onShare={handleShareAchievement} />)
          )}
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

// ─── Estilos ─────────────────────────────────────────────
const s = StyleSheet.create({
  container:     { flex: 1, backgroundColor: '#0A0A0A' },
  header:        { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#181818' },
  backBtn:       { padding: 4 },
  backTxt:       { color: '#E63946', fontSize: 15 },
  headerTitle:   { color: '#FFF', fontSize: 18, fontWeight: '700' },

  progressBox:   { margin: 16, backgroundColor: '#111', borderRadius: 16, padding: 18, borderWidth: 1, borderColor: '#1E1E1E' },
  progressRow:   { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  progressTitle: { color: '#FFF', fontSize: 15, fontWeight: '600' },
  progressCount: { color: '#E63946', fontSize: 16, fontWeight: '800' },
  progressBg:    { height: 8, backgroundColor: '#1E1E1E', borderRadius: 4, overflow: 'hidden' },
  progressFill:  { height: '100%', backgroundColor: '#E63946', borderRadius: 4 },
  progressSub:   { color: '#555', fontSize: 12, marginTop: 8, textAlign: 'center' },

  sectionTitle:  { color: '#FFF', fontSize: 17, fontWeight: '700', paddingHorizontal: 16, marginBottom: 14 },

  card:          { backgroundColor: '#111', borderRadius: 14, borderWidth: 1.5, overflow: 'hidden' },
  cardLocked:    { opacity: 0.5 },
  cardTopBar:    { height: 3, width: '100%' },
  cardInner:     { flexDirection: 'row', alignItems: 'center', padding: 12, gap: 12 },
  iconCircle:    { width: 50, height: 50, borderRadius: 25, alignItems: 'center', justifyContent: 'center' },
  iconEmoji:     { fontSize: 24 },
  cardText:      { flex: 1 },
  cardTitle:     { color: '#FFF', fontSize: 14, fontWeight: '700' },
  cardDesc:      { color: '#888', fontSize: 12, marginTop: 2, lineHeight: 16 },
  cardDate:      { fontSize: 11, marginTop: 4, fontWeight: '600' },
  cardPending:   { color: '#444', fontSize: 11, marginTop: 4 },
  catChip:       { paddingHorizontal: 7, paddingVertical: 3, borderRadius: 6 },
  catText:       { fontSize: 10, fontWeight: '700' },
  shareBtn: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: '#DC143C22', borderWidth: 1, borderColor: '#DC143C55',
    alignItems: 'center', justifyContent: 'center',
  },
  shareBtnTxt: { fontSize: 14 },

  chip:          { paddingHorizontal: 14, paddingVertical: 7, backgroundColor: '#111', borderRadius: 20, borderWidth: 1, borderColor: '#222' },
  chipActive:    { backgroundColor: '#E63946', borderColor: '#E63946' },
  chipTxt:       { color: '#555', fontSize: 13, fontWeight: '500' },
  chipTxtActive: { color: '#FFF', fontWeight: '700' },

  empty:         { alignItems: 'center', paddingVertical: 40 },
  emptyTxt:      { color: '#444', fontSize: 14, marginTop: 10 },
});

const sc = StyleSheet.create({
  card:   { width: 140, backgroundColor: '#111', borderRadius: 14, padding: 14, alignItems: 'center', borderWidth: 1 },
  emoji:  { fontSize: 26, marginBottom: 4 },
  number: { fontSize: 34, fontWeight: '800' },
  label:  { color: '#666', fontSize: 10, textAlign: 'center', marginTop: 2 },
  best:   { color: '#444', fontSize: 10, marginTop: 2, marginBottom: 8 },
  barBg:  { width: '100%', height: 4, backgroundColor: '#1E1E1E', borderRadius: 2, overflow: 'hidden', marginBottom: 8 },
  barFill:{ height: '100%', borderRadius: 2 },
  dots:   { flexDirection: 'row', flexWrap: 'wrap', gap: 4, justifyContent: 'center', marginBottom: 6 },
  dot:    { width: 10, height: 10, borderRadius: 5, borderWidth: 1 },
  next:   { color: '#555', fontSize: 9, textAlign: 'center', marginTop: 4 },
});
