import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface CountdownTimerProps {
  targetDate: string;
}

export default function CountdownTimer({ targetDate }: CountdownTimerProps) {
  const [timeLeft, setTimeLeft] = useState<{
    days: number;
    hours: number;
    minutes: number;
    seconds: number;
  } | null>(null);

  useEffect(() => {
    const calculateTimeLeft = () => {
      const difference = new Date(targetDate).getTime() - new Date().getTime();

      if (difference > 0) {
        return {
          days: Math.floor(difference / (1000 * 60 * 60 * 24)),
          hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
          minutes: Math.floor((difference / 1000 / 60) % 60),
          seconds: Math.floor((difference / 1000) % 60),
        };
      }
      return null;
    };

    setTimeLeft(calculateTimeLeft());

    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft());
    }, 1000);

    return () => clearInterval(timer);
  }, [targetDate]);

  if (!timeLeft) {
    return (
      <View style={styles.container}>
        <Ionicons name="lock-closed" size={20} color="#DC143C" />
        <Text style={styles.expiredText}>¡Ya comenzó!</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.iconContainer}>
        <Ionicons name="alarm-outline" size={20} color="#DC143C" />
      </View>
      <View style={styles.timerContainer}>
        <Text style={styles.label}>Tiempo para enviar:</Text>
        <View style={styles.timeUnits}>
          {timeLeft.days > 0 && (
            <View style={styles.timeUnit}>
              <Text style={styles.timeValue}>{timeLeft.days}</Text>
              <Text style={styles.timeLabel}>d</Text>
            </View>
          )}
          <View style={styles.timeUnit}>
            <Text style={styles.timeValue}>{timeLeft.hours}</Text>
            <Text style={styles.timeLabel}>h</Text>
          </View>
          <Text style={styles.separator}>:</Text>
          <View style={styles.timeUnit}>
            <Text style={styles.timeValue}>{timeLeft.minutes}</Text>
            <Text style={styles.timeLabel}>m</Text>
          </View>
          <Text style={styles.separator}>:</Text>
          <View style={styles.timeUnit}>
            <Text style={styles.timeValue}>{timeLeft.seconds}</Text>
            <Text style={styles.timeLabel}>s</Text>
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a0a0a',
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#DC143C',
  },
  iconContainer: {
    marginRight: 12,
  },
  timerContainer: {
    flex: 1,
  },
  label: {
    fontSize: 12,
    color: '#999',
    marginBottom: 4,
  },
  timeUnits: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  timeUnit: {
    alignItems: 'center',
    marginRight: 4,
  },
  timeValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  timeLabel: {
    fontSize: 10,
    color: '#999',
  },
  separator: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#666',
    marginHorizontal: 4,
  },
  expiredText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#DC143C',
    marginLeft: 8,
  },
});
