import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  StatusBar,
  ScrollView,
  Image,
  Animated,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { StreakWidget } from '../../components/StreakWidget';
import { AchievementToast } from '../../components/AchievementToast';
import { RulesModal } from '../../components/RulesModal';
import { InstagramFooter } from '../../components/InstagramFooter';
import api from '../lib/api';
import { SPONSORS, getNombreTorneo } from '../config/sponsors';

export default function HomeScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const insets = useSafeAreaInsets();
  const [streaks, setStreaks] = useState({ quiniela_current: 0, win_current: 0, correct_current: 0 });
  const [toast, setToast] = useState({ visible: false, emoji: '', title: '', description: '' });
  const [showRules, setShowRules] = useState(false);
  const [liveScores, setLiveScores] = useState<{
    has_live: boolean;
    live_matches: { home_name: string; away_name: string; home_score: number | null; away_score: number | null; game_time: string; status: string; start_time: string }[];
  }>({ has_live: false, live_matches: [] });
  const [jornadaMatches, setJornadaMatches] = useState<{
    id: string;
    home_team: { name: string; short_name: string };
    away_team: { name: string; short_name: string };
    start_at: string;
    status: string;
    home_score: number | null;
    away_score: number | null;
  }[]>([]);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    api.get('/api/achievements/my').then(res => {
      setStreaks(res.data.streaks);
    }).catch(() => {});
  }, []);

  // ── EN VIVO polling every 60s ──────────────────────────────────────────
  useEffect(() => {
    const fetchLive = () => {
      api.get('/api/jornadas/current/live-scores')
        .then(res => setLiveScores(res.data))
        .catch(() => {});
    };
    fetchLive();
    const interval = setInterval(fetchLive, 60_000);
    return () => clearInterval(interval);
  }, []);

  // ── HOY: partidos de la jornada activa programados para hoy ──────────
  useEffect(() => {
    const fetchJornada = () => {
      api.get('/api/jornadas/current')
        .then(res => setJornadaMatches(res.data?.jornada?.matches || []))
        .catch(() => {});
    };
    fetchJornada();
    const interval = setInterval(fetchJornada, 60_000);
    return () => clearInterval(interval);
  }, []);

  // ── Pulsating animation for EN VIVO badge ─────────────────────────────
  useEffect(() => {
    if (!liveScores.has_live) return;
    const anim = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.4, duration: 700, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 700, useNativeDriver: true }),
      ])
    );
    anim.start();
    return () => anim.stop();
  }, [liveScores.has_live]);

  const handleQuinielaPress = () => {
    console.log('NAVIGATING TO QUINIELA');
    router.push('/quiniela');
  };

  const handleFantasyPress = () => {
    console.log('NAVIGATING TO FANTASY');
    router.push('/fantasy');
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <StatusBar barStyle="light-content" />
      
      <ScrollView 
        style={styles.scrollView}
        contentContainerStyle={[
          styles.scrollContent,
          { paddingBottom: insets.bottom + 140 }
        ]}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Hola,</Text>
            <Text style={styles.userName}>{user?.display_name || 'Usuario'}</Text>
          </View>
          <View style={styles.pointsContainer}>
            <Ionicons name="trophy" size={24} color="#FFD700" />
            <Text style={styles.points}>{user?.total_points || 0}</Text>
          </View>
        </View>

        <StreakWidget
          quinielaStreak={streaks.quiniela_current}
          winStreak={streaks.win_current}
          correctStreak={streaks.correct_current}
          onPress={() => router.push('/profile/achievements')}
        />

        {/* ── Sponsor Splash Banner (solo si activo) ── */}
        {SPONSORS.oro.splash.activo && (
          <View style={styles.sponsorBanner}>
            {SPONSORS.oro.splash.logo && (
              <Image
                source={SPONSORS.oro.splash.logo}
                style={styles.sponsorBannerLogo}
                resizeMode="contain"
              />
            )}
            <View style={{ flex: 1 }}>
              <Text style={styles.sponsorBannerLabel}>PATROCINADOR OFICIAL</Text>
              <Text style={styles.sponsorBannerMarca}>{SPONSORS.oro.splash.marca}</Text>
            </View>
            {SPONSORS.oro.splash.cta_texto ? (
              <Text style={styles.sponsorBannerCta}>{SPONSORS.oro.splash.cta_texto}</Text>
            ) : null}
          </View>
        )}

        <View style={styles.content}>
          <Text style={styles.title}>SELECCIONA UN MODO</Text>
          <Text style={styles.subtitle}>Elige cómo quieres jugar</Text>

          <View style={styles.cardsContainer}>
            <TouchableOpacity
              style={styles.modeCard}
              activeOpacity={0.8}
              onPress={handleQuinielaPress}
            >
              <View style={[styles.cardIconContainer, { backgroundColor: '#DC143C' }]}>
                <Image
                  source={require('../../assets/images/FuchoQuiniela.png')}
                  style={styles.cardLogo}
                  resizeMode="contain"
                />
              </View>
              <Text style={styles.cardTitle}>{getNombreTorneo()}</Text>
              <Text style={styles.cardDescription}>
                Predice los resultados de cada partido y gana puntos
              </Text>
              <View style={styles.cardFooter}>
                <Ionicons name="arrow-forward" size={24} color="#DC143C" />
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.modeCard}
              activeOpacity={0.8}
              onPress={handleFantasyPress}
            >
              <View style={[styles.cardIconContainer, { backgroundColor: '#DC143C' }]}>
                <Image
                  source={require('../../assets/images/FuchoOnce.png')}
                  style={styles.cardLogo}
                  resizeMode="contain"
                />
              </View>
              <Text style={styles.cardTitle}>FUCHOONCE</Text>
              <Text style={styles.cardDescription}>
                Arma tu once ideal de la jornada
              </Text>
              <View style={styles.cardFooter}>
                <Ionicons name="arrow-forward" size={24} color="#DC143C" />
              </View>
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            style={styles.rulesButton}
            activeOpacity={0.8}
            onPress={() => setShowRules(true)}
          >
            <Text style={styles.rulesButtonText}>📖 Reglas</Text>
          </TouchableOpacity>

          <View style={styles.infoBox}>
            <Ionicons name="information-circle" size={20} color="#0047AB" />
            <Text style={styles.infoText}>
              Ambos modos están disponibles. Puedes jugar uno o ambos simultáneamente.
            </Text>
          </View>

          {/* ── HOY: partidos de la jornada activa programados para hoy, sin
              importar su status (scheduled/live/finished) ──
              start_at llega de Mongo en UTC pero SIN sufijo "Z" (naive) —
              hay que forzar el parseo como UTC, si no JS lo toma como hora
              local y el día calculado queda corrido (ej. un partido a las
              21:00 hora México se guarda como "03:00" del día siguiente
              en UTC, y sin el fix aparecía fechado un día después). */}
          {(() => {
            const parseUtc = (dateStr: string) =>
              new Date(/[Z+-]\d{2}:?\d{2}$|Z$/.test(dateStr) ? dateStr : `${dateStr}Z`);
            const now = new Date();
            const todayMatches = jornadaMatches.filter((m) => {
              if (!m.start_at) return false;
              const d = parseUtc(m.start_at);
              return !isNaN(d.getTime())
                && d.toLocaleDateString() === now.toLocaleDateString();
            });
            if (todayMatches.length === 0) return null;
            return (
              <View style={styles.todaySection}>
                <View style={styles.todayHeader}>
                  <Ionicons name="calendar" size={16} color="#0047AB" />
                  <Text style={styles.todayLabel}>HOY</Text>
                  <Text style={styles.todayCount}>
                    {todayMatches.length} partido{todayMatches.length !== 1 ? 's' : ''}
                  </Text>
                </View>
                {todayMatches.map((m) => {
                  const isFinished = m.status === 'finished';
                  const isLive = m.status === 'live';
                  const value = (isFinished || isLive)
                    ? `${m.home_score ?? '-'} - ${m.away_score ?? '-'}`
                    : parseUtc(m.start_at).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
                  return (
                    <View key={m.id} style={styles.todayMatch}>
                      <Text style={styles.todayMatchHome} numberOfLines={1}>
                        {m.home_team?.short_name || m.home_team?.name}
                      </Text>
                      <View style={styles.todayScore}>
                        <Text style={styles.todayScoreText}>{value}</Text>
                        {isLive ? (
                          <Text style={styles.todayLiveTag}>EN VIVO</Text>
                        ) : isFinished ? (
                          <Text style={styles.todayFinishedTag}>FINAL</Text>
                        ) : null}
                      </View>
                      <Text style={styles.todayMatchAway} numberOfLines={1}>
                        {m.away_team?.short_name || m.away_team?.name}
                      </Text>
                    </View>
                  );
                })}
              </View>
            );
          })()}

          {/* ── EN VIVO section — solo cuando hay partidos realmente en curso ──
              El backend ya filtra por status, pero se vuelve a cruzar acá
              contra la hora real por si algún partido sin arrancar se cuela
              (statusGroup de 365Scores no siempre es confiable). Un partido
              "en vivo" siempre tiene marcador real (nunca null a esta altura,
              ya sanitizado en el backend) — si por algún motivo no lo trae,
              se muestra "-" en vez de inventar un 0. */}
          {(() => {
            const now = new Date();
            const genuinelyLive = liveScores.live_matches.filter((m) => {
              if (m.status !== 'live') return false;
              if (!m.start_time) return true;
              const start = new Date(m.start_time);
              return !isNaN(start.getTime()) && now >= start;
            });
            if (genuinelyLive.length === 0) return null;
            return (
              <View style={styles.liveSection}>
                <View style={styles.liveHeader}>
                  <Animated.View style={[styles.liveDot, { opacity: pulseAnim }]} />
                  <Text style={styles.liveLabel}>EN VIVO</Text>
                  <Text style={styles.liveCount}>
                    {genuinelyLive.length} partido{genuinelyLive.length !== 1 ? 's' : ''}
                  </Text>
                </View>
                {genuinelyLive.map((m, i) => {
                  const hasScore =
                    m.home_score !== null && m.home_score !== -1 &&
                    m.away_score !== null && m.away_score !== -1;
                  const scheduledTime = m.start_time
                    ? new Date(m.start_time).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
                    : '-';
                  return (
                    <View key={i} style={styles.liveMatch}>
                      <Text style={styles.liveMatchHome} numberOfLines={1}>{m.home_name}</Text>
                      <View style={styles.liveScore}>
                        <Text style={styles.liveScoreText}>
                          {hasScore ? `${m.home_score} - ${m.away_score}` : scheduledTime}
                        </Text>
                        {hasScore && m.game_time ? (
                          <Text style={styles.liveTime}>{m.game_time}'</Text>
                        ) : null}
                      </View>
                      <Text style={styles.liveMatchAway} numberOfLines={1}>{m.away_name}</Text>
                    </View>
                  );
                })}
              </View>
            );
          })()}


        </View>
      </ScrollView>

      <AchievementToast
        visible={toast.visible}
        emoji={toast.emoji}
        title={toast.title}
        description={toast.description}
        onHide={() => setToast(t => ({ ...t, visible: false }))}
      />

      <RulesModal visible={showRules} onClose={() => setShowRules(false)} />

      <InstagramFooter />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 24,
  },
  greeting: {
    fontSize: 16,
    color: '#999',
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginTop: 4,
  },
  pointsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  points: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginLeft: 8,
  },
  content: {
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFFFFF',
    letterSpacing: 1,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginBottom: 32,
  },
  cardsContainer: {
    gap: 20,
    marginBottom: 24,
  },
  modeCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: '#333',
  },
  cardIconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
    overflow: 'hidden',
  },
  cardLogo: {
    width: 70,
    height: 70,
  },
  cardTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 12,
    letterSpacing: 0.5,
  },
  cardDescription: {
    fontSize: 14,
    color: '#999',
    lineHeight: 20,
    marginBottom: 16,
  },
  cardFooter: {
    alignItems: 'flex-end',
  },
  rulesButton: {
    alignSelf: 'center',
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#E6394650',
    borderRadius: 20,
    paddingHorizontal: 20,
    paddingVertical: 10,
    marginBottom: 20,
  },
  rulesButtonText: {
    color: '#E63946',
    fontSize: 14,
    fontWeight: '700',
  },
  infoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0a1a2a',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#0047AB',
  },
  infoText: {
    flex: 1,
    fontSize: 12,
    color: '#FFFFFF',
    marginLeft: 12,
    lineHeight: 18,
  },
  // ── Liguilla Banner Card ────────────────────────────────
  liguillaBannerCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#0D0D0D',
    borderRadius: 16,
    borderWidth: 2,
    borderColor: '#E63946',
    marginHorizontal: 16,
    marginTop: 16,
    paddingHorizontal: 20,
    paddingVertical: 20,
    shadowColor: '#E63946',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  liguillaBannerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  liguillaBannerEmoji: {
    fontSize: 40,
  },
  liguillaBannerTitle: {
    color: '#E63946',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1,
  },
  liguillaBannerSub: {
    color: '#AAAAAA',
    fontSize: 12,
    marginTop: 4,
  },
  // ── Sponsor Banner ─────────────────────────────────────
  sponsorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#FFD70033',
    marginHorizontal: 24,
    marginBottom: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    gap: 10,
  },
  sponsorBannerLogo: {
    width: 36,
    height: 36,
    borderRadius: 6,
  },
  sponsorBannerLabel: {
    fontSize: 9,
    color: '#FFD700',
    fontWeight: '800',
    letterSpacing: 1,
  },
  sponsorBannerMarca: {
    fontSize: 13,
    color: '#FFF',
    fontWeight: '700',
  },
  sponsorBannerCta: {
    fontSize: 11,
    color: '#FFD700',
    fontWeight: '600',
  },
  // ── HOY section ─────────────────────────────────────────────────────────
  todaySection: {
    marginTop: 20,
    backgroundColor: '#0D0D0D',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#0047AB50',
    overflow: 'hidden',
  },
  todayHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: '#061420',
    gap: 8,
  },
  todayLabel: {
    color: '#0047AB',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 1.5,
    flex: 1,
  },
  todayCount: {
    color: '#888',
    fontSize: 11,
    fontWeight: '600',
  },
  todayMatch: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: '#1A1A1A',
  },
  todayMatchHome: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '700',
    flex: 1,
    textAlign: 'left',
  },
  todayMatchAway: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '700',
    flex: 1,
    textAlign: 'right',
  },
  todayScore: {
    alignItems: 'center',
    paddingHorizontal: 10,
  },
  todayScoreText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1,
  },
  todayLiveTag: {
    color: '#E63946',
    fontSize: 9,
    fontWeight: '800',
    marginTop: 2,
    letterSpacing: 0.5,
  },
  todayFinishedTag: {
    color: '#00A551',
    fontSize: 9,
    fontWeight: '800',
    marginTop: 2,
    letterSpacing: 0.5,
  },
  // ── EN VIVO section ────────────────────────────────────────────────────
  liveSection: {
    marginTop: 20,
    backgroundColor: '#0D0D0D',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E6394650',
    overflow: 'hidden',
  },
  liveHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: '#1A0608',
    gap: 8,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#E63946',
  },
  liveLabel: {
    color: '#E63946',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 1.5,
    flex: 1,
  },
  liveCount: {
    color: '#888',
    fontSize: 11,
    fontWeight: '600',
  },
  liveMatch: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: '#1A1A1A',
  },
  liveMatchHome: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '700',
    flex: 1,
    textAlign: 'left',
  },
  liveMatchAway: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '700',
    flex: 1,
    textAlign: 'right',
  },
  liveScore: {
    alignItems: 'center',
    paddingHorizontal: 10,
  },
  liveScoreText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1,
  },
  liveTime: {
    color: '#E63946',
    fontSize: 10,
    fontWeight: '700',
    marginTop: 2,
  },
});