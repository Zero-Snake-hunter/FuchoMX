import React from 'react';
import { TouchableOpacity, View, Text, StyleSheet } from 'react-native';
import JerseyView from './JerseyView';

interface Player {
  id: string;
  name: string;
  number: number;
  team: {
    short_name: string;
  };
}

interface PositionSlotProps {
  position: string;
  player?: Player;
  onPress: () => void;
  locked?: boolean;
}

export default function PositionSlot({ position, player, onPress, locked = false }: PositionSlotProps) {
  return (
    <TouchableOpacity
      style={styles.container}
      onPress={onPress}
      disabled={locked}
      activeOpacity={0.7}
    >
      <JerseyView
        number={player?.number}
        isEmpty={!player}
        size={56}
      />
      {player && (
        <View style={styles.info}>
          <Text style={styles.name} numberOfLines={1}>
            {player.name.split(' ').pop()}
          </Text>
          <Text style={styles.team} numberOfLines={1}>
            {player.team.short_name}
          </Text>
        </View>
      )}
      {!player && <Text style={styles.positionLabel}>{position}</Text>}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    width: 70,
    marginVertical: 8,
  },
  info: {
    marginTop: 6,
    alignItems: 'center',
  },
  name: {
    fontSize: 11,
    fontWeight: '600',
    color: '#FFFFFF',
    textAlign: 'center',
  },
  team: {
    fontSize: 9,
    color: '#CCCCCC',
    textAlign: 'center',
  },
  positionLabel: {
    fontSize: 10,
    color: '#FFFFFF',
    marginTop: 4,
    fontWeight: '600',
  },
});