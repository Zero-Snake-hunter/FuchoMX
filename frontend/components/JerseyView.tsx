import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface JerseyViewProps {
  number?: number;
  teamColor?: string;
  isEmpty?: boolean;
  size?: number;
}

export default function JerseyView({ number, teamColor = '#DC143C', isEmpty = false, size = 50 }: JerseyViewProps) {
  if (isEmpty) {
    return (
      <View style={[styles.jersey, styles.emptyJersey, { width: size, height: size, borderRadius: size / 2 }]}>
        <Ionicons name="add" size={size * 0.5} color="#666" />
      </View>
    );
  }

  return (
    <View style={[styles.jersey, { backgroundColor: teamColor, width: size, height: size, borderRadius: size / 2 }]}>
      <Text style={[styles.number, { fontSize: size * 0.4 }]}>{number}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  jersey: {
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 5,
  },
  emptyJersey: {
    backgroundColor: '#FFFFFF',
    borderWidth: 2,
    borderColor: '#333',
    borderStyle: 'dashed',
  },
  number: {
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
});