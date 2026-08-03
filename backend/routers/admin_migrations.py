# ── routers/admin_migrations.py ─────────────────────────────────────────────
#
# Endpoints de migración/seed de un solo uso: ya se ejecutaron en producción
# para llevar la base de datos al estado actual y NO deberían volver a
# correr en operación normal (varios de ellos borran o resiembran datos por
# completo). Se separaron de routers/admin.py (que conserva los endpoints
# operacionales de uso regular) para que no puedan dispararse por accidente.
#
# Este router solo se registra en server.py si la variable de entorno
# ENABLE_MIGRATIONS=true está presente — por default NO está montado, así
# que estas rutas ni siquiera existen (404) en producción normal. Si algún
# día se necesita volver a correr una de ellas (ej. una migración futura de
# temporada), se activa la env var, se llama el endpoint puntual, y se
# vuelve a apagar.
#
# Cada endpoint sigue protegido con get_admin_user por si acaso se activa
# ENABLE_MIGRATIONS sin querer — la env var es la primera barrera, el auth
# admin es la segunda.

import logging
import random
from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from database import db, get_active_competition
from dependencies import get_admin_user
from fantasy_scoring import calculate_fantasy_points
from jornada_processor import _process_jornada_core
from models import WCMatchStatsRequest
from services.world_cup_stats_service import get_wc_match_stats
from real_liga_mx_data import (
    CLAUSURA_2026_DATES,
    CLAUSURA_2026_J13_MATCHES,
    LIGA_MX_TEAMS,
)
from apertura_2026_data import (
    APERTURA_2026_TEAMS,
    APERTURA_2026_J1_RESULTS,
    APERTURA_2026_J2_FIXTURE,
    APERTURA_2026_REMAINING_JORNADAS,
    APERTURA_2026_J3_J17_FIXTURES,
)
from routers.admin import audit_and_fix_jornadas, _shield_is_broken, _LIGA_MX_SHIELD_FALLBACK

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Seed inicial del proyecto ───────────────────────────────────────────────
# Sembraban datos de prueba/placeholder antes de que existieran datos reales
# de Liga MX. Reemplazados en la práctica por seed-real-data y luego por
# migrate-apertura-2026 — no se han vuelto a correr desde que el proyecto
# usa datos reales.

@router.post("/admin/seed-teams")
async def seed_teams(current_user: dict = Depends(get_admin_user)):
    teams_data = [
        {"name": "Club América",       "short_name": "AME", "shield_url": "https://via.placeholder.com/100/FFD700/000000?text=AME"},
        {"name": "Guadalajara",        "short_name": "GDL", "shield_url": "https://via.placeholder.com/100/FF0000/FFFFFF?text=GDL"},
        {"name": "Cruz Azul",          "short_name": "CAZ", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=CAZ"},
        {"name": "Tigres UANL",        "short_name": "TIG", "shield_url": "https://via.placeholder.com/100/FFD700/000000?text=TIG"},
        {"name": "Monterrey",          "short_name": "MTY", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=MTY"},
        {"name": "Pumas UNAM",         "short_name": "PUM", "shield_url": "https://via.placeholder.com/100/003D79/FFD700?text=PUM"},
        {"name": "Santos Laguna",      "short_name": "SAN", "shield_url": "https://via.placeholder.com/100/00A551/FFFFFF?text=SAN"},
        {"name": "Toluca",             "short_name": "TOL", "shield_url": "https://via.placeholder.com/100/DC143C/FFFFFF?text=TOL"},
        {"name": "León",               "short_name": "LEO", "shield_url": "https://via.placeholder.com/100/00A551/FFFFFF?text=LEO"},
        {"name": "Atlas",              "short_name": "ATL", "shield_url": "https://via.placeholder.com/100/DC143C/000000?text=ATL"},
        {"name": "Pachuca",            "short_name": "PAC", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=PAC"},
        {"name": "Tijuana",            "short_name": "TIJ", "shield_url": "https://via.placeholder.com/100/DC143C/000000?text=TIJ"},
        {"name": "Necaxa",             "short_name": "NEC", "shield_url": "https://via.placeholder.com/100/DC143C/FFFFFF?text=NEC"},
        {"name": "Querétaro",          "short_name": "QRO", "shield_url": "https://via.placeholder.com/100/000000/0047AB?text=QRO"},
        {"name": "Mazatlán",           "short_name": "MAZ", "shield_url": "https://via.placeholder.com/100/663399/FFFFFF?text=MAZ"},
        {"name": "Puebla",             "short_name": "PUE", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=PUE"},
        {"name": "Juárez",             "short_name": "JUA", "shield_url": "https://via.placeholder.com/100/008000/FFFFFF?text=JUA"},
        {"name": "Atlético San Luis",  "short_name": "ASL", "shield_url": "https://via.placeholder.com/100/DC143C/FFFFFF?text=ASL"},
    ]
    await db.teams.delete_many({})
    for team in teams_data:
        team["created_at"] = datetime.utcnow()
    result = await db.teams.insert_many(teams_data)
    logger.info(f"Seeded {len(result.inserted_ids)} teams")
    return {"message": f"Se crearon {len(result.inserted_ids)} equipos", "count": len(result.inserted_ids)}


@router.post("/admin/seed-jornada")
async def seed_current_jornada(current_user: dict = Depends(get_admin_user)):
    teams = await db.teams.find().to_list(100)
    if len(teams) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Primero debes crear los equipos usando /api/admin/seed-teams")

    competition = await get_active_competition()
    last_jornada = await db.jornadas.find_one(
        {"competition": competition}, sort=[("week_number", -1)]
    )
    next_week = (last_jornada["week_number"] + 1) if last_jornada else 1

    await db.jornadas.update_many(
        {"is_active": True, "competition": competition},
        {"$set": {"is_active": False, "status": "finished"}}
    )

    jornada_data = {
        "week_number": next_week,
        "start_date": datetime.utcnow() + timedelta(days=2),
        "end_date":   datetime.utcnow() + timedelta(days=4),
        "status": "upcoming", "is_active": True,
        "created_at": datetime.utcnow()
    }
    jornada_result = await db.jornadas.insert_one(jornada_data)
    jornada_id = jornada_result.inserted_id

    shuffled_teams = list(teams)
    random.shuffle(shuffled_teams)
    matches = [
        {
            "jornada_id": jornada_id,
            "home_team_id": shuffled_teams[i]["_id"],
            "away_team_id": shuffled_teams[i + 1]["_id"],
            "start_at": datetime.utcnow() + timedelta(days=2, hours=i),
            "status": "scheduled", "home_score": None, "away_score": None,
            "created_at": datetime.utcnow()
        }
        for i in range(0, min(18, len(shuffled_teams)), 2)
        if i + 1 < len(shuffled_teams)
    ]
    if matches:
        await db.matches.insert_many(matches)

    logger.info(f"Created jornada {next_week} with {len(matches)} matches")
    return {
        "message": f"Se creó la jornada {next_week} con {len(matches)} partidos (activa)",
        "jornada_id": str(jornada_id), "week_number": next_week, "matches_count": len(matches)
    }


@router.post("/admin/seed-season")
async def seed_full_season(current_user: dict = Depends(get_admin_user)):
    teams = await db.teams.find().to_list(100)
    if len(teams) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Primero debes crear los equipos usando /api/admin/seed-teams")

    await db.jornadas.delete_many({})
    await db.matches.delete_many({})

    now = datetime.utcnow()
    ACTIVE_WEEK = 13
    teams_by_name = {t["name"]: t["_id"] for t in teams}
    created_jornadas = []

    for week in range(1, 18):
        week_start = CLAUSURA_2026_DATES.get(week, now + timedelta(weeks=week - ACTIVE_WEEK))
        week_end = week_start + timedelta(days=7)
        is_past = week < ACTIVE_WEEK
        is_current = week == ACTIVE_WEEK
        week_status = "finished" if is_past else ("in_progress" if is_current else "upcoming")
        match_status_val = "finished" if is_past else "scheduled"

        jornada_result = await db.jornadas.insert_one({
            "week_number": week, "start_date": week_start, "end_date": week_end,
            "status": week_status, "is_active": is_current, "created_at": now
        })
        jornada_id = jornada_result.inserted_id

        if is_current:
            matches = [
                {
                    "jornada_id": jornada_id,
                    "home_team_id": teams_by_name.get(home_name),
                    "away_team_id": teams_by_name.get(away_name),
                    "start_at": match_dt, "status": "scheduled",
                    "home_score": None, "away_score": None, "created_at": now
                }
                for (home_name, away_name, match_dt) in CLAUSURA_2026_J13_MATCHES
                if teams_by_name.get(home_name) and teams_by_name.get(away_name)
            ]
        else:
            shuffled_teams = list(teams)
            random.shuffle(shuffled_teams)
            matches = [
                {
                    "jornada_id": jornada_id,
                    "home_team_id": shuffled_teams[i]["_id"],
                    "away_team_id": shuffled_teams[i + 1]["_id"],
                    "start_at": week_start + timedelta(hours=i),
                    "status": match_status_val,
                    "home_score": None, "away_score": None, "created_at": now
                }
                for i in range(0, min(18, len(shuffled_teams)), 2)
                if i + 1 < len(shuffled_teams)
            ]

        if matches:
            await db.matches.insert_many(matches)
        created_jornadas.append({"week_number": week, "jornada_id": str(jornada_id),
                                  "is_active": is_current, "status": week_status,
                                  "matches_count": len(matches)})

    logger.info(f"Created full season with {len(created_jornadas)} jornadas")
    return {"message": f"Se crearon {len(created_jornadas)} jornadas para la temporada completa",
            "jornadas": created_jornadas}


@router.post("/admin/seed-players")
async def seed_players(current_user: dict = Depends(get_admin_user)):
    teams = await db.teams.find().to_list(100)
    if len(teams) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Primero debes crear los equipos")

    await db.players.delete_many({})
    position_names = {
        "POR": ["Portero", "Arquero"],
        "DEF": ["Defensa Central", "Lateral Derecho", "Lateral Izquierdo"],
        "MED": ["Mediocampista", "Volante", "Medio Centro"],
        "DEL": ["Delantero", "Extremo", "Punta"]
    }
    players_created = 0
    base_stats = {"minutes_played": 0, "goals": 0, "assists": 0,
                  "saves": 0, "clean_sheets": 0, "defensive_actions": 0}

    for team in teams:
        for pos, counts, start_num in [("POR", 2, 1), ("DEF", 6, 3), ("MED", 8, 9), ("DEL", 5, 17)]:
            names = position_names[pos]
            for i in range(counts):
                await db.players.insert_one({
                    "name": f"{names[i % len(names)]} {i+1}",
                    "team_id": team["_id"], "position": pos,
                    "number": start_num + i, "stats": base_stats.copy(),
                    "created_at": datetime.utcnow()
                })
                players_created += 1

    logger.info(f"Seeded {players_created} players for {len(teams)} teams")
    return {"message": f"Se crearon {players_created} jugadores para {len(teams)} equipos",
            "players_count": players_created, "teams_count": len(teams)}


@router.post("/admin/seed-real-data")
async def seed_real_data(current_user: dict = Depends(get_admin_user)):
    logger.info("🏟️ Seeding REAL Liga MX data...")
    await db.teams.delete_many({})
    await db.players.delete_many({})
    await db.jornadas.delete_many({})
    await db.matches.delete_many({})

    teams_created = 0
    players_created = 0
    team_ids = []
    base_stats = {"minutes_played": 0, "goals": 0, "assists": 0,
                  "saves": 0, "clean_sheets": 0, "defensive_actions": 0}

    for team_data in LIGA_MX_TEAMS:
        team_result = await db.teams.insert_one({
            "name": team_data["name"], "short_name": team_data["short_name"],
            "color": team_data.get("color", "#000000"),
            "shield_url": team_data["shield_url"], "created_at": datetime.utcnow()
        })
        team_id = team_result.inserted_id
        team_ids.append(team_id)
        teams_created += 1

        for player_data in team_data.get("players", []):
            await db.players.insert_one({
                "name": player_data["name"], "team_id": team_id,
                "position": player_data["position"], "number": player_data["number"],
                "stats": base_stats.copy(), "created_at": datetime.utcnow()
            })
            players_created += 1

    now = datetime.utcnow()
    ACTIVE_WEEK = 11
    jornadas_created = 0

    for week in range(1, 18):
        weeks_from_active = week - ACTIVE_WEEK
        week_start = now + timedelta(weeks=weeks_from_active)
        week_end = week_start + timedelta(days=7)
        is_past = weeks_from_active < 0
        is_current = weeks_from_active == 0
        week_status = "finished" if is_past else ("in_progress" if is_current else "upcoming")
        match_status_val = "finished" if is_past else "scheduled"

        jornada_result = await db.jornadas.insert_one({
            "week_number": week, "start_date": week_start, "end_date": week_end,
            "status": week_status, "is_active": is_current, "created_at": now
        })
        jornada_id = jornada_result.inserted_id

        shuffled = list(team_ids)
        random.shuffle(shuffled)
        matches = [
            {
                "jornada_id": jornada_id,
                "home_team_id": shuffled[i], "away_team_id": shuffled[i + 1],
                "start_at": week_start + timedelta(hours=i),
                "status": match_status_val, "home_score": None, "away_score": None,
                "created_at": now
            }
            for i in range(0, min(len(shuffled), 18), 2)
            if i + 1 < len(shuffled)
        ]
        if matches:
            await db.matches.insert_many(matches)
        jornadas_created += 1

    logger.info(f"✅ REAL data seeded: {teams_created} teams, {players_created} players, {jornadas_created} jornadas")
    return {
        "message": "🏟️ Datos REALES de Liga MX cargados exitosamente",
        "teams_created": teams_created, "players_created": players_created,
        "jornadas_created": jornadas_created,
        "teams": [t["name"] for t in LIGA_MX_TEAMS]
    }


# ── Testing / dev-only ──────────────────────────────────────────────────────

# Genera resultados y estadísticas de jugadores ALEATORIAS para una jornada
# y sobreescribe sus marcadores reales — herramienta de testing/dev. Nunca
# se ha corrido contra una jornada real en producción; se movió aquí para
# que no pueda dispararse por accidente (sobreescribiría datos reales).
@router.post("/admin/fantasy/simulate-jornada/{jornada_id}")
async def simulate_fantasy_jornada(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    jornada_obj_id = ObjectId(jornada_id)

    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    matches = await db.matches.find({"jornada_id": jornada_obj_id}).to_list(20)
    if not matches:
        raise HTTPException(status_code=400, detail="No hay partidos en esta jornada")

    match_results = []
    player_stats_bulk = []

    for match in matches:
        home_team_id = match["home_team_id"]
        away_team_id = match["away_team_id"]
        home_score = random.choices([0, 1, 2, 3, 4], weights=[20, 35, 25, 15, 5])[0]
        away_score = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 12, 3])[0]

        await db.matches.update_one({"_id": match["_id"]}, {"$set": {
            "home_score": home_score, "away_score": away_score, "status": "finished"
        }})
        match_results.append({
            "match_id": str(match["_id"]),
            "home_team_id": str(home_team_id), "away_team_id": str(away_team_id),
            "home_score": home_score, "away_score": away_score
        })

        for team_id, _, goals_scored, goals_conceded in [
            (home_team_id, True, home_score, away_score),
            (away_team_id, False, away_score, home_score)
        ]:
            players = await db.players.find({"team_id": team_id}).to_list(30)
            goals_to_assign = goals_scored

            for player in players:
                position = player.get("position", "MED")
                played = random.random() > 0.1
                minutes = random.randint(60, 90) if played else (random.randint(0, 45) if random.random() > 0.5 else 0)

                stats = {
                    "match_id": match["_id"], "jornada_id": jornada_obj_id,
                    "player_id": player["_id"], "team_id": team_id, "position": position,
                    "minutes": minutes, "goals": 0, "assists": 0,
                    "clean_sheet": goals_conceded == 0 and minutes >= 60,
                    "goals_conceded": goals_conceded if position in ["POR", "DEF"] else 0,
                    "yellow_card": 1 if random.random() < 0.15 else 0,
                    "red_card": 1 if random.random() < 0.02 else 0,
                    "saves": random.randint(0, 6) if position == "POR" else 0,
                    "penalty_saved": 1 if position == "POR" and random.random() < 0.05 else 0,
                    "penalty_missed": 0,
                    "own_goal": 1 if random.random() < 0.01 else 0,
                    "man_of_the_match": False, "created_at": datetime.utcnow()
                }

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

                if stats["goals"] == 0 and random.random() < 0.2 and minutes >= 45:
                    stats["assists"] = 1

                player_stats_bulk.append(stats)

        if player_stats_bulk:
            match_players = [p for p in player_stats_bulk if p["match_id"] == match["_id"]]
            if match_players:
                match_players[random.randint(0, len(match_players) - 1)]["man_of_the_match"] = True

    if player_stats_bulk:
        await db.player_match_stats.delete_many({"jornada_id": jornada_obj_id})
        await db.player_match_stats.insert_many(player_stats_bulk)

    fantasy_results = await calculate_fantasy_points(jornada_id)
    return {
        "message": "Jornada simulada exitosamente", "jornada_id": jornada_id,
        "matches_simulated": len(match_results),
        "match_results": match_results, "fantasy_results": fantasy_results
    }


# ── Mundial 2026 ─────────────────────────────────────────────────────────────
# El torneo ya terminó — estos 3 endpoints (2 movidos desde liguilla.py) no
# deberían volver a correr salvo que FuchoMX vuelva a activar la competición
# world_cup_2026 en el futuro. Última vez que se usaron: julio 2026 (fase de
# grupos/eliminación del Mundial), antes de la migración a Liga MX Apertura
# 2026 (migrate-apertura-2026, más abajo).

@router.post("/admin/wc/process-match-stats")
async def process_wc_match_stats(
    body: WCMatchStatsRequest,
    current_user: dict = Depends(get_admin_user),
):
    try:
        match_oid = ObjectId(body.match_id)
    except Exception:
        raise HTTPException(status_code=400, detail="match_id inválido")

    match = await db.matches.find_one({"_id": match_oid})
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado")

    jornada_id = str(match["jornada_id"])

    stats_result = await get_wc_match_stats(body.game_id, db)
    if "error" in stats_result:
        raise HTTPException(status_code=502, detail=stats_result["error"])

    fantasy_results = await calculate_fantasy_points(jornada_id)

    logger.info(
        f"WC process-match-stats: game {body.game_id}, match {body.match_id} — "
        f"{stats_result['players_processed']} jugadores, jornada {jornada_id}"
    )
    return {
        "game_id":           body.game_id,
        "match_id":          body.match_id,
        "jornada_id":        jornada_id,
        "players_processed": stats_result["players_processed"],
        "score":             stats_result.get("score"),
        "home":              stats_result.get("home"),
        "away":              stats_result.get("away"),
        "fantasy_results":   fantasy_results,
    }


@router.post("/admin/seed-world-cup")
async def seed_world_cup(current_user: dict = Depends(get_admin_user)):
    """Movido desde routers/liguilla.py. Última vez que se usó: junio 2026,
    para sembrar los 48 equipos/96 partidos de fase de grupos del Mundial."""
    TEAMS_WC = [
        {"name": "México", "short_name": "MEX", "group": "A", "priority": 1, "shield_url": "https://upload.wikimedia.org/wikipedia/en/thumb/3/3f/Mexico_national_football_team_crest.svg/500px-Mexico_national_football_team_crest.svg.png"},
        {"name": "Sudáfrica", "short_name": "RSA", "group": "A", "priority": 99, "shield_url": "https://flagcdn.com/w160/za.png"},
        {"name": "Corea del Sur", "short_name": "KOR", "group": "A", "priority": 99, "shield_url": "https://flagcdn.com/w160/kr.png"},
        {"name": "Rep. Checa", "short_name": "CZE", "group": "A", "priority": 99, "shield_url": "https://flagcdn.com/w160/cz.png"},
        {"name": "Canadá", "short_name": "CAN", "group": "B", "priority": 99, "shield_url": "https://flagcdn.com/w160/ca.png"},
        {"name": "Bosnia", "short_name": "BIH", "group": "B", "priority": 99, "shield_url": "https://flagcdn.com/w160/ba.png"},
        {"name": "Qatar", "short_name": "QAT", "group": "B", "priority": 99, "shield_url": "https://flagcdn.com/w160/qa.png"},
        {"name": "Suiza", "short_name": "SUI", "group": "B", "priority": 99, "shield_url": "https://flagcdn.com/w160/ch.png"},
        {"name": "Brasil", "short_name": "BRA", "group": "C", "priority": 99, "shield_url": "https://flagcdn.com/w160/br.png"},
        {"name": "Marruecos", "short_name": "MAR", "group": "C", "priority": 99, "shield_url": "https://flagcdn.com/w160/ma.png"},
        {"name": "Haití", "short_name": "HAI", "group": "C", "priority": 99, "shield_url": "https://flagcdn.com/w160/ht.png"},
        {"name": "Escocia", "short_name": "SCO", "group": "C", "priority": 99, "shield_url": "https://flagcdn.com/w160/gb-sct.png"},
        {"name": "USA", "short_name": "USA", "group": "D", "priority": 99, "shield_url": "https://flagcdn.com/w160/us.png"},
        {"name": "Paraguay", "short_name": "PAR", "group": "D", "priority": 99, "shield_url": "https://flagcdn.com/w160/py.png"},
        {"name": "Australia", "short_name": "AUS", "group": "D", "priority": 99, "shield_url": "https://flagcdn.com/w160/au.png"},
        {"name": "Turquía", "short_name": "TUR", "group": "D", "priority": 99, "shield_url": "https://flagcdn.com/w160/tr.png"},
        {"name": "Alemania", "short_name": "GER", "group": "E", "priority": 99, "shield_url": "https://flagcdn.com/w160/de.png"},
        {"name": "Curaçao", "short_name": "CUW", "group": "E", "priority": 99, "shield_url": "https://flagcdn.com/w160/cw.png"},
        {"name": "Costa de Marfil", "short_name": "CIV", "group": "E", "priority": 99, "shield_url": "https://flagcdn.com/w160/ci.png"},
        {"name": "Ecuador", "short_name": "ECU", "group": "E", "priority": 99, "shield_url": "https://flagcdn.com/w160/ec.png"},
        {"name": "Países Bajos", "short_name": "NED", "group": "F", "priority": 99, "shield_url": "https://flagcdn.com/w160/nl.png"},
        {"name": "Japón", "short_name": "JPN", "group": "F", "priority": 99, "shield_url": "https://flagcdn.com/w160/jp.png"},
        {"name": "Suecia", "short_name": "SWE", "group": "F", "priority": 99, "shield_url": "https://flagcdn.com/w160/se.png"},
        {"name": "Túnez", "short_name": "TUN", "group": "F", "priority": 99, "shield_url": "https://flagcdn.com/w160/tn.png"},
        {"name": "Bélgica", "short_name": "BEL", "group": "G", "priority": 99, "shield_url": "https://flagcdn.com/w160/be.png"},
        {"name": "Egipto", "short_name": "EGY", "group": "G", "priority": 99, "shield_url": "https://flagcdn.com/w160/eg.png"},
        {"name": "Irán", "short_name": "IRN", "group": "G", "priority": 99, "shield_url": "https://flagcdn.com/w160/ir.png"},
        {"name": "Nueva Zelanda", "short_name": "NZL", "group": "G", "priority": 99, "shield_url": "https://flagcdn.com/w160/nz.png"},
        {"name": "España", "short_name": "ESP", "group": "H", "priority": 99, "shield_url": "https://flagcdn.com/w160/es.png"},
        {"name": "Cabo Verde", "short_name": "CPV", "group": "H", "priority": 99, "shield_url": "https://flagcdn.com/w160/cv.png"},
        {"name": "Arabia Saudita", "short_name": "KSA", "group": "H", "priority": 99, "shield_url": "https://flagcdn.com/w160/sa.png"},
        {"name": "Uruguay", "short_name": "URU", "group": "H", "priority": 99, "shield_url": "https://flagcdn.com/w160/uy.png"},
        {"name": "Francia", "short_name": "FRA", "group": "I", "priority": 99, "shield_url": "https://flagcdn.com/w160/fr.png"},
        {"name": "Senegal", "short_name": "SEN", "group": "I", "priority": 99, "shield_url": "https://flagcdn.com/w160/sn.png"},
        {"name": "Irak", "short_name": "IRQ", "group": "I", "priority": 99, "shield_url": "https://flagcdn.com/w160/iq.png"},
        {"name": "Noruega", "short_name": "NOR", "group": "I", "priority": 99, "shield_url": "https://flagcdn.com/w160/no.png"},
        {"name": "Argentina", "short_name": "ARG", "group": "J", "priority": 99, "shield_url": "https://flagcdn.com/w160/ar.png"},
        {"name": "Argelia", "short_name": "ALG", "group": "J", "priority": 99, "shield_url": "https://flagcdn.com/w160/dz.png"},
        {"name": "Austria", "short_name": "AUT", "group": "J", "priority": 99, "shield_url": "https://flagcdn.com/w160/at.png"},
        {"name": "Jordania", "short_name": "JOR", "group": "J", "priority": 99, "shield_url": "https://flagcdn.com/w160/jo.png"},
        {"name": "Portugal", "short_name": "POR", "group": "K", "priority": 99, "shield_url": "https://flagcdn.com/w160/pt.png"},
        {"name": "DR Congo", "short_name": "COD", "group": "K", "priority": 99, "shield_url": "https://flagcdn.com/w160/cd.png"},
        {"name": "Uzbekistán", "short_name": "UZB", "group": "K", "priority": 99, "shield_url": "https://flagcdn.com/w160/uz.png"},
        {"name": "Colombia", "short_name": "COL", "group": "K", "priority": 99, "shield_url": "https://flagcdn.com/w160/co.png"},
        {"name": "Inglaterra", "short_name": "ENG", "group": "L", "priority": 99, "shield_url": "https://flagcdn.com/w160/gb-eng.png"},
        {"name": "Croacia", "short_name": "CRO", "group": "L", "priority": 99, "shield_url": "https://flagcdn.com/w160/hr.png"},
        {"name": "Ghana", "short_name": "GHA", "group": "L", "priority": 99, "shield_url": "https://flagcdn.com/w160/gh.png"},
        {"name": "Panamá", "short_name": "PAN", "group": "L", "priority": 99, "shield_url": "https://flagcdn.com/w160/pa.png"},
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
        {"wn": 4, "title": "Round of 32",       "start": "2026-06-28", "end": "2026-07-03"},
        {"wn": 5, "title": "Round of 16",       "start": "2026-07-04", "end": "2026-07-07"},
        {"wn": 6, "title": "Cuartos de Final",  "start": "2026-07-09", "end": "2026-07-11"},
        {"wn": 7, "title": "Semifinales",       "start": "2026-07-14", "end": "2026-07-15"},
        {"wn": 8, "title": "Final Mundial",     "start": "2026-07-19", "end": "2026-07-19"},
    ]

    await db.teams.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})
    await db.players.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})
    await db.jornadas.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})
    await db.matches.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})

    await db.config.update_one(
        {"key": "active_competition"},
        {"$set": {"key": "active_competition", "value": "liga_mx"}},
        upsert=True
    )

    await db.teams.delete_many({"competition": "world_cup_2026"})
    await db.jornadas.delete_many({"competition": "world_cup_2026"})
    await db.matches.delete_many({"competition": "world_cup_2026"})

    team_ids: dict = {}
    for t in TEAMS_WC:
        result = await db.teams.insert_one({
            "name": t["name"], "short_name": t["short_name"],
            "shield_url": t["shield_url"], "competition": "world_cup_2026",
            "group": t["group"], "priority": t["priority"],
            "created_at": datetime.utcnow()
        })
        team_ids[t["name"]] = result.inserted_id

    jornada_ids: dict = {}
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


@router.post("/admin/seed-world-cup-players")
async def seed_world_cup_players(current_user: dict = Depends(get_admin_user)):
    """Movido desde routers/liguilla.py. Última vez que se usó: junio 2026,
    junto con seed-world-cup. Import de world_cup_players_data (83KB) queda
    local a esta función — no se carga en cada arranque del servidor, solo
    si este endpoint realmente se llama (y solo existe si ENABLE_MIGRATIONS
    está activo)."""
    from world_cup_players_data import WC_SQUADS

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
                "name": p["name"], "team_id": team["_id"], "team_name": team_name,
                "position": p["position"], "number": p["number"],
                "competition": "world_cup_2026",
                "stats": {"minutes_played": 0, "goals": 0, "assists": 0, "saves": 0,
                          "clean_sheets": 0, "defensive_actions": 0,
                          "yellow_cards": 0, "red_cards": 0},
                "created_at": datetime.utcnow()
            })
            inserted += 1

    return {
        "message": f"✅ Plantillas del Mundial cargadas: {inserted} jugadores de {len(WC_SQUADS) - len(skipped_teams)} selecciones",
        "players_inserted": inserted,
        "teams_loaded": len(WC_SQUADS) - len(skipped_teams),
        "skipped_teams": skipped_teams
    }


# ── Migración Mundial 2026 → Liga MX Apertura 2026 ──────────────────────────
# Corrida una sola vez, 22 de julio 2026, para el cutover del Mundial al
# Apertura 2026. No debería volver a correr — recrearía equipos/jugadores
# "liga_mx" desde cero.

@router.post("/admin/migrate-apertura-2026")
async def migrate_apertura_2026(current_user: dict = Depends(get_admin_user)):
    """
    Migración Mundial 2026 -> Liga MX Apertura 2026.
    - Desactiva cualquier jornada activa (incluye la del Mundial atorada en is_active=true).
    - NO borra equipos/jornadas/partidos del Mundial — quedan como historial.
    - Reemplaza (o re-siembra, es idempotente) los equipos/jugadores tageados "liga_mx".
    - Crea Jornada 1 (finished, resultados reales) y Jornada 2 (in_progress, fixture real).
    - Al final, cambia active_competition a "liga_mx" (cutover).
    """
    now = datetime.utcnow()

    deactivated = await db.jornadas.update_many(
        {"is_active": True}, {"$set": {"is_active": False}}
    )

    await db.teams.delete_many({"competition": "liga_mx"})
    await db.players.delete_many({"competition": "liga_mx"})

    team_ids: dict = {}
    teams_created = 0
    players_created = 0
    base_stats = {"minutes_played": 0, "goals": 0, "assists": 0, "saves": 0,
                  "clean_sheets": 0, "defensive_actions": 0,
                  "yellow_cards": 0, "red_cards": 0}

    for team_data in APERTURA_2026_TEAMS:
        team_result = await db.teams.insert_one({
            "name": team_data["name"], "short_name": team_data["short_name"],
            "color": team_data.get("color", "#000000"),
            "shield_url": team_data["shield_url"],
            "dt_name": team_data.get("dt_name", ""),
            "competition": "liga_mx", "created_at": now,
        })
        team_ids[team_data["short_name"]] = team_result.inserted_id
        teams_created += 1

        for player_data in team_data.get("players", []):
            await db.players.insert_one({
                "name": player_data["name"], "team_id": team_result.inserted_id,
                "team_name": team_data["name"],
                "position": player_data["position"], "number": player_data["number"],
                "competition": "liga_mx", "stats": base_stats.copy(),
                "created_at": now,
            })
            players_created += 1

    old_jornadas = await db.jornadas.find(
        {"competition": "liga_mx", "week_number": {"$in": [1, 2]}, "type": {"$ne": "liguilla"}}
    ).to_list(10)
    old_jornada_ids = [j["_id"] for j in old_jornadas]
    if old_jornada_ids:
        await db.matches.delete_many({"jornada_id": {"$in": old_jornada_ids}})
        await db.jornadas.delete_many({"_id": {"$in": old_jornada_ids}})

    j1_result = await db.jornadas.insert_one({
        "week_number": 1, "competition": "liga_mx",
        "start_date": datetime(2026, 7, 16), "end_date": datetime(2026, 7, 20, 12, 0),
        "status": "finished", "is_active": False, "processed": True, "created_at": now,
    })
    j1_id = j1_result.inserted_id
    j1_matches = [
        {
            "jornada_id": j1_id,
            "home_team_id": team_ids[home_sn], "away_team_id": team_ids[away_sn],
            "home_score": home_score, "away_score": away_score,
            "status": "finished", "start_at": start_at, "created_at": now,
            "ext_id_365": game_id,
        }
        for (game_id, home_sn, away_sn, home_score, away_score, start_at) in APERTURA_2026_J1_RESULTS
        if home_sn in team_ids and away_sn in team_ids
    ]
    if j1_matches:
        await db.matches.insert_many(j1_matches)

    j2_result = await db.jornadas.insert_one({
        "week_number": 2, "competition": "liga_mx",
        "start_date": datetime(2026, 7, 21), "end_date": datetime(2026, 7, 27),
        "status": "in_progress", "is_active": True, "processed": False, "created_at": now,
    })
    j2_id = j2_result.inserted_id
    j2_matches = [
        {
            "jornada_id": j2_id,
            "home_team_id": team_ids[home_sn], "away_team_id": team_ids[away_sn],
            "home_score": None, "away_score": None,
            "status": ("finished" if start_at < now else "scheduled"),
            "start_at": start_at, "created_at": now,
        }
        for (home_sn, away_sn, start_at) in APERTURA_2026_J2_FIXTURE
        if home_sn in team_ids and away_sn in team_ids
    ]
    if j2_matches:
        await db.matches.insert_many(j2_matches)

    await db.config.update_one(
        {"key": "active_competition"},
        {"$set": {"key": "active_competition", "value": "liga_mx"}},
        upsert=True
    )

    logger.info(
        f"✅ Migración Apertura 2026: {teams_created} equipos, {players_created} jugadores, "
        f"J1={len(j1_matches)} partidos, J2={len(j2_matches)} partidos, "
        f"{deactivated.modified_count} jornada(s) previa(s) desactivada(s)"
    )
    return {
        "message": "✅ Migración a Liga MX Apertura 2026 completada",
        "world_cup_jornadas_desactivadas": deactivated.modified_count,
        "teams_created": teams_created,
        "players_created": players_created,
        "jornada_1": {"id": str(j1_id), "matches": len(j1_matches)},
        "jornada_2": {"id": str(j2_id), "matches": len(j2_matches)},
        "active_competition": "liga_mx",
    }


# Backfill puntual de ext_id_365 para matches de J1 sembrados antes de que
# migrate_apertura_2026 empezara a guardar ese campo. Última vez que se usó:
# 22 de julio 2026, mismo día que la migración. Solo tiene datos para J1.
@router.post("/admin/jornada/{jornada_id}/patch-ext-ids")
async def patch_jornada_ext_ids(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    """
    Backfill de ext_id_365 en matches que ya existían antes de que
    migrate_apertura_2026 empezara a guardarlo (corridas de la migración
    hechas con una versión anterior del endpoint). Busca cada match por
    home_team_id/away_team_id (resueltos desde short_name) y le hace $set
    de ext_id_365 con el game_id real de 365Scores.
    Por ahora solo hay datos para Jornada 1 (APERTURA_2026_J1_RESULTS) — si
    se llama con otra jornada, no aplica nada y lo reporta explícitamente.
    """
    try:
        jornada_oid = ObjectId(jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")

    jornada = await db.jornadas.find_one({"_id": jornada_oid})
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    if jornada.get("competition") != "liga_mx" or jornada.get("week_number") != 1:
        return {
            "message": "Sin datos de ext_id_365 para esta jornada (solo Jornada 1 por ahora)",
            "patched": [],
            "not_found": [],
        }

    teams = await db.teams.find({"competition": "liga_mx"}).to_list(30)
    team_id_by_short_name = {t["short_name"]: t["_id"] for t in teams}

    patched = []
    not_found = []
    for game_id, home_sn, away_sn, _home_score, _away_score, _start_at in APERTURA_2026_J1_RESULTS:
        home_id = team_id_by_short_name.get(home_sn)
        away_id = team_id_by_short_name.get(away_sn)
        if not home_id or not away_id:
            not_found.append(f"{home_sn} vs {away_sn} (equipo no encontrado en DB)")
            continue

        result = await db.matches.update_one(
            {"jornada_id": jornada_oid, "home_team_id": home_id, "away_team_id": away_id},
            {"$set": {"ext_id_365": game_id}},
        )
        if result.matched_count:
            patched.append(f"{home_sn} vs {away_sn} -> {game_id}")
        else:
            not_found.append(f"{home_sn} vs {away_sn} (match no encontrado en esta jornada)")

    logger.info(
        f"patch-ext-ids jornada {jornada_id}: {len(patched)} actualizados, "
        f"{len(not_found)} no encontrados"
    )
    return {
        "message": f"✅ {len(patched)} partido(s) actualizados con ext_id_365",
        "patched": patched,
        "not_found": not_found,
    }


# Crea J3-J17 del Apertura 2026 vacías ("upcoming"). Última vez que se usó:
# 22 de julio 2026. Idempotente, pero ya no hay jornadas por crear — el
# calendario completo del Apertura 2026 ya existe en Mongo.
@router.post("/admin/create-remaining-jornadas")
async def create_remaining_jornadas(current_user: dict = Depends(get_admin_user)):
    """
    Crea J3-J17 del Apertura 2026 como "upcoming", sin partidos.
    Idempotente: si una jornada (competition="liga_mx", week_number=N) ya
    existe, se omite — no la duplica ni la modifica.
    El fixture real de cada jornada se carga por separado cuando se activa.
    """
    now = datetime.utcnow()
    created = []
    skipped = []

    for week_number, start_date, end_date, note in APERTURA_2026_REMAINING_JORNADAS:
        existing = await db.jornadas.find_one({
            "competition": "liga_mx", "week_number": week_number,
        })
        if existing:
            skipped.append(week_number)
            continue

        jornada_doc = {
            "week_number": week_number, "competition": "liga_mx",
            "start_date": start_date, "end_date": end_date,
            "status": "upcoming", "is_active": False, "processed": False,
            "created_at": now,
        }
        if note:
            jornada_doc["note"] = note
        await db.jornadas.insert_one(jornada_doc)
        created.append(week_number)

    logger.info(
        f"✅ create-remaining-jornadas: creadas={created}, ya existían={skipped}"
    )
    return {
        "message": f"✅ {len(created)} jornada(s) creada(s), {len(skipped)} ya existían",
        "created": created,
        "skipped": skipped,
    }


# Carga los partidos reales de J3-J17 (locked=true) en las jornadas creadas
# por create-remaining-jornadas. Última vez que se usó: 23 de julio 2026.
# Idempotente por jornada, pero el fixture completo ya está cargado.
@router.post("/admin/load-remaining-fixtures")
async def load_remaining_fixtures(current_user: dict = Depends(get_admin_user)):
    """
    Carga los partidos reales de J3-J17 (APERTURA_2026_J3_J17_FIXTURES,
    obtenidos de 365Scores) en las jornadas ya creadas por
    /admin/create-remaining-jornadas. Cada partido se inserta con
    "locked": True — el usuario NO puede enviar quiniela para esa jornada
    hasta que se active (el endpoint /jornadas/current pone locked=False
    en todos sus partidos al activarla, igual que ya hace con is_active).

    Idempotente por jornada: si una jornada (week_number=N, competition=
    liga_mx) ya tiene partidos, se omite — no duplica ni reemplaza.
    """
    competition = "liga_mx"
    teams = await db.teams.find({"competition": competition}).to_list(30)
    team_ids = {t["short_name"]: t["_id"] for t in teams}
    now = datetime.utcnow()

    loaded = []
    skipped = []
    missing_jornada = []

    for week_number, games in APERTURA_2026_J3_J17_FIXTURES.items():
        jornada = await db.jornadas.find_one({
            "competition": competition, "week_number": week_number,
        })
        if not jornada:
            missing_jornada.append(week_number)
            continue

        existing_count = await db.matches.count_documents({"jornada_id": jornada["_id"]})
        if existing_count > 0:
            skipped.append(week_number)
            continue

        match_docs = [
            {
                "jornada_id": jornada["_id"],
                "home_team_id": team_ids[home_sn], "away_team_id": team_ids[away_sn],
                "home_score": None, "away_score": None,
                "status": "scheduled", "start_at": start_at, "created_at": now,
                "ext_id_365": game_id, "locked": True,
            }
            for (game_id, home_sn, away_sn, start_at) in games
            if home_sn in team_ids and away_sn in team_ids
        ]
        if match_docs:
            await db.matches.insert_many(match_docs)
            loaded.append({"week_number": week_number, "matches": len(match_docs)})

    logger.info(
        f"load-remaining-fixtures: cargadas={[l['week_number'] for l in loaded]}, "
        f"ya existían={skipped}, sin jornada={missing_jornada}"
    )
    return {
        "message": f"✅ {len(loaded)} jornada(s) cargada(s) con partidos (locked=true)",
        "loaded": loaded,
        "skipped_ya_tenian_partidos": skipped,
        "sin_jornada_creada": missing_jornada,
    }


def _jornada_brief(j: dict) -> dict:
    return {
        "id": str(j["_id"]),
        "week_number": j.get("week_number"),
        "competition": j.get("competition"),
        "start_date": j["start_date"].isoformat() if j.get("start_date") else None,
        "is_active": j.get("is_active", False),
    }


# Limpieza puntual de jornadas huérfanas con is_active=true compitiendo con
# la jornada real. Última vez que se usó: 26 de julio 2026. Reemplazado en
# la práctica por audit-and-fix-jornadas (operacional, más robusto — recalcula
# por fecha en vez de asumir week_number=3 a mano).
@router.post("/admin/fix-active-jornada")
async def fix_active_jornada(current_user: dict = Depends(get_admin_user)):
    """
    Limpieza de jornadas huérfanas marcadas is_active=true (Clausura,
    Mundial 2026, etc.) que compiten con la jornada real del Apertura 2026.

    1. Lista todas las jornadas con is_active=true (diagnóstico, siempre
       incluido en la respuesta / en el detail del error).
    2. Busca la jornada correcta por week_number=3, SIN filtrar por
       competition — el filtro competition="liga_mx" no encontraba nada,
       así que asumimos que ese campo puede no estar seteado como se espera
       en el documento real y lo dejamos fuera del criterio por ahora.
    3. La marca is_active=true explícitamente y desactiva todas las demás
       jornadas que estaban activas. A las que ya no tienen partidos
       futuros pendientes, además les marca status="finished".
    """
    active_jornadas = await db.jornadas.find({"is_active": True}).to_list(100)
    active_list = [_jornada_brief(j) for j in active_jornadas]

    week3_candidates = await db.jornadas.find({"week_number": 3}).to_list(20)

    if not week3_candidates:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "No existe ninguna jornada con week_number=3 en la base de datos.",
                "active_jornadas": active_list,
            },
        )

    if len(week3_candidates) > 1:
        raise HTTPException(
            status_code=409,
            detail={
                "error": (
                    "Hay más de una jornada con week_number=3 — no se puede "
                    "decidir automáticamente cuál conservar."
                ),
                "week3_candidates": [_jornada_brief(j) for j in week3_candidates],
                "active_jornadas": active_list,
            },
        )

    keep = week3_candidates[0]
    await db.jornadas.update_one({"_id": keep["_id"]}, {"$set": {"is_active": True}})

    now = datetime.utcnow()
    deactivated = []
    for j in active_jornadas:
        if j["_id"] == keep["_id"]:
            continue

        future_matches = await db.matches.count_documents({
            "jornada_id": j["_id"],
            "start_at": {"$gt": now},
            "status": {"$ne": "finished"},
        })
        update_fields = {"is_active": False}
        if future_matches == 0:
            update_fields["status"] = "finished"
        await db.jornadas.update_one({"_id": j["_id"]}, {"$set": update_fields})

        deactivated.append({
            "id": str(j["_id"]),
            "week_number": j.get("week_number"),
            "competition": j.get("competition"),
            "status_set": update_fields.get("status", j.get("status")),
        })

    logger.info(
        f"fix-active-jornada: conservada week_number=3 ({keep['_id']}), "
        f"desactivadas {len(deactivated)}: {deactivated}"
    )
    return {
        "message": f"✅ {len(deactivated)} jornada(s) desactivada(s), quedó activa week_number=3",
        "active_jornadas_found": active_list,
        "kept_active": _jornada_brief({**keep, "is_active": True}),
        "deactivated_count": len(deactivated),
        "deactivated": deactivated,
    }


# (week_number, start_date, end_date) — calendario real del Apertura 2026
# para J3-J17. end_date se guarda a las 23:59:59 del día indicado (no a
# medianoche) para que la jornada no aparezca "finished" durante el propio
# día del último partido — mismo criterio que ya usan liguilla.py y
# apertura_2026_data.py en otras jornadas.
_JORNADA_DATE_FIXES = {
    3:  (datetime(2026, 7, 31), datetime(2026, 8, 2, 23, 59, 59)),
    4:  (datetime(2026, 8, 15), datetime(2026, 8, 17, 23, 59, 59)),
    5:  (datetime(2026, 8, 21), datetime(2026, 8, 23, 23, 59, 59)),
    6:  (datetime(2026, 8, 28), datetime(2026, 8, 30, 23, 59, 59)),
    7:  (datetime(2026, 9, 4),  datetime(2026, 9, 6, 23, 59, 59)),
    8:  (datetime(2026, 9, 11), datetime(2026, 9, 13, 23, 59, 59)),
    9:  (datetime(2026, 9, 18), datetime(2026, 9, 20, 23, 59, 59)),
    10: (datetime(2026, 9, 25), datetime(2026, 9, 27, 23, 59, 59)),
    11: (datetime(2026, 10, 9), datetime(2026, 10, 11, 23, 59, 59)),
    12: (datetime(2026, 10, 16), datetime(2026, 10, 18, 23, 59, 59)),
    13: (datetime(2026, 10, 20), datetime(2026, 10, 21, 23, 59, 59)),
    14: (datetime(2026, 10, 23), datetime(2026, 10, 25, 23, 59, 59)),
    15: (datetime(2026, 10, 30), datetime(2026, 11, 1, 23, 59, 59)),
    16: (datetime(2026, 11, 6), datetime(2026, 11, 8, 23, 59, 59)),
    17: (datetime(2026, 11, 20), datetime(2026, 11, 22, 23, 59, 59)),
}


# Corrige start_date/end_date de J3-J17 con el calendario real. Última vez
# que se usó: 27 de julio 2026. Las fechas ya quedaron corregidas en Mongo —
# no debería hacer falta volver a correrlo salvo que el calendario cambie.
@router.post("/admin/fix-jornada-dates")
async def fix_jornada_dates(current_user: dict = Depends(get_admin_user)):
    """
    Corrige start_date/end_date de J3-J17 (competition="liga_mx") con el
    calendario real del Apertura 2026 — las que tenía cada jornada en Mongo
    no correspondían (fechas viejas/formato incorrecto), lo cual hacía que
    audit-and-fix-jornadas las marcara "finished" de más.

    Busca cada jornada por (competition="liga_mx", week_number) en vez de
    por _id literal — no depende de copiar bien un ObjectId a mano. Al
    final corre audit_and_fix_jornadas para recalcular status/is_active
    con las fechas ya corregidas.
    """
    dates_report = []
    for week, (start, end) in _JORNADA_DATE_FIXES.items():
        jornada = await db.jornadas.find_one({
            "competition": "liga_mx", "week_number": week, "type": {"$ne": "liguilla"},
        })
        if not jornada:
            dates_report.append({"week_number": week, "found": False})
            continue

        before_start = jornada.get("start_date")
        before_end = jornada.get("end_date")
        await db.jornadas.update_one(
            {"_id": jornada["_id"]},
            {"$set": {"start_date": start, "end_date": end}},
        )
        dates_report.append({
            "week_number": week, "id": str(jornada["_id"]), "found": True,
            "before": {
                "start_date": before_start.isoformat() if before_start else None,
                "end_date": before_end.isoformat() if before_end else None,
            },
            "after": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        })

    fixed_count = sum(1 for r in dates_report if r["found"])
    not_found = [r["week_number"] for r in dates_report if not r["found"]]
    logger.info(f"fix-jornada-dates: {fixed_count} jornada(s) actualizadas, no encontradas={not_found}")

    audit_result = await audit_and_fix_jornadas(current_user=current_user)

    return {
        "message": f"✅ Fechas corregidas para {fixed_count} jornada(s) — auditoría re-ejecutada",
        "dates_fixed": dates_report,
        "not_found": not_found,
        "audit_result": audit_result,
    }


# Diagnostica/limpia matches vinculados por error a una jornada de otra
# temporada (causa: seed-world-cup retagueaba docs viejos sin "competition").
# Última vez que se usó: 27 de julio 2026, el mismo día que se encontró el
# bug. No debería hacer falta de nuevo salvo que reaparezca ese patrón de
# datos huérfanos.
@router.post("/admin/deep-clean-jornadas")
async def deep_clean_jornadas(current_user: dict = Depends(get_admin_user)):
    """
    Diagnostica y limpia matches vinculados por error a una jornada de otra
    temporada — causa real encontrada: /admin/seed-world-cup hace
    `update_many({"competition": {"$exists": False}}, ...)` sobre jornadas
    Y matches para retaguear docs viejos sin ese campo (ver liguilla.py) —
    eso incluyó las jornadas/matches del Clausura 2026 anterior, que se
    quedaron con competition="liga_mx" pero sus fechas y equipos viejos.
    Como create-remaining-jornadas y load-remaining-fixtures son
    idempotentes ("si ya existe/ya tiene partidos, no tocar"), esas
    jornadas Clausura retageadas con el mismo week_number que una jornada
    real del Apertura pasaron el check de "ya existe" y absorbieron el rol
    de "J3", "J4", etc. sin que nunca se les cargara el fixture correcto.

    1. Recorre TODAS las jornadas competition="liga_mx" (excluye liguilla),
       por week_number, y sus matches.
    2. Marca como huérfano (orphaned_at seteado, se le quita jornada_id —
       no se borra el documento) cualquier match cuyo start_at caiga fuera
       de la ventana [start_date - 2 días, end_date + 2 días] de su propia
       jornada — ahí es donde aparecen partidos de otra temporada (ej. un
       match de "31 de enero" colgado de una jornada de agosto).
    3. Si una jornada se queda en 0 partidos tras la limpieza, recarga su
       fixture real de APERTURA_2026_J3_J17_FIXTURES (mismo dataset que
       /admin/load-remaining-fixtures) — si la jornada está in_progress,
       los nuevos matches quedan locked=false para que se pueda picksear
       de inmediato.
    4. Para los matches que sobreviven, verifica que home_team_id/
       away_team_id resuelvan a un equipo real con shield_url válido —
       reporta huecos y repara shields rotos con el mismo fallback de
       audit-and-fix-jornadas.
    """
    jornadas = await db.jornadas.find(
        {"competition": "liga_mx", "type": {"$ne": "liguilla"}}
    ).sort("week_number", 1).to_list(100)

    teams_by_sn = None  # se resuelve una sola vez, solo si hace falta recargar fixtures
    report = []
    weeks_refixtured = []
    total_orphaned = 0

    for j in jornadas:
        jid = j["_id"]
        start, end = j.get("start_date"), j.get("end_date")
        matches = await db.matches.find({"jornada_id": jid}).to_list(100)

        orphaned, kept = [], []
        if start and end:
            window_start = start - timedelta(days=2)
            window_end = end + timedelta(days=2)
            for m in matches:
                m_start = m.get("start_at")
                if m_start and (m_start < window_start or m_start > window_end):
                    orphaned.append(m)
                else:
                    kept.append(m)
        else:
            kept = matches  # sin fechas propias no hay ventana contra la que comparar

        for m in orphaned:
            await db.matches.update_one(
                {"_id": m["_id"]},
                {
                    "$set": {"orphaned_at": datetime.utcnow(), "orphaned_from_jornada_id": jid},
                    "$unset": {"jornada_id": ""},
                },
            )
        total_orphaned += len(orphaned)

        fixture_reloaded = None
        if orphaned and not kept:
            week_fixtures = APERTURA_2026_J3_J17_FIXTURES.get(j.get("week_number"))
            if week_fixtures:
                if teams_by_sn is None:
                    teams_by_sn = {
                        t["short_name"]: t["_id"]
                        for t in await db.teams.find({"competition": "liga_mx"}).to_list(30)
                    }
                new_matches = [
                    {
                        "jornada_id": jid,
                        "home_team_id": teams_by_sn[home_sn], "away_team_id": teams_by_sn[away_sn],
                        "home_score": None, "away_score": None,
                        "status": "scheduled", "start_at": start_at, "created_at": datetime.utcnow(),
                        "ext_id_365": game_id, "locked": j.get("status") != "in_progress",
                    }
                    for (game_id, home_sn, away_sn, start_at) in week_fixtures
                    if home_sn in teams_by_sn and away_sn in teams_by_sn
                ]
                if new_matches:
                    await db.matches.insert_many(new_matches)
                    kept = new_matches
                    fixture_reloaded = len(new_matches)
                    weeks_refixtured.append(j.get("week_number"))

        shield_issues = []
        for m in kept:
            for label, team_id in (("home", m.get("home_team_id")), ("away", m.get("away_team_id"))):
                team = await db.teams.find_one({"_id": team_id}) if team_id else None
                if not team:
                    shield_issues.append({
                        "match_id": str(m.get("_id", "")), "side": label,
                        "issue": "equipo no encontrado (referencia huérfana)",
                    })
                    continue
                if _shield_is_broken(team.get("shield_url")):
                    fallback_url = _LIGA_MX_SHIELD_FALLBACK.get(team.get("short_name"))
                    if fallback_url:
                        await db.teams.update_one({"_id": team["_id"]}, {"$set": {"shield_url": fallback_url}})
                        shield_issues.append({
                            "match_id": str(m.get("_id", "")), "side": label, "team": team.get("name"),
                            "issue": "shield_url vacío/roto", "fixed": True, "after": fallback_url,
                        })
                    else:
                        shield_issues.append({
                            "match_id": str(m.get("_id", "")), "side": label, "team": team.get("name"),
                            "issue": "shield_url vacío/roto", "fixed": False,
                        })

        report.append({
            "week_number": j.get("week_number"), "jornada_id": str(jid),
            "matches_total": len(matches), "matches_orphaned": len(orphaned),
            "matches_kept": len(kept),
            "orphaned_match_ids": [str(m["_id"]) for m in orphaned],
            "fixture_reloaded": fixture_reloaded,
            "shield_issues": shield_issues,
        })

    logger.info(
        f"deep-clean-jornadas: {total_orphaned} match(es) huérfano(s) desvinculados, "
        f"semanas recargadas={weeks_refixtured}"
    )
    return {
        "message": (
            f"✅ Limpieza completada — {total_orphaned} match(es) huérfano(s) desvinculados, "
            f"{len(weeks_refixtured)} jornada(s) recargadas con su fixture real"
        ),
        "weeks_refixtured": weeks_refixtured,
        "jornadas": report,
    }


# Fuentes que solo tienen sentido si la jornada realmente cerró (nunca para
# una "upcoming" — no se puede penalizar por no seleccionar en una jornada
# donde el usuario ni siquiera podía seleccionar todavía).
_INVALID_ON_UPCOMING_SOURCES = [
    "QUINIELA_PENALIZACION", "ONCE_PENALIZACION",
    "QUINIELA_BONUS_NUEVO", "ONCE_BONUS_NUEVO",
]
# source -> campo de users.* que se le sumó cuando se insertó el points_log
# (ver scoring_penalties.py) — hay que revertirlo antes de borrar el log.
_SOURCE_USER_FIELD = {
    "QUINIELA_PENALIZACION": "total_points",
    "QUINIELA_BONUS_NUEVO": "total_points",
    "ONCE_PENALIZACION": "fantasy_total_points",
    "ONCE_BONUS_NUEVO": "fantasy_total_points",
}


# Purga el daño de J3-J12 penalizadas por error (causa raíz ya bloqueada con
# un guard de start_date en scheduler.py/scoring_penalties.py). Última vez
# que se usó: 27 de julio 2026, el mismo día que se agregó — es la corrida
# de limpieza única para ese incidente puntual.
@router.post("/admin/purge-invalid-penalties")
async def purge_invalid_penalties(current_user: dict = Depends(get_admin_user)):
    """
    Causa raíz (ver scheduler.py/scoring_penalties.py, ya bloqueada con un
    guard de start_date): jornadas "upcoming" con matches viejos huérfanos
    del Clausura marcados "finished" hicieron que _auto_close_and_advance_jornada
    las cerrara en cascada y les aplicara castigos/bonus por "no
    seleccionar" — J3 hasta J12 quedaron con QUINIELA_PENALIZACION/
    ONCE_PENALIZACION/*_BONUS_NUEVO que nunca debieron existir.

    Este endpoint limpia el daño ya hecho:
    1. Busca points_log con esas 4 fuentes cuyo jornada_id apunte a una
       jornada con status="upcoming".
    2. Revierte el efecto en users.total_points/fantasy_total_points
       (con el mismo signo invertido de lo que se sumó al insertarlos).
    3. Borra esos points_log.
    4. Resetea processed=False en las jornadas afectadas — si no, cuando
       esa jornada sí termine de verdad, _process_jornada_core la saltaría
       pensando que ya se procesó.
    """
    upcoming_jornadas = await db.jornadas.find({"status": "upcoming"}).to_list(200)
    upcoming_ids = {j["_id"] for j in upcoming_jornadas}
    if not upcoming_ids:
        return {"message": "No hay jornadas 'upcoming' — nada que revisar", "deleted": 0, "by_jornada": []}

    bad_entries = await db.points_log.find({
        "source": {"$in": _INVALID_ON_UPCOMING_SOURCES},
        "jornada_id": {"$in": list(upcoming_ids)},
    }).to_list(10000)

    if not bad_entries:
        return {"message": "No se encontraron penalizaciones inválidas", "deleted": 0, "by_jornada": []}

    by_jornada: dict = {}
    reversals: dict = {}
    for e in bad_entries:
        jid = e["jornada_id"]
        bucket = by_jornada.setdefault(jid, {"count": 0, "points_sum": 0})
        bucket["count"] += 1
        bucket["points_sum"] += e.get("points", 0)

        uid = e["user_id"]
        field = _SOURCE_USER_FIELD.get(e.get("source"), "total_points")
        reversals.setdefault(uid, {}).setdefault(field, 0)
        reversals[uid][field] -= e.get("points", 0)

    for uid, fields in reversals.items():
        inc = {f: v for f, v in fields.items() if v != 0}
        if inc:
            await db.users.update_one({"_id": uid}, {"$inc": inc})

    entry_ids = [e["_id"] for e in bad_entries]
    delete_result = await db.points_log.delete_many({"_id": {"$in": entry_ids}})

    await db.jornadas.update_many(
        {"_id": {"$in": list(by_jornada.keys())}},
        {"$set": {"processed": False}, "$unset": {"processed_at": ""}},
    )

    jornadas_by_id = {j["_id"]: j for j in upcoming_jornadas}
    report = [
        {
            "jornada_id": str(jid),
            "week_number": jornadas_by_id.get(jid, {}).get("week_number"),
            "entries_deleted": data["count"],
            "points_reverted": data["points_sum"],
        }
        for jid, data in by_jornada.items()
    ]
    report.sort(key=lambda r: r["week_number"] or 0)

    logger.info(
        f"purge-invalid-penalties: {delete_result.deleted_count} registro(s) eliminados en "
        f"{len(report)} jornada(s) upcoming, {len(reversals)} usuario(s) afectados"
    )
    return {
        "message": (
            f"✅ {delete_result.deleted_count} registro(s) inválido(s) eliminados de "
            f"{len(report)} jornada(s) upcoming"
        ),
        "deleted": delete_result.deleted_count,
        "users_affected": len(reversals),
        "by_jornada": report,
    }


# Fecha real de inicio de Jornada 3 (Apertura 2026) — ver
# APERTURA_2026_J3_J17_FIXTURES en apertura_2026_data.py. J3 tuvo el mismo
# bug de cascada que J4-J12 (auto-cierre procesando partidos huérfanos
# "finished" antes de que existieran los reales del 1-3 de agosto — ver
# purge_invalid_penalties arriba), pero quedó FUERA de esa limpieza porque
# para el 27 de julio ya no calificaba como status="upcoming" (ya estaba
# in_progress/is_active). Además del daño en points_log (Quiniela Y Once —
# ambos se insertan en la misma pasada de apply_jornada_close_adjustments),
# el bug marcó processed=True en la jornada, así que los puntos reales de
# quiniela (+3 por acierto) de los 9 partidos ya jugados nunca se calcularon.
_J3_REAL_START = datetime(2026, 8, 1)
_J3_BAD_SOURCES = [
    "QUINIELA_PENALIZACION", "QUINIELA_BONUS_NUEVO",
    "ONCE_PENALIZACION", "ONCE_BONUS_NUEVO",
]


@router.post("/admin/fix-jornada3-quiniela")
async def fix_jornada3_quiniela(current_user: dict = Depends(get_admin_user)):
    """
    Corrige Jornada 3 (Apertura 2026):
    1. Borra QUINIELA_PENALIZACION/QUINIELA_BONUS_NUEVO/ONCE_PENALIZACION/
       ONCE_BONUS_NUEVO de J3 creados antes del 2026-08-01 (basura del bug
       de cascada de J4-J12, aplicado aquí a una jornada que esa limpieza
       no cubrió).
    2. Revierte esos puntos del campo correcto de cada usuario afectado
       (total_points para Quiniela, fantasy_total_points para Once — ver
       _SOURCE_USER_FIELD) — no solo el admin, corre para todos.
    3. Resetea processed=False en J3.
    4. Vuelve a correr _process_jornada_core, que internamente llama a
       apply_jornada_close_adjustments (recalcula penalizaciones/bonus
       reales de Quiniela y Once contra los 9 partidos ya jugados, ahora
       que el guard de "todos finished" sí aplica de verdad) y calcula los
       puntos reales de quiniela (+3 por acierto).
    """
    jornada = await db.jornadas.find_one(
        {"competition": "liga_mx", "week_number": 3, "type": {"$ne": "liguilla"}}
    )
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada 3 no encontrada")

    jornada_id = jornada["_id"]

    bad_entries = await db.points_log.find({
        "jornada_id": jornada_id,
        "source": {"$in": _J3_BAD_SOURCES},
        "created_at": {"$lt": _J3_REAL_START},
    }).to_list(10000)

    reverted_by_user = []
    if bad_entries:
        reversals: dict = {}
        for e in bad_entries:
            field = _SOURCE_USER_FIELD.get(e.get("source"), "total_points")
            per_user = reversals.setdefault(e["user_id"], {})
            per_user[field] = per_user.get(field, 0) + e.get("points", 0)

        for uid, fields in reversals.items():
            inc = {f: -v for f, v in fields.items() if v != 0}
            if inc:
                await db.users.update_one({"_id": uid}, {"$inc": inc})
            user = await db.users.find_one({"_id": uid})
            reverted_by_user.append({
                "user_id": str(uid),
                "email": user.get("email") if user else None,
                "points_reverted": fields,
            })

        entry_ids = [e["_id"] for e in bad_entries]
        await db.points_log.delete_many({"_id": {"$in": entry_ids}})

    await db.jornadas.update_one(
        {"_id": jornada_id},
        {"$set": {"processed": False}, "$unset": {"processed_at": ""}},
    )

    proc_result = await _process_jornada_core(str(jornada_id))

    logger.info(
        f"fix-jornada3-quiniela: {len(bad_entries)} registro(s) inválido(s) eliminados, "
        f"{len(reverted_by_user)} usuario(s) revertidos, reprocesado: "
        f"quiniela={proc_result.get('quiniela_updated')} usuarios con puntos reales"
    )
    return {
        "message": (
            f"✅ Jornada 3 corregida — {len(bad_entries)} registro(s) inválido(s) purgados, "
            f"puntos revertidos, jornada reprocesada con resultados reales"
        ),
        "jornada_id": str(jornada_id),
        "invalid_entries_deleted": len(bad_entries),
        "users_reverted": reverted_by_user,
        "reprocess_result": proc_result,
    }
