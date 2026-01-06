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
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import * as Clipboard from 'expo-clipboard';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function LeagueDetailScreen() {
  const router = useRouter();
  const { leagueId } = useLocalSearchParams();
  const { token, user } = useAuth();
  const [league, setLeague] = useState<any>(null);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'ranking' | 'results'>('ranking');
  const [jornada, setJornada] = useState<any>(null);

  useEffect(() => {
    loadLeagueData();
    loadJornada();
  }, []);

  const loadJornada = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/jornadas/current`);
      setJornada(response.data.jornada);
    } catch (error) {
      console.error('Error loading jornada:', error);
    }
  };

  const loadLeagueData = async () => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/quiniela/league/${leagueId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setLeague(response.data.league);
      setMembers(response.data.members);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Error al cargar la liga');
      router.back();
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadLeagueData();
  };

  const copyCode = async () => {
    if (league?.code) {
      await Clipboard.setStringAsync(league.code);
      Alert.alert('¡Copiado!', 'Código copiado al portapapeles');
    }
  };

  const viewResults = () => {
    if (jornada?.status === 'finished') {
      router.push({
        pathname: '/quiniela/league-results',
        params: { leagueId, jornadaId: jornada.id },
      });
    } else {
      Alert.alert(
        'Jornada en progreso',
        'Los resultados estarán disponibles cuando finalice la jornada'
      );
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#DC143C" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scroll}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#DC143C" />
        }
      >
        {/* League Header */}
        <View style={styles.header}>
          <View style={styles.headerIcon}>
            <Ionicons name="shield" size={48} color="#DC143C" />
          </View>
          <Text style={styles.leagueName}>{league?.name}</Text>
          {league?.is_owner && (
            <View style={styles.ownerBadge}>
              <Text style={styles.ownerText}>Administrador</Text>
            </View>
          )}

          <View style={styles.codeCard}>
            <Text style={styles.codeLabel}>Código</Text>
            <Text style={styles.code}>{league?.code}</Text>
            <TouchableOpacity style={styles.copyButton} onPress={copyCode}>
              <Ionicons name="copy" size={16} color="#0047AB" />
              <Text style={styles.copyText}>Copiar</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Tabs */}
        <View style={styles.tabs}>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'ranking' && styles.tabActive]}
            onPress={() => setActiveTab('ranking')}
          >
            <Text style={[styles.tabText, activeTab === 'ranking' && styles.tabTextActive]}>
              Clasificación
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === 'results' && styles.tabActive]}
            onPress={() => setActiveTab('results')}
          >
            <Text style={[styles.tabText, activeTab === 'results' && styles.tabTextActive]}>
              Resultados
            </Text>
          </TouchableOpacity>
        </View>

        {/* Tab Content */}
        {activeTab === 'ranking' && (
          <View style={styles.content}>
            <Text style={styles.sectionTitle}>RANKING GENERAL</Text>
            {members.map((member: any, index) => {
              const isCurrentUser = member.user_id === user?.id;
              return (
                <View
                  key={member.user_id}
                  style={[
                    styles.memberItem,
                    isCurrentUser && styles.memberItemCurrent,
                    index < 3 && styles.memberItemTop,
                  ]}
                >
                  <View style={styles.positionContainer}>
                    {index < 3 ? (
                      <Ionicons
                        name={index === 0 ? 'trophy' : 'medal'}
                        size={24}
                        color={index === 0 ? '#FFD700' : index === 1 ? '#C0C0C0' : '#CD7F32'}
                      />
                    ) : (
                      <Text style={styles.position}>{index + 1}</Text>
                    )}
                  </View>

                  <View style={styles.memberInfo}>
                    <Text style={styles.memberName}>
                      {member.display_name}
                      {isCurrentUser && ' (Tú)'}
                    </Text>
                  </View>

                  <Text style={styles.memberPoints}>{member.total_points} pts</Text>
                </View>
              );
            })}
          </View>
        )}

        {activeTab === 'results' && (
          <View style={styles.content}>
            <Text style={styles.sectionTitle}>RESULTADOS DE JORNADA</Text>
            <TouchableOpacity style={styles.resultsButton} onPress={viewResults}>
              <Ionicons name="grid" size={24} color="#FFFFFF" />
              <Text style={styles.resultsButtonText}>VER TABLA DE RESULTADOS</Text>
            </TouchableOpacity>

            <View style={styles.infoBox}>
              <Ionicons name="information-circle" size={20} color="#0047AB" />
              <Text style={styles.infoText}>
                {jornada?.status === 'finished'
                  ? 'La jornada ha finalizado. Toca para ver los resultados detallados.'
                  : 'Los resultados estarán disponibles cuando finalice la jornada actual.'}
              </Text>
            </View>
          </View>
        )}
      </ScrollView>
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
  scroll: {
    flex: 1,
  },
  header: {
    padding: 24,
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  headerIcon: {
    marginBottom: 16,
  },
  leagueName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 12,
  },
  ownerBadge: {
    backgroundColor: '#DC143C',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    marginBottom: 16,
  },
  ownerText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  codeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    padding: 12,
    borderRadius: 8,
    gap: 12,
  },
  codeLabel: {
    fontSize: 14,
    color: '#999',
  },
  code: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#0047AB',
    letterSpacing: 2,
  },
  copyButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  copyText: {
    fontSize: 14,
    color: '#0047AB',
    fontWeight: '600',
  },
  tabs: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  tab: {
    flex: 1,
    paddingVertical: 16,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: {
    borderBottomColor: '#DC143C',
  },
  tabText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  tabTextActive: {
    color: '#FFFFFF',
  },
  content: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#666',
    letterSpacing: 1,
    marginBottom: 16,
  },
  memberItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    padding: 16,
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#333',
  },
  memberItemCurrent: {
    borderColor: '#0047AB',
    backgroundColor: '#0a1a2a',
  },
  memberItemTop: {
    borderColor: '#FFD700',
  },
  positionContainer: {
    width: 40,
    alignItems: 'center',
  },
  position: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  memberInfo: {
    flex: 1,
    marginLeft: 12,
  },
  memberName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  memberPoints: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#DC143C',
  },
  resultsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#DC143C',
    padding: 16,
    borderRadius: 12,
    gap: 8,
    marginBottom: 16,
  },
  resultsButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
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
});