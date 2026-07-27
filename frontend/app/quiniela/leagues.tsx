import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Modal,
  TextInput,
  Alert,
  Share,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import * as Clipboard from 'expo-clipboard';
import api from '../lib/api';


type LeagueMode = 'quiniela' | 'fantasy';

interface League {
  id: string;
  name: string;
  mode: LeagueMode;
  code: string;
  member_count: number;
  max_members: number;
  is_full: boolean;
  is_owner: boolean;
  created_at: string;
}

export default function LeaguesScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { token } = useAuth();
  
  // State
  const [activeTab, setActiveTab] = useState<LeagueMode>('quiniela');
  const [leagues, setLeagues] = useState<League[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [newLeagueName, setNewLeagueName] = useState('');
  const [newLeagueMode, setNewLeagueMode] = useState<LeagueMode>('quiniela');
  const [joinCode, setJoinCode] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadLeagues();
  }, []);

  const loadLeagues = async () => {
    try {
      const response = await api.get('/api/leagues/my-leagues');
      setLeagues(response.data.leagues);
    } catch (error: any) {
      console.error('Error loading leagues:', error);
      if (error.response?.status !== 401) {
        Alert.alert('Error', 'No se pudieron cargar las ligas');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadLeagues();
  }, []);

  const filteredLeagues = leagues.filter(l => l.mode === activeTab);

  const handleCreateLeague = async () => {
    if (!newLeagueName.trim()) {
      Alert.alert('Error', 'Ingresa un nombre para la liga');
      return;
    }

    setSubmitting(true);
    try {
      const response = await api.post('/api/leagues', { 
        name: newLeagueName.trim(), 
        mode: newLeagueMode 
      });

      Alert.alert(
        '¡Liga Creada!',
        `Código: ${response.data.code}\n\nComparte este código con tus amigos para que se unan.`,
        [
          {
            text: 'Copiar Código',
            onPress: () => copyCode(response.data.code),
          },
          { text: 'OK' },
        ]
      );

      setShowCreateModal(false);
      setNewLeagueName('');
      setActiveTab(newLeagueMode);
      loadLeagues();
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Error al crear la liga';
      Alert.alert('Error', message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleJoinLeague = async () => {
    if (!joinCode.trim() || joinCode.trim().length !== 6) {
      Alert.alert('Error', 'Ingresa un código válido de 6 caracteres');
      return;
    }

    setSubmitting(true);
    try {
      const response = await api.post('/api/leagues/join', { 
        code: joinCode.trim().toUpperCase() 
      });

      Alert.alert('¡Éxito!', `Te has unido a "${response.data.league_name}"`);
      setShowJoinModal(false);
      setJoinCode('');
      setActiveTab(response.data.mode);
      loadLeagues();
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Error al unirse a la liga';
      Alert.alert('Error', message);
    } finally {
      setSubmitting(false);
    }
  };

  const copyCode = async (code: string) => {
    await Clipboard.setStringAsync(code);
    Alert.alert('¡Copiado!', 'Código copiado al portapapeles');
  };

  const shareCode = async (league: League) => {
    const joinLink = `https://fucho.com.mx/leagues/join/${league.code}`;
    try {
      await Share.share({
        message:
          `🏆 Únete a mi liga de quiniela en FuchoMX\n` +
          `${league.name}\n` +
          `Predice partidos de Liga MX y compite con tus cuates\n\n` +
          `Únete aquí: ${joinLink}`,
        url: joinLink,
      });
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  const renderLeagueCard = ({ item }: { item: League }) => (
    <TouchableOpacity
      style={styles.leagueCard}
      onPress={() => router.push({ 
        pathname: '/quiniela/league-detail', 
        params: { leagueId: item.id, mode: item.mode } 
      })}
      activeOpacity={0.7}
    >
      <View style={styles.leagueHeader}>
        <View style={[
          styles.leagueIcon,
          { backgroundColor: item.mode === 'fantasy' ? '#0047AB' : '#DC143C' }
        ]}>
          <Ionicons 
            name={item.mode === 'fantasy' ? 'football' : 'trophy'} 
            size={24} 
            color="#FFFFFF" 
          />
        </View>
        <View style={styles.leagueInfo}>
          <Text style={styles.leagueName} numberOfLines={1}>{item.name}</Text>
          <View style={styles.leagueMeta}>
            <Ionicons name="people" size={14} color="#999" />
            <Text style={styles.metaText}>
              👥 {item.member_count}/{item.max_members ?? 25}
            </Text>
            {item.is_full && (
              <View style={styles.fullBadge}>
                <Text style={styles.fullBadgeText}>LLENA</Text>
              </View>
            )}
            {!item.is_full && (
              <TouchableOpacity
                style={styles.shareCapacityBtn}
                onPress={() => shareCode(item)}
                activeOpacity={0.7}
              >
                <Ionicons name="share-social-outline" size={13} color="#0047AB" />
                <Text style={styles.shareCapacityText}>
                  Quedan {(item.max_members ?? 25) - item.member_count} lugares
                </Text>
              </TouchableOpacity>
            )}
            {item.is_owner && (
              <View style={styles.ownerBadge}>
                <Text style={styles.ownerText}>👑 Admin</Text>
              </View>
            )}
          </View>
          {/* Capacity bar */}
          <View style={styles.capacityBarBg}>
            <View
              style={[
                styles.capacityBarFill,
                {
                  width: `${Math.min(100, ((item.member_count) / (item.max_members ?? 25)) * 100)}%`,
                  backgroundColor: item.is_full ? '#DC143C' : '#0047AB',
                },
              ]}
            />
          </View>
        </View>
        <Ionicons name="chevron-forward" size={24} color="#666" />
      </View>

      <View style={styles.codeRow}>
        <View style={styles.codeContainer}>
          <Text style={styles.codeLabel}>Código:</Text>
          <Text style={styles.code}>{item.code}</Text>
        </View>
        <View style={styles.codeActions}>
          <TouchableOpacity 
            style={styles.codeButton}
            onPress={() => copyCode(item.code)}
          >
            <Ionicons name="copy-outline" size={18} color="#0047AB" />
          </TouchableOpacity>
          <TouchableOpacity 
            style={styles.codeButton}
            onPress={() => shareCode(item)}
          >
            <Ionicons name="share-outline" size={18} color="#0047AB" />
          </TouchableOpacity>
        </View>
      </View>

      <Text style={styles.inviteHint}>
        Invita a tus amigos con este código
      </Text>
    </TouchableOpacity>
  );

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
        <Text style={styles.title}>MIS LIGAS</Text>
        <View style={{ width: 40 }} />
      </View>

      {/* Tabs */}
      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'quiniela' && styles.tabActive]}
          onPress={() => setActiveTab('quiniela')}
        >
          <Ionicons 
            name="trophy" 
            size={20} 
            color={activeTab === 'quiniela' ? '#FFFFFF' : '#666'} 
          />
          <Text style={[styles.tabText, activeTab === 'quiniela' && styles.tabTextActive]}>
            Quiniela
          </Text>
          {leagues.filter(l => l.mode === 'quiniela').length > 0 && (
            <View style={[styles.tabBadge, activeTab === 'quiniela' && styles.tabBadgeActive]}>
              <Text style={styles.tabBadgeText}>
                {leagues.filter(l => l.mode === 'quiniela').length}
              </Text>
            </View>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tab, activeTab === 'fantasy' && styles.tabActiveFantasy]}
          onPress={() => setActiveTab('fantasy')}
        >
          <Ionicons 
            name="football" 
            size={20} 
            color={activeTab === 'fantasy' ? '#FFFFFF' : '#666'} 
          />
          <Text style={[styles.tabText, activeTab === 'fantasy' && styles.tabTextActive]}>
            ONCE
          </Text>
          {leagues.filter(l => l.mode === 'fantasy').length > 0 && (
            <View style={[styles.tabBadge, activeTab === 'fantasy' && styles.tabBadgeActiveFantasy]}>
              <Text style={styles.tabBadgeText}>
                {leagues.filter(l => l.mode === 'fantasy').length}
              </Text>
            </View>
          )}
        </TouchableOpacity>
      </View>

      {/* Actions */}
      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionButton, { backgroundColor: activeTab === 'fantasy' ? '#0047AB' : '#DC143C' }]}
          onPress={() => {
            setNewLeagueMode(activeTab);
            setShowCreateModal(true);
          }}
        >
          <Ionicons name="add-circle" size={20} color="#FFFFFF" />
          <Text style={styles.actionText}>Crear Liga</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButtonSecondary}
          onPress={() => setShowJoinModal(true)}
        >
          <Ionicons name="enter-outline" size={20} color="#FFFFFF" />
          <Text style={styles.actionText}>Unirse con Código</Text>
        </TouchableOpacity>
      </View>

      {/* Banner Liguilla */}
      {activeTab === 'quiniela' && (
        <TouchableOpacity
          style={styles.liguillaBanner}
          activeOpacity={0.8}
          onPress={() => router.push('/quiniela/bracket')}
        >
          <Text style={styles.liguillaBannerEmoji}>🏆</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.liguillaBannerTitle}>LIGUILLA CLAUSURA 2026</Text>
            <Text style={styles.liguillaBannerSub}>Predice al campeón · Presentado por FuchoMX</Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color="#E63946" />
        </TouchableOpacity>
      )}

      {/* League List */}
      <FlatList
        data={filteredLeagues}
        keyExtractor={(item) => item.id}
        renderItem={renderLeagueCard}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#DC143C" />
        }
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text style={styles.emptyStadiumIcon}>🏟️</Text>
            <Text style={styles.emptyTitle}>Aún no tienes ninguna liga</Text>
            <Text style={styles.emptySubtitle}>
              Crea la tuya o únete a la de tus cuates
            </Text>
            <TouchableOpacity
              style={styles.emptyCreateButton}
              onPress={() => {
                setNewLeagueMode(activeTab);
                setShowCreateModal(true);
              }}
              activeOpacity={0.85}
            >
              <Ionicons name="add-circle" size={20} color="#FFFFFF" />
              <Text style={styles.emptyCreateButtonText}>Crear liga</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.emptyJoinLink}
              onPress={() => setShowJoinModal(true)}
              activeOpacity={0.7}
            >
              <Text style={styles.emptyJoinLinkText}>Unirme a una liga</Text>
            </TouchableOpacity>
          </View>
        }
        contentContainerStyle={filteredLeagues.length === 0 ? styles.emptyList : styles.list}
      />

      {/* Create League Modal */}
      <Modal
        visible={showCreateModal}
        animationType="slide"
        transparent
        onRequestClose={() => setShowCreateModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Crear Liga</Text>
              <TouchableOpacity onPress={() => setShowCreateModal(false)}>
                <Ionicons name="close" size={24} color="#FFFFFF" />
              </TouchableOpacity>
            </View>

            <Text style={styles.inputLabel}>Nombre de la Liga</Text>
            <TextInput
              style={styles.input}
              placeholder="Ej: La Liga del Barrio"
              placeholderTextColor="#666"
              value={newLeagueName}
              onChangeText={setNewLeagueName}
              maxLength={30}
            />

            <Text style={styles.inputLabel}>Tipo de Liga</Text>
            <View style={styles.modeSelector}>
              <TouchableOpacity
                style={[
                  styles.modeOption,
                  newLeagueMode === 'quiniela' && styles.modeOptionActiveQuiniela
                ]}
                onPress={() => setNewLeagueMode('quiniela')}
              >
                <Ionicons 
                  name="trophy" 
                  size={24} 
                  color={newLeagueMode === 'quiniela' ? '#FFFFFF' : '#666'} 
                />
                <Text style={[
                  styles.modeOptionText,
                  newLeagueMode === 'quiniela' && styles.modeOptionTextActive
                ]}>
                  Quiniela
                </Text>
                <Text style={styles.modeDescription}>
                  Predice resultados
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.modeOption,
                  newLeagueMode === 'fantasy' && styles.modeOptionActiveFantasy
                ]}
                onPress={() => setNewLeagueMode('fantasy')}
              >
                <Ionicons 
                  name="football" 
                  size={24} 
                  color={newLeagueMode === 'fantasy' ? '#FFFFFF' : '#666'} 
                />
                <Text style={[
                  styles.modeOptionText,
                  newLeagueMode === 'fantasy' && styles.modeOptionTextActive
                ]}>
                  ONCE
                </Text>
                <Text style={styles.modeDescription}>
                  Arma tu once
                </Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity
              style={[
                styles.submitButton,
                { backgroundColor: newLeagueMode === 'fantasy' ? '#0047AB' : '#DC143C' },
                submitting && styles.buttonDisabled
              ]}
              onPress={handleCreateLeague}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.submitButtonText}>CREAR LIGA</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Join League Modal */}
      <Modal
        visible={showJoinModal}
        animationType="slide"
        transparent
        onRequestClose={() => setShowJoinModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Unirse a Liga</Text>
              <TouchableOpacity onPress={() => setShowJoinModal(false)}>
                <Ionicons name="close" size={24} color="#FFFFFF" />
              </TouchableOpacity>
            </View>

            <Text style={styles.inputLabel}>Código de la Liga</Text>
            <TextInput
              style={[styles.input, styles.codeInput]}
              placeholder="XXXXXX"
              placeholderTextColor="#666"
              value={joinCode}
              onChangeText={(text) => setJoinCode(text.toUpperCase())}
              maxLength={6}
              autoCapitalize="characters"
            />

            <Text style={styles.hintText}>
              Pide el código de 6 caracteres al administrador de la liga
            </Text>

            <TouchableOpacity
              style={[styles.submitButton, styles.joinButton, submitting && styles.buttonDisabled]}
              onPress={handleJoinLeague}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <>
                  <Ionicons name="enter" size={20} color="#FFFFFF" />
                  <Text style={styles.submitButtonText}>UNIRSE</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
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
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  tabs: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#1a1a1a',
    gap: 8,
  },
  tabActive: {
    backgroundColor: '#DC143C',
  },
  tabActiveFantasy: {
    backgroundColor: '#0047AB',
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  tabTextActive: {
    color: '#FFFFFF',
  },
  tabBadge: {
    backgroundColor: '#333',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  tabBadgeActive: {
    backgroundColor: 'rgba(255,255,255,0.3)',
  },
  tabBadgeActiveFantasy: {
    backgroundColor: 'rgba(255,255,255,0.3)',
  },
  tabBadgeText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  actions: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingBottom: 16,
    gap: 12,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    gap: 8,
  },
  actionButtonSecondary: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#333',
    gap: 8,
  },
  actionText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  list: {
    padding: 16,
    paddingTop: 0,
  },
  emptyList: {
    flex: 1,
  },
  leagueCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  leagueHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  leagueIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  leagueInfo: {
    flex: 1,
  },
  leagueName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  leagueMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  metaText: {
    fontSize: 13,
    color: '#999',
  },
  ownerBadge: {
    backgroundColor: '#DC143C',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  ownerText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  fullBadge: {
    backgroundColor: '#FF4444',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  fullBadgeText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  shareCapacityBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0047AB18',
    borderRadius: 4,
    paddingHorizontal: 7,
    paddingVertical: 2,
    gap: 3,
    borderWidth: 1,
    borderColor: '#0047AB44',
  },
  shareCapacityText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#0047AB',
  },
  capacityBarBg: {
    height: 4,
    backgroundColor: '#333',
    borderRadius: 2,
    marginTop: 6,
    overflow: 'hidden',
  },
  capacityBarFill: {
    height: 4,
    borderRadius: 2,
  },
  codeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#0a0a0a',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  codeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  codeLabel: {
    fontSize: 13,
    color: '#999',
    marginRight: 8,
  },
  code: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#0047AB',
    letterSpacing: 2,
  },
  codeActions: {
    flexDirection: 'row',
    gap: 8,
  },
  codeButton: {
    padding: 8,
    backgroundColor: '#1a1a1a',
    borderRadius: 8,
  },
  inviteHint: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
    paddingTop: 60,
    paddingBottom: 40,
  },
  emptyStadiumIcon: {
    fontSize: 72,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 32,
  },
  emptyCreateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#DC143C',
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 32,
    gap: 8,
    width: '100%',
    marginBottom: 16,
  },
  emptyCreateButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  emptyJoinLink: {
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  emptyJoinLinkText: {
    color: '#666',
    fontSize: 14,
    textDecorationLine: 'underline',
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    lineHeight: 20,
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.8)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  inputLabel: {
    fontSize: 14,
    color: '#999',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#0a0a0a',
    borderRadius: 8,
    padding: 16,
    fontSize: 16,
    color: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#333',
    marginBottom: 20,
  },
  codeInput: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    letterSpacing: 8,
  },
  modeSelector: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 24,
  },
  modeOption: {
    flex: 1,
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#0a0a0a',
    borderWidth: 2,
    borderColor: '#333',
  },
  modeOptionActiveQuiniela: {
    borderColor: '#DC143C',
    backgroundColor: '#DC143C',
  },
  modeOptionActiveFantasy: {
    borderColor: '#0047AB',
    backgroundColor: '#0047AB',
  },
  modeOptionText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#666',
    marginTop: 8,
  },
  modeOptionTextActive: {
    color: '#FFFFFF',
  },
  modeDescription: {
    fontSize: 11,
    color: '#999',
    marginTop: 4,
  },
  hintText: {
    fontSize: 13,
    color: '#666',
    textAlign: 'center',
    marginBottom: 24,
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  joinButton: {
    backgroundColor: '#0047AB',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  // ── Liguilla Banner ────────────────────────────────
  liguillaBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0D0D0D',
    borderRadius: 16,
    borderWidth: 2,
    borderColor: '#E63946',
    marginHorizontal: 16,
    marginBottom: 12,
    paddingHorizontal: 16,
    paddingVertical: 16,
    gap: 12,
    shadowColor: '#E63946',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  liguillaBannerEmoji: { fontSize: 36 },
  liguillaBannerTitle: {
    color: '#E63946',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  liguillaBannerSub: {
    color: '#AAAAAA',
    fontSize: 11,
    marginTop: 2,
  },
});