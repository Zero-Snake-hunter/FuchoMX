import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function FantasyDashboardScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [team, setTeam] = useState<any>(null);
  const [jornada, setJornada] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    if (!token) return;

    try {
      const [teamRes, jornadaRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/fantasy/my-team`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        axios.get(`${BACKEND_URL}/api/jornadas/current`),
      ]);

      setTeam(teamRes.data);
      setJornada(jornadaRes.data.jornada);
    } catch (error: any) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTeam = () => {
    if (team?.exists) {
      router.push('/fantasy/field');
    } else {
      router.push('/fantasy/create-team');
    }
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
        <Ionicons name="people" size={80} color="#0047AB" />
        <Text style={styles.title}>FANTASY FÚTBOL</Text>
        <Text style={styles.subtitle}>Arma tu equipo ideal de la Liga MX</Text>
      </View>

      <View style={styles.content}>
        {team?.exists ? (
          <View style={styles.teamCard}>
            <View style={styles.teamHeader}>
              <Ionicons name="shield" size={48} color="#DC143C" />
              <View style={styles.teamInfo}>
                <Text style={styles.teamName}>{team.name}</Text>
                <Text style={styles.teamSubtitle}>Tu equipo fantasy</Text>
              </View>
            </View>

            {jornada && (
              <View style={styles.jornadaInfo}>
                <Text style={styles.jornadaLabel}>Jornada {jornada.week_number}</Text>
                <View
                  style={[
                    styles.statusBadge,
                    jornada.status === 'upcoming'
                      ? styles.statusOpen
                      : styles.statusClosed,
                  ]}
                >
                  <Text style={styles.statusText}>
                    {jornada.status === 'upcoming' ? 'Abierta' : 'Cerrada'}
                  </Text>
                </View>
              </View>
            )}

            <TouchableOpacity style={styles.primaryButton} onPress={() => router.push('/fantasy/field')}>
              <Ionicons name="create-outline" size={24} color="#FFFFFF" />
              <Text style={styles.primaryButtonText}>ARMAR ALINEACIÓN</Text>
            </TouchableOpacity>

            <View style={styles.quickActions}>
              <TouchableOpacity
                style={styles.secondaryButton}
                onPress={() => router.push('/fantasy/rankings')}
              >
                <Ionicons name="trophy-outline" size={20} color="#0047AB" />
                <Text style={styles.secondaryButtonText}>Rankings</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.secondaryButton}
                onPress={() => router.push('/fantasy/create-team')}
              >
                <Ionicons name="pencil-outline" size={20} color="#0047AB" />
                <Text style={styles.secondaryButtonText}>Cambiar Nombre</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          <View style={styles.welcomeCard}>
            <Text style={styles.welcomeTitle}>¡Bienvenido!</Text>
            <Text style={styles.welcomeText}>
              Crea tu equipo fantasy para comenzar a competir
            </Text>
            <Text style={styles.welcomeDefault}>Nombre sugerido: {team?.default_name}</Text>

            <TouchableOpacity style={styles.primaryButton} onPress={handleCreateTeam}>
              <Ionicons name="add-circle-outline" size={24} color="#FFFFFF" />
              <Text style={styles.primaryButtonText}>CREAR MI EQUIPO</Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={styles.infoBox}>
          <Ionicons name="information-circle" size={20} color="#0047AB" />
          <Text style={styles.infoText}>
            Selecciona 11 jugadores (4-4-2) y un Director Técnico cada jornada
          </Text>
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
  header: {
    alignItems: 'center',
    paddingVertical: 40,
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginTop: 16,
    letterSpacing: 1,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
    textAlign: 'center',
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
  },
  teamCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: '#333',
    marginBottom: 24,
  },
  teamHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  teamInfo: {
    marginLeft: 16,
    flex: 1,
  },
  teamName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  teamSubtitle: {
    fontSize: 14,
    color: '#999',
    marginTop: 4,
  },
  jornadaInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#0a0a0a',
    borderRadius: 8,
  },
  jornadaLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  statusOpen: {
    backgroundColor: '#00A551',
  },
  statusClosed: {
    backgroundColor: '#DC143C',
  },
  statusText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  welcomeCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 32,
    borderWidth: 1,
    borderColor: '#333',
    alignItems: 'center',
    marginBottom: 24,
  },
  welcomeTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 12,
  },
  welcomeText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 16,
  },
  welcomeDefault: {
    fontSize: 12,
    color: '#0047AB',
    marginBottom: 24,
  },
  primaryButton: {
    backgroundColor: '#DC143C',
    height: 56,
    borderRadius: 12,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  quickActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 16,
  },
  secondaryButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0a0a0a',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#0047AB',
    gap: 8,
  },
  secondaryButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  infoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0a1a2a',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#0047AB',
  },
  infoText: {
    flex: 1,
    fontSize: 12,
    color: '#FFFFFF',
    marginLeft: 12,
    lineHeight: 18,
  },
});