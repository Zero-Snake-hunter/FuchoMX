/**
 * sponsors.ts — Configuración central de patrocinadores de FuchoMX
 *
 * INSTRUCCIONES PARA ACTIVAR UN PATROCINADOR:
 *   1. Coloca el logo en: assets/images/sponsors/<nombre>.png
 *   2. Cambia activo: false → true
 *   3. Rellena marca, logo y los campos opcionales (cta_texto, cta_url)
 *
 * NIVELES:
 *   🥇 ORO   — presencia principal (torneo, splash, logros)
 *   🥈 PLATA — presencia por jornada específica
 *   🥉 BRONCE — presencia secundaria (perfil, aliados)
 */

export type Sponsor = {
  activo: boolean;
  nombre?: string;
  marca: string;
  logo: any;           // require('../assets/images/sponsors/xxx.png') | null
  cta_texto?: string;
  cta_url?: string;
};

export type JornadaSponsor = {
  activo: boolean;
  marca: string;
  logo: any;
  cta_url?: string;
};

export type Aliado = {
  nombre: string;
  url: string;
  logo: any;
};

export const SPONSORS = {
  /**
   * 🥇 ORO — patrocinador principal de la temporada
   */
  oro: {
    /** Nombre del torneo mostrado en Home y pantallas de Quiniela */
    torneo: {
      activo: false,
      nombre: 'Copa FuchoMX',     // → cambiar a "Copa Corona" al activar
      marca: '',                   // nombre del patrocinador
      logo: null as any,           // require('../../assets/images/sponsors/oro_torneo.png')
    } as Sponsor & { nombre: string },

    /** Banner en la pantalla Home (debajo del saludo) */
    splash: {
      activo: false,
      marca: '',
      logo: null as any,           // require('../../assets/images/sponsors/oro_splash.png')
      cta_texto: '',               // "Ver promoción →"
      cta_url: '',                 // "https://..."
    } as Sponsor,

    /** Pie de patrocinio en pantalla de Logros y Rachas */
    logros: {
      activo: false,
      marca: '',
      logo: null as any,           // require('../../assets/images/sponsors/oro_logros.png')
    } as Sponsor,
  },

  /**
   * 🥈 PLATA — patrocinadores por jornada
   * Estructura: { [jornada_id]: JornadaSponsor }
   * Ejemplo:
   *   "jornada_1": { activo: true, marca: "Gatorade", logo: null, cta_url: "https://..." }
   */
  plata: {
    jornadas: {} as Record<string, JornadaSponsor>,
  },

  /**
   * 🥉 BRONCE — presencia secundaria
   */
  bronce: {
    /** Pequeño badge bajo el avatar del usuario en Perfil */
    badge_perfil: {
      activo: false,
      marca: '',
      logo: null as any,           // require('../../assets/images/sponsors/bronce_badge.png')
    } as Sponsor,

    /** Pie de patrocinio en sección de Logros */
    logros: {
      activo: false,
      marca: '',
    } as Pick<Sponsor, 'activo' | 'marca'>,

    /**
     * Lista de aliados mostrada en la pantalla Tu Plan
     * Ejemplo:
     *   { nombre: "Sisolar", url: "https://sisolar.com", logo: null }
     *   { nombre: "Rolcar",  url: "https://rolcar.com",  logo: null }
     */
    aliados: [] as Aliado[],
  },
};

/**
 * Helper — devuelve el nombre del torneo (con o sin patrocinador)
 */
export const getNombreTorneo = (): string => {
  const t = SPONSORS.oro.torneo;
  if (t.activo && t.nombre) return t.nombre;
  return 'FUCHOQUINIELA';
};
