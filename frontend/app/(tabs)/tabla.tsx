import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  ScrollView,
  Image,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';

interface StandingRow {
  id: string;
  name: string;
  short_name: string;
  shield_url: string;
  pj: number;
  pg: number;
  pe: number;
  pp: number;
  gf: number;
  gc: number;
  dg: number;
  pts: number;
  position: number;
}

const LIGUILLA_SPOTS = 8;

export default function TablaScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [standings, setStandings] = useState<StandingRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const loadStandings = useCallback(async () => {
    try {
      setError(null);
      const res = await api.get('/api/standings');
      setStandings(res.data.standings || []);
    } catch (err: any) {
      console.error('Error loading standings:', err);
      setError('No se pudo cargar la tabla general');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadStandings();
  }, [loadStandings]);

  const onRefresh = () => {
    setRefreshing(true);
    loadStandings();
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      <View style={styles.header}>
        <Ionicons name="list" size={32} color="#DC143C" />
        <Text style={styles.headerTitle}>TABLA GENERAL</Text>
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#DC143C" />
        </View>
      ) : error ? (
        <View style={styles.emptyState}>
          <Ionicons name="alert-circle" size={64} color="#333" />
          <Text style={styles.emptyTitle}>{error}</Text>
        </View>
      ) : standings.length === 0 ? (
        <View style={styles.emptyState}>
          <Ionicons name="football" size={64} color="#333" />
          <Text style={styles.emptyTitle}>Aún no hay partidos terminados</Text>
          <Text style={styles.emptyDescription}>
            La tabla se llena conforme se juegan las jornadas
          </Text>
        </View>
      ) : (
        <ScrollView
          style={styles.content}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#DC143C" />}
        >
          <View style={styles.legendRow}>
            <View style={styles.legendDot} />
            <Text style={styles.legendText}>Top 8 — clasifica a Liguilla</Text>
          </View>

          <ScrollView horizontal showsHorizontalScrollIndicator={true}>
            <View>
              <View style={[styles.row, styles.headRow]}>
                <Text style={[styles.cell, styles.posCell, styles.headText]}>#</Text>
                <Text style={[styles.cell, styles.shieldCell, styles.headText]} />
                <Text style={[styles.cell, styles.teamCell, styles.headText]}>Equipo</Text>
                <Text style={[styles.cell, styles.statCell, styles.headText]}>PJ</Text>
                <Text style={[styles.cell, styles.statCell, styles.headText]}>PG</Text>
                <Text style={[styles.cell, styles.statCell, styles.headText]}>PE</Text>
                <Text style={[styles.cell, styles.statCell, styles.headText]}>PP</Text>
                <Text style={[styles.cell, styles.statCell, styles.headText]}>GF</Text>
                <Text style={[styles.cell, styles.statCell, styles.headText]}>GC</Text>
                <Text style={[styles.cell, styles.statCell, styles.headText]}>DG</Text>
                <Text style={[styles.cell, styles.ptsCell, styles.headText]}>PTS</Text>
              </View>

              {standings.map((row) => {
                const qualifies = row.position <= LIGUILLA_SPOTS;
                return (
                  <View
                    key={row.id}
                    style={[styles.row, qualifies && styles.qualifiesRow]}
                  >
                    <Text style={[styles.cell, styles.posCell, styles.posText]}>{row.position}</Text>
                    <View style={[styles.cell, styles.shieldCell]}>
                      {row.shield_url ? (
                        <Image source={{ uri: row.shield_url }} style={styles.shield} />
                      ) : (
                        <View style={styles.shieldPlaceholder} />
                      )}
                    </View>
                    <Text style={[styles.cell, styles.teamCell, styles.teamText]} numberOfLines={1}>
                      {row.short_name || row.name}
                    </Text>
                    <Text style={[styles.cell, styles.statCell, styles.statText]}>{row.pj}</Text>
                    <Text style={[styles.cell, styles.statCell, styles.statText]}>{row.pg}</Text>
                    <Text style={[styles.cell, styles.statCell, styles.statText]}>{row.pe}</Text>
                    <Text style={[styles.cell, styles.statCell, styles.statText]}>{row.pp}</Text>
                    <Text style={[styles.cell, styles.statCell, styles.statText]}>{row.gf}</Text>
                    <Text style={[styles.cell, styles.statCell, styles.statText]}>{row.gc}</Text>
                    <Text style={[styles.cell, styles.statCell, styles.statText]}>
                      {row.dg > 0 ? `+${row.dg}` : row.dg}
                    </Text>
                    <Text style={[styles.cell, styles.ptsCell, styles.ptsText]}>{row.pts}</Text>
                  </View>
                );
              })}
            </View>
          </ScrollView>

          <View style={{ height: 32 }} />
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 24,
    gap: 12,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFFFFF',
    letterSpacing: 1,
  },
  content: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 48,
    paddingTop: 120,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginTop: 24,
    marginBottom: 12,
    textAlign: 'center',
  },
  emptyDescription: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    lineHeight: 20,
  },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingBottom: 12,
    gap: 8,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: 'rgba(46, 204, 113, 0.35)',
    borderWidth: 1,
    borderColor: 'rgba(46, 204, 113, 0.8)',
  },
  legendText: {
    fontSize: 12,
    color: '#999',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  headRow: {
    borderBottomWidth: 2,
    borderBottomColor: '#333',
    paddingVertical: 8,
  },
  qualifiesRow: {
    backgroundColor: 'rgba(46, 204, 113, 0.08)',
  },
  cell: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  headText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#777',
  },
  posCell: {
    width: 28,
    paddingLeft: 20,
  },
  posText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#DC143C',
  },
  shieldCell: {
    width: 32,
  },
  shield: {
    width: 24,
    height: 24,
    resizeMode: 'contain',
  },
  shieldPlaceholder: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#222',
  },
  teamCell: {
    width: 80,
    alignItems: 'flex-start',
  },
  teamText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  statCell: {
    width: 32,
  },
  statText: {
    fontSize: 12,
    color: '#CCCCCC',
  },
  ptsCell: {
    width: 40,
    paddingRight: 20,
  },
  ptsText: {
    fontSize: 14,
    fontWeight: '800',
    color: '#FFFFFF',
  },
});
