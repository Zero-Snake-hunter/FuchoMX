import asyncio
import logging
from datetime import datetime, timedelta

from database import client, db, get_active_competition
from fantasy_scoring import calculate_fantasy_points
from jornada_processor import _process_jornada_core, close_and_advance_jornada
from services.push_service import notify_jornada_open, notify_jornada_reminder
from services.scores_service import (
    _fetch_365scores,
    _STATUS_MAP,
    get_match_results as _svc_get_match_results,
)
from services.world_cup_stats_service import get_wc_match_stats

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


# ── Auto cierre/apertura de jornadas ───────────────────────────────────────────

async def _auto_close_and_advance_jornada():
    """
    Revisa la jornada activa de temporada regular (excluye liguilla — esa
    tiene su propio flujo en _process_liguilla_phase) y, si TODOS sus
    partidos ya están "finished", la cierra y activa la siguiente de
    inmediato (misma lógica que /admin/quiniela/cerrar-jornada, sin
    importar el start_date de la siguiente). Si no hay ninguna jornada
    activa pero sí una "upcoming" con partidos ya cargados, activa la de
    week_number más bajo — nunca debe quedar un hueco sin jornada activa.

    Se llama en cada iteración del loop principal, ANTES del fetch de
    partidos "de hoy" — el cierre se decide con nuestros propios datos en
    Mongo, no con ese feed externo, porque en días sin partidos programados
    ese fetch viene vacío y el resto del loop se salta por completo.
    """
    competition = await get_active_competition()
    jornada = await db.jornadas.find_one(
        {"is_active": True, "competition": competition, "type": {"$ne": "liguilla"}}
    )

    if jornada:
        matches = await db.matches.find({"jornada_id": jornada["_id"]}).to_list(100)
        # Guard adicional a apply_jornada_close_adjustments (que ya bloquea
        # esto): si el start_date de la jornada ni siquiera llegó, "todos
        # finished" son matches huérfanos de otra temporada — no una
        # jornada real ya jugada. Causa raíz de J3-J12 penalizadas por
        # error cuando el auto-cierre las cerró en cascada antes de que
        # deep-clean-jornadas les quitara esos matches viejos.
        start_date = jornada.get("start_date")
        started = bool(start_date) and start_date <= datetime.utcnow()
        if matches and started and all(m.get("status") == "finished" for m in matches):
            result = await close_and_advance_jornada(jornada["_id"])
            next_info = result.get("next_jornada")
            if next_info:
                logger.info(
                    f"🔁 Auto-scheduler: jornada {result['closed_week']} cerrada, "
                    f"jornada {next_info['week_number']} activada automáticamente"
                )
                try:
                    await notify_jornada_open(next_info["week_number"])
                except Exception as exc:
                    logger.error(f"❌ Error notificando apertura de jornada: {exc}")
            else:
                logger.info(f"🔁 Auto-scheduler: jornada {result['closed_week']} cerrada. Temporada terminada.")
        return

    upcoming = await db.jornadas.find(
        {"status": "upcoming", "competition": competition, "type": {"$ne": "liguilla"}}
    ).sort("week_number", 1).to_list(50)
    for candidate in upcoming:
        match_count = await db.matches.count_documents({"jornada_id": candidate["_id"]})
        if match_count == 0:
            continue
        await db.jornadas.update_one(
            {"_id": candidate["_id"]}, {"$set": {"status": "in_progress", "is_active": True}}
        )
        await db.matches.update_many({"jornada_id": candidate["_id"]}, {"$set": {"locked": False}})
        logger.info(
            f"🔁 Auto-scheduler: no había jornada activa — jornada "
            f"{candidate['week_number']} activada automáticamente"
        )
        break


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
            active_competition = await get_active_competition()

            # ── Recordatorio de picks (se evalúa en cada ciclo) ───────────────────
            try:
                jornada_reminder = await db.jornadas.find_one(
                    {"is_active": True, "notified_reminder": {"$ne": True}, "competition": active_competition}
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

            # ── Cierre/apertura automática de jornadas (se evalúa en cada ciclo,
            # independiente de si hay partidos "hoy" según el feed externo) ───────
            try:
                await _auto_close_and_advance_jornada()
            except Exception as exc:
                logger.error(f"❌ Error en auto cierre/apertura de jornada: {exc}")
            # ──────────────────────────────────────────────────────────────────────

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
                jornada = await db.jornadas.find_one({"is_active": True, "competition": active_competition})
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

            # ── World Cup auto-processing ──────────────────────────────────────
            try:
                if active_competition == "world_cup_2026":
                    wc_games = await _fetch_365scores(
                        today_start, today_end, competition_id=5930
                    )
                    ended_wc = [
                        g for g in wc_games
                        if g.get("statusText") == "Ended"
                    ]
                    for game in ended_wc:
                        game_id = game.get("id")
                        if not game_id:
                            continue
                        already = await db.player_match_stats.find_one(
                            {"game_id": game_id, "competition": "world_cup_2026"}
                        )
                        if already:
                            continue
                        wc_jornada = await db.jornadas.find_one(
                            {"competition": "world_cup_2026", "is_active": True}
                        )
                        if not wc_jornada:
                            logger.warning(
                                f"⚠️ WC game {game_id}: no hay jornada activa world_cup_2026"
                            )
                            continue
                        jornada_id = str(wc_jornada["_id"])
                        try:
                            stats_result = await get_wc_match_stats(game_id, db)
                            if "error" not in stats_result:
                                await calculate_fantasy_points(jornada_id)
                                logger.info(
                                    f"✅ WC game {game_id} procesado: "
                                    f"{stats_result.get('players_processed', 0)} jugadores | "
                                    f"{stats_result.get('home')} {stats_result.get('score')} "
                                    f"{stats_result.get('away')}"
                                )
                            else:
                                logger.warning(
                                    f"⚠️ WC game {game_id} error: {stats_result['error']}"
                                )
                        except Exception as exc:
                            logger.error(f"❌ Error procesando WC game {game_id}: {exc}")
            except Exception as exc:
                logger.error(f"❌ Error en WC auto-processing: {exc}")
            # ──────────────────────────────────────────────────────────────────

            if finished_games and not live_games and not scheduled_games:
                logger.info("🏁 Todos los partidos del día terminaron — verificando proceso")
                jornada = await db.jornadas.find_one({"is_active": True, "competition": active_competition})
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
                        # Guard: la jornada activa en este punto pudo haber sido
                        # activada recién en este mismo ciclo (por
                        # _auto_close_and_advance_jornada, más arriba en el loop)
                        # y todavía no tener ningún partido jugado — sin este
                        # check se marcaría processed=True de más y ya nunca se
                        # reprocesaría cuando sus partidos sí terminen.
                        has_finished_matches = await db.matches.count_documents(
                            {"jornada_id": jornada["_id"], "status": "finished"}
                        ) > 0
                        if has_finished_matches:
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
