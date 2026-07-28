// Modal de reglas — explica cómo jugar Quiniela y FuchoOnce (tabs)

import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Modal, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface RulesModalProps {
  visible: boolean;
  onClose: () => void;
  initialTab?: 'quiniela' | 'once';
}

const RED = '#E63946';

function Rule({ icon, children }: { icon: string; children: React.ReactNode }) {
  return (
    <View style={s.ruleRow}>
      <Text style={s.ruleIcon}>{icon}</Text>
      <Text style={s.ruleText}>{children}</Text>
    </View>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <Text style={s.sectionTitle}>{children}</Text>;
}

export function RulesModal({ visible, onClose, initialTab = 'quiniela' }: RulesModalProps) {
  const [tab, setTab] = useState<'quiniela' | 'once'>(initialTab);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View style={s.overlay}>
        <View style={s.content}>
          <View style={s.header}>
            <Text style={s.headerTitle}>📖 Reglas</Text>
            <TouchableOpacity onPress={onClose} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
              <Ionicons name="close" size={26} color="#FFFFFF" />
            </TouchableOpacity>
          </View>

          <View style={s.tabBar}>
            <TouchableOpacity
              style={[s.tabButton, tab === 'quiniela' && s.tabButtonActive]}
              onPress={() => setTab('quiniela')}
            >
              <Text style={[s.tabButtonText, tab === 'quiniela' && s.tabButtonTextActive]}>⚽ Quiniela</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[s.tabButton, tab === 'once' && s.tabButtonActive]}
              onPress={() => setTab('once')}
            >
              <Text style={[s.tabButtonText, tab === 'once' && s.tabButtonTextActive]}>🎽 Once</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={s.body} showsVerticalScrollIndicator={false}>
            {tab === 'quiniela' ? (
              <>
                <SectionTitle>¿Cómo se juega?</SectionTitle>
                <Rule icon="🔮">
                  Predice el resultado de cada partido de la jornada: Local, Empate o Visitante.
                </Rule>

                <SectionTitle>Reglas de puntos</SectionTitle>
                <Rule icon="✅">
                  <Text style={s.bold}>Acierto:</Text> +1 punto por partido.
                </Rule>
                <Rule icon="⛔">
                  <Text style={s.bold}>Sin selección al cierre:</Text> -1 punto por partido sin elegir.
                </Rule>
                <Rule icon="🎁">
                  <Text style={s.bold}>Bonus nuevos usuarios:</Text> en tus primeras 3 jornadas, si quedas
                  último recibes puntos extra para quedar 3 lugares arriba.
                </Rule>
              </>
            ) : (
              <>
                <SectionTitle>¿Cómo se juega?</SectionTitle>
                <Rule icon="🎽">
                  Arma tu equipo de 11 jugadores reales de Liga MX. Elige un DT. Ganas puntos según su
                  desempeño real en cada partido.
                </Rule>

                <SectionTitle>Reglas de puntos</SectionTitle>
                <Rule icon="⏱️">Jugar 60+ minutos: +2 pts · Jugar menos de 60: +1 pt</Rule>
                <Rule icon="⚽">Gol: DEL +4 · MED +5 · DEF +6 · POR +6</Rule>
                <Rule icon="🎯">Asistencia: +3 pts</Rule>
                <Rule icon="🧤">Portería a cero (POR/DEF): +4 a +5 pts</Rule>
                <Rule icon="🥅">Cada 2 goles recibidos (POR/DEF): -1 pt</Rule>
                <Rule icon="🟨">Tarjeta amarilla: -1 pt · 🟥 Tarjeta roja: -3 pts</Rule>
                <Rule icon="🧤">Penalti atajado: +5 pts · Penalti fallado: -3 pts</Rule>
                <Rule icon="😬">Autogol: -2 pts</Rule>
                <Rule icon="⭐">Jugador del partido: +2 pts · Doblete: +1 pt · Hat-trick: +2 pts</Rule>
                <Rule icon="👔">DT: equipo gana +2 pts · empata +1 pt · pierde 0 pts</Rule>
                <Rule icon="🚫">
                  <Text style={s.bold}>Sin alineación al cierre:</Text> -5 puntos.
                </Rule>
                <Rule icon="🎁">
                  <Text style={s.bold}>Bonus nuevos usuarios:</Text> mismo sistema que Quiniela — en tus
                  primeras 3 jornadas, si quedas último recibes puntos extra para quedar 3 lugares arriba.
                </Rule>
              </>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const s = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  content: {
    backgroundColor: '#000000',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    borderWidth: 1,
    borderColor: '#1a1a1a',
    maxHeight: '85%',
    paddingBottom: 24,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 12,
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 0.5,
  },
  tabBar: {
    flexDirection: 'row',
    marginHorizontal: 20,
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 4,
    marginBottom: 8,
  },
  tabButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: 'center',
  },
  tabButtonActive: {
    backgroundColor: RED,
  },
  tabButtonText: {
    color: '#999',
    fontSize: 14,
    fontWeight: '700',
  },
  tabButtonTextActive: {
    color: '#FFFFFF',
  },
  body: {
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  sectionTitle: {
    color: RED,
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 1,
    marginTop: 16,
    marginBottom: 10,
    textTransform: 'uppercase',
  },
  ruleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
    gap: 10,
  },
  ruleIcon: {
    fontSize: 16,
    width: 22,
    textAlign: 'center',
  },
  ruleText: {
    flex: 1,
    color: '#DDDDDD',
    fontSize: 13,
    lineHeight: 19,
  },
  bold: {
    fontWeight: '800',
    color: '#FFFFFF',
  },
});
