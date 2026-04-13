import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';

interface MyStats {
  total_puntos: number;
  jornadas_quiniela: number;
  mejor_jornada: number;
  win_rate: number;
  total_aciertos: number;
  promedio_aciertos: number;
  jornadas_fantasy: number;
  mejor_posicion: number | null;
  ligas_activas: number;
}

export default function ProfileScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [stats, setStats] = useState<MyStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const res = await api.get('/api/stats/my');
      setStats(res.data);
    } catch (err) {
      console.log('Stats not available:', err);
    } finally {
      setLoadingStats(false);
    }
  };

  const handleLogout = () => {
    Alert.alert(
      'Cerrar sesión',
      '¿Estás seguro que deseas cerrar sesión?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Cerrar sesión',
          style: 'destructive',
          onPress: async () => {
            await logout();
            router.replace('/(auth)/login');
          },
        },
      ]
    );
  };

  const StatCard = ({ label, value, icon }: { label: string; value: string; icon: string }) => (
    <View style={styles.statCard}>
      <Text style={styles.statCardIcon}>{icon}</Text>
      <Text style={styles.statCardValue}>{value}</Text>
      <Text style={styles.statCardLabel}>{label}</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      <ScrollView style={styles.content}>
        <View style={styles.profileHeader}>
          <View style={styles.avatarContainer}>
            <Ionicons name="person" size={48} color="#DC143C" />
          </View>
          <Text style={styles.displayName}>{user?.display_name}</Text>
          <Text style={styles.email}>{user?.email}</Text>
        </View>

        {/* ── MI ESTADÍSTICA ── */}
        <View style={styles.statsSection}>
          <Text style={styles.sectionTitle}>MI ESTADÍSTICA</Text>
          {loadingStats ? (
            <ActivityIndicator color="#DC143C" style={{ marginVertical: 16 }} />
          ) : (
            <View style={styles.statsGrid}>
              <StatCard
                icon="⚡"
                label="Puntos totales"
                value={String(stats?.total_puntos ?? 0)}
              />
              <StatCard
                icon="📅"
                label="Jornadas jugadas"
                value={String(stats?.jornadas_quiniela ?? 0)}
              />
              <StatCard
                icon="🏆"
                label="Mejor jornada"
                value={String(stats?.mejor_jornada ?? 0)} 
              />
              <StatCard
                icon="🎯"
                label="Win rate"
                value={`${stats?.win_rate ?? 0}%`}
              />
              <StatCard
                icon="✅"
                label="Total aciertos"
                value={String(stats?.total_aciertos ?? 0)}
              />
              <StatCard
                icon="📊"
                label="Prom. aciertos"
                value={String(stats?.promedio_aciertos ?? 0)}
              />
              <StatCard
                icon="⚽"
                label="J. FuchoOnce"
                value={String(stats?.jornadas_fantasy ?? 0)}
              />
              <StatCard
                icon="🥇"
                label="Mejor posición"
                value={stats?.mejor_posicion ? `#${stats.mejor_posicion}` : '-'}
              />
            </View>
          )}
        </View>

        <View style={styles.menuSection}>
          <Text style={styles.sectionTitle}>MI ACTIVIDAD</Text>

          <TouchableOpacity
            style={styles.achievementsButton}
            onPress={() => router.push('/profile/achievements')}
          >
            <Text style={styles.achievementsEmoji}>🏅</Text>
            <View style={styles.achievementsTextContainer}>
              <Text style={styles.achievementsTitle}>Logros y Rachas</Text>
              <Text style={styles.achievementsSubtitle}>Ver mis insignias y rachas</Text>
            </View>
            <Text style={styles.achievementsArrow}>→</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.planButton}
            onPress={() => router.push('/profile/plan')}
          >
            <Text style={styles.achievementsEmoji}>🎉</Text>
            <View style={styles.achievementsTextContainer}>
              <Text style={styles.achievementsTitle}>Tu Plan Gratuito</Text>
              <Text style={styles.achievementsSubtitle}>Ver qué incluye tu plan</Text>
            </View>
            <Text style={styles.achievementsArrow}>→</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.menuSection}>
          <Text style={styles.sectionTitle}>AJUSTES</Text>
          
          <TouchableOpacity style={styles.menuItem}>
            <Ionicons name="notifications-outline" size={24} color="#FFFFFF" />
            <Text style={styles.menuText}>Notificaciones</Text>
            <Ionicons name="chevron-forward" size={24} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <Ionicons name="card-outline" size={24} color="#FFFFFF" />
            <Text style={styles.menuText}>Suscripción</Text>
            <Ionicons name="chevron-forward" size={24} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <Ionicons name="help-circle-outline" size={24} color="#FFFFFF" />
            <Text style={styles.menuText}>Ayuda</Text>
            <Ionicons name="chevron-forward" size={24} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <Ionicons name="information-circle-outline" size={24} color="#FFFFFF" />
            <Text style={styles.menuText}>Acerca de</Text>
            <Ionicons name="chevron-forward" size={24} color="#666" />
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={24} color="#DC143C" />
          <Text style={styles.logoutText}>Cerrar sesión</Text>
        </TouchableOpacity>

        <Text style={styles.version}>Versión 1.0.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  content: {
    flex: 1,
  },
  profileHeader: {
    alignItems: 'center',
    paddingVertical: 32,
    paddingHorizontal: 24,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  avatarContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#1a1a1a',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#DC143C',
    marginBottom: 16,
  },
  displayName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  email: {
    fontSize: 14,
    color: '#999',
    marginBottom: 0,
  },
  // ── Stats Section ──────────────────────────
  statsSection: {
    paddingHorizontal: 16,
    paddingTop: 24,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 12,
  },
  statCard: {
    backgroundColor: '#111',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#1E1E1E',
    width: '48%',
    padding: 14,
    alignItems: 'center',
  },
  statCardIcon: {
    fontSize: 22,
    marginBottom: 6,
  },
  statCardValue: {
    fontSize: 22,
    fontWeight: '900',
    color: '#DC143C',
    marginBottom: 2,
  },
  statCardLabel: {
    fontSize: 11,
    color: '#666',
    textAlign: 'center',
    fontWeight: '600',
    letterSpacing: 0.3,
  },
  // ── Menu ──────────────────────────────────
  menuSection: {
    paddingHorizontal: 24,
    paddingTop: 28,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#666',
    marginBottom: 16,
    letterSpacing: 1,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  menuText: {
    flex: 1,
    fontSize: 16,
    color: '#FFFFFF',
    marginLeft: 16,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginHorizontal: 24,
    marginTop: 32,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#DC143C',
  },
  logoutText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#DC143C',
    marginLeft: 12,
  },
  version: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    marginTop: 24,
    marginBottom: 32,
  },
  achievementsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
    borderWidth: 1,
    borderColor: '#1E1E1E',
  },
  achievementsEmoji: {
    fontSize: 24,
    marginRight: 12,
  },
  achievementsTextContainer: {
    flex: 1,
  },
  achievementsTitle: {
    color: '#FFF',
    fontSize: 15,
    fontWeight: '700',
  },
  achievementsSubtitle: {
    color: '#555',
    fontSize: 12,
  },
  achievementsArrow: {
    color: '#E63946',
    fontSize: 18,
  },
  planButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#111',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
    borderWidth: 1,
    borderColor: '#E6394622',
  },
});
