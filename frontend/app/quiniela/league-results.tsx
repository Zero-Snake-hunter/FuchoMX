import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';

const { width } = Dimensions.get('window');

export default function LeagueResultsScreen() {
  const { leagueId, jornadaId } = useLocalSearchParams();
  const { token } = useAuth();
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadResults();
  }, []);

  const loadResults = async () => {
    try {
      console.log('📡 [LeagueResults] Cargando resultados para liga:', leagueId, 'jornada:', jornadaId);
      const response = await api.get(
        `/api/quiniela/league/${leagueId}/results?jornada_id=${jornadaId}`
      );
      setResults(response.data);
      console.log('✅ [LeagueResults] Resultados cargados');
    } catch (error) {
      console.error('❌ [LeagueResults] Error loading results:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#DC143C" />
      </View>
    );
  }

  if (!results || results.results.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Ionicons name="grid-outline" size={80} color="#333" />
        <Text style={styles.emptyTitle}>Sin resultados</Text>
        <Text style={styles.emptyText}>
          Los resultados aparecerán cuando finalice la jornada
        </Text>
      </View>
    );
  }

  // Get unique users from first match
  const users = results.results[0]?.predictions || [];

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>{results.jornada?.type === 'liguilla' && results.jornada?.title ? results.jornada.title.replace('Liguilla Clausura 2026 — ', '') : `Jornada ${results.jornada.week_number}`}</Text>
        <Text style={styles.headerSubtitle}>Resultados Detallados</Text>
      </View>

      {/* Table Container */}
      <ScrollView horizontal showsHorizontalScrollIndicator={true} style={styles.horizontalScroll}>
        <View>
          {/* Table Header */}
          <View style={styles.tableHeader}>
            <View style={[styles.cell, styles.matchCell, styles.headerCell]}>
              <Text style={styles.headerText}>PARTIDO</Text>
            </View>
            {users.map((user: any) => (
              <View key={user.user_id} style={[styles.cell, styles.userCell, styles.headerCell]}>
                <Text style={styles.headerText} numberOfLines={1}>
                  {user.user_name}
                </Text>
              </View>
            ))}
          </View>

          {/* Table Body */}
          <ScrollView style={styles.verticalScroll} showsVerticalScrollIndicator={true}>
            {results.results.map((match: any, idx: number) => (
              <View key={match.match_id} style={styles.tableRow}>
                {/* Match Cell */}
                <View style={[styles.cell, styles.matchCell, idx % 2 === 0 && styles.rowEven]}>
                  <Text style={styles.matchText}>
                    {match.home_team} vs {match.away_team}
                  </Text>
                  {match.home_score !== null && match.away_score !== null && (
                    <Text style={styles.scoreText}>
                      {match.home_score} - {match.away_score}
                    </Text>
                  )}
                </View>

                {/* Prediction Cells */}
                {match.predictions.map((pred: any) => {
                  const icon = pred.is_correct ? (
                    <Ionicons name="checkmark-circle" size={32} color="#00A551" />
                  ) : pred.selection === null ? (
                    <Ionicons name="remove-circle" size={32} color="#666" />
                  ) : (
                    <Ionicons name="close-circle" size={32} color="#DC143C" />
                  );

                  return (
                    <View
                      key={pred.user_id}
                      style={[
                        styles.cell,
                        styles.userCell,
                        idx % 2 === 0 && styles.rowEven,
                        pred.is_correct && styles.correctCell,
                      ]}
                    >
                      {icon}
                    </View>
                  );
                })}
              </View>
            ))}

            {/* Points Row */}
            <View style={[styles.tableRow, styles.pointsRow]}>
              <View style={[styles.cell, styles.matchCell, styles.pointsCell]}>
                <Text style={styles.pointsLabel}>TOTAL</Text>
              </View>
              {users.map((user: any) => {
                const userPoints = results.user_points[user.user_id];
                return (
                  <View key={user.user_id} style={[styles.cell, styles.userCell, styles.pointsCell]}>
                    <Text style={styles.pointsValue}>{userPoints?.points || 0}</Text>
                  </View>
                );
              })}
            </View>
          </ScrollView>
        </View>
      </ScrollView>

      {/* Legend */}
      <View style={styles.legend}>
        <View style={styles.legendItem}>
          <Ionicons name="checkmark-circle" size={20} color="#00A551" />
          <Text style={styles.legendText}>Acierto</Text>
        </View>
        <View style={styles.legendItem}>
          <Ionicons name="close-circle" size={20} color="#DC143C" />
          <Text style={styles.legendText}>Error</Text>
        </View>
        <View style={styles.legendItem}>
          <Ionicons name="remove-circle" size={20} color="#666" />
          <Text style={styles.legendText}>Sin enviar</Text>
        </View>
      </View>
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
  emptyContainer: {
    flex: 1,
    backgroundColor: '#000000',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 48,
  },
  emptyTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginTop: 24,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    lineHeight: 20,
  },
  header: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#999',
    marginTop: 4,
  },
  horizontalScroll: {
    flex: 1,
  },
  verticalScroll: {
    flex: 1,
  },
  tableHeader: {
    flexDirection: 'row',
    backgroundColor: '#1a1a1a',
    borderBottomWidth: 2,
    borderBottomColor: '#DC143C',
  },
  tableRow: {
    flexDirection: 'row',
  },
  cell: {
    padding: 12,
    justifyContent: 'center',
    alignItems: 'center',
    borderRightWidth: 1,
    borderRightColor: '#333',
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  matchCell: {
    width: 140,
    alignItems: 'flex-start',
  },
  userCell: {
    width: 100,
  },
  headerCell: {
    backgroundColor: '#1a1a1a',
  },
  headerText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textTransform: 'uppercase',
  },
  rowEven: {
    backgroundColor: '#0a0a0a',
  },
  matchText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  scoreText: {
    fontSize: 12,
    color: '#0047AB',
    marginTop: 4,
    fontWeight: 'bold',
  },
  correctCell: {
    backgroundColor: '#0a2a1a',
  },
  pointsRow: {
    borderTopWidth: 2,
    borderTopColor: '#DC143C',
  },
  pointsCell: {
    backgroundColor: '#1a1a1a',
  },
  pointsLabel: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  pointsValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#DC143C',
  },
  legend: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: 16,
    backgroundColor: '#1a1a1a',
    borderTopWidth: 1,
    borderTopColor: '#333',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  legendText: {
    fontSize: 12,
    color: '#999',
  },
});
