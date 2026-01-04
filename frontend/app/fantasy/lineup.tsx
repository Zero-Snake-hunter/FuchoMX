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
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

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

export default function LineupScreen() {
  const router = useRouter();
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
    }
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
    setLineup((prev: any) => ({
      ...prev,
      [selectedSlot!]: player,
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

      Alert.alert('¡Éxito!', 'Alineación guardada correctamente', [
        { text: 'OK', onPress: () => router.back() },
      ]);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Error al guardar alineación');
    } finally {
      setSubmitting(false);
    }
  };

  const renderPlayerSlot = (slot: string, position: string, label: string) => {
    const player = lineup[slot];

    return (
      <TouchableOpacity
        key={slot}
        style={styles.playerSlot}
        onPress={() => handleSlotPress(slot, position)}
      >
        <View
          style={[
            styles.jersey,
            player
              ? { backgroundColor: '#DC143C' }
              : { backgroundColor: '#FFFFFF', borderWidth: 2, borderColor: '#333' },
          ]}
        >
          {player ? (
            <Text style={styles.jerseyNumber}>{player.number}</Text>
          ) : (
            <Ionicons name="person-add" size={20} color="#666" />
          )}
        </View>
        <Text style={styles.playerName} numberOfLines={1}>
          {player ? player.name : label}
        </Text>
        {player && (
          <Text style={styles.teamName} numberOfLines={1}>
            {player.team?.short_name}
          </Text>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
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
            style={styles.dtCard}
            onPress={() => setShowDTSelector(true)}
          >
            {dtTeam ? (
              <View style={styles.dtSelected}>
                <Ionicons name="shield" size={40} color="#DC143C" />
                <View style={styles.dtInfo}>
                  <Text style={styles.dtTeamName}>{dtTeam.name}</Text>
                  <Text style={styles.dtSubtitle}>Equipo seleccionado</Text>
                </View>
              </View>
            ) : (
              <View style={styles.dtEmpty}>
                <Ionicons name="person" size={40} color="#666" />
                <Text style={styles.dtEmptyText}>Seleccionar DT</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Submit Button */}
      <View style={styles.footer}>
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
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.teamItem}
                  onPress={() => handleTeamSelect(item)}
                >
                  <Text style={styles.teamItemName}>{item.name}</Text>
                  <Ionicons name="chevron-forward" size={20} color="#666" />
                </TouchableOpacity>
              )}
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
                {selectedTeamForPlayer?.name} - {selectedPosition}
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
                renderItem={({ item }) => (
                  <TouchableOpacity
                    style={styles.playerItem}
                    onPress={() => handlePlayerSelect(item)}
                  >
                    <View style={styles.playerItemNumber}>
                      <Text style={styles.playerItemNumberText}>{item.number}</Text>
                    </View>
                    <Text style={styles.playerItemName}>{item.name}</Text>
                    <Ionicons name="checkmark" size={20} color="#00A551" />
                  </TouchableOpacity>
                )}
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
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.teamItem}
                  onPress={() => handleDTSelect(item)}
                >
                  <Text style={styles.teamItemName}>{item.name}</Text>
                  <Ionicons name="checkmark" size={20} color="#00A551" />
                </TouchableOpacity>
              )}
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
  scrollView: {
    flex: 1,
  },
  field: {
    backgroundColor: '#2d7a3f',
    padding: 20,
    minHeight: 500,
  },
  line: {
    flexDirection: 'row',
    justifyContent: 'space-evenly',
    marginVertical: 20,
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
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  playerName: {
    fontSize: 10,
    color: '#FFFFFF',
    textAlign: 'center',
    fontWeight: '600',
  },
  teamName: {
    fontSize: 8,
    color: '#CCCCCC',
    textAlign: 'center',
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
  dtSelected: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dtInfo: {
    marginLeft: 16,
    flex: 1,
  },
  dtTeamName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  dtSubtitle: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  dtEmpty: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
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
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  teamItemName: {
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
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#DC143C',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  playerItemNumberText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  playerItemName: {
    flex: 1,
    fontSize: 16,
    color: '#FFFFFF',
  },
});
