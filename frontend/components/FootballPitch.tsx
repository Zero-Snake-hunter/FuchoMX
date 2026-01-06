import React from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';

const { width } = Dimensions.get('window');
const PITCH_WIDTH = width - 32;
const PITCH_HEIGHT = PITCH_WIDTH * 1.4;

export default function FootballPitch({ children }: { children: React.ReactNode }) {
  return (
    <View style={styles.container}>
      <View style={styles.pitch}>
        <View style={styles.centerLine} />
        <View style={styles.centerCircle} />
        <View style={styles.topPenaltyBox} />
        <View style={styles.bottomPenaltyBox} />
        <View style={styles.topGoalBox} />
        <View style={styles.bottomGoalBox} />
        {children}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  pitch: {
    width: PITCH_WIDTH,
    height: PITCH_HEIGHT,
    backgroundColor: '#2d7a3f',
    borderWidth: 3,
    borderColor: '#FFFFFF',
    borderRadius: 8,
    position: 'relative',
  },
  centerLine: {
    position: 'absolute',
    top: PITCH_HEIGHT / 2,
    left: 0,
    right: 0,
    height: 2,
    backgroundColor: '#FFFFFF',
  },
  centerCircle: {
    position: 'absolute',
    top: PITCH_HEIGHT / 2 - 40,
    left: PITCH_WIDTH / 2 - 40,
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  topPenaltyBox: {
    position: 'absolute',
    top: 0,
    left: PITCH_WIDTH * 0.2,
    width: PITCH_WIDTH * 0.6,
    height: PITCH_HEIGHT * 0.15,
    borderWidth: 2,
    borderTopWidth: 0,
    borderColor: '#FFFFFF',
  },
  bottomPenaltyBox: {
    position: 'absolute',
    bottom: 0,
    left: PITCH_WIDTH * 0.2,
    width: PITCH_WIDTH * 0.6,
    height: PITCH_HEIGHT * 0.15,
    borderWidth: 2,
    borderBottomWidth: 0,
    borderColor: '#FFFFFF',
  },
  topGoalBox: {
    position: 'absolute',
    top: 0,
    left: PITCH_WIDTH * 0.35,
    width: PITCH_WIDTH * 0.3,
    height: PITCH_HEIGHT * 0.08,
    borderWidth: 2,
    borderTopWidth: 0,
    borderColor: '#FFFFFF',
  },
  bottomGoalBox: {
    position: 'absolute',
    bottom: 0,
    left: PITCH_WIDTH * 0.35,
    width: PITCH_WIDTH * 0.3,
    height: PITCH_HEIGHT * 0.08,
    borderWidth: 2,
    borderBottomWidth: 0,
    borderColor: '#FFFFFF',
  },
});