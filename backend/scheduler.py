import asyncio
import logging
from datetime import datetime, timedelta

from database import client, db
from jornada_processor import _process_jornada_core
from services.scores_service import (
    _fetch_365scores,
    _STATUS_MAP,
    get_match_results as _svc_get_match_results,
)

logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None


# ── Liguilla phase processor ───────────────────────────────────────────────────

async def _process_liguilla_phase(phase: str):
    """Procesa automáticamente una fase de liguilla cuando terminan todos sus partidos."""
    jornada = await db.jornadas.find_one({"type": "liguilla", "phase": phase, "is_active": True})
    if not jornada or jornada.get("processed"):
        return

    jornada_id = jornada["_id"]
    logger.info(f"🏆 Procesando liguilla fase: {phase}")

    matches = await db.matches.find({"jornada_id": jornada_id}).to_list(20)
    pending = [m for m in matches if m.get("status") != "finished"]
    if pending:
        logger.info(f"⏳ Liguilla {phase}: {len(pending)} partidos pendientes")
        return

    try:
        scores_result = await _svc_get_match_results(str(jornada_id), db)
        logger.info(f"✅ Liguilla {phase} scores: {scores_result.get('matches_updated', 0)} actualizados")
    except Exception as e:
        logger.error(f"❌ Error calculando scores liguilla {phase}: {e}")

    await db.jornadas.update_one(
        {"_id": jornada_id},
        {"$set": {"processed": True, "is_active": False, "status": "finished"}}
    )
    logger.info(f"✅ Liguilla {phase} cerrada automáticamente")

    if phase == "semis":
        caz = await db.teams.find_one({"short_name": "CAZ"})
        gdl = await db.teams.find_one({"short_name": "GDL"})
        pum = await db.teams.find_one({"short_name": "PUM"})
        pac = await db.teams.find_one({"short_name": "PAC"})

        async def get_series_winner(team_a_id, team_b_id):
            partidos = await db.matches.find({
                "jornada_id": jornada_id,
                "$or": [
                    {"home_team_id": team_a_id, "away_team_id": team_b_id},
                    {"home_team_id": team_b_id, "away_team_id": team_a_id},
                ]
            }).to_list(2)
            goles_a = goles_b = 0
            for p in partidos:
                if p.get("home_team_id") == team_a_id:
                    goles_a += p.get("home_score") or 0
                    goles_b += p.get("away_score") or 0
                else:
                    goles_b += p.get("home_score") or 0
                    goles_a += p.get("away_score") or 0
            return team_a_id if goles_a >= goles_b else team_b_id

        if caz and gdl and pum and pac:
            winner_right_id = await get_series_winner(caz["_id"], gdl["_id"])
            winner_right = caz if winner_right_id == caz["_id"] else gdl
            winner_left_id = await get_series_winner(pum["_id"], pac["_id"])
            winner_left = pum if winner_left_id == pum["_id"] else pac

            logger.info(f"🏆 Finalistas: {winner_left['name']} vs {winner_right['name']}")

            final_jornada = await db.jornadas.find_one({"type": "liguilla", "phase": "final"})
            if final_jornada:
                await db.jornadas.update_one(
                    {"_id": final_jornada["_id"]},
                    {"$set": {
                        "active_teams": [winner_left["name"], winner_right["name"]],
                        "title": f"Liguilla Clausura 2026 — Final: {winner_left['name']} vs {winner_right['name']}",
                        "is_active": True,
                        "status": "upcoming",
                    }}
                )
                if await db.matches.count_documents({"jornada_id": final_jornada["_id"]}) == 0:
                    await db.matches.insert_many([
                        {
                            "jornada_id": final_jornada["_id"],
                            "home_team_id": winner_right["_id"],
                            "away_team_id": winner_left["_id"],
                            "home_score": None, "away_score": None,
                            "status": "scheduled", "leg": "ida",
                            "start_at": datetime(2026, 5, 22, 21, 0),
                            "created_at": datetime.utcnow(),
                        },
                        {
                            "jornada_id": final_jornada["_id"],
                            "home_team_id": winner_left["_id"],
                            "away_team_id": winner_right["_id"],
                            "home_score": None, "away_score": None,
                            "status": "scheduled", "leg": "vuelta",
                            "start_at": datetime(2026, 5, 25, 21, 0),
                            "created_at": datetime.utcnow(),
                        },
                    ])
                logger.info(f"✅ Final activada: {winner_left['name']} vs {winner_right['name']}")

    elif phase == "final":
        logger.info("🎉 ¡Liguilla Clausura 2026 finalizada!")


# ── Main loop ─────────────────────────────────────────────────────────────────

async def _auto_update_scores():
    """
    Corre en background continuamente.
    - Partidos live → actualiza scores cada 45 s.
    - Partidos programados hoy → revisa cada 120 s.
    - Sin partidos hoy → duerme 10 min.
    - Cuando todos terminan → procesa la jornada automáticamente.
    """
    logger.info("🤖 Auto-scheduler iniciado")

    while True:
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0,  minute=0,  second=0,  microsecond=0)
            today_end   = now.replace(hour=23, minute=59, second=59, microsecond=0)

            games = await _fetch_365scores(today_start, today_end)

            if not games:
                logger.debug("📅 Sin partidos hoy. Próxima revisión en 10 min.")
                await asyncio.sleep(600)
                continue

            live_games      = [g for g in games if _STATUS_MAP.get(g.get("statusGroup", 1)) == "live"]
            finished_games  = [g for g in games if _STATUS_MAP.get(g.get("statusGroup", 1)) == "finished"]
            scheduled_games = [g for g in games if _STATUS_MAP.get(g.get("statusGroup", 1)) == "scheduled"]

            logger.info(
                f"⚽ Partidos hoy: {len(games)} total | "
                f"{len(live_games)} live | {len(finished_games)} terminados | {len(scheduled_games)} pendientes"
            )

            if live_games or finished_games:
                jornada = await db.jornadas.find_one({"is_active": True})
                if jornada:
                    try:
                        scores_result = await _svc_get_match_results(str(jornada["_id"]), db)
                        updated = scores_result.get("matches_updated", 0)
                        if updated > 0:
                            logger.info(
                                f"✅ Scheduler: {updated} partidos actualizados en "
                                f"jornada {jornada.get('week_number')}"
                            )
                    except Exception as e:
                        logger.error(f"❌ Scheduler scores error: {e}")

            if finished_games and not live_games and not scheduled_games:
                logger.info("🏁 Todos los partidos del día terminaron — verificando proceso")
                jornada = await db.jornadas.find_one({"is_active": True})
                if jornada and not jornada.get("processed", False):
                    if jornada.get("type") == "liguilla":
                        phase = jornada.get("phase", "")
                        if jornada.get("status") == "upcoming":
                            logger.info(f"⏳ Liguilla {phase} en estado upcoming — esperando")
                        else:
                            try:
                                await _process_liguilla_phase(phase)
                                logger.info(f"🏆 Liguilla fase {phase} procesada automáticamente")
                            except Exception as e:
                                logger.error(f"❌ Error procesando liguilla {phase}: {e}")
                    else:
                        try:
                            proc_result = await _process_jornada_core(str(jornada["_id"]))
                            logger.info(
                                f"🎉 Jornada {jornada.get('week_number')} procesada: "
                                f"quiniela={proc_result.get('quiniela_updated')} usuarios, "
                                f"fantasy={proc_result.get('fantasy_updated')} equipos"
                            )
                        except Exception as e:
                            logger.error(f"❌ Scheduler process_jornada error: {e}")

            sleep_secs = 45 if live_games else (120 if scheduled_games else 300)
            logger.debug(f"⏱ Próxima actualización en {sleep_secs}s")
            await asyncio.sleep(sleep_secs)

        except asyncio.CancelledError:
            logger.info("🛑 Auto-scheduler cancelado")
            break
        except Exception as e:
            logger.error(f"❌ Error inesperado en scheduler: {e}")
            await asyncio.sleep(60)


# ── Lifecycle hooks (registrar en app con @app.on_event) ──────────────────────

async def start_scheduler():
    global _scheduler_task
    _scheduler_task = asyncio.create_task(_auto_update_scores())
    logger.info("🚀 Auto-scheduler registrado en startup")


async def shutdown_app():
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    logger.info("🛑 Auto-scheduler detenido")
    client.close()
    logger.info("🛑 MongoDB connection closed")
