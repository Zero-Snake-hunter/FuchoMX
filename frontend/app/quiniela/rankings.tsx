import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';


interface Ranking {
  position: number;
  user_id: string;
  display_name: string;
  total_points: number;
  avatar_base64: string | null;
}

export default function RankingsScreen() {
  const [rankings, setRankings] = useState<Ranking[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadRankings();
  }, []);

  const loadRankings = async () => {
    try {
      const response = await api.get(`/api/quiniela/rankings/general`);
      setRankings(response.data.rankings);
    } catch (error) {
      console.error('Error loading rankings:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadRankings();
  };

  const getMedalIcon = (position: number) => {
    if (position === 1) return { name: 'trophy' as const, color: '#FFD700' };
    if (position === 2) return { name: 'medal' as const, color: '#C0C0C0' };
    if (position === 3) return { name: 'medal' as const, color: '#CD7F32' };
    return null;
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#DC143C" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#DC143C"
          />
        }
      >
        {rankings.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="podium-outline" size={80} color="#333" />
            <Text style={styles.emptyTitle}>Aún no hay rankings</Text>
            <Text style={styles.emptyDescription}>
              Los rankings se mostrarán una vez que se calculen los puntos
            </Text>
          </View>
        ) : (
          <View style={styles.rankingsContainer}>
            <Text style={styles.sectionTitle}>CLASIFICACIÓN GENERAL</Text>
            {rankings.map((ranking) => {
              const medal = getMedalIcon(ranking.position);
              return (
                <View
                  key={ranking.user_id}
                  style={[
                    styles.rankingItem,
                    ranking.position <= 3 && styles.topThree,
                  ]}
                >
                  <View style={styles.positionContainer}>
                    {medal ? (
                      <Ionicons name={medal.name} size={24} color={medal.color} />
                    ) : (
                      <Text style={styles.position}>{ranking.position}</Text>
                    )}
                  </View>

                  <View style={styles.avatarContainer}>
                    <Ionicons name="person-circle" size={40} color="#DC143C" />
                  </View>

                  <View style={styles.userInfo}>
                    <Text style={styles.userName}>{ranking.display_name}</Text>
                  </View>

                  <View style={styles.pointsContainer}>
                    <Text style={styles.points}>{ranking.total_points}</Text>
                    <Text style={styles.pointsLabel}>pts</Text>
                  </View>
                </View>
              );
            })}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
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
  content: {
    flex: 1,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 48,
    paddingTop: 120,
  },
  emptyTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginTop: 24,
    marginBottom: 12,
  },
  emptyDescription: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    lineHeight: 20,
  },
  rankingsContainer: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#666',
    letterSpacing: 1,
    marginBottom: 16,
  },
  rankingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    padding: 16,
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#333',
  },
  topThree: {
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
  avatarContainer: {
    marginRight: 12,
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  pointsContainer: {
    alignItems: 'flex-end',
  },
  points: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#DC143C',
  },
  pointsLabel: {
    fontSize: 12,
    color: '#999',
  },
});
