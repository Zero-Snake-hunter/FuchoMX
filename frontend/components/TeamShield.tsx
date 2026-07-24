import React, { useState } from 'react';
import { Image, ImageStyle, StyleProp } from 'react-native';

// Escudos que se sirven locales en vez de por URL remota — hoy solo Atlante,
// cuya URL de ESPN (a.espncdn.com) puede estar bloqueada por Cloudflare en
// producción. Si más equipos presentan el mismo problema, agrégalos aquí.
const LOCAL_SHIELDS: { [shortName: string]: any } = {
  ATE: require('../assets/shields/atlante.png'),
};

// Fallback cuando la URL remota falla en tiempo de carga (no solo cuando
// falta el dato) — antes esto se resolvía con defaultSource, que se queda
// pegado si la carga falla, no solo mientras carga.
const FALLBACK_LOGO = require('../assets/images/FuchoMX.png');

interface TeamShieldProps {
  shortName?: string;
  shieldUrl?: string;
  style?: StyleProp<ImageStyle>;
  resizeMode?: 'contain' | 'cover' | 'stretch' | 'center';
}

export default function TeamShield({ shortName, shieldUrl, style, resizeMode = 'contain' }: TeamShieldProps) {
  const [failed, setFailed] = useState(false);
  const localAsset = shortName ? LOCAL_SHIELDS[shortName] : undefined;

  if (localAsset) {
    return <Image source={localAsset} style={style} resizeMode={resizeMode} />;
  }
  if (failed || !shieldUrl) {
    return <Image source={FALLBACK_LOGO} style={style} resizeMode={resizeMode} />;
  }
  return (
    <Image
      source={{ uri: shieldUrl }}
      style={style}
      resizeMode={resizeMode}
      onError={() => setFailed(true)}
    />
  );
}
