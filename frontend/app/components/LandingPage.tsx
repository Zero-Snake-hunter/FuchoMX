import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Image, Linking, Dimensions,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');
const isWide = width > 768;

const FEATURES = [
  { icon: 'football', title: 'FuchoQuiniela', desc: 'Predice los resultados de cada jornada de Liga MX y compite con tus cuates en tu liga privada.', color: '#E63946' },
  { icon: 'shirt', title: 'FuchoOnce', desc: 'Arma tu once ideal con jugadores reales de Liga MX y gana puntos según sus estadísticas reales.', color: '#1D88E5' },
  { icon: 'trophy', title: 'Ligas Privadas', desc: 'Crea tu liga, invita a tus amigos con un código y compite toda la temporada.', color: '#FFD700' },
  { icon: 'ribbon', title: 'Logros y Rachas', desc: '20 logros desbloqueables, rachas de aciertos y rankings en tiempo real.', color: '#2A9D8F' },
  { icon: 'bar-chart', title: 'Rankings en Vivo', desc: 'Tabla de posiciones actualizada automáticamente al terminar cada partido.', color: '#FF9800' },
  { icon: 'gift', title: '100% Gratis', desc: 'Sin suscripciones, sin pagos ocultos. Quiniela y fantasy completamente gratis.', color: '#4CAF50' },
];

const SPONSORS = [
  { tier: 'ORO', color: '#FFD700', desc: 'Presencia exclusiva en todo el torneo' },
  { tier: 'PLATA', color: '#AAAAAA', desc: 'Visibilidad por jornada, rotando' },
  { tier: 'BRONCE', color: '#CD7F32', desc: 'Presencia continua en perfiles' },
];

export default function LandingPage() {
  const router = useRouter();

  return (
    <ScrollView style={s.container} showsVerticalScrollIndicator={false}>

      {/* NAV */}
      <View style={s.nav}>
        <Image source={require('../../assets/images/FuchoMX.png')} style={s.navLogo} resizeMode="contain" />
        <Text style={s.navBrand}>FUCHO MX</Text>
        <View style={{ flex: 1 }} />
        <TouchableOpacity style={s.navBtn} onPress={() => router.push('/(auth)/login')}>
          <Text style={s.navBtnText}>Iniciar sesión</Text>
        </TouchableOpacity>
        <TouchableOpacity style={s.navBtnPrimary} onPress={() => router.push('/(auth)/register')}>
          <Text style={s.navBtnPrimaryText}>Registrarse</Text>
        </TouchableOpacity>
      </View>

      {/* HERO */}
      <View style={s.hero}>
        <View style={s.heroPill}>
          <Text style={s.heroPillText}>LIGA MX · QUINIELA · ONCE</Text>
        </View>
        <Image source={require('../../assets/images/FuchoMX.png')} style={s.heroLogo} resizeMode="contain" />
        <Text style={s.heroTitle}>La quiniela de{'\n'}tus cuates</Text>
        <Text style={s.heroSubtitle}>Predice. Arma tu once ideal. Gana.{'\n'}Tu fut, con tus cuates.</Text>
        <View style={s.heroBtns}>
          <TouchableOpacity style={s.heroBtnPrimary} onPress={() => router.push('/(auth)/register')}>
            <Ionicons name="rocket" size={18} color="#000" />
            <Text style={s.heroBtnPrimaryText}>Jugar gratis</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.heroBtnSecondary} onPress={() => router.push('/(auth)/login')}>
            <Text style={s.heroBtnSecondaryText}>Ya tengo cuenta</Text>
          </TouchableOpacity>
        </View>
        <View style={s.heroStats}>
          <View style={s.heroStat}>
            <Text style={s.heroStatNum}>2</Text>
            <Text style={s.heroStatLabel}>Modos de juego</Text>
          </View>
          <View style={s.heroStatDivider} />
          <View style={s.heroStat}>
            <Text style={s.heroStatNum}>20</Text>
            <Text style={s.heroStatLabel}>Logros</Text>
          </View>
          <View style={s.heroStatDivider} />
          <View style={s.heroStat}>
            <Text style={s.heroStatNum}>100%</Text>
            <Text style={s.heroStatLabel}>Gratis</Text>
          </View>
        </View>
      </View>

      {/* FEATURES */}
      <View style={s.section}>
        <Text style={s.sectionTag}>CARACTERÍSTICAS</Text>
        <Text style={s.sectionTitle}>Todo lo que necesitas{'\n'}para tu quiniela</Text>
        <View style={s.featuresGrid}>
          {FEATURES.map((f, i) => (
            <View key={i} style={[s.featureCard, isWide && s.featureCardWide]}>
              <View style={[s.featureIcon, { backgroundColor: f.color + '22' }]}>
                <Ionicons name={f.icon as any} size={28} color={f.color} />
              </View>
              <Text style={s.featureTitle}>{f.title}</Text>
              <Text style={s.featureDesc}>{f.desc}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* COMO FUNCIONA */}
      <View style={[s.section, { backgroundColor: '#111' }]}>
        <Text style={s.sectionTag}>ASÍ DE FÁCIL</Text>
        <Text style={s.sectionTitle}>3 pasos y ya{'\n'}estás jugando</Text>
        <View style={s.steps}>
          {[
            { n: '1', t: 'Crea tu cuenta gratis', d: 'Regístrate en segundos, sin tarjeta.' },
            { n: '2', t: 'Crea o únete a una liga', d: 'Invita a tus cuates con un código único.' },
            { n: '3', t: 'Predice y compite', d: 'Cada jornada de Liga MX, tus predicciones valen.' },
          ].map((step, i) => (
            <View key={i} style={s.stepCard}>
              <View style={s.stepNum}>
                <Text style={s.stepNumText}>{step.n}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={s.stepTitle}>{step.t}</Text>
                <Text style={s.stepDesc}>{step.d}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {/* SPONSORS */}
      <View style={s.section}>
        <Text style={s.sectionTag}>PATROCINADORES</Text>
        <Text style={s.sectionTitle}>Llega a los aficionados{'\n'}de Liga MX en Aguascalientes</Text>
        <Text style={s.sponsorSubtitle}>FuchoMX conecta marcas locales con fanáticos del fut. 100% gratis para usuarios, monetizado por sponsors.</Text>
        <View style={s.sponsorCards}>
          {SPONSORS.map((sp, i) => (
            <View key={i} style={[s.sponsorCard, { borderColor: sp.color }]}>
              <Text style={[s.sponsorTier, { color: sp.color }]}>{sp.tier}</Text>
              <Text style={s.sponsorDesc}>{sp.desc}</Text>
            </View>
          ))}
        </View>
        <TouchableOpacity
          style={s.sponsorBtn}
          onPress={() => Linking.openURL('https://wa.me/524492807269?text=Hola,%20me%20interesa%20ser%20patrocinador%20de%20FuchoMX')}
        >
          <Ionicons name="logo-whatsapp" size={20} color="#FFF" />
          <Text style={s.sponsorBtnText}>Quiero ser patrocinador</Text>
        </TouchableOpacity>
      </View>

      {/* CTA FINAL */}
      <View style={[s.section, { backgroundColor: '#E63946', alignItems: 'center' }]}>
        <Text style={[s.sectionTitle, { color: '#FFF', textAlign: 'center' }]}>¿Listo para jugar?</Text>
        <Text style={[s.heroSubtitle, { color: 'rgba(255,255,255,0.8)', textAlign: 'center' }]}>Únete gratis y empieza a competir esta jornada.</Text>
        <TouchableOpacity style={s.ctaBtn} onPress={() => router.push('/(auth)/register')}>
          <Text style={s.ctaBtnText}>Crear mi cuenta gratis 🚀</Text>
        </TouchableOpacity>
      </View>

      {/* FOOTER */}
      <View style={s.footer}>
        <Image source={require('../../assets/images/FuchoMX.png')} style={s.footerLogo} resizeMode="contain" />
        <Text style={s.footerBrand}>FUCHO MX</Text>
        <Text style={s.footerSub}>Tu fut, con tus cuates.</Text>
        <Text style={s.footerContact}>contacto@distrito.digital</Text>
        <Text style={s.footerCopy}>© 2026 FuchoMX · Aguascalientes, México</Text>
      </View>

    </ScrollView>
  );
}

const s = StyleSheet.create({
  container:           { flex: 1, backgroundColor: '#090909' },
  // NAV
  nav:                 { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 24, paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: '#1a1a1a' },
  navLogo:             { width: 36, height: 36, marginRight: 8 },
  navBrand:            { color: '#FFF', fontWeight: '900', fontSize: 16, letterSpacing: 1, marginRight: 16 },
  navBtn:              { paddingHorizontal: 16, paddingVertical: 8, marginRight: 8 },
  navBtnText:          { color: '#AAAAAA', fontSize: 14 },
  navBtnPrimary:       { backgroundColor: '#E63946', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  navBtnPrimaryText:   { color: '#FFF', fontWeight: '700', fontSize: 14 },
  // HERO
  hero:                { alignItems: 'center', paddingHorizontal: 24, paddingTop: 60, paddingBottom: 60 },
  heroPill:            { borderWidth: 1, borderColor: '#E6394655', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 5, marginBottom: 24 },
  heroPillText:        { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 2 },
  heroLogo:            { width: 140, height: 140, marginBottom: 24 },
  heroTitle:           { fontSize: isWide ? 56 : 40, fontWeight: '900', color: '#FFF', textAlign: 'center', lineHeight: isWide ? 64 : 48, marginBottom: 16 },
  heroSubtitle:        { fontSize: 16, color: '#888', textAlign: 'center', lineHeight: 24, marginBottom: 32 },
  heroBtns:            { flexDirection: 'row', gap: 12, marginBottom: 48 },
  heroBtnPrimary:      { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#E63946', paddingHorizontal: 28, paddingVertical: 16, borderRadius: 12 },
  heroBtnPrimaryText:  { color: '#FFF', fontWeight: '900', fontSize: 16 },
  heroBtnSecondary:    { paddingHorizontal: 28, paddingVertical: 16, borderRadius: 12, borderWidth: 1, borderColor: '#333' },
  heroBtnSecondaryText:{ color: '#AAA', fontSize: 16 },
  heroStats:           { flexDirection: 'row', alignItems: 'center', gap: 0 },
  heroStat:            { alignItems: 'center', paddingHorizontal: 24 },
  heroStatNum:         { fontSize: 28, fontWeight: '900', color: '#E63946' },
  heroStatLabel:       { fontSize: 12, color: '#666', marginTop: 4 },
  heroStatDivider:     { width: 1, height: 40, backgroundColor: '#222' },
  // SECTIONS
  section:             { paddingHorizontal: 24, paddingVertical: 60 },
  sectionTag:          { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 3, marginBottom: 12, textAlign: 'center' },
  sectionTitle:        { fontSize: isWide ? 36 : 28, fontWeight: '900', color: '#FFF', textAlign: 'center', marginBottom: 40, lineHeight: isWide ? 44 : 36 },
  // FEATURES
  featuresGrid:        { flexDirection: 'row', flexWrap: 'wrap', gap: 16, justifyContent: 'center' },
  featureCard:         { backgroundColor: '#181818', borderRadius: 16, padding: 24, width: '100%', maxWidth: 340 },
  featureCardWide:     { width: '30%' },
  featureIcon:         { width: 56, height: 56, borderRadius: 16, justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  featureTitle:        { color: '#FFF', fontWeight: '800', fontSize: 16, marginBottom: 8 },
  featureDesc:         { color: '#666', fontSize: 14, lineHeight: 20 },
  // STEPS
  steps:               { gap: 16, maxWidth: 600, alignSelf: 'center', width: '100%' },
  stepCard:            { flexDirection: 'row', alignItems: 'center', backgroundColor: '#181818', borderRadius: 16, padding: 20, gap: 16 },
  stepNum:             { width: 48, height: 48, borderRadius: 24, backgroundColor: '#E63946', justifyContent: 'center', alignItems: 'center' },
  stepNumText:         { color: '#FFF', fontWeight: '900', fontSize: 20 },
  stepTitle:           { color: '#FFF', fontWeight: '700', fontSize: 16, marginBottom: 4 },
  stepDesc:            { color: '#666', fontSize: 13 },
  // SPONSORS
  sponsorSubtitle:     { color: '#666', fontSize: 15, textAlign: 'center', marginBottom: 32, maxWidth: 500, alignSelf: 'center' },
  sponsorCards:        { flexDirection: 'row', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 32 },
  sponsorCard:         { borderWidth: 2, borderRadius: 16, padding: 24, minWidth: 140, alignItems: 'center' },
  sponsorTier:         { fontWeight: '900', fontSize: 18, letterSpacing: 2, marginBottom: 8 },
  sponsorDesc:         { color: '#888', fontSize: 13, textAlign: 'center' },
  sponsorBtn:          { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#25D366', paddingHorizontal: 28, paddingVertical: 16, borderRadius: 12, alignSelf: 'center' },
  sponsorBtnText:      { color: '#FFF', fontWeight: '700', fontSize: 16 },
  // CTA
  ctaBtn:              { backgroundColor: '#FFF', paddingHorizontal: 32, paddingVertical: 18, borderRadius: 12, marginTop: 24 },
  ctaBtnText:          { color: '#E63946', fontWeight: '900', fontSize: 16 },
  // FOOTER
  footer:              { alignItems: 'center', paddingVertical: 48, borderTopWidth: 1, borderTopColor: '#1a1a1a' },
  footerLogo:          { width: 60, height: 60, marginBottom: 8 },
  footerBrand:         { color: '#FFF', fontWeight: '900', fontSize: 18, letterSpacing: 1 },
  footerSub:           { color: '#555', fontSize: 14, marginTop: 4, marginBottom: 16 },
  footerContact:       { color: '#E63946', fontSize: 13, marginBottom: 8 },
  footerCopy:          { color: '#333', fontSize: 12 },
});
