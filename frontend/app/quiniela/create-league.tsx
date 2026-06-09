import React, { useState } from 'react';
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
  Share,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import api from '../lib/api';
import * as Clipboard from 'expo-clipboard';


export default function CreateLeagueScreen() {
  const router = useRouter();
  const { token } = useAuth();
  const [leagueName, setLeagueName] = useState('');
  const [loading, setLoading] = useState(false);
  const [createdLeague, setCreatedLeague] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [copied, setCopied] = useState(false);

  const handleCreate = async () => {
    setErrorMsg('');
    if (!leagueName.trim()) {
      setErrorMsg('Por favor ingresa un nombre para la liga');
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/api/quiniela/league', {
        name: leagueName.trim()
      });
      setCreatedLeague(response.data);
    } catch (error: any) {
      if (error.response?.status !== 401) {
        setErrorMsg(error.response?.data?.detail || 'Error al crear liga');
      }
    } finally {
      setLoading(false);
    }
  };

  const copyCode = async () => {
    if (createdLeague?.code) {
      await Clipboard.setStringAsync(createdLeague.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const shareCode = async () => {
    if (createdLeague?.code) {
      try {
        await Share.share({
          message: `Únete a mi liga "${createdLeague.name}" en Quiniela Liga MX!\n\nCódigo: ${createdLeague.code}`,
        });
      } catch (error) {
        console.error('Error sharing:', error);
      }
    }
  };

  const goToLeague = () => {
    if (createdLeague?.league_id) {
      router.replace({
        pathname: '/quiniela/league-detail',
        params: { leagueId: createdLeague.league_id },
      });
    }
  };

  if (createdLeague) {
    return (
      <View style={styles.container}>
        <View style={styles.successContent}>
          <View style={styles.successIcon}>
            <Ionicons name="checkmark-circle" size={80} color="#00A551" />
          </View>

          <Text style={styles.successTitle}>¡Liga Creada!</Text>
          <Text style={styles.successSubtitle}>{createdLeague.name}</Text>

          <View style={styles.codeCard}>
            <Text style={styles.codeLabel}>Código de Liga</Text>
            <Text style={styles.codeValue}>{createdLeague.code}</Text>
            <Text style={styles.codeHint}>
              Comparte este código para que otros se unan
            </Text>
          </View>

          <View style={styles.actions}>
            <TouchableOpacity style={styles.actionButton} onPress={copyCode}>
              <Ionicons name={copied ? 'checkmark' : 'copy-outline'} size={24} color="#FFFFFF" />
              <Text style={styles.actionButtonText}>{copied ? '¡Copiado!' : 'Copiar Código'}</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.actionButton, styles.actionButtonSecondary]}
              onPress={shareCode}
            >
              <Ionicons name="share-outline" size={24} color="#FFFFFF" />
              <Text style={styles.actionButtonText}>Compartir</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.continueButton} onPress={goToLeague}>
            <Text style={styles.continueButtonText}>IR A LA LIGA</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Ionicons name="people" size={80} color="#DC143C" />
        </View>

        <Text style={styles.title}>Crear Liga Privada</Text>
        <Text style={styles.subtitle}>
          Crea una liga para competir con tus amigos
        </Text>

        <View style={styles.form}>
          <Text style={styles.label}>Nombre de la Liga</Text>
          <View style={styles.inputContainer}>
            <Ionicons name="shield" size={20} color="#666" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="Liga de Amigos"
              placeholderTextColor="#666"
              value={leagueName}
              onChangeText={setLeagueName}
              maxLength={30}
            />
          </View>
          <Text style={styles.charCount}>{leagueName.length}/30 caracteres</Text>

          {errorMsg ? <Text style={styles.errorText}>{errorMsg}</Text> : null}

          <TouchableOpacity
            style={[styles.createButton, loading && styles.buttonDisabled]}
            onPress={handleCreate}
            disabled={loading}
            activeOpacity={0.7}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <Ionicons name="add-circle" size={24} color="#FFFFFF" />
                <Text style={styles.createButtonText}>CREAR LIGA</Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.infoBox}>
          <Ionicons name="information-circle" size={20} color="#0047AB" />
          <Text style={styles.infoText}>
            Se generará un código único que podrás compartir con tus amigos
          </Text>
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
  successContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  iconContainer: {
    alignItems: 'center',
    marginVertical: 32,
  },
  successIcon: {
    marginBottom: 24,
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
  successTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  successSubtitle: {
    fontSize: 18,
    color: '#999',
    marginBottom: 32,
  },
  codeCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 24,
    borderWidth: 2,
    borderColor: '#0047AB',
    alignItems: 'center',
    width: '100%',
    marginBottom: 32,
  },
  codeLabel: {
    fontSize: 14,
    color: '#999',
    marginBottom: 12,
  },
  codeValue: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#0047AB',
    letterSpacing: 4,
    marginBottom: 12,
  },
  codeHint: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
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
  createButton: {
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
  },
  createButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
    width: '100%',
    marginBottom: 16,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0047AB',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  actionButtonSecondary: {
    backgroundColor: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#0047AB',
  },
  actionButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  continueButton: {
    backgroundColor: '#DC143C',
    width: '100%',
    height: 56,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  continueButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1,
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