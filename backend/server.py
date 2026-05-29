from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from real_liga_mx_data import LIGA_MX_TEAMS, CLAUSURA_2026_DATES, CLAUSURA_2026_J13_MATCHES, LIGUILLA_CLAUSURA_2026_TEAMS
from world_cup_players_data import WC_SQUADS
from bson import ObjectId
import httpx
from services.scores_service import get_match_results as _svc_get_match_results
from services.player_stats_service import get_player_stats as _svc_get_player_stats

from database import client, db
from config import (
    API_FOOTBALL_KEY, API_FOOTBALL_BASE, API_FOOTBALL_LIGA_MX_ID, API_FOOTBALL_SEASON,
    ADMIN_EMAIL,
)
from dependencies import security, get_current_user, get_optional_user, get_admin_user
from achievements import (
    ACHIEVEMENTS_CATALOG, award_achievement,
    check_and_award_achievements_after_jornada, reset_participation_streak,
)
from fantasy_scoring import calculate_player_points, calculate_fantasy_points
from jornada_processor import _process_jornada_core
from routers import auth as auth_router
from routers import quiniela as quiniela_router
from routers import leagues as leagues_router
from models import (
    UpdateScoreRequest, FantasyTeamCreate, FantasyLineupSubmit,
    BracketUpdateRequest,
)

# Create the main app
app = FastAPI(title="Quiniela Liga MX API")
api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router.router)
api_router.include_router(quiniela_router.router)
api_router.include_router(leagues_router.router)

@app.get("/")
async def health_check():
    return {"status": "ok", "app": "FuchoMX"}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ ADMIN/SEED ROUTES ============

@api_router.post("/admin/seed-teams")
async def seed_teams(current_user: dict = Depends(get_admin_user)):
    """Seed Liga MX teams (mock data)"""
    teams_data = [
        {"name": "Club América", "short_name": "AME", "shield_url": "https://via.placeholder.com/100/FFD700/000000?text=AME"},
        {"name": "Guadalajara", "short_name": "GDL", "shield_url": "https://via.placeholder.com/100/FF0000/FFFFFF?text=GDL"},
        {"name": "Cruz Azul", "short_name": "CAZ", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=CAZ"},
        {"name": "Tigres UANL", "short_name": "TIG", "shield_url": "https://via.placeholder.com/100/FFD700/000000?text=TIG"},
        {"name": "Monterrey", "short_name": "MTY", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=MTY"},
        {"name": "Pumas UNAM", "short_name": "PUM", "shield_url": "https://via.placeholder.com/100/003D79/FFD700?text=PUM"},
        {"name": "Santos Laguna", "short_name": "SAN", "shield_url": "https://via.placeholder.com/100/00A551/FFFFFF?text=SAN"},
        {"name": "Toluca", "short_name": "TOL", "shield_url": "https://via.placeholder.com/100/DC143C/FFFFFF?text=TOL"},
        {"name": "León", "short_name": "LEO", "shield_url": "https://via.placeholder.com/100/00A551/FFFFFF?text=LEO"},
        {"name": "Atlas", "short_name": "ATL", "shield_url": "https://via.placeholder.com/100/DC143C/000000?text=ATL"},
        {"name": "Pachuca", "short_name": "PAC", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=PAC"},
        {"name": "Tijuana", "short_name": "TIJ", "shield_url": "https://via.placeholder.com/100/DC143C/000000?text=TIJ"},
        {"name": "Necaxa", "short_name": "NEC", "shield_url": "https://via.placeholder.com/100/DC143C/FFFFFF?text=NEC"},
        {"name": "Querétaro", "short_name": "QRO", "shield_url": "https://via.placeholder.com/100/000000/0047AB?text=QRO"},
        {"name": "Mazatlán", "short_name": "MAZ", "shield_url": "https://via.placeholder.com/100/663399/FFFFFF?text=MAZ"},
        {"name": "Puebla", "short_name": "PUE", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=PUE"},
        {"name": "Juárez", "short_name": "JUA", "shield_url": "https://via.placeholder.com/100/008000/FFFFFF?text=JUA"},
        {"name": "Atlético San Luis", "short_name": "ASL", "shield_url": "https://via.placeholder.com/100/DC143C/FFFFFF?text=ASL"},
    ]
    
    # Clear existing teams
    await db.teams.delete_many({})
    
    # Insert teams
    for team in teams_data:
        team["created_at"] = datetime.utcnow()
    
    result = await db.teams.insert_many(teams_data)
    
    logger.info(f"Seeded {len(result.inserted_ids)} teams")
    
    return {"message": f"Se crearon {len(result.inserted_ids)} equipos", "count": len(result.inserted_ids)}

@api_router.post("/admin/seed-jornada")
async def seed_current_jornada(current_user: dict = Depends(get_admin_user)):
    """Create current jornada with matches - auto-increments week_number"""
    # Get all teams
    teams = await db.teams.find().to_list(100)
    if len(teams) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes crear los equipos usando /api/admin/seed-teams"
        )
    
    competition = await get_active_competition()

    # Find the highest week_number to auto-increment
    last_jornada = await db.jornadas.find_one(sort=[("week_number", -1)])
    next_week = (last_jornada["week_number"] + 1) if last_jornada else 1

    # Deactivate any currently active jornada (solo la competición activa)
    await db.jornadas.update_many(
        {"is_active": True, "competition": competition},
        {"$set": {"is_active": False, "status": "finished"}}
    )
    
    # Create jornada with robust state fields
    jornada_data = {
        "week_number": next_week,
        "start_date": datetime.utcnow() + timedelta(days=2),
        "end_date": datetime.utcnow() + timedelta(days=4),
        "status": "upcoming",  # upcoming, in_progress, finished
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    jornada_result = await db.jornadas.insert_one(jornada_data)
    jornada_id = jornada_result.inserted_id
    
    # Create matches (9 matches for 18 teams) - shuffle teams for variety
    import random
    shuffled_teams = list(teams)
    random.shuffle(shuffled_teams)
    
    matches = []
    for i in range(0, min(18, len(shuffled_teams)), 2):
        if i + 1 < len(shuffled_teams):
            match = {
                "jornada_id": jornada_id,
                "home_team_id": shuffled_teams[i]["_id"],
                "away_team_id": shuffled_teams[i + 1]["_id"],
                "start_at": datetime.utcnow() + timedelta(days=2, hours=i),
                "status": "scheduled",  # scheduled, live, finished
                "home_score": None,
                "away_score": None,
                "created_at": datetime.utcnow()
            }
            matches.append(match)
    
    if matches:
        await db.matches.insert_many(matches)
    
    logger.info(f"Created jornada {next_week} (is_active=True) with {len(matches)} matches")
    
    return {
        "message": f"Se creó la jornada {next_week} con {len(matches)} partidos (activa)",
        "jornada_id": str(jornada_id),
        "week_number": next_week,
        "matches_count": len(matches)
    }

@api_router.post("/admin/seed-season")
async def seed_full_season(current_user: dict = Depends(get_admin_user)):
    """Create multiple jornadas for a full season (17 jornadas)"""
    teams = await db.teams.find().to_list(100)
    if len(teams) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes crear los equipos usando /api/admin/seed-teams"
        )
    
    import random
    
    # Delete existing jornadas and matches
    await db.jornadas.delete_many({})
    await db.matches.delete_many({})
    
    created_jornadas = []
    now = datetime.utcnow()
    ACTIVE_WEEK = 13  # Clausura 2026 — Jornada 13 activa (18-20 abril 2026)

    # Construir lookup de equipos por nombre para J13
    teams_by_name = {t["name"]: t["_id"] for t in teams}

    for week in range(1, 18):  # 17 jornadas
        # Usar fechas reales del Clausura 2026
        week_start = CLAUSURA_2026_DATES.get(week, now + timedelta(weeks=week - ACTIVE_WEEK))
        week_end   = week_start + timedelta(days=7)

        is_past    = week < ACTIVE_WEEK
        is_current = week == ACTIVE_WEEK
        week_status    = "finished" if is_past else ("in_progress" if is_current else "upcoming")
        match_status_val = "finished" if is_past else "scheduled"

        jornada_data = {
            "week_number": week,
            "start_date":  week_start,
            "end_date":    week_end,
            "status":      week_status,
            "is_active":   is_current,
            "created_at":  now
        }

        jornada_result = await db.jornadas.insert_one(jornada_data)
        jornada_id = jornada_result.inserted_id

        # ── Jornada 13: partidos reales del Clausura 2026 ──
        if is_current:
            matches = []
            for (home_name, away_name, match_dt) in CLAUSURA_2026_J13_MATCHES:
                home_id = teams_by_name.get(home_name)
                away_id = teams_by_name.get(away_name)
                if home_id and away_id:
                    matches.append({
                        "jornada_id": jornada_id,
                        "home_team_id": home_id,
                        "away_team_id": away_id,
                        "start_at": match_dt,
                        "status":   "scheduled",
                        "home_score": None,
                        "away_score": None,
                        "created_at": now
                    })
        else:
            # ── Otras jornadas: sorteo aleatorio ──
            shuffled_teams = list(teams)
            random.shuffle(shuffled_teams)
            matches = []
            for i in range(0, min(18, len(shuffled_teams)), 2):
                if i + 1 < len(shuffled_teams):
                    matches.append({
                        "jornada_id": jornada_id,
                        "home_team_id": shuffled_teams[i]["_id"],
                        "away_team_id": shuffled_teams[i + 1]["_id"],
                        "start_at": week_start + timedelta(hours=i),
                        "status":   match_status_val,
                        "home_score": None,
                        "away_score": None,
                        "created_at": now
                    })

        if matches:
            await db.matches.insert_many(matches)

        created_jornadas.append({
            "week_number": week,
            "jornada_id": str(jornada_id),
            "is_active":  is_current,
            "status":     week_status,
            "matches_count": len(matches)
        })
    
    logger.info(f"Created full season with {len(created_jornadas)} jornadas")
    
    return {
        "message": f"Se crearon {len(created_jornadas)} jornadas para la temporada completa",
        "jornadas": created_jornadas
    }


@api_router.post("/admin/reset-jornada")
async def reset_jornada(week: int = None, current_user: dict = Depends(get_admin_user)):
    """
    Utilidad para demos y pruebas.
    - Sin parámetros: cierra la jornada activa y activa la siguiente.
    - ?week=N: activa directamente la jornada N (desactiva cualquier otra).
    """
    now = datetime.utcnow()

    if week is not None:
        # Modo directo: activar jornada específica (filtrado por competición activa)
        competition = await get_active_competition()
        target = await db.jornadas.find_one({"week_number": week, "competition": competition})
        if not target:
            raise HTTPException(
                status_code=404,
                detail=f"Jornada {week} no encontrada para competición '{competition}'"
            )
        # Desactivar todas las jornadas de esta competición
        await db.jornadas.update_many({"competition": competition}, {"$set": {"is_active": False}})
        # Activar la pedida
        await db.jornadas.update_one(
            {"_id": target["_id"]},
            {"$set": {
                "is_active": True,
                "status": "in_progress",
                "start_date": now,
                "end_date": now + timedelta(days=7)
            }}
        )
        logger.info(f"Admin reset-jornada: jornada {week} activada directamente")
        return {
            "message": f"✅ Jornada {week} activada",
            "week_number": week,
            "jornada_id": str(target["_id"])
        }

    # Modo avance: cerrar activa → activar siguiente
    adv_competition = await get_active_competition()
    current = await db.jornadas.find_one({"is_active": True, "competition": adv_competition})
    if not current:
        # Fallback: buscar la de menor week_number con status != finished
        current = await db.jornadas.find_one(
            {"status": {"$ne": "finished"}, "competition": adv_competition},
            sort=[("week_number", 1)]
        )
    if not current:
        raise HTTPException(
            status_code=404,
            detail="No hay jornadas disponibles. Ejecuta /api/admin/seed-season primero."
        )

    closed_week = current["week_number"]

    # Cerrar jornada actual
    await db.jornadas.update_one(
        {"_id": current["_id"]},
        {"$set": {"is_active": False, "status": "finished"}}
    )

    # Buscar y activar la siguiente (misma competición)
    next_j = await db.jornadas.find_one({"week_number": closed_week + 1, "competition": adv_competition})
    if not next_j:
        raise HTTPException(
            status_code=404,
            detail=f"No hay jornada después de la {closed_week}. Esa era la última."
        )

    await db.jornadas.update_one(
        {"_id": next_j["_id"]},
        {"$set": {
            "is_active": True,
            "status": "in_progress",
            "start_date": now,
            "end_date": now + timedelta(days=7)
        }}
    )

    logger.info(f"Admin reset-jornada: {closed_week} → {closed_week + 1}")
    return {
        "message": f"✅ Jornada {closed_week} cerrada → Jornada {closed_week + 1} activa",
        "closed_week": closed_week,
        "active_week": closed_week + 1,
        "jornada_id": str(next_j["_id"])
    }


# ─────────────────────────────────────────────────────────────────────────
#  LIGUILLA CLAUSURA 2026
# ─────────────────────────────────────────────────────────────────────────

# ESPN → DB name mapping (names that differ)
_ESPN_TO_DB: dict = {
    "América": "Club América",
    "Atlético de San Luis": "Atlético San Luis",
    "San Luis": "Atlético San Luis",
    "Xolos": "Tijuana",
}

# Module-level cache for ESPN standings (1 hour TTL)
_espn_cache: dict = {"data": None, "fetched_at": None}
_ESPN_CACHE_TTL = 3600  # seconds


async def _fetch_espn_standings() -> Optional[List[dict]]:
    """Fetch Liga MX top-8 from ESPN API; returns list of dicts or None on failure."""
    global _espn_cache
    now = datetime.utcnow()

    # Check cache
    if _espn_cache["data"] and _espn_cache["fetched_at"]:
        age = (now - _espn_cache["fetched_at"]).total_seconds()
        if age < _ESPN_CACHE_TTL:
            logger.info(f"ESPN cache hit (age {age:.0f}s)")
            return _espn_cache["data"]

    try:
        url = "https://site.api.espn.com/apis/v2/sports/soccer/mex.1/standings"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            logger.warning(f"ESPN API → {resp.status_code}")
            return None

        data = resp.json()
        entries = data["children"][0]["standings"]["entries"]
        top8 = []
        for i, entry in enumerate(entries[:8]):
            team = entry["team"]
            espn_name = team.get("displayName", "")
            db_name = _ESPN_TO_DB.get(espn_name, espn_name)
            top8.append({"position": i + 1, "espn_name": espn_name, "db_name": db_name})

        _espn_cache["data"] = top8
        _espn_cache["fetched_at"] = now
        logger.info(f"✅ ESPN standings: {[t['espn_name'] for t in top8]}")
        return top8

    except Exception as exc:
        logger.error(f"❌ ESPN standings error: {exc}")
        return None

@api_router.get("/liguilla/bracket")
async def get_liguilla_bracket(current_user: dict = Depends(get_optional_user)):
    """Retorna la estructura del bracket de liguilla con los 8 equipos clasificados.
    Intenta obtener la tabla en vivo desde la ESPN API; si falla usa la lista provisional hardcodeada.
    """
    is_provisional = True
    teams_data = []

    # ── Intento 1: ESPN API (datos en vivo) ──────────────────────────────
    espn_top8 = await _fetch_espn_standings()
    if espn_top8:
        for entry in espn_top8:
            # Buscar en DB por nombre exacto, luego parcial
            team = await db.teams.find_one({"name": entry["db_name"]})
            if not team:
                team = await db.teams.find_one(
                    {"name": {"$regex": entry["db_name"][:4], "$options": "i"}}
                )
            if team:
                teams_data.append({
                    "position":  entry["position"],
                    "id":        str(team["_id"]),
                    "name":      team["name"],
                    "short_name": team.get("short_name", team["name"][:3].upper()),
                    "shield_url": team.get("shield_url", ""),
                })
        if len(teams_data) >= 8:
            is_provisional = False
            logger.info("✅ Bracket usando datos ESPN en vivo")
        else:
            logger.warning(f"ESPN incompleto ({len(teams_data)}/8), usando fallback")
            teams_data = []

    # ── Fallback: lista hardcodeada provisional ───────────────────────────
    if not teams_data:
        for entry in LIGUILLA_CLAUSURA_2026_TEAMS:
            team = await db.teams.find_one({"name": entry["name"]})
            if team:
                teams_data.append({
                    "position":  entry["position"],
                    "id":        str(team["_id"]),
                    "name":      team["name"],
                    "short_name": team.get("short_name", team["name"][:3].upper()),
                    "shield_url": team.get("shield_url", ""),
                })
        is_provisional = True

    # Mapear por posición para construir cuartos
    by_pos = {t["position"]: t for t in teams_data}

    # Obtener resultados guardados en DB
    results = await db.liguilla_results.find_one({"temporada": "Clausura 2026"})
    cuartos_winners   = results.get("cuartos_winners", []) if results else []
    semis_left_winner = results.get("semis_left_winner") if results else None
    semis_right_winner= results.get("semis_right_winner") if results else None
    champion          = results.get("champion") if results else None

    # Determinar status
    if champion:
        bracket_status = "finalizado"
    elif semis_left_winner or semis_right_winner:
        bracket_status = "semifinales"
    elif cuartos_winners:
        bracket_status = "semifinales"
    else:
        bracket_status = "cuartos"

    # Buscar equipos semifinalistas en DB
    async def find_team_by_short(short_name):
        if not short_name:
            return None
        t = await db.teams.find_one({"short_name": short_name})
        if not t:
            t = await db.teams.find_one({"name": {"$regex": short_name, "$options": "i"}})
        if t:
            return {
                "id": str(t["_id"]),
                "name": t["name"],
                "short_name": t.get("short_name", short_name),
                "shield_url": t.get("shield_url", ""),
            }
        return {"id": "", "name": short_name, "short_name": short_name, "shield_url": ""}

    # Semifinalistas (ganadores de cuartos)
    semi_left_home  = await find_team_by_short(cuartos_winners[0]) if len(cuartos_winners) > 0 else None
    semi_left_away  = await find_team_by_short(cuartos_winners[1]) if len(cuartos_winners) > 1 else None
    semi_right_home = await find_team_by_short(cuartos_winners[2]) if len(cuartos_winners) > 2 else None
    semi_right_away = await find_team_by_short(cuartos_winners[3]) if len(cuartos_winners) > 3 else None

    # Finalistas
    finalist_left  = await find_team_by_short(semis_left_winner) if semis_left_winner else None
    finalist_right = await find_team_by_short(semis_right_winner) if semis_right_winner else None
    champion_team  = await find_team_by_short(champion) if champion else None

    bracket = {
        "temporada":      "Clausura 2026",
        "status":         bracket_status,
        "is_provisional": is_provisional,
        "teams":          teams_data,
        "cuartos": [
            {"match": 1, "side": "left",  "home": by_pos.get(1), "away": by_pos.get(8), "winner": cuartos_winners[0] if len(cuartos_winners) > 0 else None},
            {"match": 2, "side": "left",  "home": by_pos.get(4), "away": by_pos.get(5), "winner": cuartos_winners[1] if len(cuartos_winners) > 1 else None},
            {"match": 3, "side": "right", "home": by_pos.get(2), "away": by_pos.get(7), "winner": cuartos_winners[2] if len(cuartos_winners) > 2 else None},
            {"match": 4, "side": "right", "home": by_pos.get(3), "away": by_pos.get(6), "winner": cuartos_winners[3] if len(cuartos_winners) > 3 else None},
        ],
        "semifinales": {
            "left":  {"home": semi_left_home,  "away": semi_left_away,  "winner": semis_left_winner},
            "right": {"home": semi_right_home, "away": semi_right_away, "winner": semis_right_winner},
        },
        "final": {
            "home": finalist_left,
            "away": finalist_right,
            "champion": champion_team,
        },
        "scoring": {
            "cuartos": 5,
            "semis":   10,
            "campeon": 25,
        },
        "my_prediction": None,
    }

    # Predicción guardada del usuario (si hay sesión)
    if current_user:
        pred = await db.bracket_predictions.find_one({"user_id": current_user["_id"]})
        if pred:
            bracket["my_prediction"] = {
                "cuartos_picks": pred.get("cuartos_picks", []),
                "semis_picks":   pred.get("semis_picks", []),
                "champion":      pred.get("champion"),
            }

    return bracket


@api_router.post("/liguilla/bracket/submit")
async def submit_bracket_prediction(
    prediction: dict,
    current_user: dict = Depends(get_current_user),
):
    """Guarda o actualiza la predicción de bracket del usuario."""
    await db.bracket_predictions.update_one(
        {"user_id": current_user["_id"]},
        {"$set": {
            "user_id":       current_user["_id"],
            "cuartos_picks": prediction.get("cuartos_picks", []),
            "semis_picks":   prediction.get("semis_picks", []),
            "champion":      prediction.get("champion"),
            "updated_at":    datetime.utcnow(),
        }},
        upsert=True,
    )
    return {"message": "✅ Bracket guardado exitosamente"}


@api_router.post("/admin/quiniela/cerrar-jornada/{jornada_id}")
async def close_jornada(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    """Admin: Close a jornada and activate the next one"""
    try:
        jornada_oid = ObjectId(jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")
    
    jornada = await db.jornadas.find_one({"_id": jornada_oid})
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")
    
    current_week = jornada["week_number"]
    
    # Close the current jornada
    await db.jornadas.update_one(
        {"_id": jornada_oid},
        {"$set": {"status": "finished", "is_active": False}}
    )
    
    # Activate the next jornada (same competition)
    jornada_competition = jornada.get("competition", "liga_mx")
    next_jornada = await db.jornadas.find_one(
        {"week_number": current_week + 1, "competition": jornada_competition}
    )
    
    next_info = None
    if next_jornada:
        await db.jornadas.update_one(
            {"_id": next_jornada["_id"]},
            {"$set": {"status": "upcoming", "is_active": True}}
        )
        next_info = {
            "id": str(next_jornada["_id"]),
            "week_number": next_jornada["week_number"]
        }
        logger.info(f"Closed jornada {current_week}, activated jornada {current_week + 1}")
    else:
        logger.info(f"Closed jornada {current_week}. No next jornada found (season ended)")
    
    return {
        "message": f"Jornada {current_week} cerrada exitosamente",
        "closed_jornada": {
            "id": jornada_id,
            "week_number": current_week
        },
        "next_jornada": next_info
    }


@api_router.post("/admin/sync-fixtures")
async def sync_fixtures(current_user: dict = Depends(get_admin_user)):
    """
    Sync Liga MX fixtures from TheSportsDB (ID: 4350).
    Falls back to Clausura 2025 real calendar dates if API is unavailable.
    """
    import httpx

    LEAGUE_ID = "4350"
    BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    # Map TheSportsDB team names -> our DB team names
    NAME_MAP = {
        "CF America": "Club América", "Club América": "Club América", "América": "Club América",
        "CD Guadalajara": "Guadalajara", "Chivas": "Guadalajara", "Guadalajara": "Guadalajara",
        "Cruz Azul": "Cruz Azul",
        "Tigres UANL": "Tigres UANL", "Tigres": "Tigres UANL",
        "CF Monterrey": "Monterrey", "Monterrey": "Monterrey", "Rayados": "Monterrey",
        "UNAM Pumas": "Pumas UNAM", "Pumas UNAM": "Pumas UNAM", "Pumas": "Pumas UNAM",
        "Santos Laguna": "Santos Laguna", "Santos": "Santos Laguna",
        "Deportivo Toluca": "Toluca", "Toluca": "Toluca",
        "Club León": "León", "León": "León", "Leon": "León",
        "Atlas FC": "Atlas", "Atlas": "Atlas",
        "CF Pachuca": "Pachuca", "Pachuca": "Pachuca",
        "Xolos Tijuana": "Tijuana", "FC Tijuana": "Tijuana", "Tijuana": "Tijuana",
        "Club Necaxa": "Necaxa", "Necaxa": "Necaxa",
        "Queretaro": "Querétaro", "Querétaro": "Querétaro",
        "Mazatlan FC": "Mazatlán", "Mazatlán": "Mazatlán",
        "Club Puebla": "Puebla", "Puebla": "Puebla",
        "FC Juarez": "Juárez", "Juárez": "Juárez", "Juarez": "Juárez",
        "Atletico de San Luis": "Atlético San Luis", "Atlético San Luis": "Atlético San Luis",
        "Atletico San Luis": "Atlético San Luis",
    }

    # Clausura 2026 real jornada start dates
    CLAUSURA_2025_DATES = CLAUSURA_2026_DATES

    events_fetched = 0
    matches_updated = 0
    source = "thesportsdb"
    api_error = None

    teams_list = await db.teams.find().to_list(100)
    team_by_name = {t["name"]: t["_id"] for t in teams_list}
    competition = await get_active_competition()

    # --- Attempt TheSportsDB ---
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            next_r = await client.get(
                f"{BASE_URL}/eventsnextleague.php?id={LEAGUE_ID}", headers=HEADERS
            )
            past_r = await client.get(
                f"{BASE_URL}/eventspastleague.php?id={LEAGUE_ID}", headers=HEADERS
            )

        all_events = []
        if next_r.status_code == 200 and next_r.text.strip().startswith("{"):
            all_events += (next_r.json().get("events") or [])
        if past_r.status_code == 200 and past_r.text.strip().startswith("{"):
            all_events += (past_r.json().get("results") or [])

        if not all_events:
            raise ValueError(f"No events — HTTP {next_r.status_code} (posiblemente rate-limited)")

        # Verify we got Liga MX events, not another league
        sample_league = (all_events[0].get("strLeague") or "").lower()
        if "mexico" not in sample_league and "liga mx" not in sample_league and "primera" not in sample_league:
            raise ValueError(f"Eventos no son de Liga MX — liga recibida: '{all_events[0].get('strLeague')}'. Usando fallback.")

        events_fetched = len(all_events)
        now = datetime.utcnow()

        for ev in all_events:
            home_raw = ev.get("strHomeTeam", "")
            away_raw = ev.get("strAwayTeam", "")
            home_name = NAME_MAP.get(home_raw, home_raw)
            away_name = NAME_MAP.get(away_raw, away_raw)
            home_id = team_by_name.get(home_name)
            away_id = team_by_name.get(away_name)
            if not home_id or not away_id:
                continue

            date_str = ev.get("dateEvent") or ""
            time_str = (ev.get("strTime") or "00:00:00")[:5]
            start_at = None
            if date_str:
                try:
                    start_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                except Exception:
                    pass

            home_sc = ev.get("intHomeScore")
            away_sc = ev.get("intAwayScore")
            str_status = (ev.get("strStatus") or "").lower()
            if home_sc is not None and away_sc is not None:
                match_status = "finished"
            elif "live" in str_status or "in progress" in str_status:
                match_status = "live"
            else:
                match_status = "upcoming"

            round_num = ev.get("intRound")
            match_filter: dict = {"home_team_id": home_id, "away_team_id": away_id}
            if round_num:
                try:
                    j = await db.jornadas.find_one({"week_number": int(round_num), "competition": competition})
                    if j:
                        match_filter["jornada_id"] = j["_id"]
                except Exception:
                    pass

            update_fields: dict = {"status": match_status}
            if start_at:
                update_fields["start_at"] = start_at
            if home_sc is not None:
                update_fields["home_score"] = int(home_sc)
            if away_sc is not None:
                update_fields["away_score"] = int(away_sc)

            res = await db.matches.update_one(match_filter, {"$set": update_fields})
            if res.modified_count:
                matches_updated += 1

        logger.info(f"sync-fixtures: TheSportsDB OK — {events_fetched} eventos, {matches_updated} actualizados")

    except Exception as exc:
        source = "fallback_clausura2025"
        api_error = str(exc)
        logger.warning(f"sync-fixtures: TheSportsDB falló ({exc}). Usando fallback Clausura 2025.")

        now = datetime.utcnow()
        competition = await get_active_competition()
        jornadas = await db.jornadas.find({"competition": competition}).sort("week_number", 1).to_list(25)

        for j in jornadas:
            week = j["week_number"]
            base_date = CLAUSURA_2025_DATES.get(week, datetime(2025, 1, 10) + timedelta(weeks=week - 1))
            matches = await db.matches.find({"jornada_id": j["_id"]}).to_list(20)

            for i, m in enumerate(matches):
                day_offset = i % 3
                hour = 19 + (i % 3)
                match_date = base_date + timedelta(days=day_offset, hours=hour)
                st = "finished" if match_date < now else "upcoming"
                update: dict = {"start_at": match_date, "status": st}
                await db.matches.update_one({"_id": m["_id"]}, {"$set": update})
                matches_updated += 1

    return {
        "message": f"✅ Sync completado — {matches_updated} partidos actualizados",
        "source": source,
        "events_fetched": events_fetched,
        "matches_updated": matches_updated,
        "api_error": api_error,
    }


@api_router.get("/admin/jornadas")
async def list_all_jornadas(current_user: dict = Depends(get_admin_user)):
    """Admin: List all jornadas with their status"""
    competition = await get_active_competition()
    jornadas = await db.jornadas.find({"competition": competition}).sort("week_number", 1).to_list(25)
    result = []
    for j in jornadas:
        result.append({
            "id": str(j["_id"]),
            "week_number": j["week_number"],
            "start_date": j["start_date"].isoformat() if j.get("start_date") else None,
            "end_date": j["end_date"].isoformat() if j.get("end_date") else None,
            "status": j.get("status", "unknown"),
            "is_active": j.get("is_active", False)
        })
    return {"jornadas": result, "total": len(result)}


async def get_active_competition():
    """Obtiene la competición activa desde la config"""
    config = await db.config.find_one({"key": "active_competition"})
    return config["value"] if config else "liga_mx"

@api_router.get("/teams")
async def get_teams():
    """Get all teams filtered by active competition"""
    competition = await get_active_competition()
    teams = await db.teams.find({"competition": competition}).sort([("priority", 1), ("name", 1)]).to_list(100)
    for team in teams:
        team["id"] = str(team.pop("_id"))
    return {"teams": teams}

@api_router.get("/jornadas/current")
async def get_current_jornada():
    """Get current active jornada with matches - implements automatic state transition"""
    now = datetime.utcnow()
    competition = await get_active_competition()
    
    # Step 1: Find jornada with is_active = true (filtered by active competition)
    jornada = await db.jornadas.find_one({"is_active": True, "competition": competition})
    
    # Step 2: If active jornada exists and its end_date has passed, transition to next
    if jornada and jornada.get("end_date") and jornada["end_date"] < now:
        logger.info(f"Jornada {jornada['week_number']} expirada (end_date: {jornada['end_date']}). Transitando...")

        # ── Auto-process si no fue procesada antes ────────────────────────
        if not jornada.get("processed", False):
            logger.info(
                f"Jornada {jornada['week_number']} no procesada. "
                f"Ejecutando process_jornada automáticamente..."
            )
            try:
                proc_result = await _process_jornada_core(str(jornada["_id"]))
                logger.info(
                    f"✅ Auto-proceso completado: "
                    f"scores={proc_result.get('scores_updated')}, "
                    f"quiniela={proc_result.get('quiniela_updated')} usuarios, "
                    f"fantasy={proc_result.get('fantasy_updated')} equipos, "
                    f"logros={proc_result.get('achievements_awarded')}"
                )
            except Exception as proc_exc:
                logger.error(f"❌ Auto-proceso falló: {proc_exc}")

        # Close expired jornada
        await db.jornadas.update_one(
            {"_id": jornada["_id"]},
            {"$set": {"status": "finished", "is_active": False}}
        )
        
        # Activate next jornada (filtered by same competition)
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
    
    # Step 3: Fallback - if no is_active found, try legacy status-based lookup
    if not jornada:
        jornada = await db.jornadas.find_one(
            {"status": {"$in": ["upcoming", "in_progress"]}, "competition": competition},
            sort=[("week_number", 1)]
        )
        # If found via fallback, set is_active for consistency
        if jornada:
            await db.jornadas.update_one(
                {"_id": jornada["_id"]},
                {"$set": {"is_active": True}}
            )
            jornada["is_active"] = True
            logger.info(f"Jornada {jornada['week_number']} activada via fallback (legacy status)")
    
    if not jornada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay jornada activa. Usa /api/admin/seed-jornada para crear una."
        )
    
    # Step 4: Update status based on dates
    if jornada.get("start_date") and jornada["start_date"] <= now and jornada.get("status") == "upcoming":
        await db.jornadas.update_one(
            {"_id": jornada["_id"]},
            {"$set": {"status": "in_progress"}}
        )
        jornada["status"] = "in_progress"
    
    # Step 5: Get matches for this jornada
    matches = await db.matches.find({"jornada_id": jornada["_id"]}).to_list(100)
    
    # Step 5b: Auto-advance if ALL matches are finished AND end_date has passed
    if matches:
        finished_count = sum(1 for m in matches if m.get("status") == "finished")
        total_count = len(matches)
        end_date_passed = jornada.get("end_date") and jornada["end_date"] < now
        
        if total_count > 0 and finished_count == total_count and end_date_passed:
            logger.info(
                f"Jornada {jornada['week_number']}: todos {total_count} partidos finalizados "
                f"y fecha fin pasada. Avanzando automáticamente..."
            )
            # ── Auto-process si no fue procesada antes ────────────────────
            if not jornada.get("processed", False):
                logger.info(
                    f"Jornada {jornada['week_number']} no procesada aún. "
                    f"Ejecutando process_jornada automáticamente..."
                )
                try:
                    proc_result = await _process_jornada_core(str(jornada["_id"]))
                    logger.info(
                        f"✅ Auto-proceso completado: "
                        f"quiniela={proc_result.get('quiniela_updated')} usuarios, "
                        f"fantasy={proc_result.get('fantasy_updated')} equipos, "
                        f"logros={proc_result.get('achievements_awarded')}"
                    )
                except Exception as proc_exc:
                    logger.error(f"❌ Auto-proceso falló: {proc_exc}")

            # Mark current jornada as finished
            await db.jornadas.update_one(
                {"_id": jornada["_id"]},
                {"$set": {"is_active": False, "status": "finished"}}
            )
            # Activate next jornada (misma competición)
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
                # Reload matches for the new active jornada
                matches = await db.matches.find({"jornada_id": jornada["_id"]}).to_list(100)
            else:
                logger.info("No hay siguiente jornada — temporada completada.")
    
    # Get team details for each match
    for match in matches:
        home_team = await db.teams.find_one({"_id": match["home_team_id"]})
        away_team = await db.teams.find_one({"_id": match["away_team_id"]})
        
        match["id"] = str(match.pop("_id"))
        match["jornada_id"] = str(match["jornada_id"])
        
        if home_team:
            match["home_team"] = {
                "id": str(home_team["_id"]),
                "name": home_team["name"],
                "short_name": home_team["short_name"],
                "shield_url": home_team["shield_url"]
            }
        else:
            match["home_team"] = {
                "id": "unknown",
                "name": "Equipo Local",
                "short_name": "LOC",
                "shield_url": "https://via.placeholder.com/100"
            }
        
        if away_team:
            match["away_team"] = {
                "id": str(away_team["_id"]),
                "name": away_team["name"],
                "short_name": away_team["short_name"],
                "shield_url": away_team["shield_url"]
            }
        else:
            match["away_team"] = {
                "id": "unknown",
                "name": "Equipo Visitante",
                "short_name": "VIS",
                "shield_url": "https://via.placeholder.com/100"
            }
        
        match.pop("home_team_id", None)
        match.pop("away_team_id", None)
    
    jornada["id"] = str(jornada.pop("_id"))
    jornada["matches"] = matches
    
    return {"jornada": jornada}

# ============ ADMIN ROUTES FOR QUINIELA ============

@api_router.put("/admin/match/{match_id}/score")
async def update_match_score(match_id: str, scores: UpdateScoreRequest, current_user: dict = Depends(get_admin_user)):
    """Update match score (admin only)"""
    match = await db.matches.find_one({"_id": ObjectId(match_id)})
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partido no encontrado"
        )
    
    # Update scores
    await db.matches.update_one(
        {"_id": ObjectId(match_id)},
        {"$set": {
            "home_score": scores.home_score,
            "away_score": scores.away_score,
            "status": "finished"
        }}
    )
    
    logger.info(f"Match {match_id} score updated: {scores.home_score}-{scores.away_score}")
    
    return {
        "message": "Resultado actualizado",
        "match_id": match_id,
        "score": f"{scores.home_score}-{scores.away_score}"
    }

@api_router.post("/admin/jornada/{jornada_id}/calculate-points")
async def calculate_jornada_points(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    """Calculate points for all users in a jornada"""
    jornada_obj_id = ObjectId(jornada_id)
    
    # Get jornada
    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jornada no encontrada"
        )
    
    # Get all matches with results
    matches = await db.matches.find({
        "jornada_id": jornada_obj_id,
        "status": "finished"
    }).to_list(100)
    
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay partidos finalizados en esta jornada"
        )
    
    # Calculate actual results
    match_results = {}
    for match in matches:
        match_id = match["_id"]
        home = match["home_score"]
        away = match["away_score"]
        
        if home > away:
            result = "HOME"
        elif away > home:
            result = "AWAY"
        else:
            result = "DRAW"
        
        match_results[match_id] = result
    
    # Get all selections for this jornada
    all_selections = await db.quiniela_selections.find({
        "jornada_id": jornada_obj_id
    }).to_list(10000)
    
    # Group by user
    user_selections = {}
    for sel in all_selections:
        user_id = sel["user_id"]
        if user_id not in user_selections:
            user_selections[user_id] = []
        user_selections[user_id].append(sel)
    
    # Calculate points for each user
    users_updated = 0
    total_points_awarded = 0
    
    for user_id, selections in user_selections.items():
        points = 0
        for sel in selections:
            match_id = sel["match_id"]
            if match_id in match_results:
                if sel["selection"] == match_results[match_id]:
                    points += 3  # 3 points per correct prediction (reglas oficiales)
        
        if points > 0:
            # Save points log
            await db.points_log.insert_one({
                "user_id": user_id,
                "jornada_id": jornada_obj_id,
                "source": "QUINIELA",
                "points": points,
                "created_at": datetime.utcnow()
            })

            # Update user total points
            await db.users.update_one(
                {"_id": user_id},
                {"$inc": {"total_points": points}}
            )

            users_updated += 1
            total_points_awarded += points
    
    # Update jornada status
    await db.jornadas.update_one(
        {"_id": jornada_obj_id},
        {"$set": {"status": "finished"}}
    )
    
    logger.info(f"Calculated points for jornada {jornada_id}: {users_updated} users, {total_points_awarded} points")
    
    return {
        "message": "Puntos calculados exitosamente",
        "jornada_id": jornada_id,
        "users_updated": users_updated,
        "total_points_awarded": total_points_awarded
    }


@api_router.post("/admin/process-jornada/{jornada_id}")
async def process_jornada_endpoint(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    """
    Procesa completamente una jornada:
    1. Resultados de partidos (365Scores → ESPN fallback)
    2. Puntos de FuchoQuiniela
    3. Stats de jugadores (ESPN)
    4. Puntos de FuchoOnce (Fantasy)
    5. Logros y achievements
    """
    result = await _process_jornada_core(jornada_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@api_router.post("/admin/fantasy/simulate-jornada/{jornada_id}")
async def simulate_fantasy_jornada(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    """
    Simula una jornada completa de Fantasy con estadísticas mock.
    Genera stats para todos los jugadores y calcula puntos.
    """
    import random
    
    jornada_obj_id = ObjectId(jornada_id)
    
    # Verificar jornada
    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")
    
    # Obtener partidos de esta jornada
    matches = await db.matches.find({"jornada_id": jornada_obj_id}).to_list(20)
    if not matches:
        raise HTTPException(status_code=400, detail="No hay partidos en esta jornada")
    
    # Generar resultados y estadísticas mock para cada partido
    match_results = []
    player_stats_bulk = []
    
    for match in matches:
        home_team_id = match["home_team_id"]
        away_team_id = match["away_team_id"]
        
        # Generar marcador realista
        home_score = random.choices([0, 1, 2, 3, 4], weights=[20, 35, 25, 15, 5])[0]
        away_score = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 12, 3])[0]
        
        # Actualizar partido
        await db.matches.update_one(
            {"_id": match["_id"]},
            {"$set": {
                "home_score": home_score,
                "away_score": away_score,
                "status": "finished"
            }}
        )
        
        match_results.append({
            "match_id": str(match["_id"]),
            "home_team_id": str(home_team_id),
            "away_team_id": str(away_team_id),
            "home_score": home_score,
            "away_score": away_score
        })
        
        # Generar estadísticas para jugadores de ambos equipos
        for team_id, is_home, goals_scored, goals_conceded in [
            (home_team_id, True, home_score, away_score),
            (away_team_id, False, away_score, home_score)
        ]:
            # Obtener jugadores del equipo
            players = await db.players.find({"team_id": team_id}).to_list(30)
            
            # Distribuir goles entre jugadores
            goals_to_assign = goals_scored
            
            for player in players:
                position = player.get("position", "MED")
                
                # Generar estadísticas realistas
                played = random.random() > 0.1  # 90% juegan
                minutes = random.randint(60, 90) if played else random.randint(0, 45) if random.random() > 0.5 else 0
                
                stats = {
                    "match_id": match["_id"],
                    "jornada_id": jornada_obj_id,
                    "player_id": player["_id"],
                    "team_id": team_id,
                    "position": position,
                    "minutes": minutes,
                    "goals": 0,
                    "assists": 0,
                    "clean_sheet": goals_conceded == 0 and minutes >= 60,
                    "goals_conceded": goals_conceded if position in ["POR", "DEF"] else 0,
                    "yellow_card": 1 if random.random() < 0.15 else 0,
                    "red_card": 1 if random.random() < 0.02 else 0,
                    "saves": random.randint(0, 6) if position == "POR" else 0,
                    "penalty_saved": 1 if position == "POR" and random.random() < 0.05 else 0,
                    "penalty_missed": 0,
                    "own_goal": 1 if random.random() < 0.01 else 0,
                    "man_of_the_match": False,
                    "created_at": datetime.utcnow()
                }
                
                # Asignar goles a delanteros/medios principalmente
                if goals_to_assign > 0 and minutes >= 45:
                    if position == "DEL" and random.random() < 0.5:
                        stats["goals"] = min(goals_to_assign, random.randint(1, 2))
                        goals_to_assign -= stats["goals"]
                    elif position == "MED" and random.random() < 0.3:
                        stats["goals"] = min(goals_to_assign, 1)
                        goals_to_assign -= stats["goals"]
                    elif position == "DEF" and random.random() < 0.1:
                        stats["goals"] = min(goals_to_assign, 1)
                        goals_to_assign -= stats["goals"]
                
                # Asignar asistencias
                if stats["goals"] == 0 and random.random() < 0.2 and minutes >= 45:
                    stats["assists"] = 1
                
                player_stats_bulk.append(stats)
        
        # Asignar jugador del partido a uno al azar
        if player_stats_bulk:
            match_players = [p for p in player_stats_bulk if p["match_id"] == match["_id"]]
            if match_players:
                motm_idx = random.randint(0, len(match_players) - 1)
                match_players[motm_idx]["man_of_the_match"] = True
    
    # Guardar todas las estadísticas
    if player_stats_bulk:
        # Eliminar stats anteriores de esta jornada
        await db.player_match_stats.delete_many({"jornada_id": jornada_obj_id})
        await db.player_match_stats.insert_many(player_stats_bulk)
    
    # Ahora calcular puntos para todos los equipos fantasy
    fantasy_results = await calculate_fantasy_points(jornada_id)
    
    return {
        "message": "Jornada simulada exitosamente",
        "jornada_id": jornada_id,
        "matches_simulated": len(match_results),
        "match_results": match_results,
        "fantasy_results": fantasy_results
    }

@api_router.get("/fantasy/rankings/jornada/{jornada_id}")
async def get_fantasy_jornada_rankings(jornada_id: str):
    """Obtener ranking de Fantasy para una jornada específica"""
    jornada_obj_id = ObjectId(jornada_id)
    
    # Obtener puntos de la jornada
    points_logs = await db.fantasy_points_log.find({
        "jornada_id": jornada_obj_id
    }).sort("total_points", -1).to_list(100)
    
    rankings = []
    for idx, log in enumerate(points_logs):
        fantasy_team = await db.fantasy_teams.find_one({"_id": log["fantasy_team_id"]})
        user = await db.users.find_one({"_id": log["user_id"]})
        
        rankings.append({
            "rank": idx + 1,
            "team_name": fantasy_team.get("name", "Unknown") if fantasy_team else "Unknown",
            "user_name": user.get("display_name", "Unknown") if user else "Unknown",
            "total_points": log["total_points"],
            "dt_points": log.get("dt_points", 0),
            "players_breakdown": log.get("players_breakdown", [])
        })
    
    return {"rankings": rankings, "jornada_id": jornada_id}

@api_router.get("/fantasy/rankings/general")
async def get_fantasy_general_rankings():
    """Obtener ranking general de Fantasy (acumulado)"""
    # Agregar puntos de todas las jornadas por equipo
    pipeline = [
        {"$group": {
            "_id": "$fantasy_team_id",
            "total_points": {"$sum": "$total_points"},
            "jornadas_played": {"$sum": 1}
        }},
        {"$sort": {"total_points": -1}},
        {"$limit": 100}
    ]
    
    aggregated = await db.fantasy_points_log.aggregate(pipeline).to_list(100)
    
    rankings = []
    for idx, item in enumerate(aggregated):
        fantasy_team = await db.fantasy_teams.find_one({"_id": item["_id"]})
        if fantasy_team:
            user = await db.users.find_one({"_id": fantasy_team["user_id"]})
            rankings.append({
                "rank": idx + 1,
                "team_name": fantasy_team.get("name", "Unknown"),
                "user_name": user.get("display_name", "Unknown") if user else "Unknown",
                "total_points": item["total_points"],
                "jornadas_played": item["jornadas_played"]
            })
    
    return {"rankings": rankings}

# ============ FANTASY ROUTES ============

@api_router.post("/fantasy/team")
async def create_or_update_fantasy_team(
    team_data: FantasyTeamCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create or update user's fantasy team name"""
    # Check if user already has a team
    existing_team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    
    if existing_team:
        # Update name
        await db.fantasy_teams.update_one(
            {"_id": existing_team["_id"]},
            {"$set": {"name": team_data.name}}
        )
        return {
            "message": "Nombre de equipo actualizado",
            "team_id": str(existing_team["_id"]),
            "name": team_data.name
        }
    else:
        # Create new team
        team_doc = {
            "user_id": current_user["_id"],
            "name": team_data.name,
            "created_at": datetime.utcnow()
        }
        result = await db.fantasy_teams.insert_one(team_doc)
        
        logger.info(f"User {current_user['email']} created fantasy team: {team_data.name}")
        
        return {
            "message": "Equipo fantasy creado",
            "team_id": str(result.inserted_id),
            "name": team_data.name
        }

@api_router.get("/fantasy/my-team")
async def get_my_fantasy_team(current_user: dict = Depends(get_current_user)):
    """Get user's fantasy team"""
    team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    
    if not team:
        # Return default name
        default_name = f"{current_user['display_name']} - FC"
        return {
            "exists": False,
            "default_name": default_name
        }
    
    return {
        "exists": True,
        "team_id": str(team["_id"]),
        "name": team["name"],
        "created_at": team["created_at"]
    }

@api_router.get("/players")
async def get_players(
    position: Optional[str] = None,
    team_id: Optional[str] = None,
    team_name: Optional[str] = None
):
    """Get players filtered by position and/or team"""
    competition = await get_active_competition()
    query = {"competition": competition}
    
    if position:
        query["position"] = position
    
    if team_id:
        try:
            query["team_id"] = ObjectId(team_id)
        except:
            query["team_id"] = team_id

    if team_name:
        query["team_name"] = {"$regex": team_name, "$options": "i"}
    
    players = await db.players.find(query).to_list(1000)
    
    # Format response
    formatted_players = []
    for player in players:
        try:
            team_id_val = player.get("team_id")
            team = None
            if team_id_val:
                if isinstance(team_id_val, ObjectId):
                    team = await db.teams.find_one({"_id": team_id_val})
                else:
                    try:
                        team = await db.teams.find_one({"_id": ObjectId(str(team_id_val))})
                    except:
                        pass
            
            formatted_players.append({
                "id": str(player["_id"]),
                "name": player.get("name", ""),
                "number": player.get("number", 0),
                "position": player.get("position", ""),
                "team_name": player.get("team_name", ""),
                "nationality": player.get("nationality", ""),
                "photo": player.get("photo", ""),
                "goals": player.get("goals", 0),
                "assists": player.get("assists", 0),
                "appearances": player.get("appearances", 0),
                "rating": player.get("rating", "0"),
                "team": {
                    "id": str(team["_id"]),
                    "name": team["name"],
                    "short_name": team.get("short_name", ""),
                    "shield_url": team.get("shield_url", "")
                } if team else None,
            })
        except Exception as e:
            logger.error(f"Error formatting player: {e}")
            continue
    
    return {"players": formatted_players, "total": len(formatted_players)}

@api_router.post("/fantasy/lineup")
async def submit_fantasy_lineup(
    lineup: FantasyLineupSubmit,
    current_user: dict = Depends(get_current_user)
):
    """Submit fantasy lineup for a jornada"""
    # Get user's fantasy team
    team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    if not team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes crear tu equipo fantasy"
        )
    
    try:
        jornada_id = ObjectId(lineup.jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")

    # Check if lineup already exists
    existing = await db.fantasy_lineups.find_one({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_id
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya enviaste tu alineación para esta jornada"
        )
    
    # Validate 11 players + optional DT
    if len(lineup.players) != 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes seleccionar exactamente 11 jugadores"
        )
    
    # Save lineup
    lineup_docs = []
    for player_data in lineup.players:
        lineup_docs.append({
            "fantasy_team_id": team["_id"],
            "jornada_id": jornada_id,
            "player_id": ObjectId(player_data["player_id"]),
            "position_slot": player_data["position_slot"],
            "is_dt": False,
            "created_at": datetime.utcnow()
        })
    
    # Add DT if provided
    if lineup.dt_team_id:
        lineup_docs.append({
            "fantasy_team_id": team["_id"],
            "jornada_id": jornada_id,
            "dt_team_id": ObjectId(lineup.dt_team_id),
            "position_slot": "DT",
            "is_dt": True,
            "created_at": datetime.utcnow()
        })
    
    await db.fantasy_lineups.insert_many(lineup_docs)
    
    # Award first lineup achievement
    await award_achievement(current_user["_id"], "first_lineup")
    
    return {
        "message": "Alineación guardada exitosamente",
        "jornada_id": lineup.jornada_id,
        "players_count": len(lineup_docs)
    }

@api_router.get("/fantasy/lineup/{jornada_id}")
async def get_fantasy_lineup(
    jornada_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user's fantasy lineup for a jornada"""
    team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    if not team:
        return {"submitted": False, "lineup": []}
    
    try:
        jornada_obj_id = ObjectId(jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")

    lineup = await db.fantasy_lineups.find({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_obj_id
    }).to_list(100)
    
    if not lineup:
        return {"submitted": False, "lineup": []}
    
    # Format lineup with player details
    formatted_lineup = []
    for item in lineup:
        if item.get("is_dt"):
            # DT item
            dt_team = await db.teams.find_one({"_id": item.get("dt_team_id")})
            formatted_lineup.append({
                "position_slot": "DT",
                "is_dt": True,
                "team": {
                    "id": str(dt_team["_id"]),
                    "name": dt_team["name"],
                    "short_name": dt_team["short_name"],
                    "shield_url": dt_team["shield_url"]
                } if dt_team else None
            })
        else:
            # Player item
            player = await db.players.find_one({"_id": item["player_id"]})
            if player:
                player_team = await db.teams.find_one({"_id": player["team_id"]})
                formatted_lineup.append({
                    "position_slot": item["position_slot"],
                    "is_dt": False,
                    "player": {
                        "id": str(player["_id"]),
                        "name": player["name"],
                        "number": player.get("number", 0),
                        "position": player["position"],
                        "team": {
                            "id": str(player_team["_id"]),
                            "name": player_team["name"],
                            "short_name": player_team["short_name"],
                            "shield_url": player_team["shield_url"]
                        } if player_team else None
                    }
                })
    
    return {
        "submitted": True,
        "lineup": formatted_lineup
    }


@api_router.get("/fantasy/results/{jornada_id}")
async def get_fantasy_results(
    jornada_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna la alineación del usuario con puntos desglosados por jugador
    para la jornada especificada.
    Usa fantasy_points_log si ya fue procesado, o calcula en tiempo real.
    """
    jornada_obj_id = ObjectId(jornada_id)
    team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    if not team:
        return {"has_lineup": False, "players": [], "total_points": 0}

    # ── 1. Buscar en fantasy_points_log (ya procesado) ───────────────────
    log = await db.fantasy_points_log.find_one({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_obj_id,
    })
    if log:
        return {
            "has_lineup":    True,
            "team_name":     team.get("name", "Mi Equipo"),
            "total_points":  log.get("total_points", 0),
            "dt_points":     log.get("dt_points", 0),
            "players":       log.get("players_breakdown", []),
            "processed":     True,
            "jornada_id":    jornada_id,
        }

    # ── 2. Calcular en tiempo real si no está procesado ──────────────────
    lineup_items = await db.fantasy_lineups.find({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_obj_id,
    }).to_list(100)

    if not lineup_items:
        return {"has_lineup": False, "players": [], "total_points": 0}

    # Load all player stats for the jornada
    all_stats = await db.player_match_stats.find(
        {"jornada_id": jornada_obj_id}
    ).to_list(5000)
    stats_by_player_id = {s["player_id"]: s for s in all_stats}

    players_result = []
    total_pts = 0

    for item in lineup_items:
        if item.get("is_dt"):
            continue  # Skip DT for per-player breakdown

        player_id = item.get("player_id")
        player = await db.players.find_one({"_id": player_id}) if player_id else None
        if not player:
            continue

        player_team = await db.teams.find_one({"_id": player["team_id"]})
        position = player.get("position", "MED")
        stats = stats_by_player_id.get(player_id, {})

        result = calculate_player_points(stats, position)
        total_pts += result["total_points"]

        players_result.append({
            "player_id":     str(player_id),
            "player_name":   player.get("name", "?"),
            "position":      position,
            "position_slot": item.get("position_slot"),
            "points":        result["total_points"],
            "breakdown":     result["breakdown"],
            "is_mvp":        stats.get("is_mvp", False),
            "minutes":       stats.get("minutes", 0),
            "goals":         stats.get("goals", 0),
            "assists":       stats.get("assists", 0),
            "team_shield":   player_team.get("shield_url", "") if player_team else "",
            "team_name":     player_team.get("short_name", "") if player_team else "",
        })

    return {
        "has_lineup":   True,
        "team_name":    team.get("name", "Mi Equipo"),
        "total_points": total_pts,
        "dt_points":    0,
        "players":      players_result,
        "processed":    len(all_stats) > 0,
        "jornada_id":   jornada_id,
    }

# ──────────────────────────────────────────────────────────────────────────────
#  LIVE SCORES — Caché 55 segundos
# ──────────────────────────────────────────────────────────────────────────────
_live_scores_cache: dict = {"data": None, "fetched_at": None}
_LIVE_CACHE_TTL = 55  # seconds

@api_router.get("/jornadas/current/live-scores")
async def get_live_scores():
    """
    Retorna los partidos en curso o de hoy.
    Llama a 365Scores API y cachea 55 segundos.
    """
    global _live_scores_cache
    now = datetime.utcnow()

    # Check cache
    if _live_scores_cache["data"] is not None and _live_scores_cache["fetched_at"]:
        age = (now - _live_scores_cache["fetched_at"]).total_seconds()
        if age < _LIVE_CACHE_TTL:
            return _live_scores_cache["data"]

    # Fetch today's games from 365Scores
    today_start = now.replace(hour=0, minute=0, second=0)
    today_end = now.replace(hour=23, minute=59, second=59)

    from services.scores_service import _fetch_365scores, _normalize_name, _STATUS_MAP

    games = await _fetch_365scores(today_start, today_end)

    live_matches = []
    all_matches = []

    for g in games:
        status_grp = g.get("statusGroup", 1)
        status = _STATUS_MAP.get(status_grp, "scheduled")

        home_name = _normalize_name(g.get("homeCompetitor", {}).get("name", ""))
        away_name = _normalize_name(g.get("awayCompetitor", {}).get("name", ""))
        home_score = g.get("homeCompetitor", {}).get("score")
        away_score = g.get("awayCompetitor", {}).get("score")
        game_time = g.get("gameTimeDisplay", "")
        start_time = g.get("startTime", "")

        match_data = {
            "home_name": home_name,
            "away_name": away_name,
            "home_score": int(home_score) if home_score is not None else None,
            "away_score": int(away_score) if away_score is not None else None,
            "status": status,
            "game_time": game_time,
            "start_time": start_time,
        }
        all_matches.append(match_data)
        if status == "live":
            live_matches.append(match_data)

    # ── Fallback a DB cuando 365Scores no devuelve datos ─────────────────────
    # Si la API externa no tiene partidos hoy, consultar DB por matches "live"
    if not all_matches:
        try:
            db_live = await db.matches.find({"status": "live"}).to_list(20)
            for dm in db_live:
                ht = await db.teams.find_one({"_id": dm["home_team_id"]})
                at = await db.teams.find_one({"_id": dm["away_team_id"]})
                if not ht or not at:
                    continue
                m = {
                    "home_name": ht.get("name", "?"),
                    "away_name": at.get("name", "?"),
                    "home_score": dm.get("home_score"),
                    "away_score": dm.get("away_score"),
                    "status": "live",
                    "game_time": str(dm.get("game_time", "")),
                    "start_time": "",
                }
                all_matches.append(m)
                live_matches.append(m)
        except Exception as exc:
            logger.warning(f"DB live fallback error: {exc}")

    result = {
        "has_live":    len(live_matches) > 0,
        "live_count":  len(live_matches),
        "live_matches":  live_matches,
        "all_today":   all_matches,
        "fetched_at":  now.isoformat(),
        "source":      "365scores" if games else ("db_fallback" if live_matches else "empty"),
    }

    _live_scores_cache["data"] = result
    _live_scores_cache["fetched_at"] = now
    return result



async def get_fantasy_rankings():
    """Get fantasy rankings"""
    # Get all fantasy teams with their users
    teams = await db.fantasy_teams.find().to_list(1000)
    
    rankings = []
    for team in teams:
        user = await db.users.find_one({"_id": team["user_id"]})
        if user:
            # Get total fantasy points from fantasy_points_log
            points = await db.fantasy_points_log.find({
                "user_id": user["_id"]
            }).to_list(1000)
            
            total_points = sum(p.get("total_points", 0) for p in points)
            
            rankings.append({
                "user_id": str(user["_id"]),
                "team_name": team["name"],
                "display_name": user["display_name"],
                "points": total_points
            })
    
    # Sort by points
    rankings.sort(key=lambda x: x["points"], reverse=True)
    
    # Add positions
    for idx, ranking in enumerate(rankings, 1):
        ranking["position"] = idx
    
    return {"rankings": rankings}

# ============ ADMIN ROUTES FOR FANTASY ============

@api_router.post("/admin/seed-players")
async def seed_players(current_user: dict = Depends(get_admin_user)):
    """Seed players for all teams"""
    teams = await db.teams.find().to_list(100)
    
    if len(teams) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes crear los equipos"
        )
    
    # Clear existing players
    await db.players.delete_many({})
    
    positions = ["POR", "DEF", "MED", "DEL"]
    position_names = {
        "POR": ["Portero", "Arquero"],
        "DEF": ["Defensa Central", "Lateral Derecho", "Lateral Izquierdo"],
        "MED": ["Mediocampista", "Volante", "Medio Centro"],
        "DEL": ["Delantero", "Extremo", "Punta"]
    }
    
    players_created = 0
    
    for team in teams:
        # Create players for each position
        # Porteros (2)
        for i in range(2):
            player = {
                "name": f"{position_names['POR'][i % len(position_names['POR'])]} {i+1}",
                "team_id": team["_id"],
                "position": "POR",
                "number": i + 1,
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0
                },
                "created_at": datetime.utcnow()
            }
            await db.players.insert_one(player)
            players_created += 1
        
        # Defensas (6)
        for i in range(6):
            player = {
                "name": f"{position_names['DEF'][i % len(position_names['DEF'])]} {i+1}",
                "team_id": team["_id"],
                "position": "DEF",
                "number": i + 3,
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0
                },
                "created_at": datetime.utcnow()
            }
            await db.players.insert_one(player)
            players_created += 1
        
        # Mediocampistas (8)
        for i in range(8):
            player = {
                "name": f"{position_names['MED'][i % len(position_names['MED'])]} {i+1}",
                "team_id": team["_id"],
                "position": "MED",
                "number": i + 9,
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0
                },
                "created_at": datetime.utcnow()
            }
            await db.players.insert_one(player)
            players_created += 1
        
        # Delanteros (5)
        for i in range(5):
            player = {
                "name": f"{position_names['DEL'][i % len(position_names['DEL'])]} {i+1}",
                "team_id": team["_id"],
                "position": "DEL",
                "number": i + 17,
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0
                },
                "created_at": datetime.utcnow()
            }
            await db.players.insert_one(player)
            players_created += 1
    
    logger.info(f"Seeded {players_created} players for {len(teams)} teams")
    
    return {
        "message": f"Se crearon {players_created} jugadores para {len(teams)} equipos",
        "players_count": players_created,
        "teams_count": len(teams)
    }

@api_router.post("/admin/seed-real-data")
async def seed_real_data(current_user: dict = Depends(get_admin_user)):
    """Seed database with REAL Liga MX teams and players from real_liga_mx_data.py"""
    import random
    
    logger.info("🏟️ Seeding REAL Liga MX data...")
    
    # Clear existing data
    await db.teams.delete_many({})
    await db.players.delete_many({})
    await db.jornadas.delete_many({})
    await db.matches.delete_many({})
    
    teams_created = 0
    players_created = 0
    team_ids = []
    
    for team_data in LIGA_MX_TEAMS:
        # Insert team
        team_doc = {
            "name": team_data["name"],
            "short_name": team_data["short_name"],
            "color": team_data.get("color", "#000000"),
            "shield_url": team_data["shield_url"],
            "created_at": datetime.utcnow()
        }
        team_result = await db.teams.insert_one(team_doc)
        team_id = team_result.inserted_id
        team_ids.append(team_id)
        teams_created += 1
        
        # Insert players for this team
        for player_data in team_data.get("players", []):
            player_doc = {
                "name": player_data["name"],
                "team_id": team_id,
                "position": player_data["position"],
                "number": player_data["number"],
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0
                },
                "created_at": datetime.utcnow()
            }
            await db.players.insert_one(player_doc)
            players_created += 1
    
    # Create 17 jornadas for the season with dates relative to TODAY
    now = datetime.utcnow()
    ACTIVE_WEEK = 11  # La temporada va por la jornada 11 (mitad de temporada)
    jornadas_created = 0
    
    for week in range(1, 18):
        # Fechas relativas a hoy: jornada 11 = esta semana, anteriores = pasadas, siguientes = futuras
        weeks_from_active = week - ACTIVE_WEEK
        week_start = now + timedelta(weeks=weeks_from_active)
        week_end = week_start + timedelta(days=7)
        
        is_past = weeks_from_active < 0
        is_current = weeks_from_active == 0
        week_status = "finished" if is_past else ("in_progress" if is_current else "upcoming")
        match_status_val = "finished" if is_past else "scheduled"
        
        jornada_data = {
            "week_number": week,
            "start_date": week_start,
            "end_date": week_end,
            "status": week_status,
            "is_active": is_current,  # Solo jornada 11 activa
            "created_at": now
        }
        
        jornada_result = await db.jornadas.insert_one(jornada_data)
        jornada_id = jornada_result.inserted_id
        
        # Shuffle teams and create 9 matches per jornada
        shuffled = list(team_ids)
        random.shuffle(shuffled)
        
        matches = []
        for i in range(0, min(len(shuffled), 18), 2):
            if i + 1 < len(shuffled):
                match = {
                    "jornada_id": jornada_id,
                    "home_team_id": shuffled[i],
                    "away_team_id": shuffled[i + 1],
                    "start_at": week_start + timedelta(hours=i),
                    "status": match_status_val,
                    "home_score": None,
                    "away_score": None,
                    "created_at": now
                }
                matches.append(match)
        
        if matches:
            await db.matches.insert_many(matches)
        
        jornadas_created += 1
    
    logger.info(f"✅ REAL data seeded: {teams_created} teams, {players_created} players, {jornadas_created} jornadas")
    
    return {
        "message": f"🏟️ Datos REALES de Liga MX cargados exitosamente",
        "teams_created": teams_created,
        "players_created": players_created,
        "jornadas_created": jornadas_created,
        "teams": [t["name"] for t in LIGA_MX_TEAMS]
    }

# ─── ENDPOINTS ───────────────────────────────────────────────────────────────

@api_router.get("/achievements/catalog")
async def get_achievements_catalog():
    """Catálogo público de logros."""
    return {
        "achievements": [
            {**a, "description": "???" if a["secret"] else a["description"],
                  "emoji": "🔒" if a["secret"] else a["emoji"]}
            for a in ACHIEVEMENTS_CATALOG
        ],
        "total": len(ACHIEVEMENTS_CATALOG)
    }


@api_router.get("/achievements/my")
async def get_my_achievements(current_user: dict = Depends(get_current_user)):
    """Logros + rachas del usuario autenticado."""
    user_id = current_user["_id"]

    unlocked_docs = await db.user_achievements.find({"user_id": user_id}).to_list(200)
    unlocked_map  = {d["achievement_id"]: d["unlocked_at"] for d in unlocked_docs}

    streak_doc = await db.user_streaks.find_one({"user_id": user_id}) or {}

    result = []
    for a in ACHIEVEMENTS_CATALOG:
        unlocked = a["id"] in unlocked_map
        result.append({
            "id":          a["id"],
            "title":       a["title"],
            "description": a["description"] if (not a["secret"] or unlocked) else "Logro secreto — ¡sigue jugando!",
            "emoji":       a["emoji"]       if (not a["secret"] or unlocked) else "🔒",
            "category":    a["category"],
            "secret":      a["secret"],
            "unlocked":    unlocked,
            "unlocked_at": unlocked_map[a["id"]].isoformat() if unlocked else None,
        })

    # Desbloqueados primero
    result.sort(key=lambda x: (not x["unlocked"], x["category"]))

    return {
        "achievements":    result,
        "total":           len(result),
        "unlocked_count":  len(unlocked_map),
        "streaks": {
            "quiniela_current":       streak_doc.get("quiniela_streak", 0),
            "quiniela_best":          streak_doc.get("quiniela_streak_best", 0),
            "win_current":            streak_doc.get("win_streak", 0),
            "win_best":               streak_doc.get("win_streak_best", 0),
            "correct_current":        streak_doc.get("correct_answers_streak", 0),
            "correct_best":           streak_doc.get("correct_answers_best", 0),
            "fantasy_current":        streak_doc.get("fantasy_streak", 0),
        }
    }


@api_router.post("/admin/achievements/check/{jornada_id}")
async def trigger_achievement_check(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    """Admin: verifica y otorga logros a TODOS los usuarios tras una jornada."""
    all_users = await db.users.find().to_list(10000)
    summary = []

    for user in all_users:
        new = await check_and_award_achievements_after_jornada(user["_id"], jornada_id)
        if new:
            summary.append({
                "user":             user.get("display_name"),
                "new_achievements": new
            })

    # Resetear rachas de usuarios que NO participaron esta jornada
    jornada_obj_id = ObjectId(jornada_id)
    participant_ids = set()
    async for sel in db.quiniela_selections.find({"jornada_id": jornada_obj_id}):
        participant_ids.add(sel["user_id"])

    reset_count = 0
    for user in all_users:
        if user["_id"] not in participant_ids:
            previous = await reset_participation_streak(user["_id"])
            if previous > 0:
                reset_count += 1
                logger.info(f"Racha reseteada: {user.get('display_name')} tenía {previous}")

    return {
        "message":                  f"Logros verificados: {len(all_users)} usuarios",
        "new_achievements_awarded": summary,
        "streaks_reset":            reset_count
    }


# ============ USER STATS ============

@api_router.get("/stats/my")
async def get_my_stats(current_user: dict = Depends(get_current_user)):
    """Retorna estadísticas completas del usuario autenticado para la temporada."""
    user_id = current_user["_id"]

    # 1. Quiniela points logs
    quiniela_logs = await db.points_log.find(
        {"user_id": user_id, "source": "QUINIELA"}
    ).to_list(1000)

    total_quiniela_pts = sum(log.get("points", 0) for log in quiniela_logs)
    jornada_ids_quiniela = list(set(log["jornada_id"] for log in quiniela_logs))
    jornadas_quiniela = len(jornada_ids_quiniela)
    mejor_jornada = max((log.get("points", 0) for log in quiniela_logs), default=0)
    # Cada punto = 1 acierto en quiniela
    total_aciertos = total_quiniela_pts
    promedio_aciertos = round(total_aciertos / jornadas_quiniela, 1) if jornadas_quiniela > 0 else 0

    # 2. Fantasy participation
    fantasy_jornadas = await db.fantasy_lineups.distinct("jornada_id", {"user_id": user_id})
    jornadas_fantasy = len(fantasy_jornadas)

    # 3. Fantasy points
    fantasy_pts_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$total_points"}}}
    ]
    fantasy_pts_result = await db.fantasy_points_log.aggregate(fantasy_pts_pipeline).to_list(1)
    total_fantasy_pts = fantasy_pts_result[0]["total"] if fantasy_pts_result else 0

    # 4. Total de puntos acumulados (quiniela + fantasy)
    total_puntos = total_quiniela_pts + total_fantasy_pts

    # 5. Win rate - % de jornadas donde quedó en Top 3 (global)
    top3_count = 0
    mejor_posicion = None
    if jornada_ids_quiniela:
        for jornada_id in jornada_ids_quiniela:
            user_pts = sum(
                log.get("points", 0)
                for log in quiniela_logs
                if log["jornada_id"] == jornada_id
            )
            all_for_jornada = await db.points_log.aggregate([
                {"$match": {"jornada_id": jornada_id, "source": "QUINIELA"}},
                {"$group": {"_id": "$user_id", "total": {"$sum": "$points"}}},
                {"$sort": {"total": -1}},
            ]).to_list(200)
            position = next(
                (i + 1 for i, p in enumerate(all_for_jornada) if str(p["_id"]) == str(user_id)),
                None
            )
            if position and position <= 3:
                top3_count += 1
            if position and (mejor_posicion is None or position < mejor_posicion):
                mejor_posicion = position

    win_rate = round((top3_count / jornadas_quiniela * 100)) if jornadas_quiniela > 0 else 0

    # 6. Ligas activas
    ligas_activas = await db.league_members.count_documents({"user_id": user_id})

    return {
        "total_puntos": total_puntos,
        "jornadas_quiniela": jornadas_quiniela,
        "mejor_jornada": mejor_jornada,
        "win_rate": win_rate,
        "total_aciertos": total_aciertos,
        "promedio_aciertos": promedio_aciertos,
        "jornadas_fantasy": jornadas_fantasy,
        "mejor_posicion": mejor_posicion,
        "ligas_activas": ligas_activas,
    }

# ============ ADMIN STATS DASHBOARD ============

@api_router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Dashboard de métricas para el admin de FuchoMX"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    from datetime import datetime, timedelta
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # Usuarios
    total_usuarios = await db.users.count_documents({})
    nuevos_hoy = await db.users.count_documents({"created_at": {"$gte": today_start}})
    nuevos_semana = await db.users.count_documents({"created_at": {"$gte": week_start}})
    nuevos_mes = await db.users.count_documents({"created_at": {"$gte": month_start}})

    # Jornadas
    total_jornadas = await db.jornadas.count_documents({})
    jornada_activa = await db.jornadas.find_one({"is_active": True})

    # Quinielas / predicciones
    total_predicciones = await db.quiniela_selections.count_documents({}) if hasattr(db, 'quiniela_selections') else 0
    try:
        total_predicciones = await db.quiniela_selections.count_documents({})
    except:
        total_predicciones = 0

    # Ligas
    try:
        total_ligas = await db.private_leagues.count_documents({})
        ligas_raw = await db.private_leagues.find(
            {}, {"name": 1, "mode": 1, "code": 1, "owner_id": 1, "created_at": 1}
        ).sort("created_at", -1).limit(20).to_list(20)
        ligas_detalle = []
        for liga in ligas_raw:
            owner = await db.users.find_one({"_id": liga["owner_id"]}, {"display_name": 1, "email": 1})
            miembros = await db.league_members.count_documents({"league_id": liga["_id"]})
            ligas_detalle.append({
                "id": str(liga["_id"]),
                "nombre": liga.get("name", "Sin nombre"),
                "modo": liga.get("mode", "quiniela"),
                "codigo": liga.get("code", ""),
                "creador": owner.get("display_name", owner.get("email", "?")) if owner else "?",
                "miembros": miembros,
                "creada": liga["created_at"].isoformat() if liga.get("created_at") else "",
            })
    except Exception as e:
        total_ligas = 0
        ligas_detalle = []

    # Fantasy
    try:
        total_fantasy = await db.fantasy_lineups.count_documents({})
    except:
        total_fantasy = 0

    # Últimos 5 usuarios registrados
    ultimos_usuarios = await db.users.find(
        {}, {"email": 1, "display_name": 1, "created_at": 1, "total_points": 1}
    ).sort("created_at", -1).limit(5).to_list(5)

    for u in ultimos_usuarios:
        u["_id"] = str(u["_id"])

    return {
        "usuarios": {
            "total": total_usuarios,
            "nuevos_hoy": nuevos_hoy,
            "nuevos_semana": nuevos_semana,
            "nuevos_mes": nuevos_mes,
            "ultimos": ultimos_usuarios,
        },
        "jornadas": {
            "total": total_jornadas,
            "activa": jornada_activa.get("week_number") if jornada_activa else None,
        },
        "predicciones": {
            "total": total_predicciones,
        },
        "ligas": {
            "total": total_ligas,
            "detalle": ligas_detalle,
        },
        "fantasy": {
            "total_lineups": total_fantasy,
        },
    }




# ============ API-FOOTBALL ENDPOINTS ============

from services.api_football_service import (
    get_players_by_team as _af_get_players,
    get_live_fixtures as _af_get_live,
    get_fixtures_by_date as _af_get_by_date,
)

@api_router.post("/admin/sync-players-api-football")
async def sync_players_from_api_football(
    current_user: dict = Depends(get_current_user)
):
    """Sincroniza jugadores de todos los equipos desde API-Football (solo admin)"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    total_updated = 0
    errors = []

    teams = await db.teams.find({}).to_list(20)
    for team in teams:
        team_name = team.get("name", "")
        try:
            players = await _af_get_players(team_name, API_FOOTBALL_KEY)
            if not players:
                continue

            for p in players:
                await db.players.update_one(
                    {"api_football_id": p["api_id"]},
                    {"$set": {
                        "api_football_id": p["api_id"],
                        "name":       p["name"],
                        "firstname":  p["firstname"],
                        "lastname":   p["lastname"],
                        "photo":      p["photo"],
                        "position":   p["position"],
                        "team_name":  team_name,
                        "team_id":    str(team["_id"]),
                        "nationality": p["nationality"],
                        "goals":      p["goals"],
                        "assists":    p["assists"],
                        "appearances": p["appearances"],
                        "rating":     p["rating"],
                        "updated_at": datetime.utcnow(),
                    }},
                    upsert=True
                )
                total_updated += 1

            logger.info(f"✅ {team_name}: {len(players)} jugadores sincronizados")
        except Exception as e:
            errors.append(f"{team_name}: {str(e)}")
            logger.error(f"❌ Error sincronizando {team_name}: {e}")

    return {
        "message": "Sincronización completada",
        "players_updated": total_updated,
        "errors": errors,
    }


@api_router.get("/fixtures/live")
async def get_live_fixtures_api_football():
    """Obtiene partidos en vivo de Liga MX desde API-Football"""
    try:
        fixtures = await _af_get_live(API_FOOTBALL_KEY)
        return {"fixtures": fixtures, "source": "api-football"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/fixtures/today")
async def get_today_fixtures():
    """Obtiene partidos de hoy de Liga MX desde API-Football"""
    try:
        from datetime import date
        fixtures = await _af_get_by_date(date.today(), API_FOOTBALL_KEY)
        return {"fixtures": fixtures, "source": "api-football", "date": date.today().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@api_router.post("/admin/close-all-jornadas")
async def close_all_jornadas(current_user: dict = Depends(get_current_user)):
    """Cierra todas las jornadas activas - solo admin"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")
    
    result = await db.jornadas.update_many(
        {"is_active": True},
        {"$set": {"is_active": False, "processed": True}}
    )
    
    return {
        "message": f"{result.modified_count} jornada(s) cerrada(s) correctamente",
        "modified": result.modified_count
    }


# ============ LIGUILLA JORNADAS ============

LIGUILLA_CUARTOS_MATCHES = [
    # Ida (ya jugados)
    {"home": "Pumas UNAM",  "away": "Club América",  "home_score": 3, "away_score": 3, "leg": "ida",    "date": "2026-05-08"},
    {"home": "Pachuca",     "away": "Toluca",         "home_score": 1, "away_score": 0, "leg": "ida",    "date": "2026-05-08"},
    {"home": "Guadalajara", "away": "Tigres UANL",   "home_score": 1, "away_score": 3, "leg": "ida",    "date": "2026-05-09"},
    {"home": "Cruz Azul",   "away": "Atlas",          "home_score": 3, "away_score": 2, "leg": "ida",    "date": "2026-05-09"},
    # Vuelta (ya jugados)
    {"home": "Club América",  "away": "Pumas UNAM",  "home_score": 3, "away_score": 3, "leg": "vuelta", "date": "2026-05-12"},
    {"home": "Toluca",        "away": "Pachuca",      "home_score": 0, "away_score": 2, "leg": "vuelta", "date": "2026-05-12"},
    {"home": "Tigres UANL",  "away": "Guadalajara",  "home_score": 0, "away_score": 2, "leg": "vuelta", "date": "2026-05-13"},
    {"home": "Atlas",         "away": "Cruz Azul",    "home_score": 0, "away_score": 1, "leg": "vuelta", "date": "2026-05-13"},
]

LIGUILLA_SEMIS_MATCHES = [
    # Ida (ya jugados)
    {"home": "Cruz Azul",   "away": "Guadalajara",  "home_score": 2, "away_score": 2, "leg": "ida",    "date": "2026-05-14"},
    {"home": "Pumas UNAM",  "away": "Pachuca",       "home_score": 0, "away_score": 1, "leg": "ida",    "date": "2026-05-15"},
    # Vuelta (hoy y ayer)
    {"home": "Guadalajara", "away": "Cruz Azul",    "home_score": 1, "away_score": 2, "leg": "vuelta", "date": "2026-05-16"},
    {"home": "Pachuca",     "away": "Pumas UNAM",   "home_score": None, "away_score": None, "leg": "vuelta", "date": "2026-05-17"},
]

@api_router.post("/admin/create-liguilla-jornadas")
async def create_liguilla_jornadas(current_user: dict = Depends(get_current_user)):
    """Crea las 3 jornadas de liguilla: Cuartos, Semis y Final (solo admin)"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    created = []

    # Verificar que existen equipos
    teams = await db.teams.find().to_list(100)
    team_map = {t["name"]: t["_id"] for t in teams}

    # ── 1. CUARTOS ──────────────────────────────────────────
    existing_cuartos = await db.jornadas.find_one({"type": "liguilla", "phase": "cuartos"})
    if not existing_cuartos:
        cuartos_doc = {
            "week_number": 18,
            "type": "liguilla",
            "phase": "cuartos",
            "title": "Liguilla Clausura 2026 — Cuartos",
            "active_teams": ["Pumas UNAM", "Guadalajara", "Cruz Azul", "Pachuca",
                           "Toluca", "Atlas", "Tigres UANL", "Club América"],
            "start_date": datetime(2026, 5, 8),
            "end_date": datetime(2026, 5, 13, 23, 59),
            "status": "finished",
            "is_active": False,
            "processed": True,
            "created_at": datetime.utcnow(),
        }
        cuartos_result = await db.jornadas.insert_one(cuartos_doc)
        cuartos_id = cuartos_result.inserted_id

        # Crear partidos de cuartos
        for m in LIGUILLA_CUARTOS_MATCHES:
            home_id = team_map.get(m["home"])
            away_id = team_map.get(m["away"])
            if home_id and away_id:
                await db.matches.insert_one({
                    "jornada_id": cuartos_id,
                    "home_team_id": home_id,
                    "away_team_id": away_id,
                    "home_score": m["home_score"],
                    "away_score": m["away_score"],
                    "status": "finished",
                    "leg": m["leg"],
                    "start_at": datetime.fromisoformat(m["date"]),
                    "created_at": datetime.utcnow(),
                })
        created.append("cuartos")

    # ── 2. SEMIS ─────────────────────────────────────────────
    existing_semis = await db.jornadas.find_one({"type": "liguilla", "phase": "semis"})
    if not existing_semis:
        semis_doc = {
            "week_number": 19,
            "type": "liguilla",
            "phase": "semis",
            "title": "Liguilla Clausura 2026 — Semifinales",
            "active_teams": ["Pumas UNAM", "Guadalajara", "Cruz Azul", "Pachuca"],
            "start_date": datetime(2026, 5, 14),
            "end_date": datetime(2026, 5, 17, 23, 59),
            "status": "in_progress",
            "is_active": True,
            "processed": False,
            "created_at": datetime.utcnow(),
        }
        semis_result = await db.jornadas.insert_one(semis_doc)
        semis_id = semis_result.inserted_id

        for m in LIGUILLA_SEMIS_MATCHES:
            home_id = team_map.get(m["home"])
            away_id = team_map.get(m["away"])
            if home_id and away_id:
                await db.matches.insert_one({
                    "jornada_id": semis_id,
                    "home_team_id": home_id,
                    "away_team_id": away_id,
                    "home_score": m["home_score"],
                    "away_score": m["away_score"],
                    "status": "finished" if m["home_score"] is not None else "scheduled",
                    "leg": m["leg"],
                    "start_at": datetime.fromisoformat(m["date"]),
                    "created_at": datetime.utcnow(),
                })
        created.append("semis")

    # ── 3. FINAL ─────────────────────────────────────────────
    existing_final = await db.jornadas.find_one({"type": "liguilla", "phase": "final"})
    if not existing_final:
        final_doc = {
            "week_number": 20,
            "type": "liguilla",
            "phase": "final",
            "title": "Liguilla Clausura 2026 — Final",
            "active_teams": ["Cruz Azul"],  # Se actualiza cuando sepamos el otro finalista
            "start_date": datetime(2026, 5, 22),
            "end_date": datetime(2026, 5, 25, 23, 59),
            "status": "upcoming",
            "is_active": False,
            "processed": False,
            "created_at": datetime.utcnow(),
        }
        await db.jornadas.insert_one(final_doc)
        created.append("final (pendiente finalista)")

    return {
        "message": f"Jornadas de liguilla creadas: {', '.join(created) if created else 'ya existían'}",
        "created": created,
    }


@api_router.post("/admin/activate-liguilla-final")
async def activate_liguilla_final(
    finalist: str,  # Nombre del equipo finalista (PUM o PAC)
    current_user: dict = Depends(get_current_user)
):
    """Activa la jornada Final con los 2 finalistas confirmados (solo admin)"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    # Cerrar semis
    await db.jornadas.update_one(
        {"type": "liguilla", "phase": "semis"},
        {"$set": {"is_active": False, "status": "finished", "processed": True}}
    )

    # Activar Final con los 2 equipos
    team_map = {"PUM": "Pumas UNAM", "PAC": "Pachuca"}
    finalist_name = team_map.get(finalist, finalist)

    result = await db.jornadas.update_one(
        {"type": "liguilla", "phase": "final"},
        {"$set": {
            "active_teams": ["Cruz Azul", finalist_name],
            "is_active": True,
            "status": "upcoming",
            "title": f"Liguilla Clausura 2026 — Final: Cruz Azul vs {finalist_name}",
        }}
    )

    # Crear el partido de la final en matches
    teams = await db.teams.find({"name": {"$in": ["Cruz Azul", finalist_name]}}).to_list(2)
    final_jornada = await db.jornadas.find_one({"type": "liguilla", "phase": "final"})

    if len(teams) == 2 and final_jornada:
        caz = next((t for t in teams if t["name"] == "Cruz Azul"), None)
        fin = next((t for t in teams if t["name"] == finalist_name), None)
        if caz and fin:
            # Partido de ida
            await db.matches.insert_one({
                "jornada_id": final_jornada["_id"],
                "home_team_id": caz["_id"],
                "away_team_id": fin["_id"],
                "home_score": None, "away_score": None,
                "status": "scheduled",
                "leg": "ida",
                "start_at": datetime(2026, 5, 22, 21, 0),
                "created_at": datetime.utcnow(),
            })
            # Partido de vuelta
            await db.matches.insert_one({
                "jornada_id": final_jornada["_id"],
                "home_team_id": fin["_id"],
                "away_team_id": caz["_id"],
                "home_score": None, "away_score": None,
                "status": "scheduled",
                "leg": "vuelta",
                "start_at": datetime(2026, 5, 25, 21, 0),
                "created_at": datetime.utcnow(),
            })

    return {
        "message": f"Final activada: Cruz Azul vs {finalist_name}",
        "finalist": finalist_name,
    }


@api_router.post("/admin/seed-final-players")
async def seed_final_players(current_user: dict = Depends(get_current_user)):
    """Carga jugadores reales de Cruz Azul y Pumas para la Final (solo admin)"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    CRUZ_AZUL = [
        {"name": "Andrés Gudiño", "number": 1, "position": "POR", "nationality": "México", "age": 29, "appearances": 13, "goals": 0, "assists": 0, "yellow_cards": 3, "red_cards": 0},
        {"name": "Kevin Mier", "number": 23, "position": "POR", "nationality": "Colombia", "age": 26, "appearances": 8, "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0},
        {"name": "Jesús Orozco", "number": 2, "position": "DEF", "nationality": "México", "age": 24, "appearances": 1, "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0},
        {"name": "Omar Campos", "number": 3, "position": "DEF", "nationality": "México", "age": 23, "appearances": 19, "goals": 1, "assists": 2, "yellow_cards": 3, "red_cards": 0},
        {"name": "Willer Ditta", "number": 4, "position": "DEF", "nationality": "Colombia", "age": 29, "appearances": 20, "goals": 0, "assists": 2, "yellow_cards": 6, "red_cards": 0},
        {"name": "Jorge Rodarte", "number": 22, "position": "DEF", "nationality": "México", "age": 22, "appearances": 13, "goals": 0, "assists": 1, "yellow_cards": 2, "red_cards": 0},
        {"name": "Gonzalo Piovi", "number": 33, "position": "DEF", "nationality": "Argentina", "age": 31, "appearances": 20, "goals": 0, "assists": 0, "yellow_cards": 6, "red_cards": 0},
        {"name": "Erik Lira", "number": 6, "position": "MED", "nationality": "México", "age": 26, "appearances": 17, "goals": 0, "assists": 0, "yellow_cards": 4, "red_cards": 0},
        {"name": "Agustín Palavecino", "number": 8, "position": "MED", "nationality": "Argentina", "age": 29, "appearances": 20, "goals": 6, "assists": 3, "yellow_cards": 7, "red_cards": 0},
        {"name": "Andres Montaño", "number": 10, "position": "MED", "nationality": "México", "age": 23, "appearances": 12, "goals": 2, "assists": 0, "yellow_cards": 1, "red_cards": 0},
        {"name": "Ángel Márquez", "number": 16, "position": "MED", "nationality": "México", "age": 25, "appearances": 20, "goals": 3, "assists": 0, "yellow_cards": 1, "red_cards": 0},
        {"name": "Amaury García", "number": 17, "position": "MED", "nationality": "México", "age": 24, "appearances": 16, "goals": 0, "assists": 0, "yellow_cards": 2, "red_cards": 0},
        {"name": "Carlos Rodríguez", "number": 19, "position": "MED", "nationality": "México", "age": 29, "appearances": 21, "goals": 4, "assists": 1, "yellow_cards": 1, "red_cards": 0},
        {"name": "Amaury Morales", "number": 31, "position": "MED", "nationality": "México", "age": 20, "appearances": 15, "goals": 0, "assists": 1, "yellow_cards": 0, "red_cards": 0},
        {"name": "Nicolás Ibáñez", "number": 7, "position": "DEL", "nationality": "Argentina", "age": 31, "appearances": 12, "goals": 2, "assists": 1, "yellow_cards": 2, "red_cards": 0},
        {"name": "Osinachi Ebere", "number": 11, "position": "DEL", "nationality": "Nigeria", "age": 28, "appearances": 14, "goals": 4, "assists": 1, "yellow_cards": 1, "red_cards": 0},
        {"name": "Luka Romero", "number": 18, "position": "DEL", "nationality": "Argentina", "age": 21, "appearances": 18, "goals": 1, "assists": 0, "yellow_cards": 2, "red_cards": 0},
        {"name": "José Paradela", "number": 20, "position": "DEL", "nationality": "Argentina", "age": 27, "appearances": 21, "goals": 7, "assists": 5, "yellow_cards": 3, "red_cards": 0},
        {"name": "Gabriel Fernández", "number": 21, "position": "DEL", "nationality": "Uruguay", "age": 32, "appearances": 17, "goals": 5, "assists": 4, "yellow_cards": 0, "red_cards": 1},
        {"name": "Rodolfo Rotondi", "number": 29, "position": "DEL", "nationality": "Argentina", "age": 29, "appearances": 19, "goals": 3, "assists": 4, "yellow_cards": 2, "red_cards": 0},
    ]

    PUMAS = [
        {"name": "Keylor Navas", "number": 1, "position": "POR", "nationality": "Costa Rica", "age": 39, "appearances": 20, "goals": 0, "assists": 0, "yellow_cards": 5, "red_cards": 0},
        {"name": "Pablo Lara", "number": 35, "position": "POR", "nationality": "México", "age": 20, "appearances": 1, "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0},
        {"name": "Pablo Bennevendo", "number": 2, "position": "DEF", "nationality": "México", "age": 26, "appearances": 13, "goals": 0, "assists": 0, "yellow_cards": 1, "red_cards": 0},
        {"name": "Rubén Duarte", "number": 5, "position": "DEF", "nationality": "España", "age": 30, "appearances": 16, "goals": 1, "assists": 0, "yellow_cards": 3, "red_cards": 0},
        {"name": "Nathan Silva", "number": 6, "position": "DEF", "nationality": "Brasil", "age": 29, "appearances": 20, "goals": 1, "assists": 1, "yellow_cards": 4, "red_cards": 1},
        {"name": "Álvaro Angulo", "number": 77, "position": "DEF", "nationality": "Colombia", "age": 29, "appearances": 20, "goals": 3, "assists": 0, "yellow_cards": 3, "red_cards": 1},
        {"name": "Angel Azuaje", "number": 215, "position": "DEF", "nationality": "Venezuela", "age": 21, "appearances": 11, "goals": 0, "assists": 0, "yellow_cards": 2, "red_cards": 0},
        {"name": "Rodrigo López", "number": 7, "position": "MED", "nationality": "México", "age": 24, "appearances": 21, "goals": 0, "assists": 1, "yellow_cards": 4, "red_cards": 0},
        {"name": "Cesar Garza", "number": 14, "position": "MED", "nationality": "México", "age": 20, "appearances": 15, "goals": 0, "assists": 0, "yellow_cards": 3, "red_cards": 0},
        {"name": "Alan Medina", "number": 22, "position": "MED", "nationality": "Uruguay", "age": 28, "appearances": 16, "goals": 1, "assists": 4, "yellow_cards": 3, "red_cards": 0},
        {"name": "Adalberto Carrasquilla", "number": 28, "position": "MED", "nationality": "Panamá", "age": 27, "appearances": 19, "goals": 2, "assists": 2, "yellow_cards": 6, "red_cards": 0},
        {"name": "Jordan Carrillo", "number": 33, "position": "MED", "nationality": "México", "age": 24, "appearances": 20, "goals": 6, "assists": 3, "yellow_cards": 3, "red_cards": 0},
        {"name": "Pedro Vite", "number": 45, "position": "MED", "nationality": "Ecuador", "age": 24, "appearances": 21, "goals": 1, "assists": 1, "yellow_cards": 2, "red_cards": 0},
        {"name": "Guillermo Martínez", "number": 9, "position": "DEL", "nationality": "México", "age": 31, "appearances": 15, "goals": 5, "assists": 0, "yellow_cards": 3, "red_cards": 0},
        {"name": "José Macías", "number": 11, "position": "DEL", "nationality": "México", "age": 26, "appearances": 11, "goals": 4, "assists": 2, "yellow_cards": 0, "red_cards": 0},
        {"name": "Uriel Antuna", "number": 21, "position": "DEL", "nationality": "México", "age": 28, "appearances": 21, "goals": 3, "assists": 3, "yellow_cards": 1, "red_cards": 0},
        {"name": "Juninho", "number": 23, "position": "DEL", "nationality": "Brasil", "age": 29, "appearances": 21, "goals": 8, "assists": 4, "yellow_cards": 1, "red_cards": 0},
        {"name": "Robert Morales", "number": 31, "position": "DEL", "nationality": "Paraguay", "age": 27, "appearances": 21, "goals": 8, "assists": 2, "yellow_cards": 1, "red_cards": 0},
    ]

    caz = await db.teams.find_one({"short_name": "CAZ"})
    pum = await db.teams.find_one({"short_name": "PUM"})

    if not caz or not pum:
        raise HTTPException(status_code=404, detail="No se encontraron los equipos")

    # Borrar jugadores viejos de estos equipos
    await db.players.delete_many({"team_id": {"$in": [caz["_id"], pum["_id"]]}})

    total = 0
    for p in CRUZ_AZUL:
        await db.players.insert_one({**p, "team_id": caz["_id"], "team_name": "Cruz Azul", "photo": "", "rating": "0", "season": "2025-26", "updated_at": datetime.utcnow()})
        total += 1
    for p in PUMAS:
        await db.players.insert_one({**p, "team_id": pum["_id"], "team_name": "Pumas UNAM", "photo": "", "rating": "0", "season": "2025-26", "updated_at": datetime.utcnow()})
        total += 1

    return {"message": f"✅ {total} jugadores de la Final cargados correctamente", "total": total}


@api_router.post("/admin/seed-world-cup")
async def seed_world_cup(current_user: dict = Depends(get_current_user)):
    """Carga equipos, jornadas y partidos del Mundial 2026"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    TEAMS_WC = [
        {"name": "México", "short_name": "MEX", "group": "A", "priority": 1, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/utpvpq1473543873.png"},
        {"name": "Sudáfrica", "short_name": "RSA", "group": "A", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/vvupwq1473543892.png"},
        {"name": "Corea del Sur", "short_name": "KOR", "group": "A", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvquu1473543881.png"},
        {"name": "Rep. Checa", "short_name": "CZE", "group": "A", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvr1473543865.png"},
        {"name": "Canadá", "short_name": "CAN", "group": "B", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqus1473543862.png"},
        {"name": "Bosnia", "short_name": "BIH", "group": "B", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvs1473543860.png"},
        {"name": "Qatar", "short_name": "QAT", "group": "B", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvt1473543889.png"},
        {"name": "Suiza", "short_name": "SUI", "group": "B", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvv1473543894.png"},
        {"name": "Brasil", "short_name": "BRA", "group": "C", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqut1473543861.png"},
        {"name": "Marruecos", "short_name": "MAR", "group": "C", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvq1473543884.png"},
        {"name": "Haití", "short_name": "HAI", "group": "C", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543876.png"},
        {"name": "Escocia", "short_name": "SCO", "group": "C", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvr1473543891.png"},
        {"name": "USA", "short_name": "USA", "group": "D", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvquw1473543897.png"},
        {"name": "Paraguay", "short_name": "PAR", "group": "D", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvt1473543888.png"},
        {"name": "Australia", "short_name": "AUS", "group": "D", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqus1473543858.png"},
        {"name": "Turquía", "short_name": "TUR", "group": "D", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvv1473543895.png"},
        {"name": "Alemania", "short_name": "GER", "group": "E", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqup1473543874.png"},
        {"name": "Curaçao", "short_name": "CUW", "group": "E", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvs1473543864.png"},
        {"name": "Costa de Marfil", "short_name": "CIV", "group": "E", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvs1473543863.png"},
        {"name": "Ecuador", "short_name": "ECU", "group": "E", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543868.png"},
        {"name": "Países Bajos", "short_name": "NED", "group": "F", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvr1473543886.png"},
        {"name": "Japón", "short_name": "JPN", "group": "F", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543879.png"},
        {"name": "Suecia", "short_name": "SWE", "group": "F", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvv1473543893.png"},
        {"name": "Túnez", "short_name": "TUN", "group": "F", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvv1473543896.png"},
        {"name": "Bélgica", "short_name": "BEL", "group": "G", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvs1473543859.png"},
        {"name": "Egipto", "short_name": "EGY", "group": "G", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543869.png"},
        {"name": "Irán", "short_name": "IRN", "group": "G", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543878.png"},
        {"name": "Nueva Zelanda", "short_name": "NZL", "group": "G", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvr1473543887.png"},
        {"name": "España", "short_name": "ESP", "group": "H", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543870.png"},
        {"name": "Cabo Verde", "short_name": "CPV", "group": "H", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvs1473543862.png"},
        {"name": "Arabia Saudita", "short_name": "KSA", "group": "H", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvs1473543891.png"},
        {"name": "Uruguay", "short_name": "URU", "group": "H", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvw1473543898.png"},
        {"name": "Francia", "short_name": "FRA", "group": "I", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543871.png"},
        {"name": "Senegal", "short_name": "SEN", "group": "I", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvt1473543892.png"},
        {"name": "Irak", "short_name": "IRQ", "group": "I", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543877.png"},
        {"name": "Noruega", "short_name": "NOR", "group": "I", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvr1473543887.png"},
        {"name": "Argentina", "short_name": "ARG", "group": "J", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqus1473543857.png"},
        {"name": "Argelia", "short_name": "ALG", "group": "J", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqus1473543856.png"},
        {"name": "Austria", "short_name": "AUT", "group": "J", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqus1473543858.png"},
        {"name": "Jordania", "short_name": "JOR", "group": "J", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543880.png"},
        {"name": "Portugal", "short_name": "POR", "group": "K", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvt1473543889.png"},
        {"name": "DR Congo", "short_name": "COD", "group": "K", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvs1473543863.png"},
        {"name": "Uzbekistán", "short_name": "UZB", "group": "K", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvw1473543898.png"},
        {"name": "Colombia", "short_name": "COL", "group": "K", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvs1473543863.png"},
        {"name": "Inglaterra", "short_name": "ENG", "group": "L", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543869.png"},
        {"name": "Croacia", "short_name": "CRO", "group": "L", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvs1473543864.png"},
        {"name": "Ghana", "short_name": "GHA", "group": "L", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvp1473543873.png"},
        {"name": "Panamá", "short_name": "PAN", "group": "L", "priority": 99, "shield_url": "https://www.thesportsdb.com/images/media/team/badge/sqvqvt1473543888.png"},
    ]

    MATCHES_WC = [
        # JORNADA 1
        {"j": 1, "home": "México", "away": "Sudáfrica", "date": "2026-06-11T19:00:00", "venue": "Estadio Azteca"},
        {"j": 1, "home": "Corea del Sur", "away": "Rep. Checa", "date": "2026-06-12T02:00:00", "venue": "Estadio Akron"},
        {"j": 1, "home": "Canadá", "away": "Bosnia", "date": "2026-06-12T19:00:00", "venue": "BMO Field"},
        {"j": 1, "home": "Qatar", "away": "Suiza", "date": "2026-06-13T19:00:00", "venue": "Levi's Stadium"},
        {"j": 1, "home": "Brasil", "away": "Marruecos", "date": "2026-06-13T22:00:00", "venue": "MetLife Stadium"},
        {"j": 1, "home": "Haití", "away": "Escocia", "date": "2026-06-14T01:00:00", "venue": "Gillette Stadium"},
        {"j": 1, "home": "USA", "away": "Paraguay", "date": "2026-06-13T01:00:00", "venue": "SoFi Stadium"},
        {"j": 1, "home": "Australia", "away": "Turquía", "date": "2026-06-14T04:00:00", "venue": "BC Place"},
        {"j": 1, "home": "Alemania", "away": "Curaçao", "date": "2026-06-14T17:00:00", "venue": "NRG Stadium"},
        {"j": 1, "home": "Costa de Marfil", "away": "Ecuador", "date": "2026-06-14T23:00:00", "venue": "Lincoln Financial Field"},
        {"j": 1, "home": "Países Bajos", "away": "Japón", "date": "2026-06-14T20:00:00", "venue": "AT&T Stadium"},
        {"j": 1, "home": "Suecia", "away": "Túnez", "date": "2026-06-15T02:00:00", "venue": "Estadio BBVA"},
        {"j": 1, "home": "Bélgica", "away": "Egipto", "date": "2026-06-15T19:00:00", "venue": "Lumen Field"},
        {"j": 1, "home": "Irán", "away": "Nueva Zelanda", "date": "2026-06-16T01:00:00", "venue": "SoFi Stadium"},
        {"j": 1, "home": "España", "away": "Cabo Verde", "date": "2026-06-15T16:00:00", "venue": "Mercedes-Benz Stadium"},
        {"j": 1, "home": "Arabia Saudita", "away": "Uruguay", "date": "2026-06-15T22:00:00", "venue": "Hard Rock Stadium"},
        {"j": 1, "home": "Francia", "away": "Senegal", "date": "2026-06-16T19:00:00", "venue": "MetLife Stadium"},
        {"j": 1, "home": "Irak", "away": "Noruega", "date": "2026-06-16T22:00:00", "venue": "Gillette Stadium"},
        {"j": 1, "home": "Argentina", "away": "Argelia", "date": "2026-06-17T01:00:00", "venue": "Arrowhead Stadium"},
        {"j": 1, "home": "Austria", "away": "Jordania", "date": "2026-06-17T04:00:00", "venue": "Levi's Stadium"},
        {"j": 1, "home": "Portugal", "away": "DR Congo", "date": "2026-06-17T17:00:00", "venue": "NRG Stadium"},
        {"j": 1, "home": "Uzbekistán", "away": "Colombia", "date": "2026-06-18T02:00:00", "venue": "Estadio Azteca"},
        {"j": 1, "home": "Inglaterra", "away": "Croacia", "date": "2026-06-17T20:00:00", "venue": "AT&T Stadium"},
        {"j": 1, "home": "Ghana", "away": "Panamá", "date": "2026-06-17T23:00:00", "venue": "BMO Field"},
        # JORNADA 2
        {"j": 2, "home": "Rep. Checa", "away": "Sudáfrica", "date": "2026-06-18T16:00:00", "venue": "Mercedes-Benz Stadium"},
        {"j": 2, "home": "México", "away": "Corea del Sur", "date": "2026-06-19T01:00:00", "venue": "Estadio Akron"},
        {"j": 2, "home": "Suiza", "away": "Bosnia", "date": "2026-06-18T19:00:00", "venue": "SoFi Stadium"},
        {"j": 2, "home": "Canadá", "away": "Qatar", "date": "2026-06-18T22:00:00", "venue": "BC Place"},
        {"j": 2, "home": "Escocia", "away": "Marruecos", "date": "2026-06-19T22:00:00", "venue": "Gillette Stadium"},
        {"j": 2, "home": "Brasil", "away": "Haití", "date": "2026-06-20T00:30:00", "venue": "Lincoln Financial Field"},
        {"j": 2, "home": "USA", "away": "Australia", "date": "2026-06-19T19:00:00", "venue": "Lumen Field"},
        {"j": 2, "home": "Turquía", "away": "Paraguay", "date": "2026-06-20T03:00:00", "venue": "Levi's Stadium"},
        {"j": 2, "home": "Alemania", "away": "Costa de Marfil", "date": "2026-06-20T20:00:00", "venue": "BMO Field"},
        {"j": 2, "home": "Ecuador", "away": "Curaçao", "date": "2026-06-21T00:00:00", "venue": "Arrowhead Stadium"},
        {"j": 2, "home": "Países Bajos", "away": "Suecia", "date": "2026-06-20T17:00:00", "venue": "NRG Stadium"},
        {"j": 2, "home": "Túnez", "away": "Japón", "date": "2026-06-21T04:00:00", "venue": "Estadio BBVA"},
        {"j": 2, "home": "Bélgica", "away": "Irán", "date": "2026-06-21T19:00:00", "venue": "SoFi Stadium"},
        {"j": 2, "home": "Nueva Zelanda", "away": "Egipto", "date": "2026-06-22T01:00:00", "venue": "BC Place"},
        {"j": 2, "home": "España", "away": "Arabia Saudita", "date": "2026-06-21T16:00:00", "venue": "Mercedes-Benz Stadium"},
        {"j": 2, "home": "Uruguay", "away": "Cabo Verde", "date": "2026-06-21T22:00:00", "venue": "Hard Rock Stadium"},
        {"j": 2, "home": "Francia", "away": "Irak", "date": "2026-06-22T21:00:00", "venue": "Lincoln Financial Field"},
        {"j": 2, "home": "Noruega", "away": "Senegal", "date": "2026-06-23T00:00:00", "venue": "MetLife Stadium"},
        {"j": 2, "home": "Argentina", "away": "Austria", "date": "2026-06-22T17:00:00", "venue": "AT&T Stadium"},
        {"j": 2, "home": "Jordania", "away": "Argelia", "date": "2026-06-23T03:00:00", "venue": "Levi's Stadium"},
        {"j": 2, "home": "Portugal", "away": "Uzbekistán", "date": "2026-06-23T17:00:00", "venue": "NRG Stadium"},
        {"j": 2, "home": "Colombia", "away": "DR Congo", "date": "2026-06-24T02:00:00", "venue": "Estadio Akron"},
        {"j": 2, "home": "Inglaterra", "away": "Ghana", "date": "2026-06-23T20:00:00", "venue": "Gillette Stadium"},
        {"j": 2, "home": "Panamá", "away": "Croacia", "date": "2026-06-23T23:00:00", "venue": "BMO Field"},
        # JORNADA 3
        {"j": 3, "home": "Rep. Checa", "away": "México", "date": "2026-06-25T01:00:00", "venue": "Estadio Azteca"},
        {"j": 3, "home": "Sudáfrica", "away": "Corea del Sur", "date": "2026-06-25T01:00:00", "venue": "Estadio BBVA"},
        {"j": 3, "home": "Suiza", "away": "Canadá", "date": "2026-06-24T19:00:00", "venue": "BC Place"},
        {"j": 3, "home": "Bosnia", "away": "Qatar", "date": "2026-06-24T19:00:00", "venue": "Lumen Field"},
        {"j": 3, "home": "Escocia", "away": "Brasil", "date": "2026-06-24T22:00:00", "venue": "Hard Rock Stadium"},
        {"j": 3, "home": "Marruecos", "away": "Haití", "date": "2026-06-24T22:00:00", "venue": "Mercedes-Benz Stadium"},
        {"j": 3, "home": "Turquía", "away": "USA", "date": "2026-06-26T01:00:00", "venue": "SoFi Stadium"},
        {"j": 3, "home": "Paraguay", "away": "Australia", "date": "2026-06-26T01:00:00", "venue": "Levi's Stadium"},
        {"j": 3, "home": "Curaçao", "away": "Costa de Marfil", "date": "2026-06-25T20:00:00", "venue": "Lincoln Financial Field"},
        {"j": 3, "home": "Ecuador", "away": "Alemania", "date": "2026-06-25T20:00:00", "venue": "MetLife Stadium"},
        {"j": 3, "home": "Japón", "away": "Suecia", "date": "2026-06-25T23:00:00", "venue": "AT&T Stadium"},
        {"j": 3, "home": "Túnez", "away": "Países Bajos", "date": "2026-06-25T23:00:00", "venue": "Arrowhead Stadium"},
        {"j": 3, "home": "Egipto", "away": "Irán", "date": "2026-06-27T03:00:00", "venue": "Lumen Field"},
        {"j": 3, "home": "Nueva Zelanda", "away": "Bélgica", "date": "2026-06-27T03:00:00", "venue": "BC Place"},
        {"j": 3, "home": "Cabo Verde", "away": "Arabia Saudita", "date": "2026-06-27T00:00:00", "venue": "NRG Stadium"},
        {"j": 3, "home": "Uruguay", "away": "España", "date": "2026-06-27T01:00:00", "venue": "Estadio Akron"},
        {"j": 3, "home": "Noruega", "away": "Francia", "date": "2026-06-26T19:00:00", "venue": "Gillette Stadium"},
        {"j": 3, "home": "Senegal", "away": "Irak", "date": "2026-06-26T19:00:00", "venue": "BMO Field"},
        {"j": 3, "home": "Argelia", "away": "Austria", "date": "2026-06-28T02:00:00", "venue": "Arrowhead Stadium"},
        {"j": 3, "home": "Jordania", "away": "Argentina", "date": "2026-06-28T02:00:00", "venue": "AT&T Stadium"},
        {"j": 3, "home": "Colombia", "away": "Portugal", "date": "2026-06-28T23:30:00", "venue": "Hard Rock Stadium"},
        {"j": 3, "home": "DR Congo", "away": "Uzbekistán", "date": "2026-06-28T23:30:00", "venue": "Mercedes-Benz Stadium"},
        {"j": 3, "home": "Panamá", "away": "Inglaterra", "date": "2026-06-27T21:00:00", "venue": "MetLife Stadium"},
        {"j": 3, "home": "Croacia", "away": "Ghana", "date": "2026-06-27T21:00:00", "venue": "Lincoln Financial Field"},
    ]

    JORNADAS_WC = [
        {"wn": 1, "title": "Fase de Grupos — Jornada 1", "start": "2026-06-11", "end": "2026-06-17"},
        {"wn": 2, "title": "Fase de Grupos — Jornada 2", "start": "2026-06-18", "end": "2026-06-23"},
        {"wn": 3, "title": "Fase de Grupos — Jornada 3", "start": "2026-06-24", "end": "2026-06-27"},
        {"wn": 4, "title": "Round of 32", "start": "2026-06-28", "end": "2026-07-03"},
        {"wn": 5, "title": "Round of 16", "start": "2026-07-04", "end": "2026-07-07"},
        {"wn": 6, "title": "Cuartos de Final", "start": "2026-07-09", "end": "2026-07-11"},
        {"wn": 7, "title": "Semifinales", "start": "2026-07-14", "end": "2026-07-15"},
        {"wn": 8, "title": "Final Mundial", "start": "2026-07-19", "end": "2026-07-19"},
    ]

    # Marcar datos existentes como liga_mx
    await db.teams.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})
    await db.players.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})
    await db.jornadas.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})
    await db.matches.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})

    # Config
    await db.config.update_one(
        {"key": "active_competition"},
        {"$set": {"key": "active_competition", "value": "liga_mx"}},
        upsert=True
    )

    # Borrar datos previos del Mundial
    await db.teams.delete_many({"competition": "world_cup_2026"})
    await db.jornadas.delete_many({"competition": "world_cup_2026"})
    await db.matches.delete_many({"competition": "world_cup_2026"})

    # Insertar equipos
    team_ids = {}
    for t in TEAMS_WC:
        result = await db.teams.insert_one({
            "name": t["name"], "short_name": t["short_name"],
            "shield_url": t["shield_url"], "competition": "world_cup_2026",
            "group": t["group"], "priority": t["priority"],
            "created_at": datetime.utcnow()
        })
        team_ids[t["name"]] = result.inserted_id

    # Insertar jornadas
    jornada_ids = {}
    for j in JORNADAS_WC:
        result = await db.jornadas.insert_one({
            "week_number": j["wn"], "title": j["title"],
            "type": "world_cup", "competition": "world_cup_2026",
            "status": "upcoming", "is_active": False, "processed": False,
            "start_date": datetime.fromisoformat(j["start"]),
            "end_date": datetime.fromisoformat(j["end"]),
            "created_at": datetime.utcnow()
        })
        jornada_ids[j["wn"]] = result.inserted_id

    # Insertar partidos
    matches_count = 0
    for m in MATCHES_WC:
        ht = await db.teams.find_one({"name": m["home"], "competition": "world_cup_2026"})
        at = await db.teams.find_one({"name": m["away"], "competition": "world_cup_2026"})
        if ht and at:
            await db.matches.insert_one({
                "jornada_id": jornada_ids[m["j"]],
                "home_team_id": ht["_id"], "away_team_id": at["_id"],
                "home_team_name": m["home"], "away_team_name": m["away"],
                "home_score": None, "away_score": None,
                "status": "upcoming", "match_date": datetime.fromisoformat(m["date"]),
                "venue": m["venue"], "competition": "world_cup_2026",
                "created_at": datetime.utcnow()
            })
            matches_count += 1

    return {
        "message": "✅ Mundial 2026 cargado correctamente",
        "teams": len(TEAMS_WC),
        "jornadas": len(JORNADAS_WC),
        "matches": matches_count
    }


@api_router.post("/admin/seed-world-cup-players")
async def seed_world_cup_players(current_user: dict = Depends(get_current_user)):
    """Carga las plantillas reales de las 48 selecciones del Mundial 2026"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    # Borrar jugadores previos del Mundial
    await db.players.delete_many({"competition": "world_cup_2026"})

    inserted = 0
    skipped_teams = []

    for team_name, squad in WC_SQUADS.items():
        team = await db.teams.find_one({"name": team_name, "competition": "world_cup_2026"})
        if not team:
            skipped_teams.append(team_name)
            continue

        for p in squad:
            await db.players.insert_one({
                "name": p["name"],
                "team_id": team["_id"],
                "team_name": team_name,
                "position": p["position"],
                "number": p["number"],
                "competition": "world_cup_2026",
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0,
                    "yellow_cards": 0,
                    "red_cards": 0,
                },
                "created_at": datetime.utcnow()
            })
            inserted += 1

    return {
        "message": f"✅ Plantillas del Mundial cargadas: {inserted} jugadores de {len(WC_SQUADS) - len(skipped_teams)} selecciones",
        "players_inserted": inserted,
        "teams_loaded": len(WC_SQUADS) - len(skipped_teams),
        "skipped_teams": skipped_teams
    }


@api_router.post("/admin/activate-competition")
async def activate_competition(body: dict, current_user: dict = Depends(get_current_user)):
    """Cambia la competición activa entre liga_mx y world_cup_2026"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")
    competition = body.get("competition")
    if competition not in ["liga_mx", "world_cup_2026"]:
        raise HTTPException(status_code=400, detail="Competición inválida")
    await db.config.update_one(
        {"key": "active_competition"},
        {"$set": {"value": competition}},
        upsert=True
    )
    return {"message": f"✅ Competición activa: {competition}"}

# ============ ADMIN BRACKET UPDATE ============

@api_router.post("/admin/bracket/update")
async def update_bracket_results(
    data: BracketUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Actualiza los resultados del bracket de liguilla (solo admin)"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    update_doc = {"updated_at": datetime.utcnow()}

    if data.cuartos_winners:
        update_doc["cuartos_winners"] = data.cuartos_winners
    if data.semis_left_winner:
        update_doc["semis_left_winner"] = data.semis_left_winner
    if data.semis_right_winner:
        update_doc["semis_right_winner"] = data.semis_right_winner
    if data.champion:
        update_doc["champion"] = data.champion

    await db.liguilla_results.update_one(
        {"temporada": "Clausura 2026"},
        {"$set": update_doc},
        upsert=True
    )

    return {"message": "Bracket actualizado", "data": update_doc}


@api_router.get("/liguilla/results")
async def get_liguilla_results():
    """Obtiene los resultados actuales del bracket"""
    results = await db.liguilla_results.find_one({"temporada": "Clausura 2026"})
    if not results:
        return {
            "temporada": "Clausura 2026",
            "cuartos_winners": [],
            "semis_left_winner": None,
            "semis_right_winner": None,
            "champion": None
        }
    results["_id"] = str(results["_id"])
    return results


# ============ ROOT ============

@api_router.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    return {"status": "ok"}

@api_router.get("/")
async def root():
    return {
        "message": "Quiniela Liga MX API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth/*",
            "teams": "/api/teams",
            "jornadas": "/api/jornadas/*",
            "quiniela": "/api/quiniela/*",
            "fantasy": "/api/fantasy/*",
            "players": "/api/players",
            "admin": "/api/admin/*"
        }
    }

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# shutdown consolidado abajo con stop_scheduler

# ============ AUTO-SCHEDULER ============
import asyncio

_scheduler_task: asyncio.Task | None = None


async def _process_liguilla_phase(phase: str):
    """
    Procesa automáticamente una fase de liguilla cuando terminan todos sus partidos.
    - Calcula puntos de fantasy de los jugadores
    - Avanza a la siguiente fase automáticamente
    - Identifica ganadores via marcadores en DB
    """
    jornada = await db.jornadas.find_one({"type": "liguilla", "phase": phase, "is_active": True})
    if not jornada or jornada.get("processed"):
        return

    jornada_id = jornada["_id"]
    logger.info(f"🏆 Procesando liguilla fase: {phase}")

    # Verificar que todos los partidos terminaron
    matches = await db.matches.find({"jornada_id": jornada_id}).to_list(20)
    pending = [m for m in matches if m.get("status") != "finished"]
    if pending:
        logger.info(f"⏳ Liguilla {phase}: {len(pending)} partidos pendientes")
        return

    # Calcular puntos de fantasy por stats de jugadores
    try:
        scores_result = await _svc_get_match_results(str(jornada_id), db)
        logger.info(f"✅ Liguilla {phase} scores: {scores_result.get('matches_updated', 0)} actualizados")
    except Exception as e:
        logger.error(f"❌ Error calculando scores liguilla {phase}: {e}")

    # Marcar jornada como procesada y cerrada
    await db.jornadas.update_one(
        {"_id": jornada_id},
        {"$set": {"processed": True, "is_active": False, "status": "finished"}}
    )
    logger.info(f"✅ Liguilla {phase} cerrada automáticamente")

    # ── Avanzar a la siguiente fase ────────────────────────────────
    if phase == "semis":
        # Identificar ganadores de cada serie
        # Serie izquierda: Cruz Azul vs Guadalajara
        caz = await db.teams.find_one({"short_name": "CAZ"})
        gdl = await db.teams.find_one({"short_name": "GDL"})
        pum = await db.teams.find_one({"short_name": "PUM"})
        pac = await db.teams.find_one({"short_name": "PAC"})

        # Sumar goles por serie
        async def get_series_winner(team_a_id, team_b_id):
            partidos = await db.matches.find({
                "jornada_id": jornada_id,
                "$or": [
                    {"home_team_id": team_a_id, "away_team_id": team_b_id},
                    {"home_team_id": team_b_id, "away_team_id": team_a_id},
                ]
            }).to_list(2)

            goles_a = 0
            goles_b = 0
            for p in partidos:
                if p.get("home_team_id") == team_a_id:
                    goles_a += p.get("home_score") or 0
                    goles_b += p.get("away_score") or 0
                else:
                    goles_b += p.get("home_score") or 0
                    goles_a += p.get("away_score") or 0

            if goles_a > goles_b:
                return team_a_id
            elif goles_b > goles_a:
                return team_b_id
            else:
                # Empate global — gana el de mejor posición (team_a es el mejor clasificado)
                return team_a_id

        if caz and gdl and pum and pac:
            # SF Derecha: Cruz Azul vs Guadalajara
            winner_right_id = await get_series_winner(caz["_id"], gdl["_id"])
            winner_right = caz if winner_right_id == caz["_id"] else gdl

            # SF Izquierda: Pumas vs Pachuca
            winner_left_id = await get_series_winner(pum["_id"], pac["_id"])
            winner_left = pum if winner_left_id == pum["_id"] else pac

            logger.info(f"🏆 Finalistas: {winner_left['name']} vs {winner_right['name']}")

            # Actualizar jornada Final con los finalistas
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

                # Crear partidos de la final si no existen
                existing = await db.matches.count_documents({"jornada_id": final_jornada["_id"]})
                if existing == 0:
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
                logger.info(f"✅ Final activada automáticamente: {winner_left['name']} vs {winner_right['name']}")

    elif phase == "final":
        logger.info("🎉 ¡Liguilla Clausura 2026 finalizada! Calculando campeón...")
        # Otorgar logros especiales
        try:
            # Aquí se pueden otorgar logros de campeón acertado
            pass
        except Exception as e:
            logger.error(f"❌ Error otorgando logros de liguilla: {e}")

async def _auto_update_scores():
    """
    Scheduler que corre en background continuamente.
    - Si hay partidos hoy: actualiza scores cada 60 segundos
    - Si hay partido live: actualiza cada 45 segundos
    - Si no hay partidos hoy: revisa cada 10 minutos
    - Al terminar todos los partidos: procesa jornada automáticamente
    """
    logger.info("🤖 Auto-scheduler iniciado")
    
    while True:
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)

            from services.scores_service import _fetch_365scores, _normalize_name, _STATUS_MAP

            # ── Verificar si hay partidos hoy ─────────────────────────────
            games = await _fetch_365scores(today_start, today_end)
            
            if not games:
                # Sin partidos hoy — revisar cada 10 minutos
                logger.debug("📅 Sin partidos hoy. Próxima revisión en 10 min.")
                await asyncio.sleep(600)
                continue

            # ── Clasificar partidos ───────────────────────────────────────
            live_games    = [g for g in games if _STATUS_MAP.get(g.get("statusGroup", 1)) == "live"]
            finished_games = [g for g in games if _STATUS_MAP.get(g.get("statusGroup", 1)) == "finished"]
            scheduled_games = [g for g in games if _STATUS_MAP.get(g.get("statusGroup", 1)) == "scheduled"]

            logger.info(
                f"⚽ Partidos hoy: {len(games)} total | "
                f"{len(live_games)} live | {len(finished_games)} terminados | {len(scheduled_games)} pendientes"
            )

            # ── Actualizar scores en DB si hay partidos live o terminados ─
            if live_games or finished_games:
                jornada = await db.jornadas.find_one({"is_active": True})
                if jornada:
                    jornada_id = str(jornada["_id"])
                    try:
                        scores_result = await _svc_get_match_results(jornada_id, db)
                        updated = scores_result.get("matches_updated", 0)
                        if updated > 0:
                            logger.info(f"✅ Scheduler: {updated} partidos actualizados en jornada {jornada.get('week_number')}")
                    except Exception as e:
                        logger.error(f"❌ Scheduler scores error: {e}")

            # ── Verificar si todos los partidos terminaron ─────────────────
            if finished_games and not live_games and not scheduled_games:
                logger.info("🏁 Todos los partidos del día terminaron — verificando proceso de jornada")
                jornada = await db.jornadas.find_one({"is_active": True})
                if jornada and not jornada.get("processed", False):
                    # ── Jornada de liguilla ────────────────────────────
                    if jornada.get("type") == "liguilla":
                        phase = jornada.get("phase", "")
                        status = jornada.get("status", "")
                        # No procesar jornadas upcoming — todavía no han empezado
                        if status == "upcoming":
                            logger.info(f"⏳ Liguilla {phase} en estado upcoming — esperando partidos")
                        else:
                            try:
                                await _process_liguilla_phase(phase)
                                logger.info(f"🏆 Liguilla fase {phase} procesada automáticamente")
                            except Exception as e:
                                logger.error(f"❌ Error procesando liguilla {phase}: {e}")
                    else:
                        # ── Jornada regular ───────────────────────────
                        try:
                            proc_result = await _process_jornada_core(str(jornada["_id"]))
                            logger.info(
                                f"🎉 Jornada {jornada.get('week_number')} procesada automáticamente: "
                                f"quiniela={proc_result.get('quiniela_updated')} usuarios, "
                                f"fantasy={proc_result.get('fantasy_updated')} equipos"
                            )
                        except Exception as e:
                            logger.error(f"❌ Scheduler process_jornada error: {e}")

            # ── Intervalo según estado ─────────────────────────────────────
            if live_games:
                sleep_secs = 45   # Partido en curso: actualizar cada 45s
            elif scheduled_games:
                sleep_secs = 120  # Partidos pendientes hoy: revisar cada 2 min
            else:
                sleep_secs = 300  # Solo terminados: revisar cada 5 min

            logger.debug(f"⏱ Próxima actualización en {sleep_secs}s")
            await asyncio.sleep(sleep_secs)

        except asyncio.CancelledError:
            logger.info("🛑 Auto-scheduler cancelado")
            break
        except Exception as e:
            logger.error(f"❌ Error inesperado en scheduler: {e}")
            await asyncio.sleep(60)  # En caso de error, reintentar en 1 min


@app.on_event("startup")
async def start_scheduler():
    global _scheduler_task
    _scheduler_task = asyncio.create_task(_auto_update_scores())
    logger.info("🚀 Auto-scheduler registrado en startup")


@app.on_event("shutdown")
async def shutdown_app():
    """Cierra scheduler y MongoDB al apagar el servidor"""
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
