import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Modal,
  Alert,
  ActivityIndicator,
  FlatList,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

// Colores de equipos de Liga MX (simplificado)
const TEAM_COLORS: { [key: string]: { primary: string; secondary: string } } = {
  'América': { primary: '#FFD700', secondary: '#0000FF' },
  'Guadalajara': { primary: '#CD2E3A', secondary: '#FFFFFF' },
  'Cruz Azul': { primary: '#0047AB', secondary: '#FFFFFF' },
  'Pumas UNAM': { primary: '#002D62', secondary: '#CDA349' },
  'Tigres UANL': { primary: '#F9A825', secondary: '#003366' },
  'Monterrey': { primary: '#002D62', secondary: '#FFFFFF' },
  'Santos Laguna': { primary: '#2E7D32', secondary: '#FFFFFF' },
  'León': { primary: '#006633', secondary: '#FFFFFF' },
  'Toluca': { primary: '#DC143C', secondary: '#FFFFFF' },
  'Atlas': { primary: '#C41E3A', secondary: '#000000' },
  'Pachuca': { primary: '#005BAC', secondary: '#FFFFFF' },
  'Necaxa': { primary: '#C41E3A', secondary: '#FFFFFF' },
  'Puebla': { primary: '#0047AB', secondary: '#FFFFFF' },
  'Querétaro': { primary: '#003366', secondary: '#FFFFFF' },
  'Tijuana': { primary: '#C41E3A', secondary: '#000000' },
  'Mazatlán': { primary: '#6B3FA0', secondary: '#FFFFFF' },
  'Juárez': { primary: '#006747', secondary: '#FFFFFF' },
  'San Luis': { primary: '#C41E3A', secondary: '#002F6C' },
  'default': { primary: '#666666', secondary: '#FFFFFF' },
};

// Formación 4-4-2: 1 POR, 4 DEF, 4 MED, 2 DEL
const FORMATION = {
  POR: [{ slot: 'POR_1', position: 'POR', label: 'Portero' }],
  DEF: [
    { slot: 'DEF_1', position: 'DEF', label: 'Defensa 1' },
    { slot: 'DEF_2', position: 'DEF', label: 'Defensa 2' },
    { slot: 'DEF_3', position: 'DEF', label: 'Defensa 3' },
    { slot: 'DEF_4', position: 'DEF', label: 'Defensa 4' },
  ],
  MED: [
    { slot: 'MED_1', position: 'MED', label: 'Medio 1' },
    { slot: 'MED_2', position: 'MED', label: 'Medio 2' },
    { slot: 'MED_3', position: 'MED', label: 'Medio 3' },
    { slot: 'MED_4', position: 'MED', label: 'Medio 4' },
  ],
  DEL: [
    { slot: 'DEL_1', position: 'DEL', label: 'Delantero 1' },
    { slot: 'DEL_2', position: 'DEL', label: 'Delantero 2' },
  ],
};

// Función para obtener colores del equipo
const getTeamColors = (teamName: string) => {
  // Buscar coincidencia parcial en el nombre del equipo
  for (const [key, colors] of Object.entries(TEAM_COLORS)) {
    if (teamName?.toLowerCase().includes(key.toLowerCase())) {
      return colors;
    }
  }
  return TEAM_COLORS['default'];
};

export default function LineupScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { token } = useAuth();
  const [lineup, setLineup] = useState<any>({});
  const [dtTeam, setDtTeam] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Modal states
  const [showTeamSelector, setShowTeamSelector] = useState(false);
  const [showPlayerSelector, setShowPlayerSelector] = useState(false);
  const [showDTSelector, setShowDTSelector] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null);
  const [selectedTeamForPlayer, setSelectedTeamForPlayer] = useState<any>(null);

  const [teams, setTeams] = useState([]);
  const [players, setPlayers] = useState([]);
  const [loadingPlayers, setLoadingPlayers] = useState(false);

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/teams`);
      setTeams(response.data.teams);
    } catch (error) {
      console.error('Error loading teams:', error);
      Alert.alert('Error', 'No se pudieron cargar los equipos');
    }
  };

  // Función para regresar
  const handleGoBack = () => {
    router.back();
  };

  const handleSlotPress = (slot: string, position: string) => {
    setSelectedSlot(slot);
    setSelectedPosition(position);
    setShowTeamSelector(true);
  };

  const handleTeamSelect = async (team: any) => {
    setSelectedTeamForPlayer(team);
    setShowTeamSelector(false);
    setLoadingPlayers(true);

    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/players?position=${selectedPosition}&team_id=${team.id}`
      );
      setPlayers(response.data.players);
      setShowPlayerSelector(true);
    } catch (error) {
      Alert.alert('Error', 'Error al cargar jugadores');
    } finally {
      setLoadingPlayers(false);
    }
  };

  const handlePlayerSelect = (player: any) => {
    // Guardar el jugador con información del equipo
    const playerWithTeam = {
      ...player,
      team: selectedTeamForPlayer,
    };
    setLineup((prev: any) => ({
      ...prev,
      [selectedSlot!]: playerWithTeam,
    }));
    setShowPlayerSelector(false);
    setSelectedTeamForPlayer(null);
  };

  const handleDTSelect = (team: any) => {
    setDtTeam(team);
    setShowDTSelector(false);
  };

  const handleSubmit = async () => {
    // Validate 11 players
    const allSlots = [
      ...FORMATION.POR.map(f => f.slot),
      ...FORMATION.DEF.map(f => f.slot),
      ...FORMATION.MED.map(f => f.slot),
      ...FORMATION.DEL.map(f => f.slot),
    ];

    const missingSlots = allSlots.filter(slot => !lineup[slot]);
    if (missingSlots.length > 0) {
      Alert.alert(
        'Alineación incompleta',
        `Debes seleccionar los 11 jugadores (faltan ${missingSlots.length})`
      );
      return;
    }

    if (!dtTeam) {
      Alert.alert('Director Técnico', 'Debes seleccionar un Director Técnico');
      return;
    }

    Alert.alert(
      'Confirmar alineación',
      '¿Estás seguro? No podrás modificarla después.',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Confirmar', onPress: submitLineup },
      ]
    );
  };

  const submitLineup = async () => {
    setSubmitting(true);
    try {
      // Get current jornada
      const jornadaResponse = await axios.get(`${BACKEND_URL}/api/jornadas/current`);
      const jornadaId = jornadaResponse.data.jornada.id;

      // Build players array
      const playersArray = Object.entries(lineup).map(([slot, player]: [string, any]) => ({
        player_id: player.id,
        position_slot: slot,
      }));

      await axios.post(
        `${BACKEND_URL}/api/fantasy/lineup`,
        {
          jornada_id: jornadaId,
          players: playersArray,
          dt_team_id: dtTeam.id,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Mostrar éxito y navegar inmediatamente
      Alert.alert(
        '¡Alineación Guardada!', 
        'Tu equipo está listo para competir esta jornada.'
      );
      
      // Navegar al dashboard de Fantasy
      router.replace('/fantasy');
      
    } catch (error: any) {
      console.error('Error saving lineup:', error);
      const errorMessage = error.response?.data?.detail || 'Error al guardar alineación. Intenta de nuevo.';
      Alert.alert('Error', errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const renderPlayerSlot = (slot: string, position: string, label: string) => {
    const player = lineup[slot];
    const teamColors = player?.team ? getTeamColors(player.team.name) : null;

    return (
      <TouchableOpacity
        key={slot}
        style={styles.playerSlot}
        onPress={() => handleSlotPress(slot, position)}
      >
        <View
          style={[
            styles.jersey,
            player && teamColors
              ? { backgroundColor: teamColors.primary, borderWidth: 2, borderColor: teamColors.secondary }
              : { backgroundColor: '#FFFFFF', borderWidth: 2, borderColor: '#333' },
          ]}
        >
          {player ? (
            <Text style={[styles.jerseyNumber, { color: teamColors?.secondary || '#FFFFFF' }]}>
              {player.number}
            </Text>
          ) : (
            <Ionicons name="person-add" size={20} color="#666" />
          )}
        </View>
        {/* Mostrar nombre del jugador o label de posición */}
        <Text style={styles.playerName} numberOfLines={1}>
          {player ? player.name.split(' ').slice(-1)[0] : label}
        </Text>
        {/* Mostrar equipo solo cuando hay jugador */}
        <Text style={styles.teamName} numberOfLines={1}>
          {player ? player.team?.short_name : ''}
        </Text>
      </TouchableOpacity>
    );
  };

  // Contar jugadores seleccionados
  const selectedCount = Object.keys(lineup).length;

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header con botón de regresar */}
      <View style={styles.header}>
        <TouchableOpacity 
          style={styles.backButton} 
          onPress={handleGoBack}
          activeOpacity={0.7}
        >
          <Ionicons name="arrow-back" size={24} color="#FFFFFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Armar Alineación</Text>
        <View style={styles.headerRight}>
          <Text style={styles.countText}>{selectedCount}/11</Text>
        </View>
      </View>

      <ScrollView style={styles.scrollView}>
        {/* Field */}
        <View style={styles.field}>
          {/* Delanteros */}
          <View style={styles.line}>
            {FORMATION.DEL.map(f => renderPlayerSlot(f.slot, f.position, f.label))}
          </View>

          {/* Mediocampistas */}
          <View style={styles.line}>
            {FORMATION.MED.map(f => renderPlayerSlot(f.slot, f.position, f.label))}
          </View>

          {/* Defensas */}
          <View style={styles.line}>
            {FORMATION.DEF.map(f => renderPlayerSlot(f.slot, f.position, f.label))}
          </View>

          {/* Portero */}
          <View style={styles.line}>
            {FORMATION.POR.map(f => renderPlayerSlot(f.slot, f.position, f.label))}
          </View>
        </View>

        {/* Director Técnico */}
        <View style={styles.dtSection}>
          <Text style={styles.dtTitle}>DIRECTOR TÉCNICO</Text>
          <TouchableOpacity
            style={[styles.dtCard, dtTeam && styles.dtCardSelected]}
            onPress={() => setShowDTSelector(true)}
          >
            {dtTeam ? (
              <View style={styles.dtSelected}>
                <View style={[styles.dtIcon, { backgroundColor: getTeamColors(dtTeam.name).primary }]}>
                  <Ionicons name="person" size={24} color={getTeamColors(dtTeam.name).secondary} />
                </View>
                <View style={styles.dtInfo}>
                  <Text style={styles.dtTeamName}>DT de {dtTeam.name}</Text>
                  <Text style={styles.dtSubtitle}>{dtTeam.short_name}</Text>
                </View>
                <Ionicons name="checkmark-circle" size={24} color="#00A551" />
              </View>
            ) : (
              <View style={styles.dtEmpty}>
                <Ionicons name="person-add" size={32} color="#666" />
                <Text style={styles.dtEmptyText}>Seleccionar Director Técnico</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Submit Button */}
      <View style={[styles.footer, { paddingBottom: insets.bottom + 16 }]}>
        <TouchableOpacity
          style={[styles.submitButton, submitting && styles.buttonDisabled]}
          onPress={handleSubmit}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <>
              <Ionicons name="checkmark-circle" size={24} color="#FFFFFF" />
              <Text style={styles.submitButtonText}>GUARDAR ALINEACIÓN</Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      {/* Team Selector Modal */}
      <Modal
        visible={showTeamSelector}
        animationType="slide"
        transparent
        onRequestClose={() => setShowTeamSelector(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Seleccionar Equipo</Text>
              <TouchableOpacity onPress={() => setShowTeamSelector(false)}>
                <Ionicons name="close" size={24} color="#FFFFFF" />
              </TouchableOpacity>
            </View>
            <FlatList
              data={teams}
              keyExtractor={(item: any) => item.id}
              renderItem={({ item }) => {
                const colors = getTeamColors(item.name);
                return (
                  <TouchableOpacity
                    style={styles.teamItem}
                    onPress={() => handleTeamSelect(item)}
                  >
                    <View style={[styles.teamColorDot, { backgroundColor: colors.primary }]} />
                    <Text style={styles.teamItemName}>{item.name}</Text>
                    <Ionicons name="chevron-forward" size={20} color="#666" />
                  </TouchableOpacity>
                );
              }}
            />
          </View>
        </View>
      </Modal>

      {/* Player Selector Modal */}
      <Modal
        visible={showPlayerSelector}
        animationType="slide"
        transparent
        onRequestClose={() => setShowPlayerSelector(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {selectedTeamForPlayer?.name}
              </Text>
              <TouchableOpacity onPress={() => setShowPlayerSelector(false)}>
                <Ionicons name="close" size={24} color="#FFFFFF" />
              </TouchableOpacity>
            </View>
            {loadingPlayers ? (
              <ActivityIndicator size="large" color="#DC143C" style={{ marginTop: 40 }} />
            ) : (
              <FlatList
                data={players}
                keyExtractor={(item: any) => item.id}
                renderItem={({ item }) => {
                  const colors = getTeamColors(selectedTeamForPlayer?.name);
                  return (
                    <TouchableOpacity
                      style={styles.playerItem}
                      onPress={() => handlePlayerSelect(item)}
                    >
                      <View style={[styles.playerItemNumber, { backgroundColor: colors.primary }]}>
                        <Text style={[styles.playerItemNumberText, { color: colors.secondary }]}>
                          {item.number}
                        </Text>
                      </View>
                      <View style={styles.playerItemInfo}>
                        <Text style={styles.playerItemName}>{item.name}</Text>
                        <Text style={styles.playerItemPosition}>{selectedPosition}</Text>
                      </View>
                      <Ionicons name="add-circle" size={24} color="#00A551" />
                    </TouchableOpacity>
                  );
                }}
                ListEmptyComponent={
                  <View style={styles.emptyList}>
                    <Text style={styles.emptyText}>No hay jugadores disponibles</Text>
                  </View>
                }
              />
            )}
          </View>
        </View>
      </Modal>

      {/* DT Selector Modal */}
      <Modal
        visible={showDTSelector}
        animationType="slide"
        transparent
        onRequestClose={() => setShowDTSelector(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Seleccionar DT</Text>
              <TouchableOpacity onPress={() => setShowDTSelector(false)}>
                <Ionicons name="close" size={24} color="#FFFFFF" />
              </TouchableOpacity>
            </View>
            <FlatList
              data={teams}
              keyExtractor={(item: any) => item.id}
              renderItem={({ item }) => {
                const colors = getTeamColors(item.name);
                const isSelected = dtTeam?.id === item.id;
                return (
                  <TouchableOpacity
                    style={[styles.teamItem, isSelected && styles.teamItemSelected]}
                    onPress={() => handleDTSelect(item)}
                  >
                    <View style={[styles.teamColorDot, { backgroundColor: colors.primary }]} />
                    <Text style={styles.teamItemName}>DT de {item.name}</Text>
                    {isSelected && <Ionicons name="checkmark-circle" size={24} color="#00A551" />}
                  </TouchableOpacity>
                );
              }}
            />
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
    marginLeft: -8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  headerRight: {
    backgroundColor: '#DC143C',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  countText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  scrollView: {
    flex: 1,
  },
  field: {
    backgroundColor: '#2d7a3f',
    padding: 20,
    minHeight: 450,
  },
  line: {
    flexDirection: 'row',
    justifyContent: 'space-evenly',
    marginVertical: 16,
  },
  playerSlot: {
    alignItems: 'center',
    width: 70,
  },
  jersey: {
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 4,
  },
  jerseyNumber: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  playerName: {
    fontSize: 10,
    color: '#FFFFFF',
    textAlign: 'center',
    fontWeight: '600',
    maxWidth: 65,
  },
  teamName: {
    fontSize: 8,
    color: '#CCCCCC',
    textAlign: 'center',
    minHeight: 12,
  },
  dtSection: {
    padding: 20,
  },
  dtTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 12,
    letterSpacing: 1,
  },
  dtCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: '#333',
  },
  dtCardSelected: {
    borderColor: '#00A551',
  },
  dtSelected: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dtIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  dtInfo: {
    marginLeft: 16,
    flex: 1,
  },
  dtTeamName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  dtSubtitle: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  dtEmpty: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
  },
  dtEmptyText: {
    fontSize: 16,
    color: '#666',
    marginLeft: 12,
  },
  footer: {
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
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.8)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  teamItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  teamItemSelected: {
    backgroundColor: '#0a1a2a',
  },
  teamColorDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    marginRight: 12,
  },
  teamItemName: {
    flex: 1,
    fontSize: 16,
    color: '#FFFFFF',
  },
  playerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  playerItemNumber: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  playerItemNumberText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  playerItemInfo: {
    flex: 1,
  },
  playerItemName: {
    fontSize: 16,
    color: '#FFFFFF',
    fontWeight: '500',
  },
  playerItemPosition: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  emptyList: {
    padding: 40,
    alignItems: 'center',
  },
  emptyText: {
    color: '#666',
    fontSize: 14,
  },
});
