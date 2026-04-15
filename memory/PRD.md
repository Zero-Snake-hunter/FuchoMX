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

### Sesión Abril 2026 (cont.) — Bug Fixes E2E + Branding
- **FIXED register.tsx**: Botón atrás ← movido FUERA del ScrollView (era position:absolute dentro causando fallos touch en móvil). Ambos botones usan `router.replace('/(auth)/login')`
- **FIXED plan.tsx**: Archivo tenía DOS export default completos — el segundo con sección "🔒 Próximamente Premium". Reescrito con solo la versión correcta (149 líneas, 100% gratuito, sin Premium)
- **FIXED quiniela/index.tsx**: `ShareResultCard` onClose ahora ejecuta `router.replace('/quiniela/rankings')` — redirige a rankings al cerrar la tarjeta
- **FIXED fantasy/lineup.tsx**: Alert de éxito dice "✅ ¡Alineación Guardada!" con botón "Ver Rankings" → `router.replace('/fantasy/rankings')`
- **Validado con testing agent**: 5/5 tests pasados — BUG1 ✅, BUG2 ✅, BUG3 ✅, flujo Quiniela ✅, Perfil→Plan ✅

## Backlog Priorizado

### P0 (Crítico - Próximo)
- Flujo onboarding completo para nuevos usuarios (pantalla de bienvenida en primer login)

### P1 (Alta Prioridad)
- Integración API-Football: datos en vivo de partidos, resultados, estadísticas de jugadores

### P2 (Media Prioridad)  
- Notificaciones push (próximo partido, resultados)
- Compartir resultados en redes sociales
- Historial de temporadas

### P3 (Baja Prioridad)
- Email real para recuperación de contraseña (actualmente mock)
- Refactoring: Dividir `server.py` en módulos con APIRouter
- Tests automatizados frontend (Playwright)
- Fix timing issue: display_name muestra "Usuario" brevemente en web preview tras registro (no afecta móvil)
