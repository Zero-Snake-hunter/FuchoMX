import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  RefreshControl,
  Share,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import * as Clipboard from 'expo-clipboard';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Member {
  user_id: string;
  display_name: string;
  team_name?: string;
  total_points: number;
  rank: number;
  joined_at: string;
}

interface JornadaRanking {
  user_id: string;
  display_name: string;
  team_name?: string;
  jornada_points: number;
  rank: number;
  players_breakdown?: any[];
}

export default function LeagueDetailScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { leagueId, mode: paramMode } = useLocalSearchParams();
  const { token, user } = useAuth();
  
  const [league, setLeague] = useState<any>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [jornadaRankings, setJornadaRankings] = useState<JornadaRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'jornada' | 'general'>('jornada');
  const [jornada, setJornada] = useState<any>(null);
  const [expandedPlayer, setExpandedPlayer] = useState<string | null>(null);

  const mode = paramMode || league?.mode || 'quiniela';
  const isFantasy = mode === 'fantasy';

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      await Promise.all([
        loadLeagueData(),
        loadJornada(),
      ]);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  const loadJornada = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/jornadas/current`);
      setJornada(response.data.jornada);
      
      // Load jornada rankings if available
      if (response.data.jornada?.id) {
        await loadJornadaRankings(response.data.jornada.id);
      }
    } catch (error) {
      console.error('Error loading jornada:', error);
    }
  };

  const loadLeagueData = async () => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/leagues/${leagueId}`,
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

  const loadJornadaRankings = async (jornadaId: string) => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/leagues/${leagueId}/rankings/jornada/${jornadaId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setJornadaRankings(response.data.rankings);
    } catch (error) {
      console.error('Error loading jornada rankings:', error);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadData();
  }, []);

  const copyCode = async () => {
    if (league?.code) {
      await Clipboard.setStringAsync(league.code);
      Alert.alert('¡Copiado!', 'Código copiado al portapapeles');
    }
  };

  const shareLeague = async () => {
    const modeText = isFantasy ? 'Fantasy Fútbol' : 'Quiniela';
    try {
      await Share.share({
        message: `¡Únete a mi liga "${league.name}" de ${modeText}!\n\nCódigo: ${league.code}\n\nDescarga la app y usa este código para unirte.`,
      });
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  const viewResults = () => {
    if (jornada) {
      router.push({
        pathname: '/quiniela/league-results',
        params: { leagueId, jornadaId: jornada.id },
      });
    }
  };

  const togglePlayerBreakdown = (playerId: string) => {
    setExpandedPlayer(expandedPlayer === playerId ? null : playerId);
  };

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1: return '🥇';
      case 2: return '🥈';
      case 3: return '🥉';
      default: return `${rank}`;
    }
  };

  const renderGeneralRankingItem = (member: Member) => {
    const isCurrentUser = member.user_id === user?.id;
    
    return (
      <View 
        key={member.user_id}
        style={[styles.rankingItem, isCurrentUser && styles.rankingItemHighlight]}
      >
        <View style={styles.rankBadge}>
          <Text style={styles.rankText}>{getRankIcon(member.rank)}</Text>
        </View>
        <View style={styles.memberInfo}>
          <Text style={styles.memberName}>
            {member.display_name}
            {isCurrentUser && ' (Tú)'}
          </Text>
          {isFantasy && member.team_name && (
            <Text style={styles.teamName}>{member.team_name}</Text>
          )}
        </View>
        <View style={styles.pointsContainer}>
          <Text style={styles.pointsValue}>{member.total_points}</Text>
          <Text style={styles.pointsLabel}>pts</Text>
        </View>
      </View>
    );
  };

  const renderJornadaRankingItem = (ranking: JornadaRanking) => {
    const isCurrentUser = ranking.user_id === user?.id;
    const isExpanded = expandedPlayer === ranking.user_id;
    
    return (
      <View key={ranking.user_id}>
        <TouchableOpacity 
          style={[styles.rankingItem, isCurrentUser && styles.rankingItemHighlight]}
          onPress={() => isFantasy && togglePlayerBreakdown(ranking.user_id)}
          activeOpacity={isFantasy ? 0.7 : 1}
        >
          <View style={styles.rankBadge}>
            <Text style={styles.rankText}>{getRankIcon(ranking.rank)}</Text>
          </View>
          <View style={styles.memberInfo}>
            <Text style={styles.memberName}>
              {ranking.display_name}
              {isCurrentUser && ' (Tú)'}
            </Text>
            {isFantasy && ranking.team_name && (
              <Text style={styles.teamName}>{ranking.team_name}</Text>
            )}
          </View>
          <View style={styles.pointsContainer}>
            <Text style={[styles.pointsValue, styles.pointsJornada]}>
              {ranking.jornada_points}
            </Text>
            <Text style={styles.pointsLabel}>pts</Text>
          </View>
          {isFantasy && (
            <Ionicons 
              name={isExpanded ? 'chevron-up' : 'chevron-down'} 
              size={20} 
              color="#666" 
            />
          )}
        </TouchableOpacity>

        {/* Player breakdown for Fantasy */}
        {isFantasy && isExpanded && ranking.players_breakdown && (
          <View style={styles.breakdownContainer}>
            {ranking.players_breakdown.map((player: any, idx: number) => (
              <View key={idx} style={styles.breakdownItem}>
                <View style={styles.breakdownPlayer}>
                  <Text style={styles.breakdownPosition}>{player.position}</Text>
                  <Text style={styles.breakdownName}>{player.player_name}</Text>
                </View>
                <View style={styles.breakdownPoints}>
                  <Text style={[
                    styles.breakdownPointsValue,
                    player.points > 0 ? styles.pointsPositive : 
                    player.points < 0 ? styles.pointsNegative : {}
                  ]}>
                    {player.points > 0 ? '+' : ''}{player.points}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#DC143C" />
      </View>
    );
  }

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>{league?.name}</Text>
        <TouchableOpacity onPress={shareLeague} style={styles.shareButton}>
          <Ionicons name="share-outline" size={24} color="#FFFFFF" />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#DC143C" />
        }
      >
        {/* League Info Card */}
        <View style={styles.infoCard}>
          <View style={styles.infoRow}>
            <View style={[styles.modeTag, isFantasy ? styles.modeTagFantasy : styles.modeTagQuiniela]}>
              <Ionicons 
                name={isFantasy ? 'football' : 'trophy'} 
                size={16} 
                color="#FFFFFF" 
              />
              <Text style={styles.modeTagText}>
                {isFantasy ? 'Fantasy' : 'Quiniela'}
              </Text>
            </View>
            <View style={styles.memberCount}>
              <Ionicons name="people" size={16} color="#999" />
              <Text style={styles.memberCountText}>{members.length} miembros</Text>
            </View>
          </View>

          <TouchableOpacity style={styles.codeBox} onPress={copyCode} activeOpacity={0.7}>
            <View>
              <Text style={styles.codeLabel}>Código de invitación</Text>
              <Text style={styles.codeValue}>{league?.code}</Text>
            </View>
            <View style={styles.copyButton}>
              <Ionicons name="copy-outline" size={20} color="#0047AB" />
              <Text style={styles.copyText}>Copiar</Text>
            </View>
          </TouchableOpacity>
          
          <Text style={styles.inviteHint}>
            Comparte este código para que tus amigos se unan
          </Text>
        </View>

        {/* Jornada Info */}
        {jornada && (
          <View style={styles.jornadaInfo}>
            <Text style={styles.jornadaText}>
              Jornada {jornada.week_number}
            </Text>
            <View style={[
              styles.jornadaStatus,
              jornada.status === 'finished' ? styles.statusFinished : styles.statusOpen
            ]}>
              <Text style={styles.jornadaStatusText}>
                {jornada.status === 'finished' ? 'Finalizada' : 'Abierta'}
              </Text>
            </View>
          </View>
        )}

        {/* Tabs */}
        <View style={styles.tabs}>
          <TouchableOpacity
            style={[styles.tab, activeTab === 'jornada' && styles.tabActive]}
            onPress={() => setActiveTab('jornada')}
          >
            <Ionicons 
              name="calendar" 
              size={18} 
              color={activeTab === 'jornada' ? '#FFFFFF' : '#666'} 
            />
            <Text style={[styles.tabText, activeTab === 'jornada' && styles.tabTextActive]}>
              Jornada
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.tab, activeTab === 'general' && styles.tabActive]}
            onPress={() => setActiveTab('general')}
          >
            <Ionicons 
              name="trophy" 
              size={18} 
              color={activeTab === 'general' ? '#FFFFFF' : '#666'} 
            />
            <Text style={[styles.tabText, activeTab === 'general' && styles.tabTextActive]}>
              General
            </Text>
          </TouchableOpacity>
        </View>

        {/* Rankings */}
        <View style={styles.rankingContainer}>
          <Text style={styles.rankingTitle}>
            {activeTab === 'jornada' ? '📊 Ranking Jornada' : '🏆 Ranking General'}
          </Text>

          {activeTab === 'jornada' ? (
            jornadaRankings.length > 0 ? (
              jornadaRankings.map(renderJornadaRankingItem)
            ) : (
              <View style={styles.emptyRanking}>
                <Ionicons name="hourglass-outline" size={48} color="#333" />
                <Text style={styles.emptyText}>
                  Los puntos se calcularán al finalizar la jornada
                </Text>
              </View>
            )
          ) : (
            members.map(renderGeneralRankingItem)
          )}
        </View>

        {/* Results Button for Quiniela */}
        {!isFantasy && jornada?.status === 'finished' && (
          <TouchableOpacity style={styles.resultsButton} onPress={viewResults}>
            <Ionicons name="grid-outline" size={20} color="#FFFFFF" />
            <Text style={styles.resultsButtonText}>Ver Matriz de Resultados</Text>
          </TouchableOpacity>
        )}

        <View style={{ height: 40 }} />
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    flex: 1,
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'center',
    marginHorizontal: 8,
  },
  shareButton: {
    padding: 8,
  },
  scrollView: {
    flex: 1,
  },
  infoCard: {
    margin: 16,
    padding: 16,
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  modeTag: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    gap: 6,
  },
  modeTagQuiniela: {
    backgroundColor: '#DC143C',
  },
  modeTagFantasy: {
    backgroundColor: '#0047AB',
  },
  modeTagText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  memberCount: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  memberCountText: {
    fontSize: 14,
    color: '#999',
  },
  codeBox: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#0a0a0a',
    padding: 16,
    borderRadius: 8,
    marginBottom: 8,
  },
  codeLabel: {
    fontSize: 12,
    color: '#999',
    marginBottom: 4,
  },
  codeValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#0047AB',
    letterSpacing: 4,
  },
  copyButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    gap: 6,
  },
  copyText: {
    fontSize: 12,
    color: '#0047AB',
    fontWeight: '600',
  },
  inviteHint: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  jornadaInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 12,
    backgroundColor: '#1a1a1a',
    borderRadius: 8,
  },
  jornadaText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  jornadaStatus: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusOpen: {
    backgroundColor: '#00A551',
  },
  statusFinished: {
    backgroundColor: '#666',
  },
  jornadaStatusText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  tabs: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 16,
    gap: 8,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    gap: 6,
  },
  tabActive: {
    backgroundColor: '#DC143C',
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  tabTextActive: {
    color: '#FFFFFF',
  },
  rankingContainer: {
    marginHorizontal: 16,
  },
  rankingTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 12,
  },
  rankingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#333',
  },
  rankingItemHighlight: {
    borderColor: '#DC143C',
    backgroundColor: '#1a0a0a',
  },
  rankBadge: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#0a0a0a',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  rankText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  memberInfo: {
    flex: 1,
  },
  memberName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  teamName: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  pointsContainer: {
    alignItems: 'center',
    marginRight: 8,
  },
  pointsValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  pointsJornada: {
    color: '#00A551',
  },
  pointsLabel: {
    fontSize: 10,
    color: '#999',
  },
  breakdownContainer: {
    backgroundColor: '#0a0a0a',
    marginLeft: 52,
    marginBottom: 8,
    borderRadius: 8,
    padding: 12,
  },
  breakdownItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  breakdownPlayer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  breakdownPosition: {
    fontSize: 10,
    color: '#666',
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  breakdownName: {
    fontSize: 12,
    color: '#FFFFFF',
  },
  breakdownPoints: {
    alignItems: 'flex-end',
  },
  breakdownPointsValue: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  pointsPositive: {
    color: '#00A551',
  },
  pointsNegative: {
    color: '#DC143C',
  },
  emptyRanking: {
    alignItems: 'center',
    padding: 32,
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 12,
  },
  resultsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0047AB',
    marginHorizontal: 16,
    marginTop: 16,
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  resultsButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
});
