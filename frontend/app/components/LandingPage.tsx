import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, Image,
  Linking, useWindowDimensions, Platform, Pressable,
} from 'react-native';
import { useRouter } from 'expo-router';

// ─── PLATFORM HELPERS ────────────────────────────────────────────────────────
// Barlow Condensed loaded in +html.tsx via Google Fonts. Web only — native falls back to system.
const d = (w: string) =>
  Platform.select({ web: { fontFamily: "'Barlow Condensed', system-ui, sans-serif", fontWeight: w } as any, default: {} }) as any;

const trans = Platform.select({
  web: { transition: 'transform 0.15s ease, box-shadow 0.15s ease, background-color 0.12s ease' } as any,
  default: {},
}) as any;

const pointer = Platform.select({ web: { cursor: 'pointer' } as any, default: {} }) as any;

// ─── DATA ────────────────────────────────────────────────────────────────────
const PRIMARY_FEATURES = [
  {
    emoji: '⚽',
    title: 'FuchoQuiniela',
    desc: 'Predice los 10 partidos de cada jornada antes de que arranquen. El que más aciertos junta, gana la jornada en su liga.',
    color: '#E63946',
  },
  {
    emoji: '👕',
    title: 'FuchoOnce',
    desc: 'Arma tu once con 11 jugadores reales de Liga MX. Sus goles, asistencias y actuaciones suman puntos para ti cada semana.',
    color: '#1D88E5',
  },
];

const SECONDARY_FEATURES = [
  { emoji: '👥', title: 'Ligas Privadas',          desc: 'Código único. Tus cuates entran directo — nadie más.',                         color: '#FFD700' },
  { emoji: '🏆', title: 'Logros y Rachas',           desc: '20 logros desbloqueables. Mantén tu racha, escala de rango.',                  color: '#2A9D8F' },
  { emoji: '📊', title: 'Rankings en Tiempo Real',   desc: 'Posiciones actualizadas al instante. Siempre sabes si vas ganando.',           color: '#FF9800' },
  { emoji: '🎁', title: '100% Gratis',               desc: 'Gratis hoy, gratis siempre. Sin suscripciones ni cobros ocultos.',            color: '#4CAF50' },
];

const STEPS = [
  { n: '01', t: 'Crea tu cuenta',        d: 'Solo tu correo. 30 segundos. Sin tarjeta ni número de teléfono.' },
  { n: '02', t: 'Arma tu liga',          d: 'Comparte el código. Tus cuates entran directo. Un minuto.' },
  { n: '03', t: 'Predice y compite',     d: 'Antes de cada jornada, elige tus resultados. Al final queda claro quién sabe más.' },
];

// ─── MOCKUP DIMS (unchanged) ──────────────────────────────────────────────────
const MOCKUP_W      = 230;
const MOCKUP_H      = Math.round(MOCKUP_W * 983 / 606);
const MOCKUP_W_WIDE = 295;
const MOCKUP_H_WIDE = Math.round(MOCKUP_W_WIDE * 983 / 606);
const WRAP_H        = MOCKUP_H + 40;
const GLOW_R        = 210;
const GLOW_TOP      = (WRAP_H - GLOW_R) / 2;
const RIGHT_H       = MOCKUP_H_WIDE + 48;
const GLOW_R_WIDE   = 290;
const GLOW_TOP_W    = (RIGHT_H - GLOW_R_WIDE) / 2;

// ─── COMPONENT ───────────────────────────────────────────────────────────────
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
        <Pressable
          style={({ hovered }) => [s.navBtn, hovered && s.navBtnHover]}
          onPress={() => router.push('/(auth)/login')}
        >
          <Text style={s.navBtnText}>Iniciar sesión</Text>
        </Pressable>
        <Pressable
          style={({ hovered }) => [s.navBtnPrimary, hovered && s.navBtnPrimaryHover]}
          onPress={() => router.push('/(auth)/register')}
        >
          <Text style={s.navBtnPrimaryText}>Registrarse</Text>
        </Pressable>
      </View>

      {/* ─── HERO ─────────────────────────────────────────────────────────── */}
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
                <Pressable
                  style={({ hovered, pressed }) => [s.heroBtnPrimary, (hovered || pressed) && s.heroBtnPrimaryActive]}
                  onPress={() => router.push('/(auth)/register')}
                >
                  <Text style={s.heroBtnEmoji}>🚀</Text>
                  <Text style={s.heroBtnPrimaryText}>Crear mi quiniela gratis</Text>
                </Pressable>
                <Pressable
                  style={({ hovered, pressed }) => [s.heroBtnSecondary, (hovered || pressed) && s.heroBtnSecondaryActive]}
                  onPress={() => router.push('/(auth)/login')}
                >
                  <Text style={s.heroBtnSecondaryText}>Ya tengo cuenta</Text>
                </Pressable>
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
          <>
            <View style={s.heroPill}><Text style={s.heroPillText}>LIGA MX · GRATIS</Text></View>
            <Text style={s.heroTitle}>La quiniela de{'\n'}tus cuates</Text>
            <Text style={s.heroSubtitle}>Predice resultados, arma tu once{'\n'}y sube en el ranking con tus cuates.</Text>
            <View style={s.heroMockupWrap}>
              <View style={s.heroGlow} />
              <Image
                source={require('../../assets/images/mockup-app.png')}
                style={s.heroImg}
                resizeMode="contain"
              />
            </View>
            <View style={s.heroBtns}>
              <Pressable
                style={({ hovered, pressed }) => [s.heroBtnPrimary, (hovered || pressed) && s.heroBtnPrimaryActive]}
                onPress={() => router.push('/(auth)/register')}
              >
                <Text style={s.heroBtnEmoji}>🚀</Text>
                <Text style={s.heroBtnPrimaryText}>Jugar gratis</Text>
              </Pressable>
              <Pressable
                style={({ hovered, pressed }) => [s.heroBtnSecondary, (hovered || pressed) && s.heroBtnSecondaryActive]}
                onPress={() => router.push('/(auth)/login')}
              >
                <Text style={s.heroBtnSecondaryText}>Ya tengo cuenta</Text>
              </Pressable>
            </View>
            <Text style={s.heroTagline}>Sin tarjeta · Tu liga lista en 2 minutos</Text>
          </>
        )}
      </View>

      {/* ─── FEATURES ─────────────────────────────────────────────────────── */}
      <View style={s.section}>
        <Text style={[s.secTitle, isWide && s.secTitleWide]}>
          Quiniela y Fantasy.{'\n'}Con tus cuates. Sin costo.
        </Text>
        <Text style={s.secSub}>
          Dos formas de competir, las dos gratis, las dos en tu propia liga privada.
        </Text>

        {/* Primary — 2 feature cards */}
        {isWide ? (
          <View style={s.featPrimaryRow}>
            {PRIMARY_FEATURES.map((f, i) => (
              <View key={i} style={[s.featCard, { borderColor: f.color + '35' }]}>
                <View style={[s.featCardIcon, { backgroundColor: f.color + '18', borderColor: f.color + '45' }]}>
                  <Text style={s.featCardEmoji}>{f.emoji}</Text>
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
                <Text style={s.featIconEmoji}>{f.emoji}</Text>
              </View>
              <View style={s.featPrimaryText}>
                <Text style={s.featPrimaryTitle}>{f.title}</Text>
                <Text style={s.featPrimaryDesc}>{f.desc}</Text>
              </View>
            </View>
          ))
        )}

        <View style={s.featDivider} />

        {/* Secondary — stat-row list (NOT identical card grid) */}
        <View style={[s.statGrid, isWide && s.statGridWide]}>
          {SECONDARY_FEATURES.map((f, i) => (
            <View
              key={i}
              style={[
                s.statRow,
                isWide && s.statRowWide,
                (isWide ? i < 2 : i < SECONDARY_FEATURES.length - 1) && s.statRowBorder,
              ]}
            >
              <View style={[s.statBadge, { backgroundColor: f.color + '1a' }]}>
                <Text style={s.statEmoji}>{f.emoji}</Text>
              </View>
              <View style={s.statText}>
                <Text style={[s.statTitle, isWide && s.statTitleWide]}>{f.title}</Text>
                <Text style={s.statDesc}>{f.desc}</Text>
              </View>
            </View>
          ))}
        </View>

        <Pressable
          style={({ hovered, pressed }) => [s.featCta, (hovered || pressed) && s.featCtaActive]}
          onPress={() => router.push('/(auth)/register')}
        >
          <Text style={s.featCtaText}>Empezar gratis ahora →</Text>
        </Pressable>
      </View>

      {/* ─── 3 PASOS ─────────────────────────────────────────────────────── */}
      <View style={s.stepsBg}>
        <View style={s.stepsInner}>
          <Text style={[s.secTitle, isWide && s.secTitleWide]}>
            3 pasos y ya{'\n'}estás compitiendo
          </Text>
          <View style={[s.stepsStack, isWide && s.stepsColumns]}>
            {STEPS.map((step, i) => (
              <View key={i} style={[s.stepCard, isWide && s.stepCardWide]}>
                <Text style={[s.stepDecoNum, isWide && s.stepDecoNumWide]}>{step.n}</Text>
                <View style={[s.stepContent, isWide && s.stepContentWide]}>
                  <Text style={[s.stepTitle, isWide && s.stepTitleWide]}>{step.t}</Text>
                  <Text style={s.stepDesc}>{step.d}</Text>
                </View>
              </View>
            ))}
          </View>
        </View>
      </View>

      {/* ─── PATROCINADORES ───────────────────────────────────────────────── */}
      <View style={s.section}>
        <Text style={[s.secTitle, isWide && s.secTitleWide]}>
          Conecta tu marca{'\n'}con los fans de Liga MX
        </Text>
        <Text style={s.sponsorSub}>
          La app gratuita se sostiene con patrocinios locales. Tu marca aparece donde los aficionados de Liga MX en Aguascalientes ya están — en cada jornada, en cada ranking.
        </Text>

        <View style={s.sponsorGold}>
          <View style={s.sponsorGoldBadge}>
            <Text style={s.sponsorGoldBadgeText}>MAYOR VISIBILIDAD</Text>
          </View>
          <View style={s.sponsorStars}>
            <Text style={s.sponsorStarEmoji}>⭐</Text>
            <Text style={s.sponsorStarEmoji}>⭐</Text>
            <Text style={s.sponsorStarEmoji}>⭐</Text>
          </View>
          <Text style={s.sponsorGoldTier}>ORO</Text>
          <Text style={s.sponsorGoldDesc}>
            Presencia exclusiva en todo el torneo. Tu marca aparece en cada jornada, en cada ranking, frente a todos los jugadores.
          </Text>
        </View>

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

        <Pressable
          style={({ hovered, pressed }) => [s.sponsorBtn, (hovered || pressed) && s.sponsorBtnActive]}
          onPress={() => Linking.openURL('https://wa.me/524492807269?text=Hola,%20me%20interesa%20ser%20patrocinador%20de%20FuchoMX')}
        >
          <Text style={s.sponsorBtnIcon}>📲</Text>
          <Text style={s.sponsorBtnText}>Quiero ser patrocinador</Text>
        </Pressable>
      </View>

      {/* ─── CTA FINAL ────────────────────────────────────────────────────── */}
      <View style={s.ctaWrap}>
        <View style={s.ctaInner}>
          <Text style={s.ctaDecorEmoji}>⚽</Text>
          <Text style={[s.ctaTitle, isWide && s.ctaTitleWide]}>
            ¿Quién de tu grupo{'\n'}sabe más de fut?
          </Text>
          <Text style={s.ctaSub}>
            Únete gratis hoy. Sin tarjeta, sin trampa.{'\n'}Solo queda demostrarlo.
          </Text>
          <Pressable
            style={({ hovered, pressed }) => [s.ctaBtn, (hovered || pressed) && s.ctaBtnActive]}
            onPress={() => router.push('/(auth)/register')}
          >
            <Text style={s.ctaBtnEmoji}>🚀</Text>
            <Text style={s.ctaBtnText}>Crear mi quiniela gratis</Text>
          </Pressable>
          <Text style={s.ctaMicro}>Sin tarjeta · Sin suscripción · 100% gratis</Text>
        </View>
      </View>

      {/* ─── FOOTER ───────────────────────────────────────────────────────── */}
      <View style={s.footer}>
        <Image source={require('../../assets/images/FuchoMX.png')} style={s.footerLogo} resizeMode="contain" />
        <Text style={s.footerBrand}>FUCHO MX</Text>
        <Text style={s.footerSub}>Tu fut, con tus cuates.</Text>
        <Pressable onPress={() => Linking.openURL('mailto:contacto@distrito.digital')}>
          <Text style={s.footerContact}>contacto@distrito.digital</Text>
        </Pressable>
        <Text style={s.footerCopy}>© 2026 FuchoMX · Aguascalientes, México</Text>
      </View>

    </ScrollView>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

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
  navLogo:            { width: 36, height: 36, marginRight: 8 },
  navBrand:           { ...d('900'), color: '#FFF', fontSize: 16, letterSpacing: 1.5, marginRight: 16 },
  navBtn:             { ...trans, ...pointer, paddingHorizontal: 16, paddingVertical: 12, marginRight: 8, minHeight: 44, justifyContent: 'center', borderRadius: 8 },
  navBtnHover:        { backgroundColor: '#151515' },
  navBtnText:         { color: '#AAA', fontSize: 14 },
  navBtnPrimary:      { ...trans, ...pointer, backgroundColor: '#C02030', paddingHorizontal: 16, paddingVertical: 12, borderRadius: 8, minHeight: 44, justifyContent: 'center' },
  navBtnPrimaryHover: { backgroundColor: '#E63946' },
  navBtnPrimaryText:  { ...d('700'), color: '#FFF', fontSize: 14 },

  // ─── HERO ─────────────────────────────────────────────────────────────────
  hero:            { width: '100%', alignItems: 'center', paddingHorizontal: 24, paddingTop: 72, paddingBottom: 72 },
  heroRow:         { flexDirection: 'row', alignItems: 'center', width: '100%', maxWidth: 1100, gap: 64 },
  heroLeft:        { flex: 1, minWidth: 0 },
  heroRight:       { width: 340, height: RIGHT_H, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  heroGlowWide: {
    position: 'absolute', alignSelf: 'center', top: GLOW_TOP_W,
    width: GLOW_R_WIDE, height: GLOW_R_WIDE, borderRadius: GLOW_R_WIDE / 2,
    backgroundColor: '#E63946', opacity: 0.22,
    ...Platform.select({ web: { filter: 'blur(90px)' } as any, default: {} }),
  },
  heroImgWide:      { width: MOCKUP_W_WIDE, height: MOCKUP_H_WIDE },

  heroPill:         { ...{ alignSelf: 'flex-start' }, borderWidth: 1, borderColor: '#E6394655', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 5, marginBottom: 24 },
  heroPillText:     { ...d('800'), color: '#E63946', fontSize: 11, letterSpacing: 2.5 },

  heroTitle:        { ...d('900'), fontSize: 44, color: '#FFF', textAlign: 'center', lineHeight: 50, marginBottom: 16, letterSpacing: -0.5 },
  heroTitleWide:    { ...d('900'), fontSize: 66, color: '#FFF', lineHeight: 72, marginBottom: 24, letterSpacing: -1 },
  heroSubtitle:     { fontSize: 16, color: '#999', textAlign: 'center', lineHeight: 26, marginBottom: 12 },
  heroSubtitleWide: { fontSize: 18, color: '#999', lineHeight: 29, marginBottom: 40, maxWidth: 480 },
  heroTagline:      { fontSize: 13, color: '#888', textAlign: 'center', letterSpacing: 0.4, marginTop: 20 },
  heroTaglineWide:  { fontSize: 13, color: '#888', letterSpacing: 0.4, marginTop: 20 },

  heroBtns:              { flexDirection: 'row', gap: 12, flexWrap: 'wrap' },
  heroBtnEmoji:          { fontSize: 16, lineHeight: 20 },
  heroBtnPrimary: {
    ...trans, ...pointer,
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: '#E63946', paddingHorizontal: 28, paddingVertical: 18, borderRadius: 12,
  },
  heroBtnPrimaryActive: {
    ...Platform.select({ web: { transform: [{ translateY: -2 }], boxShadow: '0 8px 28px rgba(230,57,70,0.55)' } as any, default: {} }),
    backgroundColor: '#FF4455',
  },
  heroBtnPrimaryText:   { ...d('900'), color: '#FFF', fontSize: 16 },
  heroBtnSecondary: {
    ...trans, ...pointer,
    paddingHorizontal: 24, paddingVertical: 18, borderRadius: 12,
    borderWidth: 1, borderColor: '#383838', backgroundColor: '#111', justifyContent: 'center',
  },
  heroBtnSecondaryActive: { borderColor: '#555', backgroundColor: '#1a1a1a' },
  heroBtnSecondaryText:   { color: '#AAA', fontSize: 15 },

  heroMockupWrap: { alignItems: 'center', justifyContent: 'center', width: '100%', height: WRAP_H, marginTop: 8, marginBottom: 40 },
  heroGlow: {
    position: 'absolute', alignSelf: 'center', top: GLOW_TOP,
    width: GLOW_R, height: GLOW_R, borderRadius: GLOW_R / 2,
    backgroundColor: '#E63946', opacity: 0.24,
    ...Platform.select({ web: { filter: 'blur(70px)' } as any, default: {} }),
  },
  heroImg: { width: MOCKUP_W, height: MOCKUP_H },

  // ─── SECTION ──────────────────────────────────────────────────────────────
  section:      { width: '100%', maxWidth: 1100, alignSelf: 'center', paddingHorizontal: 24, paddingVertical: 80 },
  secTitle:     { ...d('900'), fontSize: 30, color: '#FFF', textAlign: 'center', marginBottom: 48, lineHeight: 36, letterSpacing: 0.2 },
  secTitleWide: { fontSize: 42, lineHeight: 50, letterSpacing: -0.5 },
  secSub:       { color: '#777', fontSize: 16, textAlign: 'center', maxWidth: 540, alignSelf: 'center', lineHeight: 25, marginTop: -28, marginBottom: 44 },

  // ─── FEATURES primary ─────────────────────────────────────────────────────
  featPrimaryRow: { flexDirection: 'row', gap: 20 },
  featCard: {
    flex: 1, backgroundColor: '#0d0d0d', borderWidth: 1, borderRadius: 16, padding: 32,
    ...Platform.select({ web: { transition: 'border-color 0.2s ease' } as any, default: {} }),
  },
  featCardIcon:   { width: 76, height: 76, borderRadius: 20, borderWidth: 1, justifyContent: 'center', alignItems: 'center', marginBottom: 22 },
  featCardEmoji:  { fontSize: 34, lineHeight: 40 },
  featCardTitle:  { ...d('900'), color: '#FFF', fontSize: 24, marginBottom: 10, letterSpacing: 0.2 },
  featCardDesc:   { color: '#888', fontSize: 15, lineHeight: 24 },

  featPrimaryRow2:  { flexDirection: 'row', marginBottom: 28, alignItems: 'flex-start' },
  featIcon:         { width: 64, height: 64, borderRadius: 16, borderWidth: 1, justifyContent: 'center', alignItems: 'center', marginRight: 20, flexShrink: 0 },
  featIconEmoji:    { fontSize: 28, lineHeight: 34 },
  featPrimaryText:  { flex: 1, paddingTop: 6, minWidth: 0 },
  featPrimaryTitle: { ...d('800'), color: '#FFF', fontSize: 20, marginBottom: 6 },
  featPrimaryDesc:  { color: '#888', fontSize: 14, lineHeight: 22 },

  featDivider: { height: 1, backgroundColor: '#1c1c1c', marginTop: 48, marginBottom: 48 },
  featCta:     { ...trans, ...pointer, alignSelf: 'center', marginTop: 40, paddingHorizontal: 28, paddingVertical: 14, borderRadius: 10, backgroundColor: '#E63946' },
  featCtaActive: {
    ...Platform.select({ web: { transform: [{ translateY: -1 }], boxShadow: '0 6px 20px rgba(230,57,70,0.45)' } as any, default: {} }),
    backgroundColor: '#FF4455',
  },
  featCtaText: { ...d('700'), color: '#FFF', fontSize: 16 },

  // ─── FEATURES secondary — STAT ROWS (replaces identical card grid) ─────────
  statGrid:       { width: '100%' },
  statGridWide:   { flexDirection: 'row', flexWrap: 'wrap' },
  statRow: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 14,
    paddingVertical: 22,
  },
  statRowWide:    { width: '50%', paddingHorizontal: 12 },
  statRowBorder:  { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: '#252525' },
  statBadge:      { width: 46, height: 46, borderRadius: 12, justifyContent: 'center', alignItems: 'center', flexShrink: 0 },
  statEmoji:      { fontSize: 22, lineHeight: 26 },
  statText:       { flex: 1, minWidth: 0, paddingTop: 2 },
  statTitle:      { color: '#FFF', fontWeight: '700', fontSize: 15, marginBottom: 4 },
  statTitleWide:  { ...d('800'), fontSize: 17, letterSpacing: 0.1 },
  statDesc:       { color: '#666', fontSize: 13, lineHeight: 20 },

  // ─── 3 PASOS ──────────────────────────────────────────────────────────────
  stepsBg:    { width: '100%', backgroundColor: '#0d0d0d' },
  stepsInner: { width: '100%', maxWidth: 1100, alignSelf: 'center', paddingHorizontal: 24, paddingVertical: 80 },
  stepsStack:   { gap: 14, maxWidth: 560, alignSelf: 'center', width: '100%' },
  stepsColumns: { flexDirection: 'row', gap: 20, maxWidth: 980, alignSelf: 'center', width: '100%' },

  stepCard: {
    backgroundColor: '#141414', borderRadius: 16, padding: 24,
    flexDirection: 'row', alignItems: 'flex-start', gap: 16,
  },
  stepCardWide: {
    flex: 1,
    flexDirection: 'column', alignItems: 'flex-start',
    paddingTop: 32, paddingBottom: 28, paddingHorizontal: 28,
  },
  stepDecoNum: {
    ...d('900'),
    color: '#FFF', fontSize: 15,
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: '#E63946',
    textAlign: 'center',
    flexShrink: 0,
    ...Platform.select({ web: { lineHeight: '40px' } as any, default: { textAlignVertical: 'center' } }),
  },
  stepDecoNumWide: {
    width: 44, height: 44, borderRadius: 22, fontSize: 16,
    marginBottom: 20,
    ...Platform.select({ web: { lineHeight: '44px' } as any, default: {} }),
  },
  stepContent:     { flex: 1, minWidth: 0 },
  stepContentWide: { flex: undefined, width: '100%' },
  stepTitle:       { color: '#FFF', fontWeight: '700', fontSize: 16, marginBottom: 6 },
  stepTitleWide:   { ...d('800'), fontSize: 20, lineHeight: 26, marginBottom: 10 },
  stepDesc:        { color: '#777', fontSize: 13, lineHeight: 20 },

  // ─── PATROCINADORES ───────────────────────────────────────────────────────
  sponsorSub: { color: '#888', fontSize: 15, textAlign: 'center', marginBottom: 44, maxWidth: 520, alignSelf: 'center', lineHeight: 24 },

  sponsorGold: {
    backgroundColor: '#110d00', borderWidth: 1, borderColor: '#FFD70045',
    borderRadius: 16, padding: 36, alignItems: 'center',
    maxWidth: 480, alignSelf: 'center', width: '100%', marginBottom: 16,
  },
  sponsorGoldBadge:     { backgroundColor: '#FFD70015', borderWidth: 1, borderColor: '#FFD70040', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4, marginBottom: 16 },
  sponsorGoldBadgeText: { ...d('800'), color: '#FFD700', fontSize: 10, letterSpacing: 2.5 },
  sponsorStars:         { flexDirection: 'row', gap: 4, marginBottom: 12 },
  sponsorStarEmoji:     { fontSize: 18, lineHeight: 22 },
  sponsorGoldTier:      { ...d('900'), color: '#FFD700', fontSize: 32, letterSpacing: 4, marginBottom: 12 },
  sponsorGoldDesc:      { color: '#CCC', fontSize: 15, textAlign: 'center', lineHeight: 23 },

  sponsorRow:  { flexDirection: 'row', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 40, maxWidth: 480, alignSelf: 'center', width: '100%' },
  sponsorCard: { flex: 1, minWidth: 130, borderWidth: 1, borderRadius: 12, padding: 24, alignItems: 'center', backgroundColor: '#0d0d0d' },
  sponsorTier: { ...d('900'), fontSize: 17, letterSpacing: 2, marginBottom: 8 },
  sponsorDesc: { color: '#888', fontSize: 12, textAlign: 'center', lineHeight: 18 },

  sponsorBtn: {
    ...trans, ...pointer,
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: '#25D366', paddingHorizontal: 28, paddingVertical: 16, borderRadius: 12, alignSelf: 'center',
  },
  sponsorBtnActive: {
    ...Platform.select({ web: { transform: [{ translateY: -1 }], boxShadow: '0 6px 20px rgba(37,211,102,0.4)' } as any, default: {} }),
    backgroundColor: '#30e070',
  },
  sponsorBtnIcon: { fontSize: 18, lineHeight: 22 },
  sponsorBtnText: { ...d('700'), color: '#FFF', fontSize: 16 },

  // ─── CTA FINAL ────────────────────────────────────────────────────────────
  ctaWrap:       { width: '100%', backgroundColor: '#C02030' },
  ctaInner:      { maxWidth: 680, alignSelf: 'center', width: '100%', paddingHorizontal: 24, paddingVertical: 88, alignItems: 'center' },
  ctaDecorEmoji: { fontSize: 48, lineHeight: 56, marginBottom: 20, opacity: 0.35 },
  ctaTitle:      { ...d('900'), fontSize: 32, color: '#FFF', textAlign: 'center', lineHeight: 38, marginBottom: 16, letterSpacing: -0.3 },
  ctaTitleWide:  { fontSize: 48, lineHeight: 56, letterSpacing: -0.8 },
  ctaSub:        { fontSize: 17, color: 'rgba(255,255,255,0.82)', textAlign: 'center', lineHeight: 27, marginBottom: 0 },
  ctaBtn: {
    ...trans, ...pointer,
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: '#FFF', paddingHorizontal: 36, paddingVertical: 18, borderRadius: 12, marginTop: 36,
  },
  ctaBtnActive: {
    ...Platform.select({ web: { transform: [{ translateY: -2 }], boxShadow: '0 8px 28px rgba(0,0,0,0.3)' } as any, default: {} }),
    backgroundColor: '#F0F0F0',
  },
  ctaBtnEmoji:   { fontSize: 16, lineHeight: 20 },
  ctaBtnText:    { ...d('900'), color: '#C02030', fontSize: 17 },
  ctaMicro:      { color: 'rgba(255,255,255,0.82)', fontSize: 13, marginTop: 16, letterSpacing: 0.3 },

  // ─── FOOTER ───────────────────────────────────────────────────────────────
  footer:        { alignItems: 'center', paddingVertical: 56, borderTopWidth: 1, borderTopColor: '#1a1a1a', width: '100%' },
  footerLogo:    { width: 60, height: 60, marginBottom: 8 },
  footerBrand:   { ...d('900'), color: '#FFF', fontSize: 18, letterSpacing: 1.5 },
  footerSub:     { color: '#666', fontSize: 14, marginTop: 4, marginBottom: 16 },
  footerContact: { ...trans, ...pointer, color: '#E63946', fontSize: 13, marginBottom: 8 },
  footerCopy:    { color: '#444', fontSize: 12 },
});
