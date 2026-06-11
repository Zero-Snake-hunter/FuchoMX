import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Image, Linking, useWindowDimensions, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const PRIMARY_FEATURES = [
  { icon: 'football', title: 'FuchoQuiniela', desc: 'Predice los resultados de cada jornada y compite con tus cuates en tu liga privada. Puntos reales, rivalidad real.', color: '#E63946' },
  { icon: 'shirt', title: 'FuchoOnce', desc: 'Elige 11 jugadores reales de Liga MX. Cada gol, asistencia y actuación suma puntos a tu favor.', color: '#1D88E5' },
];

const SECONDARY_FEATURES = [
  { icon: 'trophy', title: 'Ligas Privadas', desc: 'Crea tu liga con código único. Solo entran tus cuates.', color: '#FFD700' },
  { icon: 'ribbon', title: 'Logros y Rachas', desc: '20 logros desbloqueables. Cada racha de aciertos tiene su recompensa.', color: '#2A9D8F' },
  { icon: 'bar-chart', title: 'Rankings en Vivo', desc: 'Posiciones actualizadas al minuto. Sabes exactamente dónde estás.', color: '#FF9800' },
  { icon: 'gift', title: 'Sin costo, sin trampa', desc: 'Gratis hoy, gratis siempre. Sin suscripciones ni pagos ocultos.', color: '#4CAF50' },
];

const SPONSORS = [
  { tier: 'ORO', color: '#FFD700', desc: 'Presencia exclusiva en todo el torneo' },
  { tier: 'PLATA', color: '#AAAAAA', desc: 'Visibilidad por jornada, rotando' },
  { tier: 'BRONCE', color: '#CD7F32', desc: 'Presencia continua en perfiles' },
];

// Imagen: 606x1103 (ratio 0.549 ancho/alto)
const MOCKUP_W = 230;
const MOCKUP_H = Math.round(MOCKUP_W / 0.549);   // 419
const MOCKUP_W_WIDE = 295;
const MOCKUP_H_WIDE = Math.round(MOCKUP_W_WIDE / 0.549); // 537

export default function LandingPage() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isWide = width > 768;
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
        {isWide ? (
          <View style={s.heroRow}>
            {/* Texto izquierda */}
            <View style={s.heroLeft}>
              <View style={s.heroPill}>
                <Text style={s.heroPillText}>LIGA MX · GRATIS</Text>
              </View>
              <Text style={s.heroTitleWide}>La quiniela{'\n'}de tus cuates</Text>
              <Text style={[s.heroSubtitle, { textAlign: 'left', marginBottom: 40 }]}>
                Predice resultados de Liga MX, arma tu once ideal y compite toda la temporada en tu liga privada.
              </Text>
              <View style={s.heroBtns}>
                <TouchableOpacity style={s.heroBtnPrimary} onPress={() => router.push('/(auth)/register')}>
                  <Ionicons name="rocket" size={18} color="#FFF" />
                  <Text style={s.heroBtnPrimaryText}>Jugar gratis</Text>
                </TouchableOpacity>
                <TouchableOpacity style={s.heroBtnSecondary} onPress={() => router.push('/(auth)/login')}>
                  <Text style={s.heroBtnSecondaryText}>Ya tengo cuenta</Text>
                </TouchableOpacity>
              </View>
              <Text style={[s.heroTagline, { textAlign: 'left' }]}>
                Sin tarjeta · Sin suscripción · Tu liga en 2 minutos
              </Text>
            </View>
            {/* Mockup derecha */}
            <View style={s.heroRight}>
              <View style={s.heroGlowWide} />
              <Image
                source={require('../../assets/images/mockup-app.png')}
                style={s.heroImgWide}
                resizeMode="contain"
              />
            </View>
          </View>
        ) : (
          <>
            <View style={s.heroPill}>
              <Text style={s.heroPillText}>LIGA MX · GRATIS</Text>
            </View>
            <Text style={s.heroTitle}>La quiniela de{'\n'}tus cuates</Text>
            <Text style={s.heroSubtitle}>
              Predice resultados, arma tu once{'\n'}y compite con tus cuates.
            </Text>
            <View style={s.heroMockupWrap}>
              <View style={s.heroGlow} />
              <Image
                source={require('../../assets/images/mockup-app.png')}
                style={s.heroImg}
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
            <Text style={s.heroTagline}>Sin tarjeta · Sin suscripción · Tu liga en 2 minutos</Text>
          </>
        )}
      </View>

      {/* FEATURES */}
      <View style={s.section}>
        <Text style={[s.sectionTitle, wideSectionTitle]}>Quiniela y fantasy.{'\n'}Un solo lugar.</Text>
        {PRIMARY_FEATURES.map((f, i) => (
          <View key={i} style={s.featurePrimary}>
            <View style={[s.featureIcon, { backgroundColor: f.color + '28', borderColor: f.color + '44' }]}>
              <Ionicons name={f.icon as any} size={28} color={f.color} />
            </View>
            <View style={s.featurePrimaryContent}>
              <Text style={s.featurePrimaryTitle}>{f.title}</Text>
              <Text style={s.featurePrimaryDesc}>{f.desc}</Text>
            </View>
          </View>
        ))}
        <View style={[s.featuresSecondary, isWide && { flexDirection: 'row', flexWrap: 'wrap', gap: 16 }]}>
          {SECONDARY_FEATURES.map((f, i) => (
            <View key={i} style={[s.featureSecondary, isWide && { width: '47%' }]}>
              <View style={[s.featureIconSm, { backgroundColor: f.color + '20' }]}>
                <Ionicons name={f.icon as any} size={18} color={f.color} />
              </View>
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
            { n: '1', t: 'Crea tu cuenta gratis', d: 'Regístrate en segundos, sin tarjeta ni correo de activación.' },
            { n: '2', t: 'Crea o únete a una liga', d: 'Comparte el código con tus cuates. En un minuto ya están dentro.' },
            { n: '3', t: 'Predice y compite', d: 'Cada jornada de Liga MX abre tu ventana de predicciones. Gana puntos, sube en el ranking.' },
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
        <Text style={s.sponsorSubtitle}>FuchoMX conecta marcas locales con fanáticos del fut. Gratis para usuarios, monetizado por sponsors comprometidos.</Text>
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
        <Text style={[s.sectionTitle, wideSectionTitle, { color: '#FFF', textAlign: 'center' }]}>¿Listo para demostrar{'\n'}que sabes de fut?</Text>
        <Text style={[s.heroSubtitle, { color: 'rgba(255,255,255,0.85)', textAlign: 'center', marginBottom: 0 }]}>
          Únete gratis. Tu primera liga en 2 minutos.
        </Text>
        <TouchableOpacity style={s.ctaBtn} onPress={() => router.push('/(auth)/register')}>
          <Text style={s.ctaBtnText}>Crear mi cuenta gratis</Text>
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

const WRAP_H      = MOCKUP_H + 32;          // 451
const GLOW_R      = 200;
const GLOW_TOP    = (WRAP_H - GLOW_R) / 2; // 125.5
const RIGHT_H     = MOCKUP_H_WIDE + 40;    // 577
const GLOW_R_WIDE = 280;
const GLOW_TOP_W  = (RIGHT_H - GLOW_R_WIDE) / 2; // 148.5

const s = StyleSheet.create({
  container:              { flex: 1, backgroundColor: '#090909' },

  // NAV
  nav:                    { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 24, paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: '#1a1a1a' },
  navLogo:                { width: 36, height: 36, marginRight: 8 },
  navBrand:               { color: '#FFF', fontWeight: '900', fontSize: 16, letterSpacing: 1, marginRight: 16 },
  navBtn:                 { paddingHorizontal: 16, paddingVertical: 12, marginRight: 8, minHeight: 44, justifyContent: 'center' },
  navBtnText:             { color: '#AAAAAA', fontSize: 14 },
  navBtnPrimary:          { backgroundColor: '#C02030', paddingHorizontal: 16, paddingVertical: 12, borderRadius: 8, minHeight: 44, justifyContent: 'center' },
  navBtnPrimaryText:      { color: '#FFF', fontWeight: '700', fontSize: 14 },

  // HERO base
  hero:                   { alignItems: 'center', paddingHorizontal: 24, paddingTop: 72, paddingBottom: 72 },
  heroPill:               { borderWidth: 1, borderColor: '#E6394666', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 5, marginBottom: 24 },
  heroPillText:           { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 2.5 },
  heroTitle:              { fontSize: 40, fontWeight: '900', color: '#FFF', textAlign: 'center', lineHeight: 48, marginBottom: 16 },
  heroTitleWide:          { fontSize: 60, fontWeight: '900', color: '#FFF', lineHeight: 68, marginBottom: 24 },
  heroSubtitle:           { fontSize: 16, color: '#999', textAlign: 'center', lineHeight: 26, marginBottom: 12 },
  heroTagline:            { fontSize: 13, color: '#666', textAlign: 'center', letterSpacing: 0.5, marginTop: 20 },
  heroBtns:               { flexDirection: 'row', gap: 12 },
  heroBtnPrimary:         { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#E63946', paddingHorizontal: 32, paddingVertical: 18, borderRadius: 12 },
  heroBtnPrimaryText:     { color: '#FFF', fontWeight: '900', fontSize: 16 },
  heroBtnSecondary:       { paddingHorizontal: 24, paddingVertical: 18, borderRadius: 12, borderWidth: 1, borderColor: '#2a2a2a', justifyContent: 'center' },
  heroBtnSecondaryText:   { color: '#888', fontSize: 15 },

  // Hero desktop (2 cols)
  heroRow:                { flexDirection: 'row', alignItems: 'center', width: '100%', maxWidth: 1100, gap: 64 },
  heroLeft:               { flex: 1 },
  heroRight:              { width: 340, height: RIGHT_H, alignItems: 'center', justifyContent: 'center' },

  // Glow desktop
  heroGlowWide:           {
    position: 'absolute',
    alignSelf: 'center',
    top: GLOW_TOP_W,
    width: GLOW_R_WIDE,
    height: GLOW_R_WIDE,
    borderRadius: GLOW_R_WIDE / 2,
    backgroundColor: '#E63946',
    opacity: 0.20,
    ...Platform.select({ web: { filter: 'blur(90px)' } as any, default: {} }),
  },

  // Mockup desktop
  heroImgWide:            { width: MOCKUP_W_WIDE, height: MOCKUP_H_WIDE },

  // Hero mobile mockup
  heroMockupWrap:         { alignItems: 'center', justifyContent: 'center', width: '100%', height: WRAP_H, marginTop: 8, marginBottom: 40 },
  heroGlow:               {
    position: 'absolute',
    alignSelf: 'center',
    top: GLOW_TOP,
    width: GLOW_R,
    height: GLOW_R,
    borderRadius: GLOW_R / 2,
    backgroundColor: '#E63946',
    opacity: 0.22,
    ...Platform.select({ web: { filter: 'blur(70px)' } as any, default: {} }),
  },
  heroImg:                { width: MOCKUP_W, height: MOCKUP_H },

  // SECTIONS
  section:                { paddingHorizontal: 24, paddingVertical: 64 },
  sectionTag:             { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 3, marginBottom: 12, textAlign: 'center' },
  sectionTitle:           { fontSize: 28, fontWeight: '900', color: '#FFF', textAlign: 'center', marginBottom: 40, lineHeight: 36 },

  // FEATURES primary
  featurePrimary:         { flexDirection: 'row', marginBottom: 36, alignItems: 'flex-start' },
  featureIcon:            { width: 64, height: 64, borderRadius: 16, borderWidth: 1, justifyContent: 'center', alignItems: 'center', marginRight: 20, flexShrink: 0 },
  featurePrimaryContent:  { flex: 1, paddingTop: 4 },
  featurePrimaryTitle:    { color: '#FFF', fontWeight: '900', fontSize: 20, marginBottom: 6 },
  featurePrimaryDesc:     { color: '#999', fontSize: 14, lineHeight: 22 },

  // FEATURES secondary
  featuresSecondary:      { marginTop: 8, gap: 20 },
  featureSecondary:       { flexDirection: 'row', gap: 14, alignItems: 'flex-start' },
  featureIconSm:          { width: 36, height: 36, borderRadius: 10, justifyContent: 'center', alignItems: 'center', flexShrink: 0, marginTop: 1 },
  featureSecondaryTitle:  { color: '#FFF', fontWeight: '700', fontSize: 14, marginBottom: 3 },
  featureSecondaryDesc:   { color: '#888', fontSize: 13, lineHeight: 19 },

  // STEPS
  steps:                  { gap: 16, maxWidth: 600, alignSelf: 'center', width: '100%' },
  stepCard:               { flexDirection: 'row', alignItems: 'flex-start', backgroundColor: '#141414', borderRadius: 16, padding: 20, gap: 16 },
  stepNum:                { width: 48, height: 48, borderRadius: 24, backgroundColor: '#E63946', justifyContent: 'center', alignItems: 'center', flexShrink: 0 },
  stepNumText:            { color: '#FFF', fontWeight: '900', fontSize: 20 },
  stepTitle:              { color: '#FFF', fontWeight: '700', fontSize: 16, marginBottom: 4 },
  stepDesc:               { color: '#AAA', fontSize: 13, lineHeight: 19 },

  // SPONSORS
  sponsorSubtitle:        { color: '#888', fontSize: 15, textAlign: 'center', marginBottom: 32, maxWidth: 500, alignSelf: 'center', lineHeight: 24 },
  sponsorCards:           { flexDirection: 'row', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 32 },
  sponsorCard:            { borderWidth: 1, borderRadius: 12, padding: 24, minWidth: 130, alignItems: 'center' },
  sponsorTier:            { fontWeight: '900', fontSize: 16, letterSpacing: 2, marginBottom: 8 },
  sponsorDesc:            { color: '#888', fontSize: 12, textAlign: 'center', lineHeight: 18 },
  sponsorBtn:             { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#25D366', paddingHorizontal: 28, paddingVertical: 16, borderRadius: 12, alignSelf: 'center' },
  sponsorBtnText:         { color: '#FFF', fontWeight: '700', fontSize: 16 },

  // CTA final
  ctaBtn:                 { backgroundColor: '#FFF', paddingHorizontal: 36, paddingVertical: 18, borderRadius: 12, marginTop: 28 },
  ctaBtnText:             { color: '#C02030', fontWeight: '900', fontSize: 16 },

  // FOOTER
  footer:                 { alignItems: 'center', paddingVertical: 48, borderTopWidth: 1, borderTopColor: '#1a1a1a' },
  footerLogo:             { width: 60, height: 60, marginBottom: 8 },
  footerBrand:            { color: '#FFF', fontWeight: '900', fontSize: 18, letterSpacing: 1 },
  footerSub:              { color: '#888', fontSize: 14, marginTop: 4, marginBottom: 16 },
  footerContact:          { color: '#E63946', fontSize: 13, marginBottom: 8 },
  footerCopy:             { color: '#555', fontSize: 12 },
});
