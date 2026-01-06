import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useFantasy } from '../context/FantasyContext';
import JerseyView from '../../components/JerseyView';
import axios from 'axios';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function SelectPlayerScreen() {
  const router = useRouter();
  const { position, posType, teamId, teamName } = useLocalSearchParams();
  const { setPlayer, hasPlayer } = useFantasy();
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPlayers();
  }, []);

  const loadPlayers = async () => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/players?position=${posType}&team_id=${teamId}`
      );
      setPlayers(response.data.players);
    } catch (error) {
      Alert.alert('Error', 'Error al cargar jugadores');
    } finally {
      setLoading(false);
    }
  };

  const handlePlayerSelect = (player: any) => {
    if (hasPlayer(player.id)) {
      Alert.alert('Jugador duplicado', 'Este jugador ya está en tu alineación');
      return;
    }

    setPlayer(position as string, player);
    router.back();
    router.back();
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#DC143C" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>{teamName}</Text>
        <Text style={styles.subtitle}>Posición: {posType}</Text>
      </View>

      <FlatList
        data={players}
        keyExtractor={(item: any) => item.id}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.playerItem}
            onPress={() => handlePlayerSelect(item)}
            activeOpacity={0.7}
          >
            <JerseyView number={item.number} size={48} />
            <View style={styles.playerInfo}>
              <Text style={styles.playerName}>{item.name}</Text>
              <Text style={styles.playerTeam}>{item.team.short_name}</Text>
            </View>
          </TouchableOpacity>
        )}
        contentContainerStyle={styles.list}
      />
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
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginTop: 4,
  },
  list: {
    padding: 16,
  },
  playerItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  playerInfo: {
    marginLeft: 16,
    flex: 1,
  },
  playerName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  playerTeam: {
    fontSize: 14,
    color: '#999',
    marginTop: 4,
  },
});