import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  ActivityIndicator, RefreshControl, Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import api from '../lib/api';

const ADMIN_EMAIL = 'contacto@distrito.digital';

interface Liga {
  id: string;
  nombre: string;
  modo: string;
  codigo: string;
  creador: string;
  miembros: number;
  creada: string;
}

interface JornadaActivaInfo {
  week_number: number;
  start_date: string | null;
  end_date: string | null;
  status: string;
}

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
  ligas: { total: number; detalle: Liga[] };
  fantasy: { total_lineups: number };
  competencia_activa: string;
  jornada_activa_info: JornadaActivaInfo | null;
  engagement_jornada_activa: {
    picks_guardados: number;
    alineaciones_guardadas: number;
  };
}

type Tab = 'resumen' | 'usuarios' | 'ligas';

export default function AdminDashboard() {
  const { user, logout, isReady } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('resumen');
  const [actionLoading, setActionLoading] = useState<{ [key: string]: boolean }>({});

  const closeJornada = async () => {
    try {
      const response = await api.post('/api/admin/close-all-jornadas');
      showToast('success', response.data.message || 'Jornadas cerradas');
      fetchStats();
    } catch (error: any) {
      showToast('error', error.message);
    }
  };

  const runAdminAction = async (
    key: string,
    action: () => Promise<any>,
    formatSuccess: (data: any) => string
  ) => {
    setActionLoading(prev => ({ ...prev, [key]: true }));
    try {
      const response = await action();
      showToast('success', formatSuccess(response.data), 4000);
      fetchStats();
    } catch (error: any) {
      showToast('error', error.response?.data?.detail || error.message || 'Ocurrió un error inesperado', 4000);
    } finally {
      setActionLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const syncResultadosJornadaActiva = () => runAdminAction(
    'sync',
    async () => {
      const current = await api.get('/api/jornadas/current');
      const jornadaId = current.data?.jornada?.id;
      if (!jornadaId) throw new Error('No hay jornada activa');
      return api.post(`/api/admin/jornada/${jornadaId}/sync-365-stats`);
    },
    (data) =>
      `${data.matches_processed ?? 0} partido(s) procesados — ` +
      `${data.players_matched ?? 0} jugadores matched, ${data.players_unmatched ?? 0} sin match`
  );

  const fixNegativeScores = () => runAdminAction(
    'fix',
    () => api.post('/api/admin/fix-negative-scores'),
    (data) => data.message || `${data.modified ?? 0} partido(s) corregidos`
  );

  const syncDtNames = () => runAdminAction(
    'dt',
    () => api.post('/api/admin/sync-dt-names'),
    (data) => data.message || `${data.updated?.length ?? 0} equipo(s) actualizados`
  );

  useEffect(() => {
    if (user && user.email !== ADMIN_EMAIL) {
      showToast('error', 'Sin acceso: esta sección es solo para administradores.');
      router.replace('/(tabs)/home');
    }
  }, [user]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await api.get('/api/admin/stats');
      setStats(response.data);
    } catch (error: any) {
      showToast('error', 'No se pudieron cargar las estadísticas');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { if (isReady) fetchStats(); }, [isReady]);

  const onRefresh = () => { setRefreshing(true); fetchStats(); };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch { return dateStr; }
  };

  const competitionLabel = (c?: string) => {
    if (c === 'world_cup_2026') return 'Mundial 2026';
    if (c === 'liga_mx') return 'Liga MX Apertura 2026';
    return c || '-';
  };

  if (!user || user.email !== ADMIN_EMAIL) return null;

  return (
    <View style={s.root}>
      {/* HEADER */}
      <View style={s.header}>
        <Image source={require('../../assets/images/FuchoMX.png')} style={s.logo} resizeMode="contain" />
        <View style={{ flex: 1, marginLeft: 10 }}>
          <Text style={s.title}>Admin Dashboard</Text>
          <Text style={s.subtitle}>FuchoMX</Text>
        </View>
        <TouchableOpacity onPress={onRefresh} style={s.refreshBtn}>
          <Ionicons name="refresh" size={22} color="#E63946" />
        </TouchableOpacity>
      </View>

      {/* TABS */}
      <View style={s.tabs}>
        {(['resumen', 'usuarios', 'ligas'] as Tab[]).map(tab => (
          <TouchableOpacity
            key={tab}
            style={[s.tab, activeTab === tab && s.tabActive]}
            onPress={() => setActiveTab(tab)}
          >
            <Text style={[s.tabText, activeTab === tab && s.tabTextActive]}>
              {tab === 'resumen' ? '📊 Resumen' : tab === 'usuarios' ? '👥 Usuarios' : '🏆 Ligas'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <View style={s.center}>
          <ActivityIndicator size="large" color="#E63946" />
          <Text style={s.loadingText}>Cargando métricas...</Text>
        </View>
      ) : stats ? (
        <ScrollView
          style={{ flex: 1 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#E63946" />}
          contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
        >
          {/* TAB RESUMEN */}
          {activeTab === 'resumen' && (
            <>
              {/* ── RESUMEN AUTOMÁTICO ───────────────────────────────────── */}
              <Text style={s.sectionTitle}>📋 Resumen</Text>
              <View style={s.summaryCard}>
                <View style={s.summaryRow}>
                  <Text style={s.summaryLabel}>Competición activa</Text>
                  <Text style={s.summaryValue}>{competitionLabel(stats.competencia_activa)}</Text>
                </View>
                <View style={s.summaryRow}>
                  <Text style={s.summaryLabel}>Jornada activa</Text>
                  <Text style={s.summaryValue}>
                    {stats.jornada_activa_info
                      ? `J${stats.jornada_activa_info.week_number} · ${formatDate(stats.jornada_activa_info.start_date || '')} - ${formatDate(stats.jornada_activa_info.end_date || '')}`
                      : 'Sin jornada activa'}
                  </Text>
                </View>
                <View style={s.summaryRow}>
                  <Text style={s.summaryLabel}>Total usuarios</Text>
                  <Text style={s.summaryValue}>{stats.usuarios.total}</Text>
                </View>
                <View style={s.summaryRow}>
                  <Text style={s.summaryLabel}>Picks guardados (jornada)</Text>
                  <Text style={s.summaryValue}>{stats.engagement_jornada_activa?.picks_guardados ?? 0}</Text>
                </View>
                <View style={[s.summaryRow, { borderBottomWidth: 0 }]}>
                  <Text style={s.summaryLabel}>Alineaciones guardadas (jornada)</Text>
                  <Text style={s.summaryValue}>{stats.engagement_jornada_activa?.alineaciones_guardadas ?? 0}</Text>
                </View>
              </View>

              <Text style={s.sectionTitle}>🔧 Herramientas de Admin</Text>

              {/* ── LIGA MX APERTURA 2026 ────────────────────────────────── */}
              <Text style={s.subSectionTitle}>⚽ Liga MX Apertura 2026</Text>

              <TouchableOpacity
                style={[s.actionBtn, actionLoading.sync && s.actionBtnDisabled]}
                onPress={syncResultadosJornadaActiva}
                disabled={actionLoading.sync}
              >
                {actionLoading.sync
                  ? <ActivityIndicator color="#FFF" />
                  : <Text style={s.syncBtnText}>🔄 Sync resultados jornada activa</Text>}
              </TouchableOpacity>

              <TouchableOpacity
                style={[s.actionBtn, actionLoading.fix && s.actionBtnDisabled]}
                onPress={fixNegativeScores}
                disabled={actionLoading.fix}
              >
                {actionLoading.fix
                  ? <ActivityIndicator color="#FFF" />
                  : <Text style={s.syncBtnText}>🔧 Fix marcadores -1/-1</Text>}
              </TouchableOpacity>

              <TouchableOpacity
                style={[s.actionBtn, actionLoading.dt && s.actionBtnDisabled]}
                onPress={syncDtNames}
                disabled={actionLoading.dt}
              >
                {actionLoading.dt
                  ? <ActivityIndicator color="#FFF" />
                  : <Text style={s.syncBtnText}>💊 Sync nombres DT</Text>}
              </TouchableOpacity>

              <TouchableOpacity style={[s.seedBtn, { backgroundColor: '#444' }]} onPress={closeJornada}>
                <Text style={s.syncBtnText}>🔒 Cerrar todas las jornadas activas</Text>
              </TouchableOpacity>

              <Text style={s.sectionTitle}>👥 Usuarios</Text>
              <View style={s.row}>
                <StatCard label="Total" value={stats.usuarios.total} icon="people" color="#E63946" />
                <StatCard label="Hoy" value={stats.usuarios.nuevos_hoy} icon="today" color="#4CAF50" />
              </View>
              <View style={s.row}>
                <StatCard label="Esta semana" value={stats.usuarios.nuevos_semana} icon="calendar" color="#2196F3" />
                <StatCard label="Este mes" value={stats.usuarios.nuevos_mes} icon="bar-chart" color="#FF9800" />
              </View>

              <Text style={s.sectionTitle}>⚽ App</Text>
              <View style={s.row}>
                <StatCard label="Jornadas" value={stats.jornadas.total} icon="football" color="#9C27B0" />
                <StatCard label="Jornada activa" value={stats.jornadas.activa ?? '-'} icon="play-circle" color="#00BCD4" />
              </View>
              <View style={s.row}>
                <StatCard label="Predicciones" value={stats.predicciones.total} icon="checkmark-circle" color="#E63946" />
                <StatCard label="Ligas totales" value={stats.ligas.total} icon="trophy" color="#FFD700" />
              </View>
              <View style={s.row}>
                <StatCard label="Fantasy lineups" value={stats.fantasy.total_lineups} icon="shirt" color="#4CAF50" />
              </View>
            </>
          )}

          {/* TAB USUARIOS */}
          {activeTab === 'usuarios' && (
            <>
              <View style={s.totalBox}>
                <Text style={s.totalNum}>{stats.usuarios.total}</Text>
                <Text style={s.totalLabel}>Usuarios registrados</Text>
              </View>
              <View style={s.row}>
                <StatCard label="Hoy" value={stats.usuarios.nuevos_hoy} icon="today" color="#4CAF50" />
                <StatCard label="Esta semana" value={stats.usuarios.nuevos_semana} icon="calendar" color="#2196F3" />
                <StatCard label="Este mes" value={stats.usuarios.nuevos_mes} icon="bar-chart" color="#FF9800" />
              </View>
              <Text style={s.sectionTitle}>🆕 Últimos registros</Text>
              <View style={s.card}>
                {stats.usuarios.ultimos.length === 0 ? (
                  <Text style={s.emptyText}>Sin registros aún</Text>
                ) : stats.usuarios.ultimos.map((u, i) => (
                  <View key={i} style={[s.userRow, i < stats.usuarios.ultimos.length - 1 && s.userRowBorder]}>
                    <View style={s.userAvatar}>
                      <Text style={s.userAvatarText}>{u.display_name?.[0]?.toUpperCase() || '?'}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={s.userName}>{u.display_name || 'Sin nombre'}</Text>
                      <Text style={s.userEmail}>{u.email}</Text>
                      <Text style={s.userDate}>{formatDate(u.created_at)}</Text>
                    </View>
                    <View style={{ alignItems: 'center' }}>
                      <Text style={s.userPointsValue}>{u.total_points ?? 0}</Text>
                      <Text style={s.userPointsLabel}>pts</Text>
                    </View>
                  </View>
                ))}
              </View>
            </>
          )}

          {/* TAB LIGAS */}
          {activeTab === 'ligas' && (
            <>
              <Text style={s.sectionTitle}>🏆 Ligas creadas ({stats.ligas.total})</Text>
              {stats.ligas.detalle.length === 0 ? (
                <View style={s.card}>
                  <Text style={s.emptyText}>No hay ligas creadas aún</Text>
                </View>
              ) : stats.ligas.detalle.map((liga, i) => (
                <View key={i} style={s.ligaCard}>
                  <View style={s.ligaHeader}>
                    <View style={[s.ligaModeBadge, { backgroundColor: liga.modo === 'fantasy' ? '#1D88E522' : '#E6394622' }]}>
                      <Text style={[s.ligaModeText, { color: liga.modo === 'fantasy' ? '#1D88E5' : '#E63946' }]}>
                        {liga.modo === 'fantasy' ? '⚽ ONCE' : liga.modo === 'ambos' ? '🎮 AMBOS' : '📝 QUINIELA'}
                      </Text>
                    </View>
                    <Text style={s.ligaCodigo}>#{liga.codigo}</Text>
                  </View>
                  <Text style={s.ligaNombre}>{liga.nombre}</Text>
                  <View style={s.ligaFooter}>
                    <View style={s.ligaInfo}>
                      <Ionicons name="person" size={13} color="#666" />
                      <Text style={s.ligaInfoText}>{liga.creador}</Text>
                    </View>
                    <View style={s.ligaInfo}>
                      <Ionicons name="people" size={13} color="#666" />
                      <Text style={s.ligaInfoText}>{liga.miembros} miembro{liga.miembros !== 1 ? 's' : ''}</Text>
                    </View>
                    <View style={s.ligaInfo}>
                      <Ionicons name="calendar" size={13} color="#666" />
                      <Text style={s.ligaInfoText}>{formatDate(liga.creada)}</Text>
                    </View>
                  </View>
                </View>
              ))}
            </>
          )}

          {/* LOGOUT */}
          <TouchableOpacity
            style={s.logoutBtn}
            onPress={async () => { await logout(); router.replace('/(auth)/login'); }}
          >
            <Text style={s.logoutEmoji}>🚪</Text>
            <Text style={s.logoutText}>Cerrar sesión</Text>
          </TouchableOpacity>
        </ScrollView>
      ) : (
        <View style={s.center}>
          <Text style={s.alertEmoji}>⚠️</Text>
          <Text style={s.loadingText}>No se pudieron cargar los datos</Text>
          <TouchableOpacity style={s.retryBtn} onPress={fetchStats}>
            <Text style={s.retryText}>Reintentar</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: any; icon: any; color: string }) {
  return (
    <View style={[s.statCard, { borderLeftColor: color }]}>
      <View style={[s.statIcon, { backgroundColor: color + '22' }]}>
        <Ionicons name={icon} size={22} color={color} />
      </View>
      <Text style={s.statValue}>{value}</Text>
      <Text style={s.statLabel}>{label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root:              { flex: 1, backgroundColor: '#090909' },
  header:            { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingTop: 48, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: '#1a1a1a' },
  logo:              { width: 40, height: 40 },
  title:             { color: '#FFF', fontWeight: 'bold', fontSize: 18 },
  subtitle:          { color: '#E63946', fontSize: 12 },
  refreshBtn:        { padding: 8 },
  tabs:              { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#1a1a1a' },
  tab:               { flex: 1, paddingVertical: 12, alignItems: 'center' },
  tabActive:         { borderBottomWidth: 2, borderBottomColor: '#E63946' },
  tabText:           { color: '#666', fontSize: 13 },
  tabTextActive:     { color: '#FFF', fontWeight: '700' },
  sectionTitle:      { fontSize: 14, fontWeight: 'bold', color: '#AAAAAA', marginBottom: 10, marginTop: 8 },
  subSectionTitle:   { fontSize: 12, fontWeight: '700', color: '#666', marginBottom: 8, marginTop: 4, textTransform: 'uppercase', letterSpacing: 1 },
  row:               { flexDirection: 'row', gap: 12, marginBottom: 12 },
  statCard:          { flex: 1, backgroundColor: '#181818', borderRadius: 12, padding: 14, borderLeftWidth: 3, alignItems: 'center' },
  statIcon:          { width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center', marginBottom: 6 },
  statValue:         { fontSize: 26, fontWeight: 'bold', color: '#FFF' },
  statLabel:         { fontSize: 11, color: '#AAAAAA', marginTop: 2, textAlign: 'center' },
  card:              { backgroundColor: '#181818', borderRadius: 12, padding: 16, marginBottom: 16 },
  userRow:           { flexDirection: 'row', alignItems: 'center', paddingVertical: 10 },
  userRowBorder:     { borderBottomWidth: 1, borderBottomColor: '#2a2a2a' },
  userAvatar:        { width: 38, height: 38, borderRadius: 19, backgroundColor: '#E63946', justifyContent: 'center', alignItems: 'center', marginRight: 10 },
  userAvatarText:    { color: '#FFF', fontWeight: 'bold', fontSize: 15 },
  userName:          { color: '#FFF', fontWeight: '600', fontSize: 13 },
  userEmail:         { color: '#AAAAAA', fontSize: 11, marginTop: 1 },
  userDate:          { color: '#666', fontSize: 10, marginTop: 1 },
  userPointsValue:   { color: '#E63946', fontWeight: 'bold', fontSize: 16 },
  userPointsLabel:   { color: '#666', fontSize: 10 },
  ligaCard:          { backgroundColor: '#181818', borderRadius: 12, padding: 16, marginBottom: 10 },
  ligaHeader:        { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  ligaModeBadge:     { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },
  ligaModeText:      { fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  ligaCodigo:        { color: '#555', fontSize: 12, fontFamily: 'monospace' },
  ligaNombre:        { color: '#FFF', fontWeight: '700', fontSize: 16, marginBottom: 10 },
  ligaFooter:        { flexDirection: 'row', gap: 12, flexWrap: 'wrap' },
  ligaInfo:          { flexDirection: 'row', alignItems: 'center', gap: 4 },
  ligaInfoText:      { color: '#666', fontSize: 12 },
  emptyText:         { color: '#666', textAlign: 'center', padding: 16 },
  center:            { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  loadingText:       { color: '#AAAAAA', fontSize: 15 },
  alertEmoji:        { fontSize: 44, lineHeight: 52 },
  retryBtn:          { backgroundColor: '#E63946', paddingHorizontal: 24, paddingVertical: 12, borderRadius: 8 },
  retryText:         { color: '#FFF', fontWeight: 'bold' },
  totalBox:          { backgroundColor: '#E63946', borderRadius: 16, padding: 24, alignItems: 'center', marginBottom: 16 },
  totalNum:          { fontSize: 64, fontWeight: '900', color: '#FFF' },
  totalLabel:        { fontSize: 14, color: 'rgba(255,255,255,0.8)', marginTop: 4 },
  seedBtn:           { borderRadius: 12, padding: 14, alignItems: 'center', marginBottom: 10 },
  syncBtn:           { backgroundColor: '#1D88E5', borderRadius: 12, padding: 14, alignItems: 'center', marginBottom: 16, flexDirection: 'row', justifyContent: 'center' },
  syncBtnText:       { color: '#FFF', fontWeight: '700', fontSize: 14 },
  actionBtn:         { backgroundColor: '#E63946', borderRadius: 12, padding: 14, alignItems: 'center', justifyContent: 'center', marginBottom: 10, minHeight: 48 },
  actionBtnDisabled: { opacity: 0.6 },
  summaryCard:       { backgroundColor: '#181818', borderRadius: 12, padding: 4, marginBottom: 20 },
  summaryRow:        { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#2a2a2a' },
  summaryLabel:      { color: '#AAAAAA', fontSize: 13 },
  summaryValue:      { color: '#FFF', fontSize: 13, fontWeight: '700', textAlign: 'right', marginLeft: 12 },
  logoutBtn:         { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 16, marginTop: 8 },
  logoutText:        { color: '#999', fontSize: 14 },
  logoutEmoji:       { fontSize: 15, lineHeight: 18 },
});
