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
import api from '../lib/api';

export default function CreateTeamScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const [teamName, setTeamName] = useState('');
  const [loading, setLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    loadCurrentTeam();
  }, []);

  const loadCurrentTeam = async () => {
    if (!token) {
      console.log('⚠️ No token disponible, no se puede cargar equipo');
      return;
    }

    try {
      console.log('🔄 Cargando equipo actual...');
      const response = await api.get('/api/fantasy/my-team');

      console.log('✅ Equipo cargado:', response.data);
      if (response.data.exists) {
        setTeamName(response.data.name);
        setIsEditing(true);
      } else {
        setTeamName(response.data.default_name);
      }
    } catch (error: any) {
      console.error('❌ Error loading team:', error.response?.status, error.message);
      if (error.response?.status !== 401) {
        Alert.alert('Error', 'No se pudo cargar la información del equipo');
      }
    }
  };

  const handleSave = async () => {
    setErrorMsg('');
    if (!teamName.trim()) {
      setErrorMsg('Por favor ingresa un nombre para tu equipo');
      return;
    }

    setLoading(true);
    try {
      await api.post('/api/fantasy/team', { name: teamName.trim() });
      if (isEditing) {
        router.back();
      } else {
        router.push('/fantasy/lineup');
      }
    } catch (error: any) {
      setErrorMsg(error.response?.data?.detail || 'Error al guardar el equipo. Intenta de nuevo.');
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

          {errorMsg ? <Text style={styles.errorText}>{errorMsg}</Text> : null}

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
  errorText: {
    color: '#DC143C',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 12,
    marginBottom: 4,
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