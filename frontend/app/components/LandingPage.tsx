import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Image, Linking, useWindowDimensions, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const PRIMARY_FEATURES = [
  { icon: 'football', title: 'FuchoQuiniela', desc: 'Predice los resultados de cada jornada de Liga MX y compite con tus cuates en tu liga privada.', color: '#E63946' },
  { icon: 'shirt', title: 'FuchoOnce', desc: 'Arma tu once ideal con jugadores reales de Liga MX y gana puntos según sus estadísticas reales.', color: '#1D88E5' },
];

const SECONDARY_FEATURES = [
  { icon: 'trophy', title: 'Ligas Privadas', desc: 'Crea tu liga, invita a tus amigos con un código y compite toda la temporada.', color: '#FFD700' },
  { icon: 'ribbon', title: 'Logros y Rachas', desc: '20 logros desbloqueables, rachas de aciertos y rankings en tiempo real.', color: '#2A9D8F' },
  { icon: 'bar-chart', title: 'Rankings en Vivo', desc: 'Tabla de posiciones actualizada al terminar cada partido.', color: '#FF9800' },
  { icon: 'gift', title: '100% Gratis', desc: 'Sin suscripciones, sin pagos ocultos. Completamente gratis.', color: '#4CAF50' },
];

const SPONSORS = [
  { tier: 'ORO', color: '#FFD700', desc: 'Presencia exclusiva en todo el torneo' },
  { tier: 'PLATA', color: '#AAAAAA', desc: 'Visibilidad por jornada, rotando' },
  { tier: 'BRONCE', color: '#CD7F32', desc: 'Presencia continua en perfiles' },
];

export default function LandingPage() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isWide = width > 768;
  const wideHeroTitle    = isWide ? { fontSize: 56, lineHeight: 64 } : undefined;
  const wideSectionTitle = isWide ? { fontSize: 36, lineHeight: 44 } : undefined;

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
        <Text style={[s.heroTitle, wideHeroTitle]}>La quiniela de{'\n'}tus cuates</Text>
        <Text style={s.heroSubtitle}>Predice. Arma tu once ideal. Gana.{'\n'}Tu fut, con tus cuates.</Text>
        <View style={[s.heroMockupWrap, isWide && s.heroMockupWrapWide]}>
          <View style={[s.heroMockupGlow, isWide && s.heroMockupGlowWide]} />
          <Image
            source={require('../../assets/images/mockup-app.png')}
            style={[s.heroMockupImg, isWide && s.heroMockupImgWide]}
            resizeMode="contain"
          />
        </View>
        <View style={s.heroBtns}>
          <TouchableOpacity style={s.heroBtnPrimary} onPress={() => router.push('/(auth)/register')}>
            <Ionicons name="rocket" size={18} color="#FFF" />
            <Text style={s.heroBtnPrimaryText}>Jugar gratis</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.heroBtnSecondary} onPress={() => router.push('/(auth)/login')}>
            <Text style={s.heroBtnSecondaryText}>Ya tengo cuenta</Text>
          </TouchableOpacity>
        </View>
        <Text style={s.heroTagline}>Liga MX · Cada jornada · Sin costo.</Text>
      </View>


      {/* FEATURES */}
      <View style={s.section}>
        <Text style={[s.sectionTitle, wideSectionTitle]}>Quiniela y fantasy.{'\n'}Un solo lugar.</Text>
        {PRIMARY_FEATURES.map((f, i) => (
          <View key={i} style={s.featurePrimary}>
            <View style={[s.featurePrimaryAccent, { backgroundColor: f.color }]} />
            <View style={s.featurePrimaryContent}>
              <View style={s.featurePrimaryHeader}>
                <Ionicons name={f.icon as any} size={22} color={f.color} />
                <Text style={s.featurePrimaryTitle}>{f.title}</Text>
              </View>
              <Text style={s.featurePrimaryDesc}>{f.desc}</Text>
            </View>
          </View>
        ))}
        <View style={[s.featuresSecondary, isWide && { flexDirection: 'row', flexWrap: 'wrap', gap: 16 }]}>
          {SECONDARY_FEATURES.map((f, i) => (
            <View key={i} style={[s.featureSecondary, isWide && { width: '47%' }]}>
              <Ionicons name={f.icon as any} size={18} color={f.color} style={s.featureSecondaryIcon} />
              <View style={{ flex: 1 }}>
                <Text style={s.featureSecondaryTitle}>{f.title}</Text>
                <Text style={s.featureSecondaryDesc}>{f.desc}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {/* COMO FUNCIONA */}
      <View style={[s.section, { backgroundColor: '#111' }]}>
        <Text style={[s.sectionTitle, wideSectionTitle]}>3 pasos y ya{'\n'}estás jugando</Text>
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
        <Text style={[s.sectionTitle, wideSectionTitle]}>Llega a los aficionados{'\n'}de Liga MX en Aguascalientes</Text>
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
      <View style={[s.section, { backgroundColor: '#C02030', alignItems: 'center' }]}>
        <Text style={[s.sectionTitle, wideSectionTitle, { color: '#FFF', textAlign: 'center' }]}>¿Listo para jugar?</Text>
        <Text style={[s.heroSubtitle, { color: '#FFF', textAlign: 'center' }]}>Únete gratis y empieza a competir esta jornada.</Text>
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
  navBtn:              { paddingHorizontal: 16, paddingVertical: 12, marginRight: 8, minHeight: 44, justifyContent: 'center' },
  navBtnText:          { color: '#AAAAAA', fontSize: 14 },
  navBtnPrimary:       { backgroundColor: '#C02030', paddingHorizontal: 16, paddingVertical: 12, borderRadius: 8, minHeight: 44, justifyContent: 'center' },
  navBtnPrimaryText:   { color: '#FFF', fontWeight: '700', fontSize: 14 },
  // HERO
  hero:                { alignItems: 'center', paddingHorizontal: 24, paddingTop: 60, paddingBottom: 60 },
  heroPill:            { borderWidth: 1, borderColor: '#E6394655', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 5, marginBottom: 24 },
  heroPillText:        { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 2 },
  heroLogo:            { width: 140, height: 140, marginBottom: 24 },
  heroTitle:           { fontSize: 40, fontWeight: '900', color: '#FFF', textAlign: 'center', lineHeight: 48, marginBottom: 16 },
  heroSubtitle:        { fontSize: 16, color: '#888', textAlign: 'center', lineHeight: 24, marginBottom: 12 },
  heroMockupWrap:      { alignItems: 'center', justifyContent: 'center', width: '100%', height: 390, marginTop: 8, marginBottom: 40 },
  heroMockupWrapWide:  { height: 510, marginBottom: 48 },
  heroMockupGlow:      {
    position: 'absolute',
    alignSelf: 'center',
    top: (390 - 230) / 2,
    width: 230,
    height: 230,
    borderRadius: 115,
    backgroundColor: '#E63946',
    opacity: 0.22,
    ...Platform.select({ web: { filter: 'blur(76px)' } as any, default: {} }),
  },
  heroMockupGlowWide:  {
    top: (510 - 320) / 2,
    width: 320,
    height: 320,
    borderRadius: 160,
    ...Platform.select({ web: { filter: 'blur(100px)' } as any, default: {} }),
  },
  heroMockupImg:       { width: 280, height: 356 },
  heroMockupImgWide:   { width: 370, height: 470 },
  heroBtns:            { flexDirection: 'row', gap: 12, marginBottom: 32 },
  heroBtnPrimary:      { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#C02030', paddingHorizontal: 28, paddingVertical: 16, borderRadius: 12 },
  heroBtnPrimaryText:  { color: '#FFF', fontWeight: '900', fontSize: 16 },
  heroBtnSecondary:    { paddingHorizontal: 28, paddingVertical: 16, borderRadius: 12, borderWidth: 1, borderColor: '#333' },
  heroBtnSecondaryText:{ color: '#AAA', fontSize: 16 },
  heroTagline:         { fontSize: 13, color: '#888', textAlign: 'center', letterSpacing: 0.5 },
  // SECTIONS
  section:             { paddingHorizontal: 24, paddingVertical: 60 },
  sectionTag:          { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 3, marginBottom: 12, textAlign: 'center' },
  sectionTitle:        { fontSize: 28, fontWeight: '900', color: '#FFF', textAlign: 'center', marginBottom: 40, lineHeight: 36 },
  // FEATURES
  featurePrimary:         { flexDirection: 'row', marginBottom: 28, gap: 0 },
  featurePrimaryAccent:   { width: 3, borderRadius: 2, marginRight: 20 },
  featurePrimaryContent:  { flex: 1 },
  featurePrimaryHeader:   { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 8 },
  featurePrimaryTitle:    { color: '#FFF', fontWeight: '900', fontSize: 20 },
  featurePrimaryDesc:     { color: '#AAA', fontSize: 14, lineHeight: 22 },
  featuresSecondary:      { marginTop: 8, gap: 16 },
  featureSecondary:       { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  featureSecondaryIcon:   { marginTop: 2 },
  featureSecondaryTitle:  { color: '#FFF', fontWeight: '700', fontSize: 14, marginBottom: 2 },
  featureSecondaryDesc:   { color: '#888', fontSize: 13, lineHeight: 18 },
  // STEPS
  steps:               { gap: 16, maxWidth: 600, alignSelf: 'center', width: '100%' },
  stepCard:            { flexDirection: 'row', alignItems: 'center', backgroundColor: '#181818', borderRadius: 16, padding: 20, gap: 16 },
  stepNum:             { width: 48, height: 48, borderRadius: 24, backgroundColor: '#E63946', justifyContent: 'center', alignItems: 'center' },
  stepNumText:         { color: '#FFF', fontWeight: '900', fontSize: 20 },
  stepTitle:           { color: '#FFF', fontWeight: '700', fontSize: 16, marginBottom: 4 },
  stepDesc:            { color: '#AAA', fontSize: 13 },
  // SPONSORS
  sponsorSubtitle:     { color: '#888', fontSize: 15, textAlign: 'center', marginBottom: 32, maxWidth: 500, alignSelf: 'center' },
  sponsorCards:        { flexDirection: 'row', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 32 },
  sponsorCard:         { borderWidth: 2, borderRadius: 16, padding: 24, minWidth: 140, alignItems: 'center' },
  sponsorTier:         { fontWeight: '900', fontSize: 18, letterSpacing: 2, marginBottom: 8 },
  sponsorDesc:         { color: '#888', fontSize: 13, textAlign: 'center' },
  sponsorBtn:          { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#25D366', paddingHorizontal: 28, paddingVertical: 16, borderRadius: 12, alignSelf: 'center' },
  sponsorBtnText:      { color: '#FFF', fontWeight: '700', fontSize: 16 },
  // CTA
  ctaBtn:              { backgroundColor: '#FFF', paddingHorizontal: 32, paddingVertical: 18, borderRadius: 12, marginTop: 24 },
  ctaBtnText:          { color: '#C02030', fontWeight: '900', fontSize: 16 },
  // FOOTER
  footer:              { alignItems: 'center', paddingVertical: 48, borderTopWidth: 1, borderTopColor: '#1a1a1a' },
  footerLogo:          { width: 60, height: 60, marginBottom: 8 },
  footerBrand:         { color: '#FFF', fontWeight: '900', fontSize: 18, letterSpacing: 1 },
  footerSub:           { color: '#888', fontSize: 14, marginTop: 4, marginBottom: 16 },
  footerContact:       { color: '#E63946', fontSize: 13, marginBottom: 8 },
  footerCopy:          { color: '#888', fontSize: 12 },
});
