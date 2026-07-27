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
} from 'react-native';
import { useRouter } from 'expo-router';
import { useFocusEffect } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';
import MatchCard from '../../components/MatchCard';
import CountdownTimer from '../../components/CountdownTimer';
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

export default function QuinielaScreen() {
  const router = useRouter();
  const { token, user } = useAuth();
  const [jornada, setJornada] = useState<Jornada | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selections, setSelections] = useState<{ [matchId: string]: string }>({});
  const [savedSelections, setSavedSelections] = useState<{ [matchId: string]: string }>({});
  const [submitting, setSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [shareData, setShareData] = useState<ShareResultData | null>(null);

  // Refresca al entrar a la pantalla (no solo al montar) para detectar si la
  // jornada activa cambió mientras el usuario estaba en otra pestaña — ej.
  // cuando un admin cierra la jornada actual y activa la siguiente.
  useFocusEffect(
    useCallback(() => {
      loadJornada();
    }, [])
  );

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
        Alert.alert('Error', error.response?.data?.detail || 'Error al cargar la jornada');
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
      Alert.alert('Nada por guardar', 'No hay picks nuevos o modificados para guardar.');
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
        Alert.alert(
          'Algunos picks no se guardaron',
          rejected.map(r => r.reason).join('\n')
        );
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
        Alert.alert('Error al guardar', message);
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
          <View style={styles.jornadaInfo}>
            <Text style={styles.jornadaTitle}>{getJornadaLabel(jornada)}</Text>
            <View style={styles.statusBadge}>
              <Text style={styles.statusText}>
                {jornada.status === 'upcoming' ? 'Próxima' : 'En curso'}
              </Text>
            </View>
          </View>

          {allPicksComplete && (
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

          {firstMatchDate && hasOpenMatches && (
            <CountdownTimer targetDate={firstMatchDate} />
          )}

          {hasAnySaved && (
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
            onPress={() => router.push('/quiniela/history')}
          >
            <Ionicons name="time-outline" size={20} color="#0047AB" />
            <Text style={styles.actionText}>Historial</Text>
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
          {jornada.matches.map((match) => (
            <MatchCard
              key={match.id}
              match={match}
              selection={selections[match.id]}
              onSelect={(selection) => handleSelection(match.id, selection)}
              disabled={submitting}
            />
          ))}
        </View>
      </ScrollView>

      {/* Submit Button — habilitado si hay al menos 1 pick nuevo/modificado por guardar */}
      {hasOpenMatches && (
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
  statusText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '600',
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
});
