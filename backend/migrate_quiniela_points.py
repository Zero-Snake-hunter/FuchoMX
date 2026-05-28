#!/usr/bin/env python3
"""
Migración: recalcula puntos de quiniela de +1 a +3 por acierto.

Los registros anteriores a este fix usaban 1 punto por predicción correcta
en lugar de 3 (reglas oficiales). Este script corrige points_log y
total_points de cada usuario.

Uso:
    python migrate_quiniela_points.py

Requiere: MONGO_URL en .env (igual que server.py).
Seguro de re-ejecutar: marca cada registro con migrated_v2=True y los omite
en ejecuciones posteriores.
"""

import asyncio
import os
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "quiniela_db")


async def migrate() -> None:
    client = AsyncIOMotorClient(MONGO_URL, tls=True, tlsAllowInvalidCertificates=True)
    db = client[DB_NAME]

    # Solo registros de QUINIELA aún no migrados
    logs = await db.points_log.find(
        {"source": "QUINIELA", "migrated_v2": {"$ne": True}}
    ).to_list(100_000)

    if not logs:
        print("✅ No hay registros pendientes — migración ya aplicada o sin datos.")
        return

    print(f"📋 {len(logs)} registros de QUINIELA por migrar (×1 → ×3)...")

    # Acumular el ajuste por usuario antes de tocar la DB
    user_diffs: dict = {}
    for log in logs:
        old_pts = log.get("points", 0)
        diff = old_pts * 2          # new = old * 3  →  diff = old * 2
        uid = log["user_id"]
        user_diffs[uid] = user_diffs.get(uid, 0) + diff

    # Actualizar points_log
    for log in logs:
        old_pts = log.get("points", 0)
        await db.points_log.update_one(
            {"_id": log["_id"]},
            {"$set": {"points": old_pts * 3, "migrated_v2": True}},
        )

    print(f"✅ {len(logs)} registros de points_log actualizados.")

    # Ajustar total_points de cada usuario
    updated_users = 0
    for uid, diff in user_diffs.items():
        if diff > 0:
            result = await db.users.update_one(
                {"_id": uid}, {"$inc": {"total_points": diff}}
            )
            if result.modified_count:
                updated_users += 1

    print(f"✅ {updated_users} usuarios con total_points ajustado.")
    print()
    print("🎉 Migración completada.")
    print("   Ejemplo: 3 aciertos → antes 3 pts, ahora 9 pts.")


if __name__ == "__main__":
    asyncio.run(migrate())
