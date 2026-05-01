# PRD - Quiniela Liga MX App

## Problema Original
Aplicación móvil multiplataforma (iOS/Android) de pool de fútbol con dos modalidades: Quiniela Tradicional y Fantasy Fútbol, basada en Liga MX.

## Usuarios Objetivo
- Fanáticos de la Liga MX que quieren competir con amigos
- Grupos de amigos que hacen quinielas informales
- Usuarios que quieren probar su conocimiento del fútbol

## Requisitos Core
1. Autenticación: Registro, login, JWT, perfil de usuario
2. Quiniela Tradicional: Predecir resultados, puntos, tabla de posiciones
3. Fantasy Fútbol: Crear equipo, puntuación basada en rendimiento real
4. Ligas Privadas: Crear/unirse con código de 6 caracteres (ambos modos)
5. Datos Reales: Liga MX - equipos, jugadores, jornadas
6. Gamificación: Logros y rachas
7. Plan Gratuito: Límites (1 liga por usuario, max 25 miembros)
8. Onboarding: Flujo de bienvenida para usuarios nuevos

## Arquitectura
- **Frontend**: Expo (React Native) + Expo Router
- **Backend**: FastAPI (Python) + Motor (async MongoDB)
- **DB**: MongoDB
- **Auth**: JWT + bcrypt
- **API**: Centralizada en `frontend/app/lib/api.ts`

---

## Lo Implementado

### Sesión Inicial
- Sistema completo de autenticación (JWT, bcrypt, registro, login)
- Modelos MongoDB: usuarios, equipos, jornadas, partidos, jugadores
- Seed de 18 equipos Liga MX + jugadores (378 total)
- Endpoints de jornadas con transición automática de estado por fechas
- Sistema de ligas privadas (Quiniela + Fantasy) con código de 6 chars
- Pantallas: Login, Registro, Recuperación, Home, Rankings, Perfil
- Pantalla de predicciones Quiniela
- Navegación con Expo Router + tabs

### Bug Fixes Críticos
- **Auth 401 en móvil**: Centralización de Axios + interceptors en `lib/api.ts`
- **Quiniela atascada en Jornada 1**: Sistema de progresión automática por fechas
- **Jornada auto-avanzando con datos mock**: Auto-advance ahora requiere que `end_date` haya pasado además de que todos los partidos estén terminados (fix 2026-04)
- **Fantasy Lineup no guardaba**: submitLineup ahora usa jornada cacheada del mount (no re-fetch), detección de duplicados, pantalla "ya enviaste", verificación de equipo existente (fix 2026-04)

### Datos Reales Liga MX
- Script de seed con equipos y jugadores reales (`real_liga_mx_data.py`)
- Endpoint `POST /api/admin/seed-real-data`

### Gamificación (Logros y Rachas)
- Backend: Definición, asignación y tracking de logros + rachas
- Pantalla `profile/achievements.tsx`
- Widget `StreakWidget` en home
- Toast `AchievementToast` para notificaciones en tiempo real

### Feature: Onboarding + Límites Plan Gratuito (Feb 2026)
- Frontend: `app/onboarding/index.tsx` - Pantalla de bienvenida
- Frontend: `app/profile/plan.tsx` - Pantalla "Tu Plan" (free tier)
- Backend: Límite 1 liga por usuario (owner) con mensaje informativo
- Backend: Límite 25 miembros por liga con verificación de capacidad
- Backend: `max_members` en schema de `private_leagues`
- Backend: Nuevo endpoint `GET /api/leagues/{id}/availability`
- Backend: `my-leagues` ahora retorna `max_members` e `is_full`
- Frontend: `leagues.tsx` muestra `👥 X/25`, badge "LLENA", barra de progreso

---

### Sesión Abril 2026 — UI/UX Mejoras
- **Sponsors Config**: `app/config/sponsors.ts` centralizado con sistema de niveles Oro/Plata/Bronce; integrado en Home, Perfil, Logros, Plan
- **MI ESTADÍSTICA**: Sección nueva en Perfil con grid 2 columnas: puntos, jornadas, mejor jornada, win rate, aciertos, FuchoOnce, mejor posición
- **Branding FuchoMX**: Logo/icono aplicado globalmente en Login, Registro, Onboarding, App Icon
- **Datos reales Liga MX**: Pull de GitHub + re-seed con URLs TheSportsDB (escudos reales)
- **Endpoint stats**: `GET /api/stats/my` — agrega datos de predicciones, fantasy, ligas

### Sesión Abril 2026 (cont.) — Welcome Screen + Empty States
- **P3 Welcome Screen**: `/(auth)/welcome.tsx` — pantalla post-registro con nombre en rojo, botón "Crear mi liga" y "Unirme a una liga", link "Explorar primero"
- **P4 Empty State Ligas**: `leagues.tsx` mejorado con emoji 🏟️, texto contextual, botón rojo "Crear liga", link "Unirme a una liga"
- **P2 Dark Mode**: Verificación visual de todas las pantallas solicitadas — todas respetan paleta #000000/#DC143C correctamente

### Sesión Abril 2026 — Bug Crítico Backend: Quiniela Submit
- **FIXED quiniela/submit**: Validación cambiada de `start_at < now` a `status in ['live','finished']`. Los partidos con fechas pasadas pero status='scheduled' YA NO bloquean el submit.
- **FIXED seed-season** (ambos endpoints): Ahora usan `ACTIVE_WEEK=11` con fechas relativas a HOY:
  - Jornadas 1-10: pasadas (finished), matches status=finished
  - Jornada 11: activa (in_progress), matches status=scheduled, fechas esta semana
  - Jornadas 12-17: futuras (upcoming), matches status=scheduled
- **Ejecutado seed-season**: DB regenerada. Jornada 11 tiene 9 partidos del 15-22 abril 2026.
- **Verificado con curl**: 200 OK submit + 400 correcto para partido 'finished'
- **FIXED register.tsx**: Botón atrás ← movido FUERA del ScrollView (era position:absolute dentro causando fallos touch en móvil). Ambos botones usan `router.replace('/(auth)/login')`
- **FIXED plan.tsx**: Archivo tenía DOS export default completos — el segundo con sección "🔒 Próximamente Premium". Reescrito con solo la versión correcta (149 líneas, 100% gratuito, sin Premium)
- **FIXED quiniela/index.tsx**: `ShareResultCard` onClose ahora ejecuta `router.replace('/quiniela/rankings')` — redirige a rankings al cerrar la tarjeta
- **FIXED fantasy/lineup.tsx**: Alert de éxito dice "✅ ¡Alineación Guardada!" con botón "Ver Rankings" → `router.replace('/fantasy/rankings')`
- **Validado con testing agent**: 5/5 tests pasados — BUG1 ✅, BUG2 ✅, BUG3 ✅, flujo Quiniela ✅, Perfil→Plan ✅

### Sesión Abril 2026 — Bracket Interactivo de Liguilla
- **NUEVO `GET /api/liguilla/bracket`**: Retorna los 8 equipos clasificados (provisionales) con `name`, `short_name`, `shield_url`, `position` y la estructura de cuartos de final. is_provisional=true hasta fin de J17.
- **NUEVO `POST /api/liguilla/bracket/submit`**: Guarda predicciones del bracket (cuartos_picks, semis_picks, champion).
- **NUEVO `bracket.tsx`**: UI interactiva de bracket con fondo `#090909`, bordes `#E63946`, escudos reales, badge Provisional, sistema de picks progresivo (Cuartos→Semis→Final), botón "GUARDAR MI BRACKET" en rojo.
- **NUEVO `bracket-results.tsx`**: Pantalla de resultados/estado del bracket guardado.
- **ACTUALIZADO `home.tsx`**: Card 🏆 "BRACKET DE LIGUILLA" — "Predice al campeón del Clausura 2026" que navega a `/quiniela/bracket`.
- **DATOS REALES CLAUSURA 2026**: `real_liga_mx_data.py` actualizado con fixtures reales de La Liga MX Clausura 2026 (J1-J17). `ACTIVE_WEEK=13`, jornada activa 18-25 abril 2026.
- **VERIFICADO** (Abril 2026): Todos los 5 puntos del checklist del usuario pasados. Screenshots tomados de home card, bracket vacío, bracket con selección, bracket completo con botón GUARDAR.

### Sesión Abril 2026 — Compartir Bracket + ESPN en Vivo
- **Compartir Bracket (Feature 1)**: Agregado `captureRef` (react-native-view-shot) + `expo-sharing`. BracketShareCard off-screen con header rojo, cuartos con escudos, semis, campeón, footer "fuchomx.mx". Botón "📤 Compartir mi bracket" aparece tras guardar. Texto: "Mi bracket del Clausura 2026 🏆 Mi campeón: [equipo] #FuchoMX #LigaMX #Clausura2026".
- **ESPN API en Vivo (Feature 2)**: Backend ahora llama a `site.api.espn.com/apis/v2/sports/soccer/mex.1/standings`. Cache de 1 hora, fallback al hardcode. `is_provisional: false` cuando ESPN responde. Tabla actual: GDL 31pts, CAZ 28pts, PAC 28pts, PUM 27pts, TOL 27pts, TIG 20pts, AME 19pts, ATL 19pts.
- **`setSaved(true)`**: Al cargar bracket con predicción previa, el botón Compartir aparece automáticamente.
- **Verificado**: Screenshots de share card, botones GUARDAR + Compartir, curl ESPN en vivo confirmado.

### Sesión Mayo 2026 — Servicios de Datos en Vivo (scores + player_stats)
- **`/app/backend/services/scores_service.py`** (NUEVO): Obtiene resultados de partidos desde 365Scores API (`webws.365scores.com`). Normalización de 18+ nombres de equipos. Fallback a ESPN API. Actualiza `db.matches` con `home_score`, `away_score`, `status`.
- **`/app/backend/services/player_stats_service.py`** (NUEVO): Stats de jugadores desde ESPN Summary API. 185 jugadores por jornada. Calcula `goals`, `assists`, `yellow_cards`, `red_cards`, `saves`, `own_goals`, `is_mvp`, minutos estimados. Guarda en `db.player_match_stats`.
- **`POST /api/admin/process-jornada/{jornada_id}`** (NUEVO): Orquestador completo — scores + quiniela_points + player_stats + fantasy_points + achievements. Retorna `{scores_updated, quiniela_updated, player_stats_saved, fantasy_updated, achievements_awarded}`.
- **Auto-proceso en `GET /api/jornadas/current`** (ACTUALIZADO): Cuando una jornada expira (end_date < now) y `processed=False`, llama automáticamente a `_process_jornada_core()` antes de avanzar a la siguiente jornada.
- **Verificado con datos REALES Jornada 13**: `9/9 partidos actualizados` (GDL 5-0 PUE, MTY 1-3 PAC, etc.), `185 jugadores` con stats reales de ESPN, auto-proceso confirmado.
- **Dependencias instaladas**: `requests==2.32.5`, `beautifulsoup4==4.14.3`, `lxml==6.1.0`

### Sesión Mayo 2026 — Widget EN VIVO + Fantasy Results + FBref
- **BUG CRÍTICO RESUELTO**: Todos los estilos del widget "EN VIVO" en `home.tsx` faltaban completamente del StyleSheet (`liveSection`, `liveDot`, `liveLabel`, `liveCount`, `liveMatch`, `liveScore`, `liveTime`, `liveMatchHome`, `liveMatchAway`, `liveScoreText`). Añadidos todos con diseño oscuro/rojo.
- **BACKEND FALLBACK DB**: `GET /api/jornadas/current/live-scores` ahora cae al `db.matches` cuando 365Scores retorna 0 juegos (no hay Liga MX ese día). `source: "db_fallback"` indica este modo.
- **MVP BADGE MEJORADO**: `results.tsx` — badge antes era `#FFD70022` (casi invisible). Ahora es `backgroundColor: '#E63946'` (rojo sólido) + `color: '#FFD700'` (dorado). Badge separado en `mvpBadge` (View) + `mvpBadgeText` (Text).
- **FBREF MINUTOS**: `player_stats_service.py` — nueva función `_get_fbref_minutes(home, away, date)` consulta `fbref.com/en/comps/31/schedule/Liga-MX-Scores-and-Fixtures`, encuentra el match report y extrae minutos exactos de sustitución. Se activa solo cuando ESPN retorna estimados (65/25 min). `minutes_source` field trackea el origen del dato.
- **VERIFICADO con screenshots**: EN VIVO muestra Pumas 1-0 Atlas (67') y Toluca 2-1 AtlSL (88'). Fantasy Results: Demo FC Estrella 71pts, Memo Ochoa, Álvaro Fidalgo ⭐MVP (16pts: doblete+asistencias), Quiñones, todos con minutos reales (45, 55, 62, 73, 82, 90).

### P0 (Crítico - Próximo)
- COMPLETADO: Bracket Interactivo de Liguilla ✅

### P1 (Alta Prioridad)
- Integración API-Football: datos en vivo de partidos, resultados, estadísticas de jugadores
- Live Standings Scraping: `GET /api/liguilla/bracket` → scraping de `ligamx.net/cancha/posiciones` para top 8 real

### P2 (Media Prioridad)  
- Notificaciones push (próximo partido, resultados)
- Compartir resultados en redes sociales
- Historial de temporadas
- Scraping de posiciones reales para el bracket de Liguilla

### P3 (Baja Prioridad)
- Email real para recuperación de contraseña (actualmente mock)
- Refactoring: Dividir `server.py` (>3200 líneas) en módulos con APIRouter
- Tests automatizados frontend (Playwright)
- Fix timing issue: display_name muestra "Usuario" brevemente en web preview tras registro (no afecta móvil)
