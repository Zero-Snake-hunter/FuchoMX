import logging
from datetime import datetime

from database import db

logger = logging.getLogger(__name__)

QUINIELA_MISS_PENALTY = -1     # por partido sin pick
ONCE_MISS_PENALTY = -5         # por no guardar alineación
NEW_USER_BONUS_WINDOW = 3      # primeras N jornadas de cada usuario
NEW_USER_BONUS_MARGIN = 3      # puntos por encima del último lugar


async def _jornadas_elapsed_for_user(user: dict, jornada: dict) -> int:
    """
    Cuenta cuántas jornadas de esta competición (incluyendo la que se está
    cerrando) arrancaron desde que el usuario se registró. Se usa para saber
    si la jornada actual cae dentro de las primeras 3 jornadas del usuario
    (no las primeras 3 del torneo) — un usuario que se registró en J10
    sigue siendo "nuevo" en J10, J11 y J12.
    """
    created_at = user.get("created_at")
    if not created_at:
        return 0
    return await db.jornadas.count_documents({
        "competition": jornada.get("competition"),
        "week_number": {"$lte": jornada.get("week_number", 0)},
        "start_date": {"$gte": created_at},
    })


async def _apply_quiniela_penalty(jornada_obj_id, total_matches: int, all_users: list) -> int:
    """-1 punto por cada partido de la jornada sin pick al momento del cierre."""
    applied = 0
    for user in all_users:
        already = await db.points_log.find_one({
            "user_id": user["_id"], "jornada_id": jornada_obj_id,
            "source": "QUINIELA_PENALIZACION",
        })
        if already:
            continue

        picks = await db.quiniela_selections.count_documents({
            "user_id": user["_id"], "jornada_id": jornada_obj_id,
        })
        missing = total_matches - picks
        if missing <= 0:
            continue

        penalty = missing * QUINIELA_MISS_PENALTY
        await db.points_log.insert_one({
            "user_id": user["_id"], "jornada_id": jornada_obj_id,
            "source": "QUINIELA_PENALIZACION", "points": penalty,
            "matches_sin_pick": missing, "created_at": datetime.utcnow(),
        })
        await db.users.update_one({"_id": user["_id"]}, {"$inc": {"total_points": penalty}})
        applied += 1
    return applied


async def _apply_once_penalty(jornada_obj_id, all_users: list) -> int:
    """-5 puntos si el usuario no tiene alineación guardada al cierre de la jornada."""
    applied = 0
    for user in all_users:
        already = await db.points_log.find_one({
            "user_id": user["_id"], "jornada_id": jornada_obj_id,
            "source": "ONCE_PENALIZACION",
        })
        if already:
            continue

        team = await db.fantasy_teams.find_one({"user_id": user["_id"]})
        has_lineup = False
        if team:
            has_lineup = await db.fantasy_lineups.count_documents({
                "fantasy_team_id": team["_id"], "jornada_id": jornada_obj_id,
            }) > 0
        if has_lineup:
            continue

        await db.points_log.insert_one({
            "user_id": user["_id"], "jornada_id": jornada_obj_id,
            "source": "ONCE_PENALIZACION", "points": ONCE_MISS_PENALTY,
            "created_at": datetime.utcnow(),
        })
        await db.users.update_one(
            {"_id": user["_id"]}, {"$inc": {"fantasy_total_points": ONCE_MISS_PENALTY}}
        )
        applied += 1
    return applied


async def _apply_new_user_bonus(
    jornada_obj_id, jornada: dict, all_users: list, score_field: str, bonus_source: str
) -> int:
    """
    Empuje invisible para usuarios en sus primeras 3 jornadas: si tras los
    ajustes de esta jornada quedan en último lugar del ranking global
    (empatados o no), reciben lo necesario para quedar 3 puntos arriba del
    último lugar. No se expone como "bonus" — se suma directo al puntaje
    (fuente en points_log solo para trazabilidad/idempotencia interna).
    """
    if not all_users:
        return 0

    user_ids = [u["_id"] for u in all_users]
    fresh_users = await db.users.find({"_id": {"$in": user_ids}}).to_list(len(user_ids))
    if not fresh_users:
        return 0

    last_place_score = min(u.get(score_field, 0) for u in fresh_users)
    target = last_place_score + NEW_USER_BONUS_MARGIN

    applied = 0
    for user in fresh_users:
        current_score = user.get(score_field, 0)
        if current_score > last_place_score:
            continue

        already = await db.points_log.find_one({
            "user_id": user["_id"], "jornada_id": jornada_obj_id, "source": bonus_source,
        })
        if already:
            continue

        elapsed = await _jornadas_elapsed_for_user(user, jornada)
        if elapsed == 0 or elapsed > NEW_USER_BONUS_WINDOW:
            continue

        boost = target - current_score
        if boost <= 0:
            continue

        await db.points_log.insert_one({
            "user_id": user["_id"], "jornada_id": jornada_obj_id,
            "source": bonus_source, "points": boost, "created_at": datetime.utcnow(),
        })
        await db.users.update_one({"_id": user["_id"]}, {"$inc": {score_field: boost}})
        applied += 1
    return applied


async def apply_jornada_close_adjustments(jornada: dict, matches: list) -> dict:
    """
    Se ejecuta cuando TODOS los partidos de la jornada ya están "finished"
    (idempotente vía points_log — reprocesar la jornada no vuelve a aplicar
    nada). Aplica, en este orden:
    1. Castigo Quiniela: -1 pt por cada partido sin pick.
    2. Castigo Once: -5 pts si no hay alineación guardada.
    3. Bonus invisible de nuevos usuarios (primeras 3 jornadas de cada
       usuario) que hayan quedado en último lugar — Quiniela y Once por
       separado, calculado sobre los puntajes ya ajustados por 1 y 2.
    """
    if not matches or any(m.get("status") != "finished" for m in matches):
        return {"applied": False, "reason": "jornada aún no cierra — hay partidos pendientes"}

    # Guard real de la causa raíz de J3-J12 penalizadas por error: una
    # jornada "upcoming" cuyo start_date todavía no llega NO puede tener
    # partidos "finished" de verdad — si los tiene, son datos huérfanos de
    # otra temporada (matches viejos del Clausura, ver deep-clean-jornadas)
    # y "penalizar por no seleccionar" no tiene sentido porque el usuario ni
    # siquiera podía seleccionar todavía. Sin este check, el auto-cierre del
    # scheduler los trataba como jornadas legítimamente terminadas.
    start_date = jornada.get("start_date")
    if not start_date or start_date > datetime.utcnow():
        return {
            "applied": False,
            "reason": (
                "start_date de la jornada todavía no llega — los partidos 'finished' "
                "son datos huérfanos, no se penaliza una jornada que no ha empezado"
            ),
        }

    jornada_obj_id = jornada["_id"]
    total_matches = len(matches)
    all_users = await db.users.find().to_list(100000)

    quiniela_penalized = await _apply_quiniela_penalty(jornada_obj_id, total_matches, all_users)
    once_penalized = await _apply_once_penalty(jornada_obj_id, all_users)
    quiniela_bonus = await _apply_new_user_bonus(
        jornada_obj_id, jornada, all_users, "total_points", "QUINIELA_BONUS_NUEVO"
    )
    once_bonus = await _apply_new_user_bonus(
        jornada_obj_id, jornada, all_users, "fantasy_total_points", "ONCE_BONUS_NUEVO"
    )

    logger.info(
        f"🔒 Cierre jornada {jornada.get('week_number')}: "
        f"quiniela_penalizados={quiniela_penalized}, once_penalizados={once_penalized}, "
        f"quiniela_bonus_nuevos={quiniela_bonus}, once_bonus_nuevos={once_bonus}"
    )
    return {
        "applied": True,
        "quiniela_penalized": quiniela_penalized,
        "once_penalized": once_penalized,
        "quiniela_new_user_bonus": quiniela_bonus,
        "once_new_user_bonus": once_bonus,
    }
