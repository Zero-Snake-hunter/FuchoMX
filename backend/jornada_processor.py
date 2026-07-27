import logging
from datetime import datetime

from bson import ObjectId

from achievements import check_and_award_achievements_after_jornada
from database import db
from fantasy_scoring import calculate_fantasy_points
from scoring_penalties import apply_jornada_close_adjustments
from services.player_stats_service import get_player_stats as _svc_get_player_stats
from services.scores_service import get_match_results as _svc_get_match_results

logger = logging.getLogger(__name__)


async def _process_jornada_core(jornada_id: str) -> dict:
    """
    Orquesta el procesamiento completo de una jornada:
    1. Resultados de partidos (365Scores → ESPN fallback)
    1.5. Cierre de jornada: castigos por no seleccionar + bonus nuevos usuarios
    2. Puntos de Quiniela
    3. Stats de jugadores (ESPN Summary)
    4. Puntos de Fantasy
    5. Logros y achievements
    Marca la jornada como processed=True al finalizar.
    """
    jornada_obj_id = ObjectId(jornada_id)
    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        return {"error": "Jornada no encontrada"}

    logger.info(f"🔄 Procesando jornada {jornada.get('week_number')} ({jornada_id})")

    # Paso 1: Actualizar resultados de partidos
    scores_result = await _svc_get_match_results(jornada_id, db)
    logger.info(f"  ✅ Scores: {scores_result.get('matches_updated')}/{scores_result.get('matches_total')} actualizados")

    # Paso 1.5: Cierre de jornada — castigos por no seleccionar + bonus de nuevos usuarios
    # (no-op si aún quedan partidos sin terminar; idempotente si ya se aplicó)
    close_result = {"applied": False}
    try:
        all_matches = await db.matches.find({"jornada_id": jornada_obj_id}).to_list(100)
        close_result = await apply_jornada_close_adjustments(jornada, all_matches)
    except Exception as exc:
        logger.error(f"  ❌ Jornada close adjustments error: {exc}")

    # Paso 2: Calcular puntos de Quiniela
    quiniela_updated = 0
    try:
        matches_done = await db.matches.find(
            {"jornada_id": jornada_obj_id, "status": "finished"}
        ).to_list(100)

        if matches_done:
            match_results_map = {}
            for m in matches_done:
                h, a = m.get("home_score", 0), m.get("away_score", 0)
                if h > a:
                    result_val = "HOME"
                elif a > h:
                    result_val = "AWAY"
                else:
                    result_val = "DRAW"
                match_results_map[m["_id"]] = result_val

            all_selections = await db.quiniela_selections.find(
                {"jornada_id": jornada_obj_id}
            ).to_list(10000)

            user_sels: dict = {}
            for sel in all_selections:
                user_sels.setdefault(sel["user_id"], []).append(sel)

            for uid, sels in user_sels.items():
                pts = sum(
                    3 for s in sels
                    if s.get("match_id") in match_results_map
                    and s["selection"] == match_results_map[s["match_id"]]
                )
                if pts > 0:
                    existing = await db.points_log.find_one({
                        "user_id": uid, "jornada_id": jornada_obj_id, "source": "QUINIELA",
                    })
                    if not existing:
                        await db.points_log.insert_one({
                            "user_id": uid, "jornada_id": jornada_obj_id,
                            "source": "QUINIELA", "points": pts,
                            "created_at": datetime.utcnow(),
                        })
                        await db.users.update_one(
                            {"_id": uid}, {"$inc": {"total_points": pts}}
                        )
                        quiniela_updated += 1
    except Exception as exc:
        logger.error(f"  ❌ Quiniela points error: {exc}")

    # Paso 3: Stats de jugadores
    stats_result = await _svc_get_player_stats(jornada_id, db)
    logger.info(f"  ✅ Player stats: {stats_result.get('players_saved')} jugadores guardados")

    # Paso 4: Calcular puntos Fantasy
    fantasy_updated = 0
    try:
        f_result = await calculate_fantasy_points(jornada_id)
        fantasy_updated = f_result.get("teams_processed", 0)
    except Exception as exc:
        logger.error(f"  ❌ Fantasy points error: {exc}")

    # Paso 5: Logros
    achievements_awarded = 0
    try:
        user_ids = await db.users.distinct("_id", {})
        for uid in user_ids:
            awarded = await check_and_award_achievements_after_jornada(uid, jornada_id)
            achievements_awarded += len(awarded)
    except Exception as exc:
        logger.error(f"  ❌ Achievements error: {exc}")

    # Marcar jornada como procesada
    await db.jornadas.update_one(
        {"_id": jornada_obj_id},
        {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
    )

    summary = {
        "jornada_id":           jornada_id,
        "week_number":          jornada.get("week_number"),
        "scores_updated":       scores_result.get("matches_updated", 0),
        "scores_not_found":     scores_result.get("matches_not_found", []),
        "quiniela_updated":     quiniela_updated,
        "player_stats_saved":   stats_result.get("players_saved", 0),
        "fantasy_updated":      fantasy_updated,
        "achievements_awarded": achievements_awarded,
        "jornada_close":        close_result,
        "processed_at":         datetime.utcnow().isoformat(),
    }
    logger.info(f"✅ Jornada {jornada.get('week_number')} procesada: {summary}")
    return summary


async def close_and_advance_jornada(jornada_oid: ObjectId, reminder_hours: int = 2) -> dict:
    """
    Cierra una jornada (status=finished, is_active=False) y activa de
    inmediato la siguiente por week_number+1 en la misma competition —
    status=in_progress, is_active=True, partidos desbloqueados — sin
    importar su start_date. Si la jornada todavía no tiene processed=True,
    corre _process_jornada_core antes de cerrarla para no dejar puntos de
    quiniela/fantasy sin calcular.

    Comparte esta lógica /admin/quiniela/cerrar-jornada (acción manual del
    admin) y el auto-scheduler (cierre automático) — así ambos cierran y
    abren jornadas exactamente igual.
    """
    jornada = await db.jornadas.find_one({"_id": jornada_oid})
    if not jornada:
        return {"error": "Jornada no encontrada"}

    if not jornada.get("processed", False):
        await _process_jornada_core(str(jornada_oid))

    current_week = jornada["week_number"]
    competition = jornada.get("competition", "liga_mx")
    await db.jornadas.update_one({"_id": jornada_oid}, {"$set": {"status": "finished", "is_active": False}})

    next_jornada = await db.jornadas.find_one(
        {"week_number": current_week + 1, "competition": competition}
    )
    next_info = None
    if next_jornada:
        await db.jornadas.update_one({"_id": next_jornada["_id"]}, {"$set": {
            "status": "in_progress", "is_active": True,
            "reminder_hours": reminder_hours, "notified_reminder": False,
        }})
        await db.matches.update_many(
            {"jornada_id": next_jornada["_id"]}, {"$set": {"locked": False}}
        )
        next_info = {"id": str(next_jornada["_id"]), "week_number": next_jornada["week_number"]}

    return {"closed_week": current_week, "next_jornada": next_info}
