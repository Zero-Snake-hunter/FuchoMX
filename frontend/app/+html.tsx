import { ScrollViewStyleReset } from 'expo-router/html';
import type { PropsWithChildren } from 'react';

const SITE_URL = 'https://fucho.com.mx';
const TITLE = 'FuchoMX — Quiniela y Fantasy de Liga MX';
const DESCRIPTION =
  'La quiniela y el fantasy de Liga MX con tus cuates. Predice resultados, arma tu once de 11 jugadores reales y compite en ligas privadas. 100% gratis, sin apuestas.';
const OG_IMAGE = `${SITE_URL}/og-image.png`;

const SCHEMA_WEB_APP = JSON.stringify({
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  name: 'FuchoMX',
  description: 'Quiniela y fantasy de Liga MX, 100% gratis.',
  url: SITE_URL,
  applicationCategory: 'GameApplication',
  operatingSystem: 'Web, iOS, Android',
  offers: { '@type': 'Offer', price: '0', priceCurrency: 'MXN' },
});

const SCHEMA_ORG = JSON.stringify({
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: 'FuchoMX',
  url: SITE_URL,
  email: 'contacto@distrito.digital',
  foundingLocation: { '@type': 'Place', addressLocality: 'Aguascalientes', addressCountry: 'MX' },
});

const GLOBAL_CSS = `
  *, *::before, *::after { box-sizing: border-box; }
  html { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility; }
  :root { scroll-behavior: smooth; }
`;

export default function Root({ children }: PropsWithChildren) {
  return (
    <html lang="es-MX">
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />

        {/* Primary SEO */}
        <title>{TITLE}</title>
        <meta name="description" content={DESCRIPTION} />
        <link rel="canonical" href={`${SITE_URL}/`} />
        <meta name="robots" content="index, follow" />
        <meta name="theme-color" content="#090909" />

        {/* App meta */}
        <meta name="application-name" content="FuchoMX" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="FuchoMX" />

        {/* Open Graph */}
        <meta property="og:type" content="website" />
        <meta property="og:url" content={`${SITE_URL}/`} />
        <meta property="og:title" content={TITLE} />
        <meta property="og:description" content={DESCRIPTION} />
        <meta property="og:image" content={OG_IMAGE} />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />
        <meta property="og:locale" content="es_MX" />
        <meta property="og:site_name" content="FuchoMX" />

        {/* Twitter Card */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:site" content="@FuchoMX" />
        <meta name="twitter:title" content={TITLE} />
        <meta name="twitter:description" content={DESCRIPTION} />
        <meta name="twitter:image" content={OG_IMAGE} />

        {/* Barlow Condensed (display) + Barlow (body) — stadium energy, not on reflex-reject list */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,700;0,800;0,900;1,800&family=Barlow:wght@400;500;600&display=swap"
          rel="stylesheet"
        />

        {/* Global render quality */}
        <style dangerouslySetInnerHTML={{ __html: GLOBAL_CSS }} />

        {/* Structured data */}
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: SCHEMA_WEB_APP }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: SCHEMA_ORG }} />

        <ScrollViewStyleReset />
      </head>
      <body>{children}</body>
    </html>
  );
}
