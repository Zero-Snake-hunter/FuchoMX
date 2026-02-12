import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';
import MatchCard from '../../components/MatchCard';
import CountdownTimer from '../../components/CountdownTimer';


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
  start_date: string;
  end_date: string;
  status: string;
  matches: Match[];
}

export default function QuinielaScreen() {
  const router = useRouter();
  const { token } = useAuth();
  const [jornada, setJornada] = useState<Jornada | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selections, setSelections] = useState<{ [matchId: string]: string }>({});
  const [submitting, setSubmitting] = useState(false);
  const [alreadySubmitted, setAlreadySubmitted] = useState(false);

  useEffect(() => {
    loadJornada();
  }, []);

  const loadJornada = async () => {
    try {
      const response = await api.get(`/api/jornadas/current`);
      const jornadaData = response.data.jornada;
      setJornada(jornadaData);

      // Check if user already submitted
      if (token) {
        try {
          const picksResponse = await axios.get(
            `${BACKEND_URL}/api/quiniela/my-picks/${jornadaData.id}`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          
          if (picksResponse.data.submitted) {
            setAlreadySubmitted(true);
            // Load existing selections
            const existingSelections: { [key: string]: string } = {};
            picksResponse.data.selections.forEach((sel: any) => {
              existingSelections[sel.match_id] = sel.selection;
            });
            setSelections(existingSelections);
          }
        } catch (error) {
          console.log('No previous picks found');
        }
      }
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Error al cargar la jornada');
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
    if (alreadySubmitted) return;
    setSelections(prev => ({ ...prev, [matchId]: selection }));
  };

  const handleSubmit = async () => {
    if (!jornada) return;

    // Validate all matches have selections
    const allMatchesSelected = jornada.matches.every(match => selections[match.id]);
    if (!allMatchesSelected) {
      Alert.alert(
        'Selección incompleta',
        'Debes seleccionar un resultado para cada partido'
      );
      return;
    }

    Alert.alert(
      'Confirmar quiniela',
      '¿Estás seguro? No podrás modificar tu selección después de enviarla.',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Enviar',
          style: 'default',
          onPress: submitQuiniela,
        },
      ]
    );
  };

  const submitQuiniela = async () => {
    if (!jornada || !token) return;

    setSubmitting(true);
    try {
      const selectionsArray = Object.entries(selections).map(([matchId, selection]) => ({
        match_id: matchId,
        selection,
      }));

      await axios.post(
        `${BACKEND_URL}/api/quiniela/submit`,
        {
          jornada_id: jornada.id,
          selections: selectionsArray,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      Alert.alert(
        '¡Quiniela enviada!',
        'Tu quiniela ha sido enviada exitosamente. ¡Buena suerte!',
        [
          {
            text: 'Ver Rankings',
            onPress: () => router.push('/quiniela/rankings'),
          },
          { text: 'OK' },
        ]
      );

      setAlreadySubmitted(true);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Error al enviar quiniela');
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
  const allSelected = jornada.matches.every(match => selections[match.id]);

  return (
    <View style={styles.container}>
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
            <Text style={styles.jornadaTitle}>Jornada {jornada.week_number}</Text>
            <View style={styles.statusBadge}>
              <Text style={styles.statusText}>
                {jornada.status === 'upcoming' ? 'Próxima' : 'En curso'}
              </Text>
            </View>
          </View>

          {firstMatchDate && !alreadySubmitted && (
            <CountdownTimer targetDate={firstMatchDate} />
          )}

          {alreadySubmitted && (
            <View style={styles.submittedBadge}>
              <Ionicons name="checkmark-circle" size={20} color="#00A551" />
              <Text style={styles.submittedText}>Quiniela enviada</Text>
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
              disabled={alreadySubmitted}
            />
          ))}
        </View>
      </ScrollView>

      {/* Submit Button */}
      {!alreadySubmitted && (
        <View style={styles.footer}>
          <TouchableOpacity
            style={[
              styles.submitButton,
              (!allSelected || submitting) && styles.submitButtonDisabled,
            ]}
            onPress={handleSubmit}
            disabled={!allSelected || submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <Ionicons name="send" size={20} color="#FFFFFF" />
                <Text style={styles.submitButtonText}>ENVIAR QUINIELA</Text>
              </>
            )}
          </TouchableOpacity>
          <Text style={styles.footerInfo}>
            {allSelected
              ? 'Todos los partidos seleccionados'
              : `Faltan ${jornada.matches.length - Object.keys(selections).length} partidos`}
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
    backgroundColor: '#0a2a1a',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#00A551',
  },
  submittedText: {
    color: '#00A551',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 8,
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
