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
