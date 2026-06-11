import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  Image, Linking, useWindowDimensions, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

const PRIMARY_FEATURES = [
  {
    icon: 'football',
    title: 'FuchoQuiniela',
    desc: 'Predice los 10 partidos de cada jornada antes de que arranquen. Cada acierto sube tu posición en el ranking de tu liga.',
    color: '#E63946',
  },
  {
    icon: 'shirt',
    title: 'FuchoOnce',
    desc: 'Selecciona 11 jugadores reales de Liga MX cada semana. Sus goles, asistencias y actuaciones se convierten en tus puntos.',
    color: '#1D88E5',
  },
];

const SECONDARY_FEATURES = [
  { icon: 'people', title: 'Ligas Privadas', desc: 'Crea tu liga con código único. Solo entran tus cuates, nadie más.', color: '#FFD700' },
  { icon: 'trophy', title: 'Logros y Rachas', desc: '20 logros desbloqueables. Cada racha de aciertos tiene su recompensa.', color: '#2A9D8F' },
  { icon: 'bar-chart', title: 'Rankings en Vivo', desc: 'Posiciones actualizadas al minuto. Sabes exactamente dónde estás.', color: '#FF9800' },
  { icon: 'gift', title: 'Sin costo, sin trampa', desc: 'Gratis hoy, gratis siempre. Sin suscripciones ni cobros ocultos.', color: '#4CAF50' },
];

const SPONSORS = [
  { tier: 'ORO', color: '#FFD700', desc: 'Presencia exclusiva en todo el torneo' },
  { tier: 'PLATA', color: '#AAAAAA', desc: 'Visibilidad por jornada, rotando' },
  { tier: 'BRONCE', color: '#CD7F32', desc: 'Presencia continua en perfiles' },
];

// PNG: 606×1103 → ratio ancho/alto = 0.549
const MOCKUP_W      = 230;
const MOCKUP_H      = Math.round(MOCKUP_W / 0.549);       // 419
const MOCKUP_W_WIDE = 295;
const MOCKUP_H_WIDE = Math.round(MOCKUP_W_WIDE / 0.549);  // 537

const WRAP_H      = MOCKUP_H + 40;
const GLOW_R      = 210;
const GLOW_TOP    = (WRAP_H - GLOW_R) / 2;
const RIGHT_H     = MOCKUP_H_WIDE + 48;
const GLOW_R_WIDE = 290;
const GLOW_TOP_W  = (RIGHT_H - GLOW_R_WIDE) / 2;

export default function LandingPage() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isWide = width > 768;

  return (
    <ScrollView style={s.container} contentContainerStyle={s.contentContainer} showsVerticalScrollIndicator={false}>

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

      {/* ─── HERO ─────────────────────────────────────────────────────────── */}
      <View style={s.hero}>
        {isWide ? (
          /* Desktop: 2 columnas */
          <View style={s.heroRow}>
            <View style={s.heroLeft}>
              <View style={s.heroPill}>
                <Text style={s.heroPillText}>LIGA MX · GRATIS</Text>
              </View>
              <Text style={s.heroTitleWide}>La quiniela{'\n'}de tus cuates</Text>
              <Text style={s.heroSubtitleWide}>
                Predice resultados, arma tu once de 11 jugadores reales y compite jornada a jornada en tu liga privada.
              </Text>
              <View style={s.heroBtns}>
                <TouchableOpacity style={s.heroBtnPrimary} onPress={() => router.push('/(auth)/register')}>
                  <Ionicons name="rocket" size={18} color="#FFF" />
                  <Text style={s.heroBtnPrimaryText}>Crear mi quiniela gratis</Text>
                </TouchableOpacity>
                <TouchableOpacity style={s.heroBtnSecondary} onPress={() => router.push('/(auth)/login')}>
                  <Text style={s.heroBtnSecondaryText}>Ya tengo cuenta</Text>
                </TouchableOpacity>
              </View>
              <Text style={s.heroTaglineWide}>Sin tarjeta · Tu liga lista en 2 minutos</Text>
            </View>

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
          /* Mobile: apilado */
          <>
            <View style={s.heroPill}>
              <Text style={s.heroPillText}>LIGA MX · GRATIS</Text>
            </View>
            <Text style={s.heroTitle}>La quiniela de{'\n'}tus cuates</Text>
            <Text style={s.heroSubtitle}>
              Predice resultados, arma tu once{'\n'}y sube en el ranking con tus cuates.
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
            <Text style={s.heroTagline}>Sin tarjeta · Tu liga lista en 2 minutos</Text>
          </>
        )}
      </View>

      {/* ─── FEATURES ─────────────────────────────────────────────────────── */}
      <View style={s.section}>
        <Text style={[s.sectionTitle, isWide && s.sectionTitleWide]}>
          Quiniela y fantasy.{'\n'}Un solo lugar.
        </Text>

        {PRIMARY_FEATURES.map((f, i) => (
          <View key={i} style={s.featurePrimary}>
            <View style={[s.featureIcon, { backgroundColor: f.color + '22', borderColor: f.color + '55' }]}>
              <Ionicons name={f.icon as any} size={30} color={f.color} />
            </View>
            <View style={s.featurePrimaryContent}>
              <Text style={s.featurePrimaryTitle}>{f.title}</Text>
              <Text style={s.featurePrimaryDesc}>{f.desc}</Text>
            </View>
          </View>
        ))}

        <View style={[s.featuresGrid, isWide && s.featuresGridWide]}>
          {SECONDARY_FEATURES.map((f, i) => (
            <View key={i} style={[s.featureSecondary, isWide && s.featureSecondaryWide]}>
              <View style={[s.featureIconSm, { backgroundColor: f.color + '30', borderColor: f.color + '60', borderWidth: 1 }]}>
                <Ionicons name={f.icon as any} size={20} color={f.color} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={s.featureSecondaryTitle}>{f.title}</Text>
                <Text style={s.featureSecondaryDesc}>{f.desc}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {/* ─── CÓMO FUNCIONA ────────────────────────────────────────────────── */}
      <View style={[s.section, s.sectionDark]}>
        <Text style={[s.sectionTitle, isWide && s.sectionTitleWide]}>
          3 pasos y ya{'\n'}estás jugando
        </Text>
        <View style={[s.steps, isWide && s.stepsWide]}>
          {[
            {
              n: '1',
              t: 'Crea tu cuenta gratis',
              d: 'Regístrate con tu correo en 30 segundos. Sin tarjeta, sin número de teléfono.',
            },
            {
              n: '2',
              t: 'Crea tu liga y comparte el código',
              d: 'Tus cuates entran directo con el código. En un minuto ya están todos adentro.',
            },
            {
              n: '3',
              t: 'Predice cada jornada y compite',
              d: 'Antes de cada fecha, predice los 10 partidos. Al final sabes quién de tu grupo sabe más de fut.',
            },
          ].map((step, i) => (
            <View key={i} style={s.stepCard}>
              <View style={s.stepNum}>
                <Text style={s.stepNumText}>{step.n}</Text>
              </View>
              <View style={{ flex: 1, minWidth: 0 }}>
                <Text style={s.stepTitle}>{step.t}</Text>
                <Text style={s.stepDesc}>{step.d}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {/* ─── SPONSORS ─────────────────────────────────────────────────────── */}
      <View style={s.section}>
        <Text style={s.sectionTag}>PATROCINADORES</Text>
        <Text style={[s.sectionTitle, isWide && s.sectionTitleWide]}>
          Llega directo a los fanáticos{'\n'}del fut en Aguascalientes
        </Text>
        <Text style={s.sponsorSubtitle}>
          FuchoMX conecta marcas locales con aficionados de Liga MX. Gratis para los jugadores, sostenido por sponsors que quieren aparecer donde sí se ven.
        </Text>
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

      {/* ─── CTA FINAL ────────────────────────────────────────────────────── */}
      <View style={[s.section, s.ctaSection]}>
        <Text style={[s.sectionTitle, isWide && s.sectionTitleWide, s.ctaTitle]}>
          ¿Quién de tu grupo{'\n'}sabe más de fut?
        </Text>
        <Text style={s.ctaSubtitle}>
          Crea tu quiniela ahora y demuéstralo esta jornada.
        </Text>
        <TouchableOpacity style={s.ctaBtn} onPress={() => router.push('/(auth)/register')}>
          <Text style={s.ctaBtnText}>Crear mi quiniela gratis</Text>
        </TouchableOpacity>
        <Text style={s.ctaMicro}>Sin tarjeta · Sin suscripción · 100% gratis</Text>
      </View>

      {/* ─── FOOTER ───────────────────────────────────────────────────────── */}
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
  container: {
    flex: 1,
    backgroundColor: '#090909',
  },
  // FIX LAYOUT: contentContainerStyle en lugar de style para el ScrollView
  // garantiza que los hijos se expanden al ancho completo en web
  contentContainer: {
    flexGrow: 1,
    width: '100%',
  },

  // ─── NAV ────────────────────────────────────────────────────────────────
  nav: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1a1a1a',
    width: '100%',
  },
  navLogo:         { width: 36, height: 36, marginRight: 8 },
  navBrand:        { color: '#FFF', fontWeight: '900', fontSize: 16, letterSpacing: 1, marginRight: 16 },
  navBtn:          { paddingHorizontal: 16, paddingVertical: 12, marginRight: 8, minHeight: 44, justifyContent: 'center' },
  navBtnText:      { color: '#AAA', fontSize: 14 },
  navBtnPrimary:   { backgroundColor: '#C02030', paddingHorizontal: 16, paddingVertical: 12, borderRadius: 8, minHeight: 44, justifyContent: 'center' },
  navBtnPrimaryText: { color: '#FFF', fontWeight: '700', fontSize: 14 },

  // ─── HERO ───────────────────────────────────────────────────────────────
  // width: '100%' es crítico: sin esto, alignItems:'center' en un flex:column
  // colapsa el ancho a contenido, y width:'100%' de heroRow referencia ese 0
  hero: {
    width: '100%',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 72,
    paddingBottom: 72,
  },

  // Desktop 2 columnas
  heroRow: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    maxWidth: 1100,
    gap: 64,
  },
  heroLeft: {
    flex: 1,
    minWidth: 0, // evita overflow en flex items en web
  },
  heroRight: {
    width: 340,
    height: RIGHT_H,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },

  // Glow desktop — position:absolute es relativo al heroRight (RN default: position:'relative')
  heroGlowWide: {
    position: 'absolute',
    alignSelf: 'center',
    top: GLOW_TOP_W,
    width: GLOW_R_WIDE,
    height: GLOW_R_WIDE,
    borderRadius: GLOW_R_WIDE / 2,
    backgroundColor: '#E63946',
    opacity: 0.22,
    ...Platform.select({ web: { filter: 'blur(90px)' } as any, default: {} }),
  },
  heroImgWide: { width: MOCKUP_W_WIDE, height: MOCKUP_H_WIDE },

  // Pill
  heroPill: {
    borderWidth: 1,
    borderColor: '#E6394655',
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 5,
    marginBottom: 24,
  },
  heroPillText: { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 2.5 },

  // Títulos
  heroTitle:     { fontSize: 40, fontWeight: '900', color: '#FFF', textAlign: 'center', lineHeight: 48, marginBottom: 16 },
  heroTitleWide: { fontSize: 60, fontWeight: '900', color: '#FFF', lineHeight: 68, marginBottom: 24 },

  // Subtítulos
  heroSubtitle:     { fontSize: 16, color: '#999', textAlign: 'center', lineHeight: 26, marginBottom: 12 },
  heroSubtitleWide: { fontSize: 17, color: '#999', lineHeight: 28, marginBottom: 40 },

  // Taglines
  heroTagline:     { fontSize: 13, color: '#777', textAlign: 'center', letterSpacing: 0.4, marginTop: 20 },
  heroTaglineWide: { fontSize: 13, color: '#777', letterSpacing: 0.4, marginTop: 20 },

  // Botones CTA
  heroBtns: { flexDirection: 'row', gap: 12, flexWrap: 'wrap' },
  heroBtnPrimary: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#E63946',
    paddingHorizontal: 28,
    paddingVertical: 18,
    borderRadius: 12,
  },
  heroBtnPrimaryText:   { color: '#FFF', fontWeight: '900', fontSize: 16 },
  heroBtnSecondary: {
    paddingHorizontal: 24,
    paddingVertical: 18,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#383838',
    backgroundColor: '#111',
    justifyContent: 'center',
  },
  heroBtnSecondaryText: { color: '#AAA', fontSize: 15 },

  // Mobile mockup container
  heroMockupWrap: {
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    height: WRAP_H,
    marginTop: 8,
    marginBottom: 40,
  },
  heroGlow: {
    position: 'absolute',
    alignSelf: 'center',
    top: GLOW_TOP,
    width: GLOW_R,
    height: GLOW_R,
    borderRadius: GLOW_R / 2,
    backgroundColor: '#E63946',
    opacity: 0.24,
    ...Platform.select({ web: { filter: 'blur(70px)' } as any, default: {} }),
  },
  heroImg: { width: MOCKUP_W, height: MOCKUP_H },

  // ─── SECTIONS ───────────────────────────────────────────────────────────
  section: {
    width: '100%',
    paddingHorizontal: 24,
    paddingVertical: 64,
  },
  sectionDark: { backgroundColor: '#111' },
  sectionTag: {
    color: '#E63946',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 3,
    marginBottom: 12,
    textAlign: 'center',
  },
  sectionTitle: {
    fontSize: 28,
    fontWeight: '900',
    color: '#FFF',
    textAlign: 'center',
    marginBottom: 40,
    lineHeight: 36,
  },
  sectionTitleWide: { fontSize: 36, lineHeight: 44 },

  // ─── FEATURES primary ───────────────────────────────────────────────────
  featurePrimary: { flexDirection: 'row', marginBottom: 36, alignItems: 'flex-start' },
  featureIcon: {
    width: 64,
    height: 64,
    borderRadius: 16,
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 20,
    flexShrink: 0,
  },
  featurePrimaryContent: { flex: 1, paddingTop: 6, minWidth: 0 },
  featurePrimaryTitle:   { color: '#FFF', fontWeight: '900', fontSize: 20, marginBottom: 6 },
  featurePrimaryDesc:    { color: '#999', fontSize: 14, lineHeight: 22 },

  // ─── FEATURES secondary ─────────────────────────────────────────────────
  featuresGrid:     { marginTop: 8, gap: 20 },
  featuresGridWide: { flexDirection: 'row', flexWrap: 'wrap', gap: 16 },

  featureSecondary:     { flexDirection: 'row', gap: 14, alignItems: 'flex-start' },
  featureSecondaryWide: { width: '47%' },

  featureIconSm: {
    width: 40,
    height: 40,
    borderRadius: 11,
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
    marginTop: 1,
  },
  featureSecondaryTitle: { color: '#FFF', fontWeight: '700', fontSize: 14, marginBottom: 3 },
  featureSecondaryDesc:  { color: '#888', fontSize: 13, lineHeight: 19 },

  // ─── STEPS ──────────────────────────────────────────────────────────────
  steps:     { gap: 16, maxWidth: 600, alignSelf: 'center', width: '100%' },
  stepsWide: { maxWidth: 700 },
  stepCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#141414',
    borderRadius: 14,
    padding: 20,
    gap: 16,
  },
  stepNum: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#E63946',
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
  },
  stepNumText: { color: '#FFF', fontWeight: '900', fontSize: 20 },
  stepTitle:   { color: '#FFF', fontWeight: '700', fontSize: 16, marginBottom: 4 },
  stepDesc:    { color: '#AAA', fontSize: 13, lineHeight: 19 },

  // ─── SPONSORS ───────────────────────────────────────────────────────────
  sponsorSubtitle: {
    color: '#888',
    fontSize: 15,
    textAlign: 'center',
    marginBottom: 32,
    maxWidth: 520,
    alignSelf: 'center',
    lineHeight: 24,
  },
  sponsorCards: {
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'center',
    flexWrap: 'wrap',
    marginBottom: 32,
  },
  sponsorCard:  { borderWidth: 1, borderRadius: 12, padding: 24, minWidth: 130, alignItems: 'center' },
  sponsorTier:  { fontWeight: '900', fontSize: 16, letterSpacing: 2, marginBottom: 8 },
  sponsorDesc:  { color: '#888', fontSize: 12, textAlign: 'center', lineHeight: 18 },
  sponsorBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#25D366',
    paddingHorizontal: 28,
    paddingVertical: 16,
    borderRadius: 12,
    alignSelf: 'center',
  },
  sponsorBtnText: { color: '#FFF', fontWeight: '700', fontSize: 16 },

  // ─── CTA FINAL ──────────────────────────────────────────────────────────
  ctaSection: { backgroundColor: '#C02030', alignItems: 'center' },
  ctaTitle:   { color: '#FFF', textAlign: 'center' },
  ctaSubtitle: {
    fontSize: 17,
    color: 'rgba(255,255,255,0.80)',
    textAlign: 'center',
    lineHeight: 26,
    marginBottom: 0,
  },
  ctaBtn: {
    backgroundColor: '#FFF',
    paddingHorizontal: 36,
    paddingVertical: 18,
    borderRadius: 12,
    marginTop: 28,
  },
  ctaBtnText:  { color: '#C02030', fontWeight: '900', fontSize: 16 },
  ctaMicro:    { color: 'rgba(255,255,255,0.55)', fontSize: 13, marginTop: 14, letterSpacing: 0.3 },

  // ─── FOOTER ─────────────────────────────────────────────────────────────
  footer: {
    alignItems: 'center',
    paddingVertical: 48,
    borderTopWidth: 1,
    borderTopColor: '#1a1a1a',
    width: '100%',
  },
  footerLogo:    { width: 60, height: 60, marginBottom: 8 },
  footerBrand:   { color: '#FFF', fontWeight: '900', fontSize: 18, letterSpacing: 1 },
  footerSub:     { color: '#888', fontSize: 14, marginTop: 4, marginBottom: 16 },
  footerContact: { color: '#E63946', fontSize: 13, marginBottom: 8 },
  footerCopy:    { color: '#555', fontSize: 12 },
});
