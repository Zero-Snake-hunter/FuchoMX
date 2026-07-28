import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import api from '../lib/api';
import { useToast } from '../context/ToastContext';


export default function SelectPositionScreen() {
  const router = useRouter();
  const { position, posType } = useLocalSearchParams();
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    try {
      const response = await api.get(`/api/teams`);
      setTeams(response.data.teams);
    } catch (error) {
      console.error('Error loading teams:', error);
      showToast('error', 'No se pudieron cargar los equipos');
    } finally {
      setLoading(false);
    }
  };

  const handleTeamSelect = (team: any) => {
    router.push({
      pathname: '/fantasy/select-player',
      params: { position, posType, teamId: team.id, teamName: team.name },
    });
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
        <Text style={styles.title}>Seleccionar Equipo</Text>
        <Text style={styles.subtitle}>Posición: {posType}</Text>
      </View>

      <FlatList
        data={teams}
        keyExtractor={(item: any) => item.id}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.teamItem}
            onPress={() => handleTeamSelect(item)}
            activeOpacity={0.7}
          >
            <View style={styles.teamContent}>
              <Text style={styles.teamName}>{item.name}</Text>
              <Text style={styles.teamShort}>{item.short_name}</Text>
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
  teamItem: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  teamContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  teamName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  teamShort: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#DC143C',
  },
});