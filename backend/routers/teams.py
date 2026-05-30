import logging
from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from database import db, get_active_competition
from dependencies import get_current_user
from jornada_processor import _process_jornada_core

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/teams")
async def get_teams():
    competition = await get_active_competition()
    teams = await db.teams.find({"competition": competition}).sort(
        [("priority", 1), ("name", 1)]
    ).to_list(100)
    for team in teams:
        team["id"] = str(team.pop("_id"))
    return {"teams": teams}


@router.get("/jornadas/current")
async def get_current_jornada():
    now = datetime.utcnow()
    competition = await get_active_competition()

    # Step 1: Find jornada with is_active = true
    jornada = await db.jornadas.find_one({"is_active": True, "competition": competition})

    # Step 2: If expired, auto-process and transition to next
    if jornada and jornada.get("end_date") and jornada["end_date"] < now:
        logger.info(f"Jornada {jornada['week_number']} expirada. Transitando...")
        if not jornada.get("processed", False):
            try:
                proc_result = await _process_jornada_core(str(jornada["_id"]))
                logger.info(
                    f"✅ Auto-proceso completado: "
                    f"scores={proc_result.get('scores_updated')}, "
                    f"quiniela={proc_result.get('quiniela_updated')} usuarios, "
                    f"fantasy={proc_result.get('fantasy_updated')} equipos, "
                    f"logros={proc_result.get('achievements_awarded')}"
                )
            except Exception as exc:
                logger.error(f"❌ Auto-proceso falló: {exc}")

        await db.jornadas.update_one(
            {"_id": jornada["_id"]},
            {"$set": {"status": "finished", "is_active": False}}
        )
        next_jornada = await db.jornadas.find_one(
            {"week_number": jornada["week_number"] + 1, "competition": competition}
        )
        if next_jornada:
            await db.jornadas.update_one(
                {"_id": next_jornada["_id"]},
                {"$set": {"status": "upcoming", "is_active": True}}
            )
            jornada = next_jornada
            jornada["status"] = "upcoming"
            jornada["is_active"] = True
            logger.info(f"Jornada {next_jornada['week_number']} activada automáticamente")
        else:
            jornada = None
            logger.info("No hay siguiente jornada disponible. Temporada terminada.")

    # Step 3: Fallback legacy status-based lookup
    if not jornada:
        jornada = await db.jornadas.find_one(
            {"status": {"$in": ["upcoming", "in_progress"]}, "competition": competition},
            sort=[("week_number", 1)]
        )
        if jornada:
            await db.jornadas.update_one(
                {"_id": jornada["_id"]}, {"$set": {"is_active": True}}
            )
            jornada["is_active"] = True
            logger.info(f"Jornada {jornada['week_number']} activada via fallback")

    if not jornada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay jornada activa. Usa /api/admin/seed-jornada para crear una."
        )

    # Step 4: Update status based on dates
    if jornada.get("start_date") and jornada["start_date"] <= now and jornada.get("status") == "upcoming":
        await db.jornadas.update_one(
            {"_id": jornada["_id"]}, {"$set": {"status": "in_progress"}}
        )
        jornada["status"] = "in_progress"

    # Step 5: Get matches
    matches = await db.matches.find({"jornada_id": jornada["_id"]}).to_list(100)

    # Step 5b: Auto-advance if ALL matches finished AND end_date passed
    if matches:
        finished_count = sum(1 for m in matches if m.get("status") == "finished")
        total_count = len(matches)
        end_date_passed = jornada.get("end_date") and jornada["end_date"] < now

        if total_count > 0 and finished_count == total_count and end_date_passed:
            logger.info(
                f"Jornada {jornada['week_number']}: todos {total_count} partidos finalizados "
                f"y fecha fin pasada. Avanzando automáticamente..."
            )
            if not jornada.get("processed", False):
                try:
                    proc_result = await _process_jornada_core(str(jornada["_id"]))
                    logger.info(
                        f"✅ Auto-proceso: quiniela={proc_result.get('quiniela_updated')} usuarios, "
                        f"fantasy={proc_result.get('fantasy_updated')} equipos"
                    )
                except Exception as exc:
                    logger.error(f"❌ Auto-proceso falló: {exc}")

            await db.jornadas.update_one(
                {"_id": jornada["_id"]},
                {"$set": {"is_active": False, "status": "finished"}}
            )
            next_j = await db.jornadas.find_one(
                {"week_number": jornada["week_number"] + 1, "competition": competition}
            )
            if next_j:
                await db.jornadas.update_one(
                    {"_id": next_j["_id"]},
                    {"$set": {"is_active": True, "status": "upcoming"}}
                )
                jornada = next_j
                logger.info(
                    f"Jornada {next_j['week_number']} activada porque todos los partidos de "
                    f"Jornada {next_j['week_number'] - 1} terminaron"
                )
                matches = await db.matches.find({"jornada_id": jornada["_id"]}).to_list(100)
            else:
                logger.info("No hay siguiente jornada — temporada completada.")

    # Get team details for each match
    for match in matches:
        home_team = await db.teams.find_one({"_id": match["home_team_id"]})
        away_team = await db.teams.find_one({"_id": match["away_team_id"]})

        match["id"] = str(match.pop("_id"))
        match["jornada_id"] = str(match["jornada_id"])

        match["home_team"] = {
            "id": str(home_team["_id"]),
            "name": home_team["name"],
            "short_name": home_team["short_name"],
            "shield_url": home_team["shield_url"]
        } if home_team else {
            "id": "unknown", "name": "Equipo Local",
            "short_name": "LOC", "shield_url": "https://via.placeholder.com/100"
        }
        match["away_team"] = {
            "id": str(away_team["_id"]),
            "name": away_team["name"],
            "short_name": away_team["short_name"],
            "shield_url": away_team["shield_url"]
        } if away_team else {
            "id": "unknown", "name": "Equipo Visitante",
            "short_name": "VIS", "shield_url": "https://via.placeholder.com/100"
        }

        match.pop("home_team_id", None)
        match.pop("away_team_id", None)

    jornada["id"] = str(jornada.pop("_id"))
    jornada["matches"] = matches
    return {"jornada": jornada}
