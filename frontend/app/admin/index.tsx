import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
  Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';

const ADMIN_EMAIL = 'contacto@fuchomx.mx';

interface AdminStats {
  usuarios: {
    total: number;
    nuevos_hoy: number;
    nuevos_semana: number;
    nuevos_mes: number;
    ultimos: { email: string; display_name: string; created_at: string; total_points: number }[];
  };
  jornadas: { total: number; activa: number | null };
  predicciones: { total: number };
  ligas: { total: number; activas: number };
  fantasy: { total_lineups: number };
}

export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Verificar acceso
  useEffect(() => {
    if (user && user.email !== ADMIN_EMAIL) {
      Alert.alert('Sin acceso', 'Esta sección es solo para administradores.');
      router.replace('/(tabs)/home');
    }
  }, [user]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await api.get('/api/admin/stats');
      setStats(response.data);
    } catch (error: any) {
      Alert.alert('Error', 'No se pudieron cargar las estadísticas');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchStats();
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  if (!user || user.email !== ADMIN_EMAIL) return null;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#E63946" />}
    >
      {/* Header */}
      <View style={styles.header}>
        <Image
          source={require('../../assets/images/FuchoMX.png')}
          style={styles.logo}
          resizeMode="contain"
        />
        <View style={styles.headerText}>
          <Text style={styles.title}>Admin Dashboard</Text>
          <Text style={styles.subtitle}>FuchoMX</Text>
        </View>
        <TouchableOpacity onPress={onRefresh} style={styles.refreshBtn}>
          <Ionicons name="refresh" size={22} color="#E63946" />
        </TouchableOpacity>
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#E63946" />
          <Text style={styles.loadingText}>Cargando métricas...</Text>
        </View>
      ) : stats ? (
        <>
          {/* Fila principal de usuarios */}
          <Text style={styles.sectionTitle}>👥 Usuarios</Text>
          <View style={styles.row}>
            <StatCard label="Total" value={stats.usuarios.total} icon="people" color="#E63946" />
            <StatCard label="Hoy" value={stats.usuarios.nuevos_hoy} icon="today" color="#4CAF50" />
          </View>
          <View style={styles.row}>
            <StatCard label="Esta semana" value={stats.usuarios.nuevos_semana} icon="calendar" color="#2196F3" />
            <StatCard label="Este mes" value={stats.usuarios.nuevos_mes} icon="bar-chart" color="#FF9800" />
          </View>

          {/* Jornadas y ligas */}
          <Text style={styles.sectionTitle}>⚽ App</Text>
          <View style={styles.row}>
            <StatCard label="Jornadas" value={stats.jornadas.total} icon="football" color="#9C27B0" />
            <StatCard
              label="Jornada activa"
              value={stats.jornadas.activa ?? '-'}
              icon="play-circle"
              color="#00BCD4"
            />
          </View>
          <View style={styles.row}>
            <StatCard label="Predicciones" value={stats.predicciones.total} icon="checkmark-circle" color="#E63946" />
            <StatCard label="Ligas activas" value={stats.ligas.activas} icon="trophy" color="#FFD700" />
          </View>
          <View style={styles.row}>
            <StatCard label="Lineups Fantasy" value={stats.fantasy.total_lineups} icon="shirt" color="#4CAF50" />
            <StatCard label="Ligas totales" value={stats.ligas.total} icon="grid" color="#607D8B" />
          </View>

          {/* Últimos registros */}
          <Text style={styles.sectionTitle}>🆕 Últimos registros</Text>
          <View style={styles.card}>
            {stats.usuarios.ultimos.length === 0 ? (
              <Text style={styles.emptyText}>Sin registros aún</Text>
            ) : (
              stats.usuarios.ultimos.map((u, i) => (
                <View key={i} style={[styles.userRow, i < stats.usuarios.ultimos.length - 1 && styles.userRowBorder]}>
                  <View style={styles.userAvatar}>
                    <Text style={styles.userAvatarText}>{u.display_name?.[0]?.toUpperCase() || '?'}</Text>
                  </View>
                  <View style={styles.userInfo}>
                    <Text style={styles.userName}>{u.display_name || 'Sin nombre'}</Text>
                    <Text style={styles.userEmail}>{u.email}</Text>
                    <Text style={styles.userDate}>{formatDate(u.created_at)}</Text>
                  </View>
                  <View style={styles.userPoints}>
                    <Text style={styles.userPointsValue}>{u.total_points ?? 0}</Text>
                    <Text style={styles.userPointsLabel}>pts</Text>
                  </View>
                </View>
              ))
            )}
          </View>

          {/* Botón logout */}
          <TouchableOpacity
            style={styles.logoutBtn}
            onPress={async () => {
              await logout();
              router.replace('/(auth)/login');
            }}
          >
            <Ionicons name="log-out-outline" size={18} color="#999" />
            <Text style={styles.logoutText}>Cerrar sesión</Text>
          </TouchableOpacity>
        </>
      ) : (
        <View style={styles.loadingContainer}>
          <Ionicons name="alert-circle-outline" size={48} color="#666" />
          <Text style={styles.loadingText}>No se pudieron cargar los datos</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={fetchStats}>
            <Text style={styles.retryText}>Reintentar</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: any; icon: any; color: string }) {
  return (
    <View style={[styles.statCard, { borderLeftColor: color }]}>
      <View style={[styles.statIcon, { backgroundColor: color + '22' }]}>
        <Ionicons name={icon} size={22} color={color} />
      </View>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#090909',
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
    paddingTop: 48,
  },
  logo: {
    width: 44,
    height: 44,
  },
  headerText: {
    flex: 1,
    marginLeft: 12,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  subtitle: {
    fontSize: 13,
    color: '#E63946',
  },
  refreshBtn: {
    padding: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#AAAAAA',
    marginBottom: 12,
    marginTop: 8,
  },
  row: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#181818',
    borderRadius: 12,
    padding: 16,
    borderLeftWidth: 3,
    alignItems: 'center',
  },
  statIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  statValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  statLabel: {
    fontSize: 12,
    color: '#AAAAAA',
    marginTop: 4,
    textAlign: 'center',
  },
  card: {
    backgroundColor: '#181818',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  userRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
  },
  userRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: '#2a2a2a',
  },
  userAvatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#E63946',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  userAvatarText: {
    color: '#FFF',
    fontWeight: 'bold',
    fontSize: 16,
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    color: '#FFFFFF',
    fontWeight: '600',
    fontSize: 14,
  },
  userEmail: {
    color: '#AAAAAA',
    fontSize: 12,
    marginTop: 2,
  },
  userDate: {
    color: '#666',
    fontSize: 11,
    marginTop: 2,
  },
  userPoints: {
    alignItems: 'center',
  },
  userPointsValue: {
    color: '#E63946',
    fontWeight: 'bold',
    fontSize: 18,
  },
  userPointsLabel: {
    color: '#666',
    fontSize: 11,
  },
  emptyText: {
    color: '#666',
    textAlign: 'center',
    padding: 16,
  },
  loadingContainer: {
    alignItems: 'center',
    paddingTop: 80,
    gap: 16,
  },
  loadingText: {
    color: '#AAAAAA',
    fontSize: 15,
  },
  retryBtn: {
    backgroundColor: '#E63946',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryText: {
    color: '#FFF',
    fontWeight: 'bold',
  },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 16,
    marginTop: 8,
    marginBottom: 32,
  },
  logoutText: {
    color: '#999',
    fontSize: 14,
  },
});
