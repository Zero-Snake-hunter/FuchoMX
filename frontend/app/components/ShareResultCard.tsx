/**
 * ShareResultCard.tsx
 * Tarjeta visual para compartir resultados de quiniela/logros en redes sociales.
 * Usa ViewShot para capturar la tarjeta como imagen y expo-sharing para compartir.
 */
import React, { useRef, forwardRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  Share, Platform,
} from 'react-native';
import ViewShot from 'react-native-view-shot';
import * as Sharing from 'expo-sharing';
import { useToast } from '../context/ToastContext';

// ─── Tipos ────────────────────────────────────────────────
export interface ShareResultData {
  userName: string;
  leagueName?: string;
  leagueCode?: string;
  jornadaNumber?: number;
  points?: number;
  position?: number;
  streak?: number;
  // Para logros
  achievementTitle?: string;
  achievementEmoji?: string;
  achievementDesc?: string;
  mode: 'result' | 'achievement';
}

interface Props {
  data: ShareResultData;
  onClose?: () => void;
}

// ─── Tarjeta visual (la que se captura) ──────────────────
const VisualCard = forwardRef<ViewShot, { data: ShareResultData }>(({ data }, ref) => {
  const isAchievement = data.mode === 'achievement';

  return (
    <ViewShot ref={ref as any} options={{ format: 'png', quality: 1.0 }}>
      <View style={card.container}>
        {/* Fondo con gradiente visual via capas */}
        <View style={card.bgAccent} />

        {/* Logo / Marca */}
        <View style={card.logoRow}>
          <Text style={card.logoIcon}>⚽</Text>
          <Text style={card.logoText}>FuchoMX</Text>
        </View>

        {/* Contenido principal */}
        {isAchievement ? (
          <View style={card.achieveBlock}>
            <Text style={card.achieveEmoji}>{data.achievementEmoji ?? '🏆'}</Text>
            <Text style={card.achieveTitle}>¡Logro desbloqueado!</Text>
            <Text style={card.achieveName}>{data.achievementTitle}</Text>
            {data.achievementDesc ? (
              <Text style={card.achieveDesc}>{data.achievementDesc}</Text>
            ) : null}
          </View>
        ) : (
          <>
            <Text style={card.jornadaLabel}>
              🏆 Jornada {data.jornadaNumber} completada
            </Text>

            <View style={card.statsRow}>
              <View style={card.statBox}>
                <Text style={card.statValue}>{data.points ?? 0}</Text>
                <Text style={card.statLabel}>Puntos</Text>
              </View>
              {data.position ? (
                <View style={[card.statBox, card.statBoxAccent]}>
                  <Text style={[card.statValue, card.statValueAccent]}>#{data.position}</Text>
                  <Text style={[card.statLabel, { color: '#fff' }]}>Posición</Text>
                </View>
              ) : null}
              {(data.streak ?? 0) > 0 ? (
                <View style={card.statBox}>
                  <Text style={card.statValue}>{data.streak}🔥</Text>
                  <Text style={card.statLabel}>Racha</Text>
                </View>
              ) : null}
            </View>
          </>
        )}

        {/* Usuario y liga */}
        <View style={card.userRow}>
          <View style={card.avatar}>
            <Text style={card.avatarLetter}>{data.userName.charAt(0).toUpperCase()}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={card.userName}>{data.userName}</Text>
            {data.leagueName ? (
              <Text style={card.leagueName} numberOfLines={1}>📍 {data.leagueName}</Text>
            ) : null}
          </View>
          {data.leagueCode ? (
            <View style={card.codeBox}>
              <Text style={card.codeLabel}>Únete</Text>
              <Text style={card.codeValue}>{data.leagueCode}</Text>
            </View>
          ) : null}
        </View>

        {/* Hashtags */}
        <Text style={card.hashtags}>#FuchoMX #FuchoQuiniela</Text>
      </View>
    </ViewShot>
  );
});

// ─── Componente principal ─────────────────────────────────
export default function ShareResultCard({ data, onClose }: Props) {
  const shotRef = useRef<any>(null);
  const { showToast } = useToast();

  const buildShareText = (): string => {
    if (data.mode === 'achievement') {
      return [
        `${data.achievementEmoji ?? '🏆'} ¡Acabo de desbloquear un logro en FuchoMX!`,
        `🎖️ ${data.achievementTitle}`,
        data.achievementDesc ? `"${data.achievementDesc}"` : '',
        data.leagueCode ? `\n¡Únete: código ${data.leagueCode}` : '',
        '\n#FuchoMX #FuchoQuiniela',
      ].filter(Boolean).join('\n');
    }

    return [
      `🏆 Jornada ${data.jornadaNumber ?? '?'} completada!`,
      `📊 ${data.points ?? 0} puntos · Posición #${data.position ?? '?'} en ${data.leagueName ?? 'FuchoMX'}`,
      (data.streak ?? 0) > 0 ? `🔥 Racha: ${data.streak} jornadas` : '',
      data.leagueCode ? `¡Únete: código ${data.leagueCode}` : '',
      '#FuchoMX #FuchoQuiniela',
    ].filter(Boolean).join('\n');
  };

  const handleShare = async () => {
    try {
      // 1. Intenta capturar imagen con ViewShot
      const uri: string = await shotRef.current.capture();
      const canShare = await Sharing.isAvailableAsync();

      if (canShare) {
        await Sharing.shareAsync(uri, {
          mimeType: 'image/png',
          dialogTitle: 'Compartir resultado FuchoMX',
        });
      } else {
        // Fallback: compartir solo texto
        await Share.share({ message: buildShareText() });
      }
    } catch (_err) {
      // Si falla la captura, compartir texto plano
      try {
        await Share.share({ message: buildShareText() });
      } catch (e2) {
        showToast('error', 'No se pudo compartir. Intenta de nuevo.');
      }
    }
  };

  const handleTextShare = async () => {
    try {
      await Share.share({ message: buildShareText() });
    } catch (_) {}
  };

  return (
    <View style={modal.overlay}>
      <View style={modal.sheet}>

        {/* Tarjeta visual captureable */}
        <VisualCard ref={shotRef} data={data} />

        {/* Acciones */}
        <View style={modal.actions}>
          <TouchableOpacity style={modal.btnShare} onPress={handleShare} activeOpacity={0.8}>
            <Text style={modal.btnShareTxt}>📤 Compartir imagen</Text>
          </TouchableOpacity>
          <TouchableOpacity style={modal.btnText} onPress={handleTextShare} activeOpacity={0.8}>
            <Text style={modal.btnTextTxt}>💬 Solo texto</Text>
          </TouchableOpacity>
          {onClose && (
            <TouchableOpacity style={modal.btnClose} onPress={onClose} activeOpacity={0.7}>
              <Text style={modal.btnCloseTxt}>Cerrar</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    </View>
  );
}

// ─── Estilos tarjeta ──────────────────────────────────────
const card = StyleSheet.create({
  container: {
    width: 320,
    backgroundColor: '#0D0D0D',
    borderRadius: 20,
    padding: 20,
    borderWidth: 1.5,
    borderColor: '#DC143C44',
    overflow: 'hidden',
  },
  bgAccent: {
    position: 'absolute', top: -40, right: -40,
    width: 150, height: 150, borderRadius: 75,
    backgroundColor: '#DC143C18',
  },
  logoRow: {
    flexDirection: 'row', alignItems: 'center',
    gap: 8, marginBottom: 18,
  },
  logoIcon: { fontSize: 22 },
  logoText: {
    color: '#DC143C', fontSize: 18, fontWeight: '900',
    letterSpacing: 1,
  },

  jornadaLabel: {
    color: '#FFFFFF', fontSize: 15, fontWeight: '700',
    marginBottom: 16,
  },

  statsRow: {
    flexDirection: 'row', gap: 10, marginBottom: 18,
  },
  statBox: {
    flex: 1, backgroundColor: '#1A1A1A',
    borderRadius: 12, padding: 12,
    alignItems: 'center', borderWidth: 1, borderColor: '#222',
  },
  statBoxAccent: {
    backgroundColor: '#DC143C', borderColor: '#DC143C',
  },
  statValue: {
    color: '#FFF', fontSize: 22, fontWeight: '800',
  },
  statValueAccent: { color: '#FFF' },
  statLabel: {
    color: '#888', fontSize: 10, marginTop: 2, fontWeight: '500',
  },

  achieveBlock: {
    alignItems: 'center', paddingVertical: 12, marginBottom: 16,
  },
  achieveEmoji: { fontSize: 52, marginBottom: 8 },
  achieveTitle: {
    color: '#DC143C', fontSize: 13, fontWeight: '700',
    letterSpacing: 0.5, marginBottom: 6,
  },
  achieveName: {
    color: '#FFF', fontSize: 18, fontWeight: '800',
    textAlign: 'center',
  },
  achieveDesc: {
    color: '#888', fontSize: 12, textAlign: 'center',
    marginTop: 6, lineHeight: 18,
  },

  userRow: {
    flexDirection: 'row', alignItems: 'center',
    gap: 10, marginBottom: 14,
    backgroundColor: '#111', borderRadius: 12,
    padding: 10, borderWidth: 1, borderColor: '#1E1E1E',
  },
  avatar: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: '#DC143C',
    alignItems: 'center', justifyContent: 'center',
  },
  avatarLetter: { color: '#FFF', fontSize: 16, fontWeight: '800' },
  userName: { color: '#FFF', fontSize: 13, fontWeight: '700' },
  leagueName: { color: '#888', fontSize: 11, marginTop: 2 },

  codeBox: {
    alignItems: 'center', backgroundColor: '#DC143C22',
    borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6,
    borderWidth: 1, borderColor: '#DC143C55',
  },
  codeLabel: { color: '#DC143C', fontSize: 9, fontWeight: '700' },
  codeValue: { color: '#FFF', fontSize: 14, fontWeight: '900', letterSpacing: 1 },

  hashtags: {
    color: '#333', fontSize: 10, textAlign: 'center',
    letterSpacing: 0.5,
  },
});

// ─── Estilos modal ────────────────────────────────────────
const modal = StyleSheet.create({
  overlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.85)',
    alignItems: 'center', justifyContent: 'center',
    zIndex: 999,
  },
  sheet: {
    alignItems: 'center', padding: 20,
    backgroundColor: '#0D0D0D',
    borderRadius: 24, borderWidth: 1, borderColor: '#1E1E1E',
    marginHorizontal: 16,
  },
  actions: {
    width: 320, marginTop: 16, gap: 10,
  },
  btnShare: {
    backgroundColor: '#DC143C', borderRadius: 14,
    paddingVertical: 14, alignItems: 'center',
  },
  btnShareTxt: { color: '#FFF', fontSize: 15, fontWeight: '700' },
  btnText: {
    backgroundColor: '#1A1A1A', borderRadius: 14,
    paddingVertical: 12, alignItems: 'center',
    borderWidth: 1, borderColor: '#333',
  },
  btnTextTxt: { color: '#CCC', fontSize: 14, fontWeight: '600' },
  btnClose: { alignItems: 'center', paddingVertical: 10 },
  btnCloseTxt: { color: '#555', fontSize: 13 },
});
