import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function CreateTeamScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const [teamName, setTeamName] = useState('');
  const [loading, setLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    loadCurrentTeam();
  }, []);

  const loadCurrentTeam = async () => {
    if (!token) return;

    try {
      console.log('Loading team...');
      const response = await axios.get(`${BACKEND_URL}/api/fantasy/my-team`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      console.log('Team response:', response.data);
      if (response.data.exists) {
        setTeamName(response.data.name);
        setIsEditing(true);
      } else {
        setTeamName(response.data.default_name);
      }
    } catch (error) {
      console.error('Error loading team:', error);
    }
  };

  const handleSave = async () => {
    console.log('handleSave called');
    console.log('Team name:', teamName);
    console.log('Token:', token ? 'exists' : 'missing');

    if (!teamName.trim()) {
      Alert.alert('Error', 'Por favor ingresa un nombre para tu equipo');
      return;
    }

    setLoading(true);
    try {
      console.log('Sending request to backend...');
      const response = await axios.post(
        `${BACKEND_URL}/api/fantasy/team`,
        { name: teamName.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      console.log('Response:', response.data);
      
      if (isEditing) {
        // Si está editando, solo muestra mensaje y regresa
        Alert.alert('¡Éxito!', 'Nombre actualizado');
        router.back();
      } else {
        // Si es nuevo equipo, navega a lineup inmediatamente
        console.log('Team created! Navigating to lineup...');
        router.push('/fantasy/lineup');
      }
    } catch (error: any) {
      console.error('Error saving team:', error);
      const errorMessage = error.response?.data?.detail || 'Error al guardar el equipo. Intenta de nuevo.';
      Alert.alert('Error', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Ionicons name="shield" size={80} color="#DC143C" />
        </View>

        <Text style={styles.title}>
          {isEditing ? 'Cambiar Nombre' : 'Crear Tu Equipo'}
        </Text>
        <Text style={styles.subtitle}>
          {isEditing
            ? 'Actualiza el nombre de tu equipo'
            : 'Este nombre te representará toda la temporada'}
        </Text>

        <View style={styles.form}>
          <Text style={styles.label}>Nombre del Equipo</Text>
          <View style={styles.inputContainer}>
            <Ionicons name="football" size={20} color="#666" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Mi Equipo - FC"
              placeholderTextColor="#666"
              value={teamName}
              onChangeText={setTeamName}
              maxLength={30}
            />
          </View>
          <Text style={styles.charCount}>{teamName.length}/30 caracteres</Text>

          <TouchableOpacity
            style={[styles.saveButton, loading && styles.buttonDisabled]}
            onPress={handleSave}
            disabled={loading}
            activeOpacity={0.7}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <Ionicons name="checkmark-circle" size={24} color="#FFFFFF" />
                <Text style={styles.saveButtonText}>
                  {isEditing ? 'ACTUALIZAR' : 'CREAR EQUIPO'}
                </Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.tipsBox}>
          <Text style={styles.tipsTitle}>💡 Consejos:</Text>
          <Text style={styles.tip}>• Usa un nombre único y creativo</Text>
          <Text style={styles.tip}>• Máximo 30 caracteres</Text>
          <Text style={styles.tip}>• Podrás cambiarlo después</Text>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  content: {
    flex: 1,
    padding: 24,
  },
  iconContainer: {
    alignItems: 'center',
    marginVertical: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 32,
  },
  form: {
    marginBottom: 32,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  inputIcon: {
    marginLeft: 16,
  },
  input: {
    flex: 1,
    height: 56,
    color: '#FFFFFF',
    fontSize: 16,
    paddingHorizontal: 16,
  },
  charCount: {
    fontSize: 12,
    color: '#666',
    marginTop: 8,
    textAlign: 'right',
  },
  saveButton: {
    backgroundColor: '#DC143C',
    height: 56,
    borderRadius: 12,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
    marginTop: 24,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  saveButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  tipsBox: {
    backgroundColor: '#0a1a2a',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#0047AB',
  },
  tipsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 12,
  },
  tip: {
    fontSize: 14,
    color: '#999',
    marginBottom: 8,
    lineHeight: 20,
  },
});