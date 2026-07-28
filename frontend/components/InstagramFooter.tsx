// Barra fija "Síguenos en IG" — se mantiene visible arriba del tab bar

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Linking } from 'react-native';

const IG_URL = 'https://instagram.com/fuchomx.oficial';

export function InstagramFooter() {
  return (
    <View style={s.container} pointerEvents="box-none">
      <TouchableOpacity
        style={s.bar}
        activeOpacity={0.8}
        onPress={() => Linking.openURL(IG_URL)}
      >
        <Text style={s.text}>📷 Síguenos en IG: @fuchomx.oficial</Text>
      </TouchableOpacity>
    </View>
  );
}

const s = StyleSheet.create({
  container: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
  },
  bar: {
    backgroundColor: '#1a1a1a',
    borderTopWidth: 1,
    borderTopColor: '#E6394650',
    paddingVertical: 10,
    alignItems: 'center',
  },
  text: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
});
