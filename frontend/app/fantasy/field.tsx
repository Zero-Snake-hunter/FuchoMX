import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import { useFantasy } from '../context/FantasyContext';
import { useToast } from '../context/ToastContext';
import { Ionicons } from '@expo/vector-icons';
import FootballPitch from '../../components/FootballPitch';
import PositionSlot from '../../components/PositionSlot';
import CoachCard from '../../components/CoachCard';
import api from '../lib/api';


const POSITIONS = {
  FW: ['FW_1', 'FW_2'],
  MF: ['MF_1', 'MF_2', 'MF_3', 'MF_4'],
  DF: ['DF_1', 'DF_2', 'DF_3', 'DF_4'],
  GK: ['GK_1'],
};

export default function FieldScreen() {
  const router = useRouter();
  const { token } = useAuth();
  const { showToast } = useToast();
  const { lineup, dtTeam, isLineupComplete, submitLineup, setDTTeam } = useFantasy();
  const [submitting, setSubmitting] = useState(false);
  const [jornada, setJornada] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadJornada();
  }, []);

  const loadJornada = async () => {
    try {
      const response = await api.get(`/api/jornadas/current`);
      setJornada(response.data.jornada);
    } catch (error) {
      showToast('error', 'No hay jornada activa');
    } finally {
      setLoading(false);
    }
  };

  const handlePositionPress = (position: string) => {
    const posType = position.split('_')[0];
    router.push({
      pathname: '/fantasy/select-position',
      params: { position, posType },
    });
  };

  const handleDTPress = () => {
    router.push('/fantasy/select-dt');
  };

  const handleSubmit = async () => {
    if (!isLineupComplete()) {
      showToast('error', 'Debes seleccionar 11 jugadores y un Director Técnico');
      return;
    }

    // Alert.alert con array de botones no dispara sus onPress de forma
    // confiable en web (mismo caso ya resuelto en handleLogout de
    // profile.tsx) — en web se saltaba la confirmación.
    if (Platform.OS === 'web') {
      await handleConfirmSubmit();
      return;
    }

    Alert.alert(
      'Confirmar Alineación',
      '¿Estás seguro? No podrás modificarla después.',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Confirmar', onPress: handleConfirmSubmit },
      ]
    );
  };

  const handleConfirmSubmit = async () => {
    if (!jornada || !token) return;

    setSubmitting(true);
    try {
      await submitLineup(jornada.id, token);
      showToast('success', 'Alineación guardada correctamente');
      router.back();
    } catch (error: any) {
      showToast('error', error.response?.data?.detail || 'Error al guardar');
    } finally {
      setSubmitting(false);
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
      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.title}>ARMAR ALINEACIÓN</Text>
          <Text style={styles.subtitle}>Formación 4-4-2</Text>
        </View>

        <FootballPitch>
          <View style={styles.formation}>
            <View style={styles.line}>
              {POSITIONS.FW.map(pos => (
                <PositionSlot
                  key={pos}
                  position="FW"
                  player={lineup[pos]}
                  onPress={() => handlePositionPress(pos)}
                />
              ))}
            </View>

            <View style={styles.line}>
              {POSITIONS.MF.map(pos => (
                <PositionSlot
                  key={pos}
                  position="MF"
                  player={lineup[pos]}
                  onPress={() => handlePositionPress(pos)}
                />
              ))}
            </View>

            <View style={styles.line}>
              {POSITIONS.DF.map(pos => (
                <PositionSlot
                  key={pos}
                  position="DF"
                  player={lineup[pos]}
                  onPress={() => handlePositionPress(pos)}
                />
              ))}
            </View>

            <View style={styles.line}>
              {POSITIONS.GK.map(pos => (
                <PositionSlot
                  key={pos}
                  position="GK"
                  player={lineup[pos]}
                  onPress={() => handlePositionPress(pos)}
                />
              ))}
            </View>
          </View>
        </FootballPitch>

        <View style={styles.dtSection}>
          <CoachCard team={dtTeam} onPress={handleDTPress} />
        </View>
      </ScrollView>

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
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 100,
  },
  header: {
    padding: 20,
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    letterSpacing: 1,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginTop: 4,
  },
  formation: {
    flex: 1,
    justifyContent: 'space-evenly',
    paddingVertical: 20,
  },
  line: {
    flexDirection: 'row',
    justifyContent: 'space-evenly',
    marginVertical: 10,
  },
  dtSection: {
    padding: 20,
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    backgroundColor: '#000000',
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
});