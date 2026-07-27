import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Platform,
  RefreshControl,
  Modal,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useFocusEffect } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';
import MatchCard from '../../components/MatchCard';
import CountdownTimer from '../../components/CountdownTimer';
import TeamShield from '../../components/TeamShield';
import ShareResultCard, { ShareResultData } from '../components/ShareResultCard';


interface Match {
  id: string;
  home_team: {
    id: string;
    name: string;
    short_name: string;
    shield_url: string;
  };
  away_team: {
    id: string;
    name: string;
    short_name: string;
    shield_url: string;
  };
  start_at: string;
  status: string;
  home_score: number | null;
  away_score: number | null;
}

interface Jornada {
  id: string;
  week_number: number;
  type?: string;
  title?: string;
  start_date: string;
  end_date: string;
  status: string;
  matches: Match[];
}

const getJornadaLabel = (jornada: any): string => {
  if (jornada?.type === 'liguilla' && jornada?.title) {
    return jornada.title.replace('Liguilla Clausura 2026 \u2014 ', '');
  }
  return `Jornada ${jornada?.week_number}`;
};

interface JornadaListItem {
  id: string;
  week_number: number;
  status: string;
  is_active: boolean;
}

interface ResultadosMatch {
  id: string;
  home_team: { id: string; name: string; short_name: string; shield_url: string };
  away_team: { id: string; name: string; short_name: string; shield_url: string };
  home_score: number | null;
  away_score: number | null;
  status: string;
  start_at: string | null;
  user_pick: string | null;
  actual_result: string | null;
  correct: boolean | null;
}

interface ResultadosData {
  jornada: { id: string; week_number: number; status: string; is_active: boolean };
  matches: ResultadosMatch[];
  summary: { aciertos: number; jugados: number; total: number; puntos: number };
}

const pickLabel = (pick: string | null, match: ResultadosMatch): string => {
  if (!pick) return 'Sin selecci\u00f3n';
  if (pick === 'HOME') return `Gana ${match.home_team.short_name}`;
  if (pick === 'AWAY') return `Gana ${match.away_team.short_name}`;
  return 'Empate';
};

// Fila de solo lectura para partidos de una jornada pasada \u2014 a diferencia de
// MatchCard (interactivo, usado para la jornada activa), esto solo muestra
// el pick ya hecho y si acert\u00f3 o no. No reutiliza MatchCard porque ese
// componente est\u00e1 pensado para seleccionar, no para mostrar resultado.
function HistoryMatchRow({ match }: { match: ResultadosMatch }) {
  const icon = match.correct === true ? '\u2705' : match.correct === false ? '\u274c' : null;

  return (
    <View style={styles.historyRow}>
      <View style={styles.historyTeams}>
        <View style={styles.historyTeam}>
          <TeamShield
            shortName={match.home_team.short_name}
            shieldUrl={match.home_team.shield_url}
            style={styles.historyShield}
          />
          <Text style={styles.historyTeamName} numberOfLines={1}>{match.home_team.short_name}</Text>
        </View>
        <Text style={styles.historyScore}>
          {match.home_score !== null && match.away_score !== null
            ? `${match.home_score} - ${match.away_score}`
            : 'vs'}
        </Text>
        <View style={styles.historyTeam}>
          <TeamShield
            shortName={match.away_team.short_name}
            shieldUrl={match.away_team.shield_url}
            style={styles.historyShield}
          />
          <Text style={styles.historyTeamName} numberOfLines={1}>{match.away_team.short_name}</Text>
        </View>
      </View>
      <View
        style={[
          styles.historyPickBadge,
          match.correct === true && styles.historyPickCorrect,
          match.correct === false && styles.historyPickWrong,
        ]}
      >
        {icon && <Text style={styles.historyPickIcon}>{icon}</Text>}
        <Text style={[styles.historyPickText, match.correct === null && styles.historyPickTextMuted]}>
          {pickLabel(match.user_pick, match)}
        </Text>
      </View>
    </View>
  );
}

export default function QuinielaScreen() {
  const router = useRouter();
  const { token, user } = useAuth();
  const { showToast } = useToast();
  const [jornada, setJornada] = useState<Jornada | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selections, setSelections] = useState<{ [matchId: string]: string }>({});
  const [savedSelections, setSavedSelections] = useState<{ [matchId: string]: string }>({});
  const [submitting, setSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [shareData, setShareData] = useState<ShareResultData | null>(null);

  // Selector de jornada (reemplaza la pantalla de Historial) — null significa
  // "viendo la jornada activa"; con un id de una jornada pasada se muestra
  // esa jornada en modo solo-lectura con los picks ya hechos.
  const [jornadasList, setJornadasList] = useState<JornadaListItem[]>([]);
  const [selectedJornadaId, setSelectedJornadaId] = useState<string | null>(null);
  const [showJornadaPicker, setShowJornadaPicker] = useState(false);
  const [resultados, setResultados] = useState<ResultadosData | null>(null);
  const [loadingResultados, setLoadingResultados] = useState(false);

  const viewingCurrent = !selectedJornadaId || selectedJornadaId === jornada?.id;

  // Refresca al entrar a la pantalla (no solo al montar) para detectar si la
  // jornada activa cambió mientras el usuario estaba en otra pestaña — ej.
  // cuando un admin cierra la jornada actual y activa la siguiente.
  useFocusEffect(
    useCallback(() => {
      loadJornada();
      loadJornadasList();
    }, [])
  );

  const loadJornadasList = async () => {
    try {
      const res = await api.get('/api/quiniela/jornadas');
      setJornadasList(res.data.jornadas || []);
    } catch (error) {
      console.log('[Quiniela] Error cargando lista de jornadas:', error);
    }
  };

  const selectJornada = async (item: JornadaListItem) => {
    console.log('[Quiniela] Jornada seleccionada del picker:', item.week_number);
    setShowJornadaPicker(false);

    if (jornada && item.id === jornada.id) {
      setSelectedJornadaId(null);
      setResultados(null);
      return;
    }

    setSelectedJornadaId(item.id);
    setLoadingResultados(true);
    try {
      const res = await api.get(`/api/quiniela/jornada/${item.id}/resultados`);
      setResultados(res.data);
    } catch (error: any) {
      showToast('error', error.response?.data?.detail || 'No se pudieron cargar los resultados de esa jornada');
      setSelectedJornadaId(null);
    } finally {
      setLoadingResultados(false);
    }
  };

  const loadJornada = async () => {
    try {
      const response = await api.get('/api/jornadas/current');
      const jornadaData = response.data.jornada;
      setJornada(jornadaData);

      // Check if user already submitted
      if (token) {
        try {
          const picksResponse = await api.get(`/api/quiniela/my-picks/${jornadaData.id}`);
          
          if (picksResponse.data.submitted) {
            // Cargar picks ya guardados como baseline (pueden ser parciales)
            const existingSelections: { [key: string]: string } = {};
            picksResponse.data.selections.forEach((sel: any) => {
              existingSelections[sel.match_id] = sel.selection;
            });
            setSelections(existingSelections);
            setSavedSelections(existingSelections);
          }
        } catch (error: any) {
          // 404 significa que no hay picks previos (normal)
          if (error.response?.status !== 404 && error.response?.status !== 401) {
            console.log('Error loading picks:', error);
          }
        }
      }
    } catch (error: any) {
      if (error.response?.status !== 401) {
        showToast('error', error.response?.data?.detail || 'Error al cargar la jornada');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadJornada();
  };

  const handleSelection = (matchId: string, selection: string) => {
    const match = jornada?.matches.find(m => m.id === matchId);
    if (match && (match.status === 'live' || match.status === 'finished')) return;
    setSelections(prev => ({ ...prev, [matchId]: selection }));
  };

  const handleSubmit = async () => {
    console.log('[Quiniela] handleSubmit ejecutado', { hasNewPicks, jornadaId: jornada?.id });

    if (!jornada) return;

    if (!hasNewPicks) {
      showToast('info', 'No hay picks nuevos o modificados para guardar.');
      return;
    }

    // En web, Alert.alert con array de botones no dispara sus onPress de forma
    // confiable (mismo caso ya resuelto así en handleLogout de profile.tsx) —
    // ahí es donde el botón "no hacía nada": el submit nunca llegaba a correr.
    if (Platform.OS === 'web') {
      await submitQuiniela();
      return;
    }

    Alert.alert(
      'Confirmar picks',
      'Se guardarán tus picks de los partidos que aún no han comenzado. Podrás seguir ajustándolos hasta que arranquen.',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Guardar',
          style: 'default',
          onPress: submitQuiniela,
        },
      ]
    );
  };

  const submitQuiniela = async () => {
    console.log('[Quiniela] submitQuiniela ejecutado');

    if (!jornada || !token) {
      console.log('[Quiniela] submitQuiniela abortado: falta jornada o token');
      return;
    }

    // Solo se mandan picks nuevos/modificados de partidos que aún no arrancan
    const selectionsArray = jornada.matches
      .filter(m => m.status === 'scheduled' && selections[m.id] && selections[m.id] !== savedSelections[m.id])
      .map(m => ({ match_id: m.id, selection: selections[m.id] }));

    console.log('[Quiniela] picks a enviar:', selectionsArray);

    if (selectionsArray.length === 0) return;

    setSubmitting(true);
    try {
      const response = await api.post('/api/quiniela/submit', {
        jornada_id: jornada.id,
        selections: selectionsArray,
      });
      console.log('[Quiniela] respuesta del servidor:', response.data);

      const saved: { match_id: string; selection: string }[] = response.data.saved || [];
      if (saved.length > 0) {
        setSavedSelections(prev => {
          const next = { ...prev };
          saved.forEach(s => { next[s.match_id] = s.selection; });
          return next;
        });
      }

      const rejected: { match?: string; reason: string }[] = response.data.rejected || [];
      if (rejected.length > 0) {
        showToast('error', 'Algunos picks no se guardaron: ' + rejected.map(r => r.reason).join('; '));
      }

      if (saved.length === 0) {
        return;
      }

      // Intentar obtener ranking/liga para la tarjeta de compartir
      let position: number | undefined;
      let leagueName: string | undefined;
      let leagueCode: string | undefined;
      let streak: number | undefined;
      try {
        const [rankRes, leagueRes, streakRes] = await Promise.allSettled([
          api.get('/api/quiniela/rankings'),
          api.get('/api/leagues/my-leagues'),
          api.get('/api/achievements/my'),
        ]);
        if (rankRes.status === 'fulfilled') {
          const me = rankRes.value.data.rankings?.findIndex(
            (r: any) => r.user_id === (user as any)?._id || r.display_name === (user as any)?.display_name
          );
          if (me !== undefined && me >= 0) position = me + 1;
        }
        if (leagueRes.status === 'fulfilled' && leagueRes.value.data.leagues?.length) {
          const first = leagueRes.value.data.leagues[0];
          leagueName = first.name;
          leagueCode = first.code;
        }
        if (streakRes.status === 'fulfilled') {
          streak = streakRes.value.data.streaks?.quiniela_current;
        }
      } catch (_) {}

      setShareData({
        mode: 'result',
        userName: (user as any)?.display_name ?? 'Jugador',
        jornadaNumber: jornada.week_number,
        points: saved.length,
        position,
        streak,
        leagueName,
        leagueCode,
      });

    } catch (error: any) {
      console.error('[Quiniela] Error al guardar picks:', error?.response?.data || error?.message || error);
      // El 401 ya lo maneja el interceptor global de api.ts (redirige a login)
      if (error.response?.status !== 401) {
        const message = error.response?.data?.detail
          || (error.message === 'Network Error'
            ? 'Sin conexión — revisa tu internet e intenta de nuevo'
            : 'No se pudieron guardar tus picks. Intenta de nuevo.');
        showToast('error', message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#DC143C" />
        <Text style={styles.loadingText}>Cargando jornada...</Text>
      </View>
    );
  }

  if (!jornada) {
    return (
      <View style={styles.emptyContainer}>
        <Ionicons name="calendar-outline" size={80} color="#333" />
        <Text style={styles.emptyTitle}>No hay jornada activa</Text>
        <Text style={styles.emptyText}>Vuelve pronto para participar</Text>
      </View>
    );
  }

  const firstMatchDate = jornada.matches[0]?.start_at;
  const openMatches = jornada.matches.filter(match => match.status === 'scheduled');
  const hasOpenMatches = openMatches.length > 0;
  const hasAnySaved = Object.keys(savedSelections).length > 0;
  const hasNewPicks = openMatches.some(
    match => selections[match.id] && selections[match.id] !== savedSelections[match.id]
  );
  const openMatchesPending = openMatches.filter(match => !selections[match.id]).length;
  // Todos los partidos "scheduled" ya tienen pick guardado (los cerrados no cuentan)
  const allPicksComplete =
    hasAnySaved && jornada.matches.every(m => m.status !== 'scheduled' || !!savedSelections[m.id]);

  return (
    <View style={styles.container}>
      {/* ShareResultCard overlay */}
      {shareData && (
        <ShareResultCard
          data={shareData}
          onClose={() => {
            setShareData(null);
            router.replace('/quiniela/rankings');
          }}
        />
      )}

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#DC143C"
          />
        }
      >
        {/* Header Info */}
        <View style={styles.header}>
          <TouchableOpacity
            style={styles.jornadaInfo}
            onPress={() => setShowJornadaPicker(true)}
            activeOpacity={0.7}
          >
            <View style={styles.jornadaTitleRow}>
              <Text style={styles.jornadaTitle}>
                {viewingCurrent ? getJornadaLabel(jornada) : `Jornada ${resultados?.jornada.week_number ?? ''}`}
              </Text>
              <Ionicons name="chevron-down" size={20} color="#999" />
            </View>
            <View style={[styles.statusBadge, !viewingCurrent && styles.statusBadgeHistory]}>
              <Text style={styles.statusText}>
                {viewingCurrent
                  ? (jornada.status === 'upcoming' ? 'Próxima' : 'En curso')
                  : 'Jornada anterior'}
              </Text>
            </View>
          </TouchableOpacity>

          {viewingCurrent && allPicksComplete && (
            <View style={styles.completeBanner}>
              <Ionicons name="checkmark-circle" size={22} color="#00A551" />
              <View style={{ flex: 1 }}>
                <Text style={styles.completeBannerText}>✅ Quiniela enviada</Text>
                <Text style={styles.completeBannerSubtext}>
                  Ya guardaste todos tus picks disponibles de esta jornada
                </Text>
              </View>
            </View>
          )}

          {viewingCurrent && firstMatchDate && hasOpenMatches && (
            <CountdownTimer targetDate={firstMatchDate} />
          )}

          {viewingCurrent && hasAnySaved && (
            <View style={styles.submittedBlock}>
              {!allPicksComplete && (
                <View style={styles.submittedBadge}>
                  <Ionicons name="checkmark-circle" size={20} color="#00A551" />
                  <Text style={styles.submittedText}>Picks guardados</Text>
                </View>
              )}
              {shareData && (
                <TouchableOpacity
                  style={styles.shareBtn}
                  onPress={() => setShareData({ ...shareData })}
                  activeOpacity={0.8}
                >
                  <Ionicons name="share-social-outline" size={16} color="#FFF" />
                  <Text style={styles.shareBtnText}>Compartir resultado</Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          {!viewingCurrent && resultados && (
            <View style={styles.summaryBanner}>
              <Text style={styles.summaryText}>
                Aciertos: {resultados.summary.aciertos}/{resultados.summary.total} · Puntos: {resultados.summary.puntos}
              </Text>
            </View>
          )}
        </View>

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => router.push('/quiniela/leagues')}
          >
            <Ionicons name="people-outline" size={20} color="#0047AB" />
            <Text style={styles.actionText}>Mis Ligas</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => router.push('/quiniela/rankings')}
          >
            <Ionicons name="trophy-outline" size={20} color="#FFD700" />
            <Text style={styles.actionText}>Rankings</Text>
          </TouchableOpacity>
        </View>

        {/* Matches */}
        <View style={styles.matchesContainer}>
          <Text style={styles.sectionTitle}>PARTIDOS</Text>
          {viewingCurrent ? (
            jornada.matches.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                selection={selections[match.id]}
                onSelect={(selection) => handleSelection(match.id, selection)}
                disabled={submitting}
              />
            ))
          ) : loadingResultados ? (
            <ActivityIndicator size="large" color="#DC143C" style={{ marginTop: 24 }} />
          ) : (
            resultados?.matches.map((match) => (
              <HistoryMatchRow key={match.id} match={match} />
            ))
          )}
        </View>
      </ScrollView>

      {/* Submit Button — solo aplica viendo la jornada activa; jornadas
          pasadas son de solo lectura */}
      {viewingCurrent && hasOpenMatches && (
        <View style={styles.footer}>
          <TouchableOpacity
            style={[
              styles.submitButton,
              (!hasNewPicks || submitting) && styles.submitButtonDisabled,
            ]}
            onPress={handleSubmit}
            disabled={!hasNewPicks || submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <Ionicons name="send" size={20} color="#FFFFFF" />
                <Text style={styles.submitButtonText}>GUARDAR PICKS</Text>
              </>
            )}
          </TouchableOpacity>
          <Text style={styles.footerInfo}>
            {hasNewPicks
              ? 'Tienes picks nuevos sin guardar'
              : openMatchesPending > 0
                ? `Faltan ${openMatchesPending} partido${openMatchesPending !== 1 ? 's' : ''} por seleccionar`
                : 'Todo guardado'}
          </Text>
        </View>
      )}

      {/* Selector de jornada — reemplaza la pantalla de Historial */}
      <Modal
        visible={showJornadaPicker}
        animationType="slide"
        transparent
        onRequestClose={() => setShowJornadaPicker(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Elegir jornada</Text>
              <TouchableOpacity onPress={() => setShowJornadaPicker(false)}>
                <Ionicons name="close" size={24} color="#FFFFFF" />
              </TouchableOpacity>
            </View>
            <ScrollView style={styles.pickerList}>
              {jornadasList.map((item) => {
                const isCurrentJornada = jornada?.id === item.id;
                const isSelected = viewingCurrent ? isCurrentJornada : item.id === selectedJornadaId;
                return (
                  <TouchableOpacity
                    key={item.id}
                    style={[styles.pickerRow, isSelected && styles.pickerRowSelected]}
                    onPress={() => selectJornada(item)}
                  >
                    <Text style={styles.pickerRowText}>Jornada {item.week_number}</Text>
                    <View style={styles.pickerRowRight}>
                      {isCurrentJornada && (
                        <View style={styles.pickerCurrentBadge}>
                          <Text style={styles.pickerCurrentBadgeText}>Actual</Text>
                        </View>
                      )}
                      {isSelected && <Ionicons name="checkmark" size={18} color="#DC143C" />}
                    </View>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#FFFFFF',
    marginTop: 16,
    fontSize: 16,
  },
  emptyContainer: {
    flex: 1,
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  emptyTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginTop: 24,
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 100,
  },
  header: {
    marginBottom: 16,
  },
  jornadaInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  jornadaTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  jornadaTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  statusBadge: {
    backgroundColor: '#0047AB',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  statusBadgeHistory: {
    backgroundColor: '#333',
  },
  statusText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '600',
  },
  summaryBanner: {
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#333',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
    marginTop: 12,
  },
  summaryText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
    textAlign: 'center',
  },
  submittedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#0A2E1A',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#00A551',
  },
  submittedBlock: {
    gap: 8,
    alignItems: 'flex-end',
  },
  shareBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#DC143C',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 20,
  },
  shareBtnText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '700',
  },
  submittedText: {
    color: '#00A551',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 8,
  },
  completeBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#0A2E1A',
    borderWidth: 1,
    borderColor: '#00A551',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
    marginTop: 12,
  },
  completeBannerText: {
    color: '#00A551',
    fontSize: 15,
    fontWeight: '700',
  },
  completeBannerSubtext: {
    color: '#7FC9A0',
    fontSize: 12,
    marginTop: 2,
  },
  quickActions: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 24,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1a1a1a',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
    gap: 8,
  },
  actionText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  matchesContainer: {
    gap: 12,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#666',
    letterSpacing: 1,
    marginBottom: 12,
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#000000',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#1a1a1a',
  },
  submitButton: {
    backgroundColor: '#DC143C',
    height: 56,
    borderRadius: 12,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  submitButtonDisabled: {
    opacity: 0.4,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  footerInfo: {
    color: '#999',
    fontSize: 12,
    textAlign: 'center',
  },
  // ── Fila de resultado (jornada pasada) ──────────────────────
  historyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
    padding: 12,
    gap: 12,
  },
  historyTeams: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  historyTeam: {
    alignItems: 'center',
    width: 56,
  },
  historyShield: {
    width: 32,
    height: 32,
    marginBottom: 4,
  },
  historyTeamName: {
    fontSize: 11,
    color: '#FFFFFF',
    fontWeight: '600',
  },
  historyScore: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#999',
  },
  historyPickBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#0a0a0a',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  historyPickCorrect: {
    backgroundColor: '#0A2E1A',
  },
  historyPickWrong: {
    backgroundColor: '#2A0A0A',
  },
  historyPickIcon: {
    fontSize: 14,
  },
  historyPickText: {
    fontSize: 12,
    color: '#FFFFFF',
    fontWeight: '600',
  },
  historyPickTextMuted: {
    color: '#666',
  },
  // ── Modal selector de jornada ────────────────────────────────
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.8)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
    maxHeight: '70%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  pickerList: {
    maxHeight: 400,
  },
  pickerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderRadius: 10,
    marginBottom: 6,
  },
  pickerRowSelected: {
    backgroundColor: '#2a0a0a',
  },
  pickerRowText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '600',
  },
  pickerRowRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  pickerCurrentBadge: {
    backgroundColor: '#0047AB',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  pickerCurrentBadgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '700',
  },
});
