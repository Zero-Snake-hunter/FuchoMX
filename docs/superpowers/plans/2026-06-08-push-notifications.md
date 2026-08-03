# Push Notifications — FuchoMX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enviar push notifications a usuarios de FuchoMX en dos momentos: apertura de jornada (todos) y recordatorio X horas antes del primer partido (solo quienes no han enviado picks).

**Architecture:** Nuevo módulo `push_service.py` llama a Expo Push API en batches. El endpoint de activación de jornada en `admin.py` dispara la notificación de apertura de forma asíncrona (fire-and-forget). El scheduler detecta cuándo se cumple la ventana de recordatorio y lo envía exactamente una vez, usando un flag `notified_reminder` en el documento de jornada.

**Tech Stack:** FastAPI + Motor (async MongoDB) + httpx (ya usado en el proyecto) + expo-notifications (~0.32.17, ya instalado en frontend) + Expo Push API.

---

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---------|--------|----------------|
| `backend/services/push_service.py` | CREAR | Cliente de Expo Push API |
| `backend/models.py` | MODIFICAR | Agregar `RegisterPushTokenRequest` |
| `backend/routers/auth.py` | MODIFICAR | `POST /api/auth/push-token` |
| `backend/routers/admin.py` | MODIFICAR | Param `reminder_hours`, fire notif 1, endpoint PATCH reminder |
| `backend/scheduler.py` | MODIFICAR | Check de recordatorio en el loop |
| `backend/tests/test_push_service.py` | CREAR | Unit tests con mocks |
| `frontend/hooks/usePushNotifications.ts` | CREAR | Pide permiso y registra token |
| `frontend/app/_layout.tsx` | MODIFICAR | Montar `PushNotificationRegistrar` |
| `frontend/app.json` | MODIFICAR | Plugin expo-notifications |

---

## Task 1: push_service.py — cliente de Expo Push API

**Files:**
- Create: `backend/services/push_service.py`
- Create: `backend/tests/test_push_service.py`

- [ ] **Step 1: Instalar pytest-asyncio** (necesario para unit tests async)

```bash
cd backend
pip install pytest-asyncio
```

- [ ] **Step 2: Escribir los tests que fallan**

Crear `backend/tests/test_push_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from bson import ObjectId



@pytest.mark.asyncio
async def test_send_batch_llama_expo_api():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("services.push_service.httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        from services.push_service import _send_batch
        await _send_batch(["ExponentPushToken[abc123]"], "Título", "Cuerpo")

        mock_client.post.assert_called_once()
        url, kwargs = mock_client.post.call_args[0][0], mock_client.post.call_args[1]
        assert url == "https://exp.host/--/api/v2/push/send"
        assert kwargs["json"][0]["to"] == "ExponentPushToken[abc123]"
        assert kwargs["json"][0]["title"] == "Título"


@pytest.mark.asyncio
async def test_notify_all_users_no_llama_api_sin_tokens():
    with patch("services.push_service.db") as mock_db:
        mock_db.users.find.return_value.to_list = AsyncMock(return_value=[])

        with patch("services.push_service._send_batch") as mock_send:
            from services.push_service import notify_all_users
            await notify_all_users("T", "B")
            mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_notify_users_without_picks_excluye_enviados():
    jornada_id = ObjectId()
    user_sin_picks = ObjectId()
    user_con_picks = ObjectId()

    with patch("services.push_service.db") as mock_db:
        mock_db.quiniela_selections.distinct = AsyncMock(return_value=[user_con_picks])
        mock_db.users.find.return_value.to_list = AsyncMock(return_value=[
            {"_id": user_sin_picks, "push_tokens": ["ExponentPushToken[zzz]"]}
        ])

        with patch("services.push_service._send_batch") as mock_send:
            from services.push_service import notify_jornada_reminder
            await notify_jornada_reminder(jornada_id, week_number=5, reminder_hours=2)

            query = mock_db.users.find.call_args[0][0]
            assert user_con_picks in query["_id"]["$nin"]
            mock_send.assert_called_once()
            tokens_enviados = mock_send.call_args[0][0]
            assert "ExponentPushToken[zzz]" in tokens_enviados


@pytest.mark.asyncio
async def test_send_batch_en_lotes_de_100():
    tokens = [f"ExponentPushToken[t{i}]" for i in range(250)]
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("services.push_service.httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        from services.push_service import notify_all_users
        with patch("services.push_service.db") as mock_db:
            mock_db.users.find.return_value.to_list = AsyncMock(return_value=[
                {"push_tokens": tokens}
            ])
            await notify_all_users("T", "B")

        # 250 tokens → 3 llamadas: 100 + 100 + 50
        assert mock_client.post.call_count == 3
```

- [ ] **Step 3: Ejecutar tests — deben fallar**

```bash
cd backend
python -m pytest tests/test_push_service.py -v
```

Salida esperada: `ImportError` o `ModuleNotFoundError: No module named 'services.push_service'`

- [ ] **Step 4: Crear `backend/services/push_service.py`**

```python
import logging
from typing import List

import httpx
from bson import ObjectId

from database import db

logger = logging.getLogger(__name__)

_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_BATCH_SIZE = 100


async def _send_batch(tokens: List[str], title: str, body: str) -> None:
    messages = [
        {"to": t, "title": title, "body": body, "sound": "default"}
        for t in tokens
    ]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_EXPO_PUSH_URL, json=messages)
            resp.raise_for_status()
        logger.info(f"✅ Push enviado: {len(tokens)} tokens")
    except Exception as exc:
        logger.error(f"❌ Expo Push error: {exc}")


async def _gather_tokens(query: dict) -> List[str]:
    users = await db.users.find(query, {"push_tokens": 1}).to_list(None)
    return [t for u in users for t in u.get("push_tokens", [])]


async def notify_all_users(title: str, body: str) -> None:
    tokens = await _gather_tokens({"push_tokens": {"$exists": True, "$ne": []}})
    if not tokens:
        logger.info("notify_all_users: sin tokens registrados")
        return
    for i in range(0, len(tokens), _BATCH_SIZE):
        await _send_batch(tokens[i : i + _BATCH_SIZE], title, body)


async def notify_jornada_open(week_number: int) -> None:
    await notify_all_users(
        title="⚽ FuchoMX — Jornada abierta",
        body=f"La Jornada {week_number} ya está abierta. ¡Haz tus picks ahora!",
    )


async def notify_jornada_reminder(
    jornada_id: ObjectId, week_number: int, reminder_hours: int
) -> None:
    already_picked = await db.quiniela_selections.distinct(
        "user_id", {"jornada_id": jornada_id}
    )
    tokens = await _gather_tokens({
        "push_tokens": {"$exists": True, "$ne": []},
        "_id": {"$nin": already_picked},
    })
    if not tokens:
        logger.info("notify_jornada_reminder: sin tokens para recordatorio")
        return
    for i in range(0, len(tokens), _BATCH_SIZE):
        await _send_batch(
            tokens[i : i + _BATCH_SIZE],
            title="⏰ FuchoMX — Última oportunidad",
            body=f"El primer partido de la Jornada {week_number} arranca en {reminder_hours}h. ¿Ya hiciste tus picks?",
        )
```

- [ ] **Step 5: Ejecutar tests — deben pasar**

```bash
cd backend
python -m pytest tests/test_push_service.py -v
```

Salida esperada:
```
PASSED tests/test_push_service.py::test_send_batch_llama_expo_api
PASSED tests/test_push_service.py::test_notify_all_users_no_llama_api_sin_tokens
PASSED tests/test_push_service.py::test_notify_users_without_picks_excluye_enviados
PASSED tests/test_push_service.py::test_send_batch_en_lotes_de_100
4 passed
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/push_service.py backend/tests/test_push_service.py
git commit -m "feat: add push_service with Expo Push API client"
```

---

## Task 2: Endpoint para registrar token de push

**Files:**
- Modify: `backend/models.py` (al final del archivo)
- Modify: `backend/routers/auth.py`

- [ ] **Step 1: Agregar `RegisterPushTokenRequest` a `backend/models.py`**

Al final del archivo (después de `BracketUpdateRequest`), agregar:

```python
# ── Push Notifications ────────────────────────────────────────────────────────

class RegisterPushTokenRequest(BaseModel):
    token: str
```

- [ ] **Step 2: Agregar endpoint en `backend/routers/auth.py`**

Primero agregar el import de models en el bloque de imports existente:

```python
from models import (
    RecoverPasswordRequest,
    RegisterPushTokenRequest,   # ← agregar esta línea
    TokenResponse,
    UserRegister,
    UserLogin,
    UserResponse,
    serialize_user,
)
```

Luego, al final del archivo agregar el endpoint:

```python
@router.post("/push-token")
async def register_push_token(
    request: RegisterPushTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    token = request.token.strip()
    if not token.startswith("ExponentPushToken["):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de push inválido. Debe empezar con 'ExponentPushToken['",
        )
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$addToSet": {"push_tokens": token}},
    )
    logger.info(f"Push token registrado para {current_user['email']}")
    return {"message": "Token registrado"}
```

- [ ] **Step 3: Verificar que el servidor levanta sin errores**

```bash
cd backend
uvicorn server:app --reload --port 8001
```

Salida esperada: servidor arranca, sin ImportError.
Detener con Ctrl+C.

- [ ] **Step 4: Prueba manual rápida (opcional si tienes el servidor corriendo)**

```bash
# Login primero para obtener token
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"tu@email.com","password":"tupassword"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Registrar push token
curl -X POST http://localhost:8001/api/auth/push-token \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"token":"ExponentPushToken[test123]"}'
```

Respuesta esperada: `{"message":"Token registrado"}`

- [ ] **Step 5: Commit**

```bash
git add backend/models.py backend/routers/auth.py
git commit -m "feat: add POST /api/auth/push-token to register Expo push token"
```

---

## Task 3: Notificación de apertura al activar jornada desde admin

**Files:**
- Modify: `backend/routers/admin.py`

Los cambios son en tres funciones: `reset_jornada`, `close_jornada`, y un nuevo endpoint PATCH.

- [ ] **Step 1: Agregar imports en `backend/routers/admin.py`**

Agregar al bloque de imports al inicio del archivo (después de los imports existentes):

```python
import asyncio
from services.push_service import notify_jornada_open
```

- [ ] **Step 2: Modificar `reset_jornada` — agregar `reminder_hours` y notificación**

Cambiar la firma de la función (línea ~296):

```python
# ANTES:
@router.post("/admin/reset-jornada")
async def reset_jornada(week: int = None, current_user: dict = Depends(get_admin_user)):

# DESPUÉS:
@router.post("/admin/reset-jornada")
async def reset_jornada(week: int = None, reminder_hours: int = 2, current_user: dict = Depends(get_admin_user)):
```

En el bloque `if week is not None:` (línea ~305), agregar los campos nuevos al `update_one` y la llamada a notify:

```python
# ANTES:
        await db.jornadas.update_one({"_id": target["_id"]}, {"$set": {
            "is_active": True, "status": "in_progress",
            "start_date": now, "end_date": now + timedelta(days=7)
        }})
        logger.info(f"Admin reset-jornada: jornada {week} activada directamente")
        return {"message": f"✅ Jornada {week} activada", "week_number": week, "jornada_id": str(target["_id"])}

# DESPUÉS:
        await db.jornadas.update_one({"_id": target["_id"]}, {"$set": {
            "is_active": True, "status": "in_progress",
            "start_date": now, "end_date": now + timedelta(days=7),
            "reminder_hours": reminder_hours, "notified_reminder": False,
        }})
        asyncio.create_task(notify_jornada_open(week))
        logger.info(f"Admin reset-jornada: jornada {week} activada directamente")
        return {"message": f"✅ Jornada {week} activada", "week_number": week, "jornada_id": str(target["_id"])}
```

En el bloque que avanza a `next_j` (línea ~332), hacer el mismo cambio:

```python
# ANTES:
    await db.jornadas.update_one({"_id": next_j["_id"]}, {"$set": {
        "is_active": True, "status": "in_progress",
        "start_date": now, "end_date": now + timedelta(days=7)
    }})
    logger.info(f"Admin reset-jornada: {closed_week} → {closed_week + 1}")
    return {
        "message": f"✅ Jornada {closed_week} cerrada → Jornada {closed_week + 1} activa",
        "closed_week": closed_week, "active_week": closed_week + 1, "jornada_id": str(next_j["_id"])
    }

# DESPUÉS:
    await db.jornadas.update_one({"_id": next_j["_id"]}, {"$set": {
        "is_active": True, "status": "in_progress",
        "start_date": now, "end_date": now + timedelta(days=7),
        "reminder_hours": reminder_hours, "notified_reminder": False,
    }})
    asyncio.create_task(notify_jornada_open(closed_week + 1))
    logger.info(f"Admin reset-jornada: {closed_week} → {closed_week + 1}")
    return {
        "message": f"✅ Jornada {closed_week} cerrada → Jornada {closed_week + 1} activa",
        "closed_week": closed_week, "active_week": closed_week + 1, "jornada_id": str(next_j["_id"])
    }
```

- [ ] **Step 3: Modificar `close_jornada` — agregar `reminder_hours` y notificación**

Cambiar la firma (línea ~343):

```python
# ANTES:
@router.post("/admin/quiniela/cerrar-jornada/{jornada_id}")
async def close_jornada(jornada_id: str, current_user: dict = Depends(get_admin_user)):

# DESPUÉS:
@router.post("/admin/quiniela/cerrar-jornada/{jornada_id}")
async def close_jornada(jornada_id: str, reminder_hours: int = 2, current_user: dict = Depends(get_admin_user)):
```

En el bloque `if next_jornada:` (línea ~363), agregar los campos y la notificación:

```python
# ANTES:
    if next_jornada:
        await db.jornadas.update_one({"_id": next_jornada["_id"]},
                                     {"$set": {"status": "upcoming", "is_active": True}})
        next_info = {"id": str(next_jornada["_id"]), "week_number": next_jornada["week_number"]}
        logger.info(f"Closed jornada {current_week}, activated jornada {current_week + 1}")

# DESPUÉS:
    if next_jornada:
        await db.jornadas.update_one({"_id": next_jornada["_id"]}, {"$set": {
            "status": "upcoming", "is_active": True,
            "reminder_hours": reminder_hours, "notified_reminder": False,
        }})
        asyncio.create_task(notify_jornada_open(next_jornada["week_number"]))
        next_info = {"id": str(next_jornada["_id"]), "week_number": next_jornada["week_number"]}
        logger.info(f"Closed jornada {current_week}, activated jornada {current_week + 1}")
```

- [ ] **Step 4: Agregar endpoint PATCH para ajustar `reminder_hours` después de activar**

Al final del archivo `admin.py`, agregar:

```python
@router.patch("/admin/jornada/{jornada_id}/reminder")
async def update_reminder_hours(
    jornada_id: str,
    reminder_hours: int,
    current_user: dict = Depends(get_admin_user),
):
    """Actualiza reminder_hours y resetea notified_reminder para reenviar el recordatorio."""
    try:
        jornada_oid = ObjectId(jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")

    result = await db.jornadas.update_one(
        {"_id": jornada_oid},
        {"$set": {"reminder_hours": reminder_hours, "notified_reminder": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    logger.info(f"Admin: reminder_hours de jornada {jornada_id} → {reminder_hours}h")
    return {"message": f"✅ Recordatorio ajustado a {reminder_hours}h antes del partido"}
```

- [ ] **Step 5: Verificar que el servidor levanta sin errores**

```bash
cd backend
uvicorn server:app --reload --port 8001
```

Sin ImportError ni SyntaxError. Detener con Ctrl+C.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/admin.py
git commit -m "feat: trigger push notification on jornada activation, add PATCH /admin/jornada/{id}/reminder"
```

---

## Task 4: Recordatorio automático en el scheduler

**Files:**
- Modify: `backend/scheduler.py`

- [ ] **Step 1: Agregar imports en `backend/scheduler.py`**

Agregar al bloque de imports existente (después de los imports actuales):

```python
from services.push_service import notify_jornada_reminder
```

La línea `from datetime import datetime, timedelta` ya está — `timedelta` se usa en el nuevo código.

- [ ] **Step 2: Agregar el check de recordatorio al inicio del loop**

En `_auto_update_scores`, justo después de `now = datetime.utcnow()` y antes de `games = await _fetch_365scores(...)`, insertar:

```python
        # ── Recordatorio de picks (se evalúa en cada ciclo) ───────────────────
        try:
            jornada_reminder = await db.jornadas.find_one(
                {"is_active": True, "notified_reminder": {"$ne": True}}
            )
            if jornada_reminder:
                first_match = await db.matches.find_one(
                    {"jornada_id": jornada_reminder["_id"], "status": "scheduled"},
                    sort=[("start_at", 1)],
                )
                if first_match and first_match.get("start_at"):
                    reminder_hours = jornada_reminder.get("reminder_hours", 2)
                    reminder_time = first_match["start_at"] - timedelta(hours=reminder_hours)
                    if now >= reminder_time:
                        week = jornada_reminder.get("week_number", "?")
                        await notify_jornada_reminder(
                            jornada_reminder["_id"], week, reminder_hours
                        )
                        await db.jornadas.update_one(
                            {"_id": jornada_reminder["_id"]},
                            {"$set": {"notified_reminder": True}},
                        )
                        logger.info(f"✅ Recordatorio enviado para jornada {week}")
        except Exception as exc:
            logger.error(f"❌ Error en check de recordatorio: {exc}")
        # ──────────────────────────────────────────────────────────────────────
```

El bloque completo del loop debe quedar así (solo el inicio, para ubicar):

```python
    while True:
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0,  minute=0,  second=0,  microsecond=0)
            today_end   = now.replace(hour=23, minute=59, second=59, microsecond=0)

            # ── Recordatorio de picks (se evalúa en cada ciclo) ───────────────────
            try:
                jornada_reminder = await db.jornadas.find_one(
                    {"is_active": True, "notified_reminder": {"$ne": True}}
                )
                if jornada_reminder:
                    first_match = await db.matches.find_one(
                        {"jornada_id": jornada_reminder["_id"], "status": "scheduled"},
                        sort=[("start_at", 1)],
                    )
                    if first_match and first_match.get("start_at"):
                        reminder_hours = jornada_reminder.get("reminder_hours", 2)
                        reminder_time = first_match["start_at"] - timedelta(hours=reminder_hours)
                        if now >= reminder_time:
                            week = jornada_reminder.get("week_number", "?")
                            await notify_jornada_reminder(
                                jornada_reminder["_id"], week, reminder_hours
                            )
                            await db.jornadas.update_one(
                                {"_id": jornada_reminder["_id"]},
                                {"$set": {"notified_reminder": True}},
                            )
                            logger.info(f"✅ Recordatorio enviado para jornada {week}")
            except Exception as exc:
                logger.error(f"❌ Error en check de recordatorio: {exc}")
            # ──────────────────────────────────────────────────────────────────────

            games = await _fetch_365scores(today_start, today_end)
            # ... resto del loop sin cambios
```

- [ ] **Step 3: Verificar que el servidor levanta sin errores**

```bash
cd backend
uvicorn server:app --reload --port 8001
```

Sin errores en los logs de startup. Detener con Ctrl+C.

- [ ] **Step 4: Commit**

```bash
git add backend/scheduler.py
git commit -m "feat: add reminder check to scheduler loop"
```

---

## Task 5: Frontend — registrar token de push al login

**Files:**
- Create: `frontend/hooks/usePushNotifications.ts`
- Modify: `frontend/app/_layout.tsx`
- Modify: `frontend/app.json`

- [ ] **Step 1: Agregar plugin de expo-notifications en `frontend/app.json`**

En la sección `"plugins"`, agregar `"expo-notifications"` después de `"expo-router"`:

```json
"plugins": [
  "expo-router",
  "expo-notifications",
  [
    "expo-splash-screen",
    {
      "image": "./assets/images/FuchoMX.png",
      "imageWidth": 200,
      "resizeMode": "contain",
      "backgroundColor": "#000"
    }
  ],
  "expo-web-browser"
],
```

- [ ] **Step 2: Crear carpeta hooks y el archivo `usePushNotifications.ts`**

Crear `frontend/hooks/usePushNotifications.ts`:

```typescript
import { useEffect } from 'react';
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

import api from '../app/lib/api';

const STORAGE_KEY = 'expo_push_token_sent';

export function usePushNotifications(authToken: string | null) {
  useEffect(() => {
    if (!authToken || Platform.OS === 'web') return;

    (async () => {
      try {
        const alreadySent = await AsyncStorage.getItem(STORAGE_KEY);
        if (alreadySent) return;

        const { status } = await Notifications.requestPermissionsAsync();
        if (status !== 'granted') return;

        const projectId =
          Constants.expoConfig?.extra?.eas?.projectId ?? undefined;
        const { data: pushToken } = await Notifications.getExpoPushTokenAsync({
          projectId,
        });

        await api.post('/api/auth/push-token', { token: pushToken });
        await AsyncStorage.setItem(STORAGE_KEY, pushToken);
      } catch (err) {
        // No lanzar error — push notifications son best-effort
        console.warn('[usePushNotifications]', err);
      }
    })();
  }, [authToken]);
}
```

> **Nota:** `projectId` puede quedar como `undefined` durante desarrollo con Expo Go. En builds de producción con EAS, setear el `projectId` en `app.json > extra > eas > projectId`. Ejecutar `npx eas-cli init` para obtenerlo.

- [ ] **Step 3: Modificar `frontend/app/_layout.tsx` para montar el registrador**

Agregar el import de `useAuth` y del hook, y crear el componente `PushNotificationRegistrar`:

```tsx
import { Stack } from 'expo-router';
import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { FantasyProvider } from './context/FantasyContext';
import * as SplashScreen from 'expo-splash-screen';
import { usePushNotifications } from '../hooks/usePushNotifications';

SplashScreen.preventAutoHideAsync();

function PushNotificationRegistrar() {
  const { token } = useAuth();
  usePushNotifications(token);
  return null;
}

export default function RootLayout() {
  console.log('🏗️ [RootLayout] Montando aplicación...');

  React.useEffect(() => {
    const timer = setTimeout(() => {
      SplashScreen.hideAsync();
      console.log('✅ [RootLayout] SplashScreen oculto');
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <AuthProvider>
      <FantasyProvider>
        <PushNotificationRegistrar />
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="onboarding" />
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(tabs)" />
        </Stack>
      </FantasyProvider>
    </AuthProvider>
  );
}
```

> **Importante:** Verificar que `AuthContext.tsx` exporta `useAuth` como export nombrado (la línea `export function AuthProvider` ya existe — buscar si `useAuth` también se exporta al fondo del archivo). Si solo existe como `const AuthContext`, agregar al final de `AuthContext.tsx`:
> ```typescript
> export function useAuth() {
>   const ctx = useContext(AuthContext);
>   if (!ctx) throw new Error('useAuth must be used within AuthProvider');
>   return ctx;
> }
> ```

- [ ] **Step 4: Levantar la app y verificar en Expo Go**

```bash
cd frontend
npx expo start
```

Pasos de verificación:
1. Abrir en Expo Go (iOS o Android)
2. Login con una cuenta
3. Revisar que aparece el diálogo de permiso de notificaciones
4. Aceptar el permiso
5. En los logs del servidor backend, verificar que aparece `Push token registrado para <email>`
6. En MongoDB, verificar `db.users.findOne({email: "..."})` — debe tener `push_tokens: ["ExponentPushToken[...]"]`

- [ ] **Step 5: Commit**

```bash
git add frontend/hooks/usePushNotifications.ts frontend/app/_layout.tsx frontend/app.json
git commit -m "feat: register Expo push token on login via usePushNotifications hook"
```

---

## Task 6: Prueba end-to-end del flujo completo

- [ ] **Step 1: Prueba de notificación de apertura**

Con el backend en Render (o local con ngrok), usar el token de admin:

```bash
# Activar jornada con reminder_hours personalizado (ej: 6h)
curl -X POST "https://tu-backend.onrender.com/api/admin/reset-jornada?week=14&reminder_hours=6" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Verificar en el dispositivo que llega la notificación: `"⚽ FuchoMX — Jornada abierta"`

- [ ] **Step 2: Prueba de recordatorio**

Simular que el tiempo de recordatorio ya pasó actualizando `start_at` de un partido en la DB a `now + 1 hora` y `reminder_hours = 2`:

```javascript
// En mongosh:
db.matches.updateOne(
  { status: "scheduled" },
  { $set: { start_at: new Date(Date.now() + 3600000) } }  // 1 hora desde ahora
)
db.jornadas.updateOne(
  { is_active: true },
  { $set: { reminder_hours: 2, notified_reminder: false } }
)
```

Esperar hasta 120s (próximo ciclo del scheduler). Verificar en logs: `✅ Recordatorio enviado para jornada X`.
Verificar que el recordatorio solo llega a usuarios SIN picks enviados para esa jornada.

- [ ] **Step 3: Push final**

```bash
git push
```

Render despliega automáticamente con los cambios.

---

## Prerequisitos para producción (EAS)

Si se quiere distribuir en App Store / Play Store:

1. Crear proyecto EAS: `cd frontend && npx eas-cli init`
2. Copiar el `projectId` generado en `frontend/app.json > extra > eas > projectId`
3. Para Android: `npx eas credentials` → generar FCM config
4. Para iOS: `npx eas credentials` → generar APNS certificate

Durante desarrollo con **Expo Go**, los tokens funcionan sin EAS — las notificaciones llegan normalmente.
