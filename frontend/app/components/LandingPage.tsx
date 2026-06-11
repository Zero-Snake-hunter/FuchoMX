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
  { icon: 'people',    title: 'Ligas Privadas',     desc: 'Crea tu liga con código único. Solo entran tus cuates, nadie más.',            color: '#FFD700' },
  { icon: 'trophy',   title: 'Logros y Rachas',     desc: '20 logros desbloqueables. Cada racha de aciertos tiene su recompensa.',        color: '#2A9D8F' },
  { icon: 'bar-chart', title: 'Rankings en Vivo',   desc: 'Posiciones actualizadas al minuto. Sabes exactamente dónde estás.',            color: '#FF9800' },
  { icon: 'gift',     title: 'Sin costo, sin trampa', desc: 'Gratis hoy, gratis siempre. Sin suscripciones ni cobros ocultos.',           color: '#4CAF50' },
];

const STEPS = [
  { n: '1', icon: 'person-add' as const,  t: 'Crea tu cuenta gratis',             d: 'Regístrate con tu correo en 30 segundos. Sin tarjeta, sin número de teléfono.' },
  { n: '2', icon: 'people'     as const,  t: 'Crea tu liga y comparte el código', d: 'Tus cuates entran directo con el código. En un minuto ya están todos adentro.' },
  { n: '3', icon: 'football'   as const,  t: 'Predice cada jornada y compite',    d: 'Antes de cada fecha, predice los 10 partidos. Al final sabes quién sabe más de fut.' },
];

// PNG: 606×1103 → ratio ancho/alto = 0.549
const MOCKUP_W      = 230;
const MOCKUP_H      = Math.round(MOCKUP_W / 0.549);
const MOCKUP_W_WIDE = 295;
const MOCKUP_H_WIDE = Math.round(MOCKUP_W_WIDE / 0.549);

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
    <ScrollView style={s.root} contentContainerStyle={s.rootContent} showsVerticalScrollIndicator={false}>

      {/* ─── NAV ──────────────────────────────────────────────────────────── */}
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

      {/* ─── HERO — NO TOCAR ──────────────────────────────────────────────── */}
      <View style={s.hero}>
        {isWide ? (
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
              <Image source={require('../../assets/images/mockup-app.png')} style={s.heroImgWide} resizeMode="contain" />
            </View>
          </View>
        ) : (
          <>
            <View style={s.heroPill}><Text style={s.heroPillText}>LIGA MX · GRATIS</Text></View>
            <Text style={s.heroTitle}>La quiniela de{'\n'}tus cuates</Text>
            <Text style={s.heroSubtitle}>Predice resultados, arma tu once{'\n'}y sube en el ranking con tus cuates.</Text>
            <View style={s.heroMockupWrap}>
              <View style={s.heroGlow} />
              <Image source={require('../../assets/images/mockup-app.png')} style={s.heroImg} resizeMode="contain" />
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
        <Text style={[s.secTitle, isWide && s.secTitleWide]}>
          Quiniela y fantasy.{'\n'}Un solo lugar.
        </Text>

        {/* Primary: 2-col cards en desktop, rows en mobile */}
        {isWide ? (
          <View style={s.featPrimaryRow}>
            {PRIMARY_FEATURES.map((f, i) => (
              <View key={i} style={[s.featCard, { borderColor: f.color + '35' }]}>
                <View style={[s.featCardIcon, { backgroundColor: f.color + '18', borderColor: f.color + '45' }]}>
                  <Ionicons name={f.icon as any} size={36} color={f.color} />
                </View>
                <Text style={s.featCardTitle}>{f.title}</Text>
                <Text style={s.featCardDesc}>{f.desc}</Text>
              </View>
            ))}
          </View>
        ) : (
          PRIMARY_FEATURES.map((f, i) => (
            <View key={i} style={s.featPrimaryRow2}>
              <View style={[s.featIcon, { backgroundColor: f.color + '22', borderColor: f.color + '55' }]}>
                <Ionicons name={f.icon as any} size={30} color={f.color} />
              </View>
              <View style={s.featPrimaryText}>
                <Text style={s.featPrimaryTitle}>{f.title}</Text>
                <Text style={s.featPrimaryDesc}>{f.desc}</Text>
              </View>
            </View>
          ))
        )}

        <View style={s.featDivider} />

        {/* Secondary: mini-cards 2×2 */}
        <View style={[s.featSecGrid, isWide && s.featSecGridWide]}>
          {SECONDARY_FEATURES.map((f, i) => (
            <View key={i} style={[s.featSecItem, isWide && s.featSecItemCard]}>
              <View style={[s.featSecIcon, { backgroundColor: f.color + '28', borderColor: f.color + '55', borderWidth: 1 }]}>
                <Ionicons name={f.icon as any} size={20} color={f.color} />
              </View>
              <View style={{ flex: 1, minWidth: 0 }}>
                <Text style={s.featSecTitle}>{f.title}</Text>
                <Text style={s.featSecDesc}>{f.desc}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {/* ─── 3 PASOS ─────────────────────────────────────────────────────── */}
      {/* Wrapper full-width para que el bg #0d0d0d cubra toda la pantalla */}
      <View style={s.stepsBg}>
        <View style={s.stepsInner}>
          <Text style={[s.secTitle, isWide && s.secTitleWide]}>
            3 pasos y ya{'\n'}estás jugando
          </Text>
          <View style={[s.stepsStack, isWide && s.stepsColumns]}>
            {STEPS.map((step, i) => (
              <View key={i} style={[s.stepCard, isWide && s.stepCardWide]}>
                {isWide ? (
                  <>
                    <View style={s.stepBubble}>
                      <Ionicons name={step.icon} size={26} color="#FFF" />
                    </View>
                    <Text style={s.stepLabel}>{step.n} de 3</Text>
                    <Text style={s.stepTitleWide}>{step.t}</Text>
                    <Text style={s.stepDescWide}>{step.d}</Text>
                  </>
                ) : (
                  <>
                    <View style={s.stepNum}>
                      <Text style={s.stepNumText}>{step.n}</Text>
                    </View>
                    <View style={{ flex: 1, minWidth: 0 }}>
                      <Text style={s.stepTitle}>{step.t}</Text>
                      <Text style={s.stepDesc}>{step.d}</Text>
                    </View>
                  </>
                )}
              </View>
            ))}
          </View>
        </View>
      </View>

      {/* ─── PATROCINADORES ───────────────────────────────────────────────── */}
      <View style={s.section}>
        <Text style={s.secTag}>PATROCINADORES</Text>
        <Text style={[s.secTitle, isWide && s.secTitleWide]}>
          Llega directo a los fanáticos{'\n'}del fut en Aguascalientes
        </Text>
        <Text style={s.sponsorSub}>
          FuchoMX conecta marcas locales con aficionados de Liga MX. Gratis para los jugadores, sostenido por sponsors que quieren aparecer donde sí se ven.
        </Text>

        {/* ORO — tier destacado */}
        <View style={s.sponsorGold}>
          <View style={s.sponsorGoldBadge}>
            <Text style={s.sponsorGoldBadgeText}>MAYOR VISIBILIDAD</Text>
          </View>
          <View style={s.sponsorStars}>
            <Ionicons name="star" size={18} color="#FFD700" />
            <Ionicons name="star" size={18} color="#FFD700" />
            <Ionicons name="star" size={18} color="#FFD700" />
          </View>
          <Text style={s.sponsorGoldTier}>ORO</Text>
          <Text style={s.sponsorGoldDesc}>
            Presencia exclusiva en todo el torneo. Tu marca aparece en cada jornada, en cada ranking, frente a todos los jugadores.
          </Text>
        </View>

        {/* PLATA + BRONCE */}
        <View style={s.sponsorRow}>
          {[
            { tier: 'PLATA',  color: '#AAAAAA', desc: 'Visibilidad rotativa por jornada' },
            { tier: 'BRONCE', color: '#CD7F32', desc: 'Presencia continua en perfiles'   },
          ].map((sp, i) => (
            <View key={i} style={[s.sponsorCard, { borderColor: sp.color + '45' }]}>
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
      {/* ctaWrap full-width: el rojo cubre toda la pantalla, no solo 1100px */}
      <View style={s.ctaWrap}>
        <View style={s.ctaInner}>
          <Ionicons name="football" size={44} color="rgba(255,255,255,0.20)" style={{ marginBottom: 20 }} />
          <Text style={[s.ctaTitle, isWide && s.ctaTitleWide]}>
            ¿Quién de tu grupo{'\n'}sabe más de fut?
          </Text>
          <Text style={s.ctaSub}>
            Crea tu quiniela ahora y demuéstralo esta jornada.
          </Text>
          <TouchableOpacity style={s.ctaBtn} onPress={() => router.push('/(auth)/register')}>
            <Ionicons name="rocket" size={18} color="#C02030" />
            <Text style={s.ctaBtnText}>Crear mi quiniela gratis</Text>
          </TouchableOpacity>
          <Text style={s.ctaMicro}>Sin tarjeta · Sin suscripción · 100% gratis</Text>
        </View>
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

/* ─────────────────────────────────────────────────────────────────────────── */

const s = StyleSheet.create({

  // ─── ROOT ─────────────────────────────────────────────────────────────────
  root:        { flex: 1, backgroundColor: '#090909' },
  rootContent: { flexGrow: 1, width: '100%' },

  // ─── NAV ──────────────────────────────────────────────────────────────────
  nav: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 24, paddingVertical: 16,
    borderBottomWidth: 1, borderBottomColor: '#1a1a1a',
    width: '100%',
  },
  navLogo:          { width: 36, height: 36, marginRight: 8 },
  navBrand:         { color: '#FFF', fontWeight: '900', fontSize: 16, letterSpacing: 1, marginRight: 16 },
  navBtn:           { paddingHorizontal: 16, paddingVertical: 12, marginRight: 8, minHeight: 44, justifyContent: 'center' },
  navBtnText:       { color: '#AAA', fontSize: 14 },
  navBtnPrimary:    { backgroundColor: '#C02030', paddingHorizontal: 16, paddingVertical: 12, borderRadius: 8, minHeight: 44, justifyContent: 'center' },
  navBtnPrimaryText:{ color: '#FFF', fontWeight: '700', fontSize: 14 },

  // ─── HERO (sin cambios) ────────────────────────────────────────────────────
  hero: { width: '100%', alignItems: 'center', paddingHorizontal: 24, paddingTop: 72, paddingBottom: 72 },
  heroRow:    { flexDirection: 'row', alignItems: 'center', width: '100%', maxWidth: 1100, gap: 64 },
  heroLeft:   { flex: 1, minWidth: 0 },
  heroRight:  { width: 340, height: RIGHT_H, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  heroGlowWide: {
    position: 'absolute', alignSelf: 'center', top: GLOW_TOP_W,
    width: GLOW_R_WIDE, height: GLOW_R_WIDE, borderRadius: GLOW_R_WIDE / 2,
    backgroundColor: '#E63946', opacity: 0.22,
    ...Platform.select({ web: { filter: 'blur(90px)' } as any, default: {} }),
  },
  heroImgWide:     { width: MOCKUP_W_WIDE, height: MOCKUP_H_WIDE },
  heroPill:        { borderWidth: 1, borderColor: '#E6394655', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 5, marginBottom: 24 },
  heroPillText:    { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 2.5 },
  heroTitle:       { fontSize: 40, fontWeight: '900', color: '#FFF', textAlign: 'center', lineHeight: 48, marginBottom: 16 },
  heroTitleWide:   { fontSize: 60, fontWeight: '900', color: '#FFF', lineHeight: 68, marginBottom: 24 },
  heroSubtitle:    { fontSize: 16, color: '#999', textAlign: 'center', lineHeight: 26, marginBottom: 12 },
  heroSubtitleWide:{ fontSize: 17, color: '#999', lineHeight: 28, marginBottom: 40 },
  heroTagline:     { fontSize: 13, color: '#777', textAlign: 'center', letterSpacing: 0.4, marginTop: 20 },
  heroTaglineWide: { fontSize: 13, color: '#777', letterSpacing: 0.4, marginTop: 20 },
  heroBtns:        { flexDirection: 'row', gap: 12, flexWrap: 'wrap' },
  heroBtnPrimary:  { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#E63946', paddingHorizontal: 28, paddingVertical: 18, borderRadius: 12 },
  heroBtnPrimaryText:  { color: '#FFF', fontWeight: '900', fontSize: 16 },
  heroBtnSecondary:    { paddingHorizontal: 24, paddingVertical: 18, borderRadius: 12, borderWidth: 1, borderColor: '#383838', backgroundColor: '#111', justifyContent: 'center' },
  heroBtnSecondaryText:{ color: '#AAA', fontSize: 15 },
  heroMockupWrap:  { alignItems: 'center', justifyContent: 'center', width: '100%', height: WRAP_H, marginTop: 8, marginBottom: 40 },
  heroGlow: {
    position: 'absolute', alignSelf: 'center', top: GLOW_TOP,
    width: GLOW_R, height: GLOW_R, borderRadius: GLOW_R / 2,
    backgroundColor: '#E63946', opacity: 0.24,
    ...Platform.select({ web: { filter: 'blur(70px)' } as any, default: {} }),
  },
  heroImg: { width: MOCKUP_W, height: MOCKUP_H },

  // ─── SECTION base (sin bg especial) ───────────────────────────────────────
  section: {
    width: '100%', maxWidth: 1100, alignSelf: 'center',
    paddingHorizontal: 24, paddingVertical: 72,
  },
  secTag: { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 3, marginBottom: 12, textAlign: 'center' },
  secTitle:    { fontSize: 28, fontWeight: '900', color: '#FFF', textAlign: 'center', marginBottom: 48, lineHeight: 36 },
  secTitleWide:{ fontSize: 38, lineHeight: 46 },

  // ─── FEATURES primary ─────────────────────────────────────────────────────
  // Desktop: cards lado a lado
  featPrimaryRow: { flexDirection: 'row', gap: 20, marginBottom: 0 },
  featCard: {
    flex: 1, backgroundColor: '#0d0d0d', borderWidth: 1,
    borderRadius: 16, padding: 32,
  },
  featCardIcon: {
    width: 76, height: 76, borderRadius: 20, borderWidth: 1,
    justifyContent: 'center', alignItems: 'center', marginBottom: 22,
  },
  featCardTitle: { color: '#FFF', fontWeight: '900', fontSize: 22, marginBottom: 10 },
  featCardDesc:  { color: '#888', fontSize: 15, lineHeight: 24 },

  // Mobile: rows
  featPrimaryRow2: { flexDirection: 'row', marginBottom: 28, alignItems: 'flex-start' },
  featIcon: { width: 64, height: 64, borderRadius: 16, borderWidth: 1, justifyContent: 'center', alignItems: 'center', marginRight: 20, flexShrink: 0 },
  featPrimaryText:  { flex: 1, paddingTop: 6, minWidth: 0 },
  featPrimaryTitle: { color: '#FFF', fontWeight: '900', fontSize: 20, marginBottom: 6 },
  featPrimaryDesc:  { color: '#888', fontSize: 14, lineHeight: 22 },

  // Divider entre primary y secondary
  featDivider: { height: 1, backgroundColor: '#1c1c1c', marginTop: 48, marginBottom: 48 },

  // ─── FEATURES secondary ───────────────────────────────────────────────────
  featSecGrid:     { gap: 14 },
  featSecGridWide: {
    flexDirection: 'row', flexWrap: 'wrap', gap: 16,
    maxWidth: 820, alignSelf: 'center', width: '100%',
  },
  featSecItem:     { flexDirection: 'row', gap: 14, alignItems: 'flex-start' },
  featSecItemCard: {
    width: '47%',
    backgroundColor: '#0d0d0d', borderWidth: 1,
    borderColor: '#1e1e1e', borderRadius: 14, padding: 20,
  },
  featSecIcon: { width: 42, height: 42, borderRadius: 12, justifyContent: 'center', alignItems: 'center', flexShrink: 0, marginTop: 1 },
  featSecTitle: { color: '#FFF', fontWeight: '700', fontSize: 14, marginBottom: 4 },
  featSecDesc:  { color: '#777', fontSize: 13, lineHeight: 19 },

  // ─── 3 PASOS ──────────────────────────────────────────────────────────────
  // Full-width bg: wrapper abarca toda la pantalla, inner centra el contenido
  stepsBg:    { width: '100%', backgroundColor: '#0d0d0d' },
  stepsInner: { width: '100%', maxWidth: 1100, alignSelf: 'center', paddingHorizontal: 24, paddingVertical: 72 },

  stepsStack:   { gap: 14, maxWidth: 560, alignSelf: 'center', width: '100%' },
  stepsColumns: { flexDirection: 'row', gap: 20, maxWidth: 940, alignSelf: 'center', width: '100%' },

  stepCard: {
    flexDirection: 'row', alignItems: 'flex-start',
    backgroundColor: '#141414', borderRadius: 14, padding: 20, gap: 16,
  },
  stepCardWide: {
    flex: 1, flexDirection: 'column', alignItems: 'flex-start',
    backgroundColor: '#141414', borderRadius: 16, padding: 28, gap: 0,
  },

  // Mobile step internals
  stepNum:     { width: 48, height: 48, borderRadius: 24, backgroundColor: '#E63946', justifyContent: 'center', alignItems: 'center', flexShrink: 0 },
  stepNumText: { color: '#FFF', fontWeight: '900', fontSize: 20 },
  stepTitle:   { color: '#FFF', fontWeight: '700', fontSize: 16, marginBottom: 4 },
  stepDesc:    { color: '#888', fontSize: 13, lineHeight: 19 },

  // Desktop step internals
  stepBubble:    { width: 60, height: 60, borderRadius: 30, backgroundColor: '#E63946', justifyContent: 'center', alignItems: 'center', marginBottom: 18 },
  stepLabel:     { color: '#E63946', fontSize: 11, fontWeight: '800', letterSpacing: 2.5, marginBottom: 10 },
  stepTitleWide: { color: '#FFF', fontWeight: '900', fontSize: 18, lineHeight: 24, marginBottom: 8 },
  stepDescWide:  { color: '#888', fontSize: 13, lineHeight: 20 },

  // ─── PATROCINADORES ───────────────────────────────────────────────────────
  sponsorSub: {
    color: '#888', fontSize: 15, textAlign: 'center', marginBottom: 44,
    maxWidth: 520, alignSelf: 'center', lineHeight: 24,
  },

  // ORO — card destacado (más grande, fondo dorado tenue, estrellas)
  sponsorGold: {
    backgroundColor: '#110d00', borderWidth: 1, borderColor: '#FFD70045',
    borderRadius: 16, padding: 36, alignItems: 'center',
    maxWidth: 480, alignSelf: 'center', width: '100%', marginBottom: 16,
  },
  sponsorGoldBadge: {
    backgroundColor: '#FFD70015', borderWidth: 1, borderColor: '#FFD70040',
    borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4, marginBottom: 16,
  },
  sponsorGoldBadgeText: { color: '#FFD700', fontSize: 10, fontWeight: '800', letterSpacing: 2.5 },
  sponsorStars:         { flexDirection: 'row', gap: 6, marginBottom: 12 },
  sponsorGoldTier:      { color: '#FFD700', fontWeight: '900', fontSize: 30, letterSpacing: 4, marginBottom: 12 },
  sponsorGoldDesc:      { color: '#CCC', fontSize: 15, textAlign: 'center', lineHeight: 23 },

  // PLATA + BRONCE
  sponsorRow: {
    flexDirection: 'row', gap: 12, justifyContent: 'center',
    flexWrap: 'wrap', marginBottom: 40,
    maxWidth: 480, alignSelf: 'center', width: '100%',
  },
  sponsorCard: { flex: 1, minWidth: 130, borderWidth: 1, borderRadius: 12, padding: 24, alignItems: 'center', backgroundColor: '#0d0d0d' },
  sponsorTier: { fontWeight: '900', fontSize: 16, letterSpacing: 2, marginBottom: 8 },
  sponsorDesc: { color: '#777', fontSize: 12, textAlign: 'center', lineHeight: 18 },

  sponsorBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: '#25D366', paddingHorizontal: 28, paddingVertical: 16,
    borderRadius: 12, alignSelf: 'center',
  },
  sponsorBtnText: { color: '#FFF', fontWeight: '700', fontSize: 16 },

  // ─── CTA FINAL ────────────────────────────────────────────────────────────
  // ctaWrap full-width: el rojo cubre toda la pantalla sin corte de maxWidth
  ctaWrap:  { width: '100%', backgroundColor: '#C02030' },
  ctaInner: {
    maxWidth: 680, alignSelf: 'center', width: '100%',
    paddingHorizontal: 24, paddingVertical: 80, alignItems: 'center',
  },
  ctaTitle:     { fontSize: 30, fontWeight: '900', color: '#FFF', textAlign: 'center', lineHeight: 38, marginBottom: 16 },
  ctaTitleWide: { fontSize: 42, lineHeight: 50 },
  ctaSub:       { fontSize: 17, color: 'rgba(255,255,255,0.80)', textAlign: 'center', lineHeight: 26 },
  ctaBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: '#FFF', paddingHorizontal: 36, paddingVertical: 18,
    borderRadius: 12, marginTop: 36,
  },
  ctaBtnText: { color: '#C02030', fontWeight: '900', fontSize: 16 },
  ctaMicro:   { color: 'rgba(255,255,255,0.50)', fontSize: 13, marginTop: 16, letterSpacing: 0.3 },

  // ─── FOOTER ───────────────────────────────────────────────────────────────
  footer: {
    alignItems: 'center', paddingVertical: 48,
    borderTopWidth: 1, borderTopColor: '#1a1a1a', width: '100%',
  },
  footerLogo:    { width: 60, height: 60, marginBottom: 8 },
  footerBrand:   { color: '#FFF', fontWeight: '900', fontSize: 18, letterSpacing: 1 },
  footerSub:     { color: '#888', fontSize: 14, marginTop: 4, marginBottom: 16 },
  footerContact: { color: '#E63946', fontSize: 13, marginBottom: 8 },
  footerCopy:    { color: '#555', fontSize: 12 },
});
