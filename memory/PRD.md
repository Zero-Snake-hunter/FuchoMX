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

## Backlog Priorizado

### P0 (Crítico - Próximo)
- Flujo onboarding completo para nuevos usuarios (pantalla de bienvenida en primer login)

### P1 (Alta Prioridad)
- Integración API-Football: datos en vivo de partidos, resultados, estadísticas de jugadores
- Sistema de pagos PayPal: upgrade a Premium para más ligas

### P2 (Media Prioridad)  
- Plan Premium: > 1 liga, > 25 miembros
- Notificaciones push (próximo partido, resultados)
- Compartir resultados en redes sociales
- Historial de temporadas

### P3 (Baja Prioridad)
- Email real para recuperación de contraseña (actualmente mock)
- Refactoring: Dividir `server.py` en módulos con APIRouter
- Tests automatizados frontend (Playwright)
