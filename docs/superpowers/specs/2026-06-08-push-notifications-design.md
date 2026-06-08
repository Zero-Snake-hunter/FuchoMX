# Push Notifications — FuchoMX
**Fecha:** 2026-06-08
**Autor:** Jorge Alba / Claude Code

---

## Objetivo

Avisar a los usuarios en dos momentos críticos de cada jornada:

1. **Apertura** — cuando Jorge activa la jornada: "Ya puedes hacer tus picks"
2. **Recordatorio** — X horas antes del primer partido: "Última oportunidad, el partido arranca en X horas"

El recordatorio es el más crítico: una vez que arranca el primer partido los picks se cierran y el usuario pierde la jornada.

---

## Audiencia por evento

| Evento | Destinatarios |
|--------|--------------|
| Apertura de jornada | Todos los usuarios con push token registrado |
| Recordatorio previo al partido | Solo usuarios que **no** han enviado picks para esa jornada |

---

## Arquitectura

### Servicio de push (nuevo)

`backend/services/push_service.py`

Módulo con dos funciones públicas:

- `notify_jornada_open(jornada: dict)` — envía notificación a todos los tokens registrados
- `notify_jornada_reminder(jornada: dict)` — consulta quién no ha enviado picks y envía solo a ellos

Internamente llama a la **Expo Push API** (`https://exp.host/--/api/v2/push/send`) en batches de hasta 100 tokens (límite del API). Usa `httpx` (ya disponible en FastAPI). No gestiona recibos de entrega en esta versión.

### Registro de token (frontend → backend)

**Endpoint nuevo:** `POST /api/auth/push-token`
- Autenticado (JWT)
- Body: `{ "token": "ExponentPushToken[xxxx]" }`
- Upsert: agrega el token al array `push_tokens` del usuario si no existe ya
- Un usuario puede tener múltiples tokens (varios dispositivos)

**Frontend:** nuevo hook `usePushNotifications` que se ejecuta al iniciar sesión:
1. Solicita permiso con `expo-notifications`
2. Obtiene el Expo Push Token
3. Hace POST al endpoint anterior
4. Guarda el token en AsyncStorage para no repetir el registro en cada sesión

---

## Cambios en MongoDB

### Colección `users`

```json
{
  "push_tokens": ["ExponentPushToken[xxxxxx]"]
}
```

Campo nuevo, array vacío por default. Índice no requerido (consultas siempre van por `_id` o `$exists`).

### Colección `jornadas`

```json
{
  "reminder_hours": 2,
  "notified_reminder": false
}
```

- `reminder_hours`: configurable por Jorge al activar/editar la jornada (default `2`)
- `notified_reminder`: flag para garantizar que el recordatorio se envía exactamente una vez

No se agrega flag para la notificación de apertura — se dispara sincrónicamente al activar, no necesita idempotencia.

---

## Flujo de Evento 1 — Apertura de jornada

```
Jorge hace POST /api/admin/reset-jornada  (activa jornada específica)
            ó  POST /api/admin/close-jornada (cierra actual y activa siguiente)
    ↓
admin.py setea is_active = True en la jornada
    ↓
llama push_service.notify_jornada_open(jornada)
    ↓
push_service busca users con push_tokens no vacío
    ↓
Expo Push API (batch ≤ 100 tokens por llamada)
    ↓
Notificación: "⚽ Jornada {N} abierta — Ya puedes hacer tus picks"
```

El envío es fire-and-forget: si falla, se loguea el error pero no bloquea la respuesta del endpoint admin.

---

## Flujo de Evento 2 — Recordatorio previo

```
Scheduler loop (cada 120 s cuando hay partidos programados hoy)
    ↓
¿Hay jornada activa con notified_reminder == False?
    ↓  Sí
¿now >= min(matches.start_at) - reminder_hours horas?   ← primer partido cronológico
    ↓  Sí
Consulta: users con push_tokens que NO tienen pick en quiniela_picks para esta jornada
    ↓
Expo Push API (batch)
    ↓
Notificación: "⏰ Última oportunidad — El partido arranca en {reminder_hours}h. ¿Ya hiciste tus picks?"
    ↓
jornada.notified_reminder = True  (evita re-envío)
```

---

## Configuración de `reminder_hours` desde admin

El endpoint de activación de jornada acepta el parámetro opcional `reminder_hours` (int, default `2`). Jorge puede sobreescribirlo al activar la jornada. Si necesita cambiar el valor después de activar, habrá un endpoint `PATCH /api/admin/jornada/{id}` que permita actualizar `reminder_hours` y resetear `notified_reminder = False`.

---

## Configuración de Expo (prerequisito)

Antes de que las notificaciones funcionen en builds de producción:

1. Configurar `projectId` en `app.json` → requiere cuenta EAS
2. Agregar plugin `expo-notifications` en `app.json`
3. Para Android: agregar `google-services.json` (FCM)
4. Para iOS: certificado APNS (solo si se distribuye en App Store)

En desarrollo con Expo Go, los tokens funcionan sin EAS.

---

## Lo que NO incluye esta versión

- Recibos de entrega (Expo Push Receipt API) — se puede agregar después si se detectan problemas de entrega
- Configuración de notificaciones por usuario (opt-out por tipo) — fuera de scope
- Notificaciones para resultados o logros — tema separado
- Soporte web — `expo-notifications` no funciona en web, se omite silenciosamente

---

## Archivos a crear / modificar

| Archivo | Cambio |
|---------|--------|
| `backend/services/push_service.py` | NUEVO |
| `backend/routers/auth.py` | Nuevo endpoint `/push-token` |
| `backend/routers/admin.py` | Llamada a push_service al activar jornada |
| `backend/scheduler.py` | Check de recordatorio en el loop |
| `backend/models.py` | `RegisterPushTokenRequest` |
| `frontend/hooks/usePushNotifications.ts` | NUEVO |
| `frontend/app.json` | Plugin expo-notifications + projectId |
