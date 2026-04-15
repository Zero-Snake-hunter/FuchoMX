// Archivo: /app/frontend/app/profile/plan.tsx
// Pantalla "Tu Plan" — 100% gratuito, sin sección premium

import React from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { SPONSORS } from '../config/sponsors';

const FREE_PERKS = [
  { icon: '📝', text: 'Quiniela tradicional',           sub: 'Todas las jornadas de Liga MX' },
  { icon: '⚽', text: 'FuchoOnce',                      sub: 'Formación 4-4-2 con jugadores reales' },
  { icon: '🏟️', text: 'Crea ligas ilimitadas',          sub: 'Hasta 25 amigos por liga' },
  { icon: '🤝', text: 'Únete a ligas ilimitadas',       sub: 'Sin límite de ligas ajenas' },
  { icon: '🔀', text: 'Quiniela y ONCE en una liga',    sub: 'Ambos modos disponibles' },
  { icon: '🏆', text: 'Rankings globales',              sub: 'Compite con todos los usuarios' },
  { icon: '🔥', text: 'Rachas y logros',                sub: '20 logros desbloqueables' },
  { icon: '🔔', text: 'Notificaciones de jornada',      sub: 'Recordatorios automáticos' },
];

const PerkRow = ({ icon, text, sub }: { icon: string; text: string; sub: string }) => (
  <View style={p.perkRow}>
    <View style={p.perkIcon}>
      <Text style={p.perkEmoji}>{icon}</Text>
    </View>
    <View style={p.perkInfo}>
      <Text style={p.perkTitle}>{text}</Text>
      <Text style={p.perkSub}>{sub}</Text>
    </View>
    <Text style={p.checkIcon}>✅</Text>
  </View>
);

export default function PlanScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={st.container}>
      <StatusBar barStyle="light-content" />

      <View style={st.header}>
        <TouchableOpacity onPress={() => router.back()} style={st.backBtn}>
          <Text style={st.backText}>← Atrás</Text>
        </TouchableOpacity>
        <Text style={st.headerTitle}>Tu Plan</Text>
        <View style={{ width: 60 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 50 }}>

        <View style={st.planBadge}>
          <View style={st.planBadgeLeft}>
            <Text style={st.planIcon}>🎉</Text>
            <View>
              <Text style={st.planName}>Plan Gratuito</Text>
              <Text style={st.planSub}>Sin fecha de vencimiento · Siempre gratis</Text>
            </View>
          </View>
          <View style={st.planStatusPill}>
            <Text style={st.planStatusText}>ACTIVO</Text>
          </View>
        </View>

        <View style={st.highlightBox}>
          <Text style={st.highlightEmoji}>👥</Text>
          <View style={st.highlightInfo}>
            <Text style={st.highlightTitle}>Ligas ilimitadas, hasta 25 amigos</Text>
            <Text style={st.highlightSub}>
              Crea todas las ligas que quieras e invita hasta a{' '}
              <Text style={{ color: '#E63946', fontWeight: '700' }}>25 personas</Text> en cada una.
            </Text>
          </View>
        </View>

        <Text style={st.sectionTitle}>✅ Incluido en tu plan gratuito</Text>
        <View style={st.perksList}>
          {FREE_PERKS.map((item, i) => (
            <PerkRow key={i} icon={item.icon} text={item.text} sub={item.sub} />
          ))}
        </View>

        <View style={st.noteBox}>
          <Text style={st.noteText}>
            💚 FuchoMX es y será siempre{' '}
            <Text style={{ color: '#00A551', fontWeight: '700' }}>100% gratuito</Text>.
            {'\n'}Sin anuncios, sin pagos ocultos, sin trampas.
          </Text>
        </View>

        {/* ── Aliados (solo si hay) ── */}
        {SPONSORS.bronce.aliados.length > 0 && (
          <View style={st.aliadosBox}>
            <Text style={st.aliadosTitle}>🤝 ALIADOS</Text>
            {SPONSORS.bronce.aliados.map((a, i) => (
              <View key={i} style={st.aliadoRow}>
                <Text style={st.aliadoNombre}>{a.nombre}</Text>
                <Text style={st.aliadoUrl}>{a.url}</Text>
              </View>
            ))}
          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const p = StyleSheet.create({
  perkRow:   { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 16, borderBottomWidth: 1, borderBottomColor: '#111' },
  perkIcon:  { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center', marginRight: 12, backgroundColor: '#E6394611' },
  perkEmoji: { fontSize: 20 },
  perkInfo:  { flex: 1 },
  perkTitle: { color: '#EEE', fontSize: 14, fontWeight: '600' },
  perkSub:   { color: '#666', fontSize: 12, marginTop: 1 },
  checkIcon: { fontSize: 16 },
});

const st = StyleSheet.create({
  container:       { flex: 1, backgroundColor: '#0A0A0A' },
  header:          { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#181818' },
  backBtn:         { padding: 4 },
  backText:        { color: '#E63946', fontSize: 15 },
  headerTitle:     { color: '#FFF', fontSize: 18, fontWeight: '700' },
  planBadge:       { margin: 16, backgroundColor: '#111', borderRadius: 16, padding: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderWidth: 1, borderColor: '#E6394633' },
  planBadgeLeft:   { flexDirection: 'row', alignItems: 'center' },
  planIcon:        { fontSize: 32, marginRight: 12 },
  planName:        { color: '#FFF', fontSize: 17, fontWeight: '800' },
  planSub:         { color: '#666', fontSize: 12, marginTop: 2 },
  planStatusPill:  { backgroundColor: '#E6394622', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5, borderWidth: 1, borderColor: '#E6394666' },
  planStatusText:  { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  highlightBox:    { marginHorizontal: 16, marginBottom: 8, backgroundColor: '#0D1117', borderRadius: 14, padding: 16, flexDirection: 'row', borderWidth: 1, borderColor: '#1D88E533' },
  highlightEmoji:  { fontSize: 30, marginTop: 2, marginRight: 14 },
  highlightInfo:   { flex: 1 },
  highlightTitle:  { color: '#FFF', fontSize: 15, fontWeight: '700', marginBottom: 4 },
  highlightSub:    { color: '#888', fontSize: 13, lineHeight: 19 },
  sectionTitle:    { color: '#FFF', fontSize: 15, fontWeight: '700', paddingHorizontal: 16, marginBottom: 4, marginTop: 8 },
  perksList:       { backgroundColor: '#111', borderRadius: 14, marginHorizontal: 16, overflow: 'hidden', borderWidth: 1, borderColor: '#1A1A1A' },
  noteBox:         { margin: 16, backgroundColor: '#0D1117', borderRadius: 12, padding: 16, borderWidth: 1, borderColor: '#00A55133', alignItems: 'center' },
  noteText:        { color: '#888', fontSize: 13, lineHeight: 20, textAlign: 'center' },
  aliadosBox:      { margin: 16, backgroundColor: '#111', borderRadius: 12, padding: 16, borderWidth: 1, borderColor: '#1A1A1A' },
  aliadosTitle:    { color: '#666', fontSize: 12, fontWeight: '700', marginBottom: 8, letterSpacing: 1 },
  aliadoRow:       { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#1A1A1A' },
  aliadoNombre:    { color: '#EEE', fontSize: 14, fontWeight: '600' },
  aliadoUrl:       { color: '#666', fontSize: 12 },
});

import React from 'react';
import {
  View, Text, StyleSheet, ScrollView,
  TouchableOpacity, StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { SPONSORS } from '../config/sponsors';

const FREE_PERKS = [
  { icon: '📝', text: 'Quiniela tradicional',           sub: 'Todas las jornadas de Liga MX' },
  { icon: '⚽', text: 'FuchoOnce',                      sub: 'Formación 4-4-2 con jugadores reales' },
  { icon: '🏟️', text: 'Crea ligas ilimitadas',          sub: 'Hasta 25 amigos por liga' },
  { icon: '🤝', text: 'Únete a ligas ilimitadas',       sub: 'Sin límite de ligas ajenas' },
  { icon: '🔀', text: 'Quiniela y ONCE en una liga', sub: 'Ambos modos disponibles' },
  { icon: '🏆', text: 'Rankings globales',              sub: 'Compite con todos los usuarios' },
  { icon: '🔥', text: 'Rachas y logros',                sub: '20 logros desbloqueables' },
  { icon: '🔔', text: 'Notificaciones de jornada',      sub: 'Recordatorios automáticos' },
];

const COMING_SOON = [
  { icon: '🥇', text: 'Ligas con premios reales',        sub: 'Torneos patrocinados' },
  { icon: '📊', text: 'Estadísticas avanzadas',          sub: 'Análisis de tu rendimiento' },
  { icon: '👥', text: 'Ligas de más de 25 personas',     sub: 'Para grupos grandes' },
  { icon: '🎨', text: 'Escudos y nombres personalizados',sub: 'Identidad de tu liga' },
];

const PerkRow = ({
  icon, text, sub, locked = false,
}: {
  icon: string; text: string; sub: string; locked?: boolean;
}) => (
  <View style={[p.perkRow, locked && p.perkRowLocked]}>
    <View style={[p.perkIcon, { backgroundColor: locked ? '#1A1A1A' : '#E6394611' }]}>
      <Text style={[p.perkEmoji, locked && { opacity: 0.4 }]}>{icon}</Text>
    </View>
    <View style={p.perkInfo}>
      <Text style={[p.perkTitle, locked && { color: '#444' }]}>{text}</Text>
      <Text style={[p.perkSub,   locked && { color: '#333' }]}>{sub}</Text>
    </View>
    {locked
      ? <Text style={p.lockIcon}>🔒</Text>
      : <Text style={p.checkIcon}>✅</Text>
    }
  </View>
);

export default function PlanScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={st.container}>
      <StatusBar barStyle="light-content" />

      <View style={st.header}>
        <TouchableOpacity onPress={() => router.back()} style={st.backBtn}>
          <Text style={st.backText}>← Atrás</Text>
        </TouchableOpacity>
        <Text style={st.headerTitle}>Tu Plan</Text>
        <View style={{ width: 60 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 50 }}>

        <View style={st.planBadge}>
          <View style={st.planBadgeLeft}>
            <Text style={st.planIcon}>🎉</Text>
            <View>
              <Text style={st.planName}>Plan Gratuito</Text>
              <Text style={st.planSub}>Sin fecha de vencimiento</Text>
            </View>
          </View>
          <View style={st.planStatusPill}>
            <Text style={st.planStatusText}>ACTIVO</Text>
          </View>
        </View>

        <View style={st.highlightBox}>
          <Text style={st.highlightEmoji}>👥</Text>
          <View style={st.highlightInfo}>
            <Text style={st.highlightTitle}>Ligas ilimitadas, hasta 25 amigos</Text>
            <Text style={st.highlightSub}>
              Crea todas las ligas que quieras por cada grupo de amigos que tengas e invita hasta a{' '}
              <Text style={{ color: '#E63946', fontWeight: '700' }}>25 personas</Text> en cada una.
            </Text>
          </View>
        </View>

        <Text style={st.sectionTitle}>✅ Incluido en tu plan gratuito</Text>
        <View style={st.perksList}>
          {FREE_PERKS.map((item, i) => (
            <PerkRow key={i} icon={item.icon} text={item.text} sub={item.sub} locked={false} />
          ))}
        </View>

        <Text style={[st.sectionTitle, { marginTop: 28 }]}>🔒 Próximamente (Premium)</Text>
        <View style={st.perksList}>
          {COMING_SOON.map((item, i) => (
            <PerkRow key={i} icon={item.icon} text={item.text} sub={item.sub} locked={true} />
          ))}
        </View>

        <View style={st.noteBox}>
          <Text style={st.noteText}>
            💬 Esta app no tiene anuncios ni pagos ocultos. Las funciones premium
            serán opcionales y no afectarán el juego gratuito.
          </Text>
        </View>

        {/* ── Aliados (solo si hay) ── */}
        {SPONSORS.bronce.aliados.length > 0 && (
          <View style={st.aliadosBox}>
            <Text style={st.aliadosTitle}>🤝 ALIADOS</Text>
            {SPONSORS.bronce.aliados.map((a, i) => (
              <View key={i} style={st.aliadoRow}>
                <Text style={st.aliadoNombre}>{a.nombre}</Text>
                <Text style={st.aliadoUrl}>{a.url}</Text>
              </View>
            ))}
          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const p = StyleSheet.create({
  perkRow:       { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 16, borderBottomWidth: 1, borderBottomColor: '#111' },
  perkRowLocked: { opacity: 0.6 },
  perkIcon:      { width: 42, height: 42, borderRadius: 21, alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  perkEmoji:     { fontSize: 20 },
  perkInfo:      { flex: 1 },
  perkTitle:     { color: '#EEE', fontSize: 14, fontWeight: '600' },
  perkSub:       { color: '#666', fontSize: 12, marginTop: 1 },
  lockIcon:      { fontSize: 16 },
  checkIcon:     { fontSize: 16 },
});

const st = StyleSheet.create({
  container:       { flex: 1, backgroundColor: '#0A0A0A' },
  header:          { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#181818' },
  backBtn:         { padding: 4 },
  backText:        { color: '#E63946', fontSize: 15 },
  headerTitle:     { color: '#FFF', fontSize: 18, fontWeight: '700' },
  planBadge:       { margin: 16, backgroundColor: '#111', borderRadius: 16, padding: 18, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderWidth: 1, borderColor: '#E6394633' },
  planBadgeLeft:   { flexDirection: 'row', alignItems: 'center' },
  planIcon:        { fontSize: 32, marginRight: 12 },
  planName:        { color: '#FFF', fontSize: 17, fontWeight: '800' },
  planSub:         { color: '#666', fontSize: 12, marginTop: 2 },
  planStatusPill:  { backgroundColor: '#E6394622', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5, borderWidth: 1, borderColor: '#E6394666' },
  planStatusText:  { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  highlightBox:    { marginHorizontal: 16, marginBottom: 8, backgroundColor: '#0D1117', borderRadius: 14, padding: 16, flexDirection: 'row', borderWidth: 1, borderColor: '#1D88E533' },
  highlightEmoji:  { fontSize: 30, marginTop: 2, marginRight: 14 },
  highlightInfo:   { flex: 1 },
  highlightTitle:  { color: '#FFF', fontSize: 15, fontWeight: '700', marginBottom: 4 },
  highlightSub:    { color: '#888', fontSize: 13, lineHeight: 19 },
  sectionTitle:    { color: '#FFF', fontSize: 15, fontWeight: '700', paddingHorizontal: 16, marginBottom: 4, marginTop: 8 },
  perksList:       { backgroundColor: '#111', borderRadius: 14, marginHorizontal: 16, overflow: 'hidden', borderWidth: 1, borderColor: '#1A1A1A' },
  noteBox:         { margin: 16, backgroundColor: '#0D0D0D', borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#1E1E1E' },
  noteText:        { color: '#555', fontSize: 12, lineHeight: 18, textAlign: 'center' },
});
