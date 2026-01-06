import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface CoachCardProps {
  team?: {
    name: string;
    short_name: string;
  };
  onPress: () => void;
  locked?: boolean;
}

export default function CoachCard({ team, onPress, locked = false }: CoachCardProps) {
  return (
    <TouchableOpacity
      style={styles.container}
      onPress={onPress}
      disabled={locked}
      activeOpacity={0.8}
    >
      {team ? (
        <View style={styles.selected}>
          <View style={styles.icon}>
            <Ionicons name="shield" size={32} color="#DC143C" />
          </View>
          <View style={styles.info}>
            <Text style={styles.label}>DIRECTOR TÉCNICO</Text>
            <Text style={styles.teamName}>{team.name}</Text>
          </View>
        </View>
      ) : (
        <View style={styles.empty}>
          <Ionicons name="person-add" size={32} color="#666" />
          <Text style={styles.emptyText}>Seleccionar DT</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  selected: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  icon: {
    marginRight: 12,
  },
  info: {
    flex: 1,
  },
  label: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#666',
    letterSpacing: 1,
    marginBottom: 4,
  },
  teamName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  empty: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 12,
  },
});