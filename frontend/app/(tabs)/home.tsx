import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  StatusBar,
  ScrollView,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';

export default function HomeScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const insets = useSafeAreaInsets();

  const handleQuinielaPress = () => {
    console.log('NAVIGATING TO QUINIELA');
    router.push('/quiniela');
  };

  const handleFantasyPress = () => {
    console.log('NAVIGATING TO FANTASY');
    router.push('/fantasy');
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <StatusBar barStyle="light-content" />
      
      <ScrollView 
        style={styles.scrollView}
        contentContainerStyle={[
          styles.scrollContent,
          { paddingBottom: insets.bottom + 100 }
        ]}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <View>
            <Text style={styles.greeting}>Hola,</Text>
            <Text style={styles.userName}>{user?.display_name || 'Usuario'}</Text>
          </View>
          <View style={styles.pointsContainer}>
            <Ionicons name="trophy" size={24} color="#FFD700" />
            <Text style={styles.points}>{user?.total_points || 0}</Text>
          </View>
        </View>

        <View style={styles.content}>
          <Text style={styles.title}>SELECCIONA UN MODO</Text>
          <Text style={styles.subtitle}>Elige cómo quieres jugar</Text>

          <View style={styles.cardsContainer}>
            <TouchableOpacity
              style={styles.modeCard}
              activeOpacity={0.8}
              onPress={handleQuinielaPress}
            >
              <View style={[styles.cardIconContainer, { backgroundColor: '#DC143C' }]}>
                <Ionicons name="checkmark-circle" size={48} color="#FFFFFF" />
              </View>
              <Text style={styles.cardTitle}>QUINIELA{' \n'}TRADICIONAL</Text>
              <Text style={styles.cardDescription}>
                Predice los resultados de cada partido y gana puntos
              </Text>
              <View style={styles.cardFooter}>
                <Ionicons name="arrow-forward" size={24} color="#DC143C" />
              </View>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.modeCard}
              activeOpacity={0.8}
              onPress={handleFantasyPress}
            >
              <View style={[styles.cardIconContainer, { backgroundColor: '#0047AB' }]}>
                <Ionicons name="people" size={48} color="#FFFFFF" />
              </View>
              <Text style={styles.cardTitle}>FANTASY{' \n'}FÚTBOL</Text>
              <Text style={styles.cardDescription}>
                Arma tu equipo ideal y compite con otros managers
              </Text>
              <View style={styles.cardFooter}>
                <Ionicons name="arrow-forward" size={24} color="#0047AB" />
              </View>
            </TouchableOpacity>
          </View>

          <View style={styles.infoBox}>
            <Ionicons name="information-circle" size={20} color="#0047AB" />
            <Text style={styles.infoText}>
              Ambos modos están disponibles. Puedes jugar uno o ambos simultáneamente.
            </Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
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
  scrollContent: {
    paddingBottom: 120,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 24,
  },
  greeting: {
    fontSize: 16,
    color: '#999',
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginTop: 4,
  },
  pointsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  points: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginLeft: 8,
  },
  content: {
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFFFFF',
    letterSpacing: 1,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginBottom: 32,
  },
  cardsContainer: {
    gap: 20,
    marginBottom: 24,
  },
  modeCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: '#333',
  },
  cardIconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 12,
    letterSpacing: 0.5,
  },
  cardDescription: {
    fontSize: 14,
    color: '#999',
    lineHeight: 20,
    marginBottom: 16,
  },
  cardFooter: {
    alignItems: 'flex-end',
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