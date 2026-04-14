import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { format } from 'date-fns';
import es from 'date-fns/locale/es';

interface Match {
  id: string;
  home_team: {
    name: string;
    short_name: string;
    shield_url: string;
  };
  away_team: {
    name: string;
    short_name: string;
    shield_url: string;
  };
  start_at: string;
  status: string;
  home_score: number | null;
  away_score: number | null;
}

interface MatchCardProps {
  match: Match;
  selection?: string;
  onSelect: (selection: string) => void;
  disabled?: boolean;
}

export default function MatchCard({ match, selection, onSelect, disabled }: MatchCardProps) {
  const matchDate = new Date(match.start_at);
  const isFinished = match.status === 'finished';

  const renderOption = (option: string, label: string) => {
    const isSelected = selection === option;
    
    return (
      <TouchableOpacity
        style={[
          styles.option,
          isSelected && styles.optionSelected,
          disabled && styles.optionDisabled,
        ]}
        onPress={() => !disabled && onSelect(option)}
        disabled={disabled}
      >
        <View style={[
          styles.radio,
          isSelected && styles.radioSelected,
        ]}>
          {isSelected && <View style={styles.radioInner} />}
        </View>
        <Text style={[
          styles.optionText,
          isSelected && styles.optionTextSelected,
        ]}>
          {label}
        </Text>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.card}>
      {/* Match Info */}
      <View style={styles.matchInfo}>
        <Text style={styles.matchDate}>
          {format(matchDate, "EEEE d 'de' MMMM", { locale: es })}
        </Text>
        <Text style={styles.matchTime}>
          {format(matchDate, 'HH:mm')} hrs
        </Text>
      </View>

      {/* Teams */}
      <View style={styles.teamsContainer}>
        {/* Home Team */}
        <View style={styles.team}>
          <Image
            source={{ uri: match.home_team.shield_url }}
            defaultSource={require('../assets/images/FuchoMX.png')}
            style={styles.shield}
            resizeMode="contain"
            onError={(e) => console.log('Shield error home:', e.nativeEvent.error)}
          />
          <Text style={styles.teamName} numberOfLines={2}>
            {match.home_team.name}
          </Text>
          {isFinished && match.home_score !== null && (
            <View style={styles.scoreBox}>
              <Text style={styles.scoreText}>{match.home_score}</Text>
            </View>
          )}
        </View>

        {/* VS */}
        <View style={styles.vsContainer}>
          <Text style={styles.vsText}>VS</Text>
        </View>

        {/* Away Team */}
        <View style={styles.team}>
          <Image
            source={{ uri: match.away_team.shield_url }}
            defaultSource={require('../assets/images/FuchoMX.png')}
            style={styles.shield}
            resizeMode="contain"
            onError={(e) => console.log('Shield error away:', e.nativeEvent.error)}
          />
          <Text style={styles.teamName} numberOfLines={2}>
            {match.away_team.name}
          </Text>
          {isFinished && match.away_score !== null && (
            <View style={styles.scoreBox}>
              <Text style={styles.scoreText}>{match.away_score}</Text>
            </View>
          )}
        </View>
      </View>

      {/* Selection Options */}
      {!isFinished && (
        <View style={styles.options}>
          {renderOption('HOME', `Gana ${match.home_team.name}`)}
          {renderOption('DRAW', 'Empate')}
          {renderOption('AWAY', `Gana ${match.away_team.name}`)}
        </View>
      )}

      {isFinished && (
        <View style={styles.finishedBadge}>
          <Ionicons name="checkmark-circle" size={16} color="#00A551" />
          <Text style={styles.finishedText}>Finalizado</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  matchInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  matchDate: {
    fontSize: 12,
    color: '#999',
    textTransform: 'capitalize',
  },
  matchTime: {
    fontSize: 12,
    color: '#0047AB',
    fontWeight: '600',
  },
  teamsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  team: {
    flex: 1,
    alignItems: 'center',
  },
  shield: {
    width: 48,
    height: 48,
    marginBottom: 8,
  },
  teamName: {
    fontSize: 12,
    color: '#FFFFFF',
    textAlign: 'center',
    fontWeight: '600',
  },
  scoreBox: {
    marginTop: 8,
    backgroundColor: '#DC143C',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 8,
  },
  scoreText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  vsContainer: {
    width: 40,
    alignItems: 'center',
  },
  vsText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#666',
  },
  options: {
    gap: 8,
  },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0a0a0a',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#333',
  },
  optionSelected: {
    backgroundColor: '#2a0a0a',
    borderColor: '#DC143C',
  },
  optionDisabled: {
    opacity: 0.5,
  },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#666',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  radioSelected: {
    borderColor: '#DC143C',
  },
  radioInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#DC143C',
  },
  optionText: {
    fontSize: 14,
    color: '#FFFFFF',
  },
  optionTextSelected: {
    fontWeight: '600',
    color: '#DC143C',
  },
  finishedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0a2a1a',
    padding: 8,
    borderRadius: 8,
    gap: 8,
  },
  finishedText: {
    color: '#00A551',
    fontSize: 12,
    fontWeight: '600',
  },
});
