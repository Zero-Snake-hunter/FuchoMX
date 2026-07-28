import asyncio
import logging

_bg_tasks: set = set()
import random
from datetime import datetime, timedelta

import httpx
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from config import ADMIN_EMAIL, API_FOOTBALL_KEY
from database import db, get_active_competition
from dependencies import get_admin_user, get_current_user
from fantasy_scoring import calculate_fantasy_points
from jornada_processor import _process_jornada_core, close_and_advance_jornada
from models import UpdateScoreRequest, WCMatchStatsRequest, UpdateRostersRequest
from services.world_cup_stats_service import get_wc_match_stats
from services.liga_mx_stats_service import sync_match_stats_365, _normalize_player_name
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
from services.api_football_service import (
    get_fixtures_by_date as _af_get_by_date,
    get_live_fixtures as _af_get_live,
    get_players_by_team as _af_get_players,
)
from services.push_service import notify_jornada_open

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Seed ──────────────────────────────────────────────────────────────────────

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


# ── Jornada management ────────────────────────────────────────────────────────

@router.post("/admin/reset-jornada")
async def reset_jornada(week: int = None, reminder_hours: int = 2, current_user: dict = Depends(get_admin_user)):
    now = datetime.utcnow()

    if week is not None:
        competition = await get_active_competition()
        target = await db.jornadas.find_one({"week_number": week, "competition": competition})
        if not target:
            raise HTTPException(status_code=404,
                                detail=f"Jornada {week} no encontrada para competición '{competition}'")
        await db.jornadas.update_many({"competition": competition}, {"$set": {"is_active": False}})
        await db.jornadas.update_one({"_id": target["_id"]}, {"$set": {
            "is_active": True, "status": "in_progress",
            "start_date": now, "end_date": now + timedelta(days=7),
            "reminder_hours": reminder_hours, "notified_reminder": False,
        }})
        _task = asyncio.create_task(notify_jornada_open(week))
        _bg_tasks.add(_task)
        _task.add_done_callback(_bg_tasks.discard)
        logger.info(f"Admin reset-jornada: jornada {week} activada directamente")
        return {"message": f"✅ Jornada {week} activada", "week_number": week, "jornada_id": str(target["_id"])}

    adv_competition = await get_active_competition()
    current = await db.jornadas.find_one({"is_active": True, "competition": adv_competition})
    if not current:
        current = await db.jornadas.find_one(
            {"status": {"$ne": "finished"}, "competition": adv_competition},
            sort=[("week_number", 1)]
        )
    if not current:
        raise HTTPException(status_code=404,
                            detail="No hay jornadas disponibles. Ejecuta /api/admin/seed-season primero.")

    closed_week = current["week_number"]
    await db.jornadas.update_one({"_id": current["_id"]}, {"$set": {"is_active": False, "status": "finished"}})

    next_j = await db.jornadas.find_one({"week_number": closed_week + 1, "competition": adv_competition})
    if not next_j:
        raise HTTPException(status_code=404,
                            detail=f"No hay jornada después de la {closed_week}. Esa era la última.")

    await db.jornadas.update_one({"_id": next_j["_id"]}, {"$set": {
        "is_active": True, "status": "in_progress",
        "start_date": now, "end_date": now + timedelta(days=7),
        "reminder_hours": reminder_hours, "notified_reminder": False,
    }})
    _task = asyncio.create_task(notify_jornada_open(closed_week + 1))
    _bg_tasks.add(_task)
    _task.add_done_callback(_bg_tasks.discard)
    logger.info(f"Admin reset-jornada: {closed_week} → {closed_week + 1}")
    return {
        "message": f"✅ Jornada {closed_week} cerrada → Jornada {closed_week + 1} activa",
        "closed_week": closed_week, "active_week": closed_week + 1, "jornada_id": str(next_j["_id"])
    }


@router.post("/admin/quiniela/cerrar-jornada/{jornada_id}")
async def close_jornada(jornada_id: str, reminder_hours: int = 2, current_user: dict = Depends(get_admin_user)):
    try:
        jornada_oid = ObjectId(jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")

    jornada = await db.jornadas.find_one({"_id": jornada_oid})
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    current_week = jornada["week_number"]
    # Lógica compartida con el auto-scheduler — ambos cierran/abren igual.
    result = await close_and_advance_jornada(jornada_oid, reminder_hours=reminder_hours)

    next_info = result.get("next_jornada")
    if next_info:
        _task = asyncio.create_task(notify_jornada_open(next_info["week_number"]))
        _bg_tasks.add(_task)
        _task.add_done_callback(_bg_tasks.discard)
        logger.info(f"Closed jornada {current_week}, activated jornada {next_info['week_number']}")
    else:
        logger.info(f"Closed jornada {current_week}. No next jornada (season ended)")

    return {
        "message": f"Jornada {current_week} cerrada exitosamente",
        "closed_jornada": {"id": jornada_id, "week_number": current_week},
        "next_jornada": next_info
    }


@router.post("/admin/sync-fixtures")
async def sync_fixtures(current_user: dict = Depends(get_admin_user)):
    LEAGUE_ID = "4350"
    BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }
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
    CLAUSURA_2025_DATES = CLAUSURA_2026_DATES

    events_fetched = 0
    matches_updated = 0
    source = "thesportsdb"
    api_error = None

    teams_list = await db.teams.find().to_list(100)
    team_by_name = {t["name"]: t["_id"] for t in teams_list}
    competition = await get_active_competition()

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            next_r = await client.get(f"{BASE_URL}/eventsnextleague.php?id={LEAGUE_ID}", headers=HEADERS)
            past_r = await client.get(f"{BASE_URL}/eventspastleague.php?id={LEAGUE_ID}", headers=HEADERS)

        all_events = []
        if next_r.status_code == 200 and next_r.text.strip().startswith("{"):
            all_events += (next_r.json().get("events") or [])
        if past_r.status_code == 200 and past_r.text.strip().startswith("{"):
            all_events += (past_r.json().get("results") or [])

        if not all_events:
            raise ValueError(f"No events — HTTP {next_r.status_code}")

        sample_league = (all_events[0].get("strLeague") or "").lower()
        if "mexico" not in sample_league and "liga mx" not in sample_league and "primera" not in sample_league:
            raise ValueError(f"Eventos no son de Liga MX — liga recibida: '{all_events[0].get('strLeague')}'.")

        events_fetched = len(all_events)
        now = datetime.utcnow()

        for ev in all_events:
            home_name = NAME_MAP.get(ev.get("strHomeTeam", ""), ev.get("strHomeTeam", ""))
            away_name = NAME_MAP.get(ev.get("strAwayTeam", ""), ev.get("strAwayTeam", ""))
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

            match_filter: dict = {"home_team_id": home_id, "away_team_id": away_id}
            round_num = ev.get("intRound")
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
        logger.warning(f"sync-fixtures: TheSportsDB falló ({exc}). Usando fallback.")

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
                await db.matches.update_one({"_id": m["_id"]}, {"$set": {"start_at": match_date, "status": st}})
                matches_updated += 1

    return {
        "message": f"✅ Sync completado — {matches_updated} partidos actualizados",
        "source": source, "events_fetched": events_fetched,
        "matches_updated": matches_updated, "api_error": api_error,
    }


@router.get("/admin/jornadas")
async def list_all_jornadas(current_user: dict = Depends(get_admin_user)):
    competition = await get_active_competition()
    jornadas = await db.jornadas.find({"competition": competition}).sort("week_number", 1).to_list(25)
    result = [
        {
            "id": str(j["_id"]),
            "week_number": j["week_number"],
            "start_date": j["start_date"].isoformat() if j.get("start_date") else None,
            "end_date":   j["end_date"].isoformat()   if j.get("end_date")   else None,
            "status":     j.get("status", "unknown"),
            "is_active":  j.get("is_active", False)
        }
        for j in jornadas
    ]
    return {"jornadas": result, "total": len(result)}


@router.get("/admin/jornada/{jornada_id}/matches")
async def list_jornada_matches(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    try:
        jornada_oid = ObjectId(jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")

    jornada = await db.jornadas.find_one({"_id": jornada_oid})
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    matches = await db.matches.find({"jornada_id": jornada_oid}).to_list(50)

    result = []
    for m in matches:
        home_team = await db.teams.find_one({"_id": m["home_team_id"]})
        away_team = await db.teams.find_one({"_id": m["away_team_id"]})
        result.append({
            "match_id":   str(m["_id"]),
            "home_team":  home_team.get("name", "?") if home_team else "?",
            "away_team":  away_team.get("name", "?") if away_team else "?",
            "home_score": m.get("home_score"),
            "away_score": m.get("away_score"),
            "status":     m.get("status", "scheduled"),
            "start_at":   m["start_at"].isoformat() if m.get("start_at") else None,
        })

    return {
        "jornada_id":  jornada_id,
        "week_number": jornada.get("week_number"),
        "competition": jornada.get("competition"),
        "matches":     result,
        "total":       len(result),
    }


# ── Quiniela admin ────────────────────────────────────────────────────────────

@router.put("/admin/match/{match_id}/score")
async def update_match_score(match_id: str, scores: UpdateScoreRequest,
                             current_user: dict = Depends(get_admin_user)):
    match = await db.matches.find_one({"_id": ObjectId(match_id)})
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partido no encontrado")

    await db.matches.update_one(
        {"_id": ObjectId(match_id)},
        {"$set": {"home_score": scores.home_score, "away_score": scores.away_score, "status": "finished"}}
    )
    logger.info(f"Match {match_id} score updated: {scores.home_score}-{scores.away_score}")
    return {"message": "Resultado actualizado", "match_id": match_id,
            "score": f"{scores.home_score}-{scores.away_score}"}


@router.post("/admin/jornada/{jornada_id}/calculate-points")
async def calculate_jornada_points(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    jornada_obj_id = ObjectId(jornada_id)

    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jornada no encontrada")

    matches = await db.matches.find({"jornada_id": jornada_obj_id, "status": "finished"}).to_list(100)
    if not matches:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No hay partidos finalizados en esta jornada")

    match_results = {}
    for match in matches:
        h, a = match["home_score"], match["away_score"]
        match_results[match["_id"]] = "HOME" if h > a else ("AWAY" if a > h else "DRAW")

    all_selections = await db.quiniela_selections.find({"jornada_id": jornada_obj_id}).to_list(10000)
    user_selections: dict = {}
    for sel in all_selections:
        user_selections.setdefault(sel["user_id"], []).append(sel)

    users_updated = 0
    total_points_awarded = 0

    for user_id, selections in user_selections.items():
        points = sum(
            3 for sel in selections
            if sel["match_id"] in match_results and sel["selection"] == match_results[sel["match_id"]]
        )
        if points > 0:
            await db.points_log.insert_one({
                "user_id": user_id, "jornada_id": jornada_obj_id,
                "source": "QUINIELA", "points": points, "created_at": datetime.utcnow()
            })
            await db.users.update_one({"_id": user_id}, {"$inc": {"total_points": points}})
            users_updated += 1
            total_points_awarded += points

    await db.jornadas.update_one({"_id": jornada_obj_id}, {"$set": {"status": "finished"}})
    logger.info(f"Calculated points for jornada {jornada_id}: {users_updated} users, {total_points_awarded} points")
    return {"message": "Puntos calculados exitosamente", "jornada_id": jornada_id,
            "users_updated": users_updated, "total_points_awarded": total_points_awarded}


@router.post("/admin/process-jornada/{jornada_id}")
async def process_jornada_endpoint(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    result = await _process_jornada_core(jornada_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ── Fantasy admin ─────────────────────────────────────────────────────────────

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


# ── API-Football ──────────────────────────────────────────────────────────────

@router.post("/admin/sync-players-api-football")
async def sync_players_from_api_football(current_user: dict = Depends(get_current_user)):
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
                        "api_football_id": p["api_id"], "name": p["name"],
                        "firstname": p["firstname"], "lastname": p["lastname"],
                        "photo": p["photo"], "position": p["position"],
                        "team_name": team_name, "team_id": str(team["_id"]),
                        "nationality": p["nationality"], "goals": p["goals"],
                        "assists": p["assists"], "appearances": p["appearances"],
                        "rating": p["rating"], "updated_at": datetime.utcnow(),
                    }},
                    upsert=True
                )
                total_updated += 1
            logger.info(f"✅ {team_name}: {len(players)} jugadores sincronizados")
        except Exception as e:
            errors.append(f"{team_name}: {str(e)}")
            logger.error(f"❌ Error sincronizando {team_name}: {e}")

    return {"message": "Sincronización completada", "players_updated": total_updated, "errors": errors}


# ── Migración Apertura 2026 ─────────────────────────────────────────────────────

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


@router.post("/admin/update-rosters-from-espn")
async def update_rosters_from_espn(
    body: UpdateRostersRequest, current_user: dict = Depends(get_admin_user)
):
    """
    Reconcilia el roster de uno o más equipos (competition="liga_mx") contra
    una lista de jugadores dada — borra los que ya no están, inserta los que
    faltan, y NO toca a los que coinciden (conserva su _id, stats acumuladas,
    etc.). Idempotente por equipo.

    IMPORTANTE — por qué esto no consulta a ESPN en vivo por sí mismo:
    ESPN (espn.com.mx) está detrás de un challenge de AWS WAF — cualquier
    request HTTP simple (httpx, requests, curl) recibe un HTTP 202 con una
    página de JS de verificación en vez del HTML real, verificado en vivo
    contra este mismo endpoint de plantel. No hay forma de resolver ese
    challenge desde un backend sin un navegador real. Por eso este endpoint
    recibe el roster ya extraído (vía WebFetch en una sesión de Claude Code,
    o cualquier otro método que sí pueda pasar el challenge) en vez de
    scrapear la URL él mismo — el nombre se mantiene porque el dato en sí
    sigue viniendo de ESPN, solo que la extracción pasa por fuera del backend.
    """
    results = []
    for team_update in body.teams:
        team = await db.teams.find_one({
            "competition": "liga_mx", "short_name": team_update.team_short_name,
        })
        if not team:
            results.append({
                "team_short_name": team_update.team_short_name,
                "error": "Equipo no encontrado (competition=liga_mx)",
            })
            continue

        team_id = team["_id"]
        current_players = await db.players.find({"team_id": team_id}).to_list(60)
        current_by_norm = {_normalize_player_name(p["name"]): p for p in current_players}
        incoming_by_norm = {
            _normalize_player_name(p.name): p for p in team_update.players
        }

        to_delete = [p for norm, p in current_by_norm.items() if norm not in incoming_by_norm]
        to_insert = [p for norm, p in incoming_by_norm.items() if norm not in current_by_norm]
        kept = len(current_by_norm) - len(to_delete)

        if to_delete:
            await db.players.delete_many({"_id": {"$in": [p["_id"] for p in to_delete]}})

        base_stats = {"minutes_played": 0, "goals": 0, "assists": 0, "saves": 0,
                      "clean_sheets": 0, "defensive_actions": 0,
                      "yellow_cards": 0, "red_cards": 0}
        if to_insert:
            await db.players.insert_many([
                {
                    "name": p.name, "team_id": team_id, "team_name": team["name"],
                    "position": p.position, "number": p.number,
                    "competition": "liga_mx", "stats": base_stats.copy(),
                    "created_at": datetime.utcnow(),
                }
                for p in to_insert
            ])

        results.append({
            "team_short_name": team_update.team_short_name,
            "team_name": team["name"],
            "deleted": [p["name"] for p in to_delete],
            "inserted": [p.name for p in to_insert],
            "kept": kept,
        })

    logger.info(
        "update-rosters-from-espn: " +
        ", ".join(
            f"{r.get('team_short_name')}=+{len(r.get('inserted', []))}/-{len(r.get('deleted', []))}"
            for r in results
        )
    )
    return {"message": f"✅ {len(results)} equipo(s) procesados", "results": results}


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


@router.post("/admin/update-team-shield")
async def update_team_shield(
    short_name: str, shield_url: str, current_user: dict = Depends(get_admin_user)
):
    """
    Corrige el shield_url de un equipo ya sembrado en Mongo (competition=
    liga_mx) sin tener que volver a correr una migración completa. Uso
    puntual — ej. Atlante se sembró con un placeholder (via.placeholder.com)
    porque no había shield real disponible al momento de migrar.
    """
    result = await db.teams.update_one(
        {"competition": "liga_mx", "short_name": short_name},
        {"$set": {"shield_url": shield_url}},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipo con short_name={short_name} no encontrado (competition=liga_mx)",
        )
    logger.info(f"update-team-shield: {short_name} -> {shield_url}")
    return {
        "message": f"✅ shield_url actualizado para {short_name}",
        "matched": result.matched_count,
        "modified": result.modified_count,
    }


@router.post("/admin/sync-dt-names")
async def sync_dt_names(current_user: dict = Depends(get_admin_user)):
    """
    Actualiza dt_name en los 18 equipos ya sembrados en Mongo (competition=
    liga_mx) desde APERTURA_2026_TEAMS, sin re-migrar todo. Uso puntual —
    los equipos se sembraron antes de que se agregara el campo dt_name.
    """
    updated = []
    not_found = []
    for team_data in APERTURA_2026_TEAMS:
        sn = team_data["short_name"]
        dt_name = team_data.get("dt_name", "")
        result = await db.teams.update_one(
            {"competition": "liga_mx", "short_name": sn},
            {"$set": {"dt_name": dt_name}},
        )
        if result.matched_count:
            updated.append(f"{sn}={dt_name}")
        else:
            not_found.append(sn)

    logger.info(f"sync-dt-names: {len(updated)} actualizados, {len(not_found)} sin equipo")
    return {
        "message": f"✅ {len(updated)} equipo(s) actualizados con dt_name",
        "updated": updated,
        "not_found": not_found,
    }


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


@router.post("/admin/jornada/{jornada_id}/sync-365-stats")
async def sync_jornada_stats_365(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    """
    Trae stats reales (goles, tarjetas, minutos) de 365Scores para cada
    partido "finished" de la jornada que tenga ext_id_365, empareja
    jugadores contra el roster propio y guarda en player_match_stats.
    Al final recalcula puntos fantasy de la jornada.
    Reporta jugadores de la alineación real que NO se pudieron emparejar
    contra el roster sembrado (roster desactualizado = jugadores sin puntos).
    """
    try:
        jornada_oid = ObjectId(jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")

    jornada = await db.jornadas.find_one({"_id": jornada_oid})
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    matches = await db.matches.find({
        "jornada_id": jornada_oid, "status": "finished", "ext_id_365": {"$exists": True},
    }).to_list(50)

    results = []
    total_matched = 0
    total_unmatched = 0
    for match in matches:
        result = await sync_match_stats_365(match, db)
        results.append(result)
        total_matched += result.get("players_matched", 0)
        total_unmatched += result.get("players_unmatched", 0)

    fantasy_result = await calculate_fantasy_points(jornada_id)

    logger.info(
        f"sync-365-stats jornada {jornada_id}: {len(matches)} partidos, "
        f"{total_matched} jugadores emparejados, {total_unmatched} sin match"
    )
    return {
        "message": f"✅ {len(matches)} partido(s) procesados desde 365Scores",
        "jornada_id": jornada_id,
        "matches_processed": len(matches),
        "players_matched": total_matched,
        "players_unmatched": total_unmatched,
        "match_results": results,
        "fantasy_teams_processed": fantasy_result.get("teams_processed", 0),
    }


@router.post("/admin/close-all-jornadas")
async def close_all_jornadas(current_user: dict = Depends(get_current_user)):
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    result = await db.jornadas.update_many(
        {"is_active": True},
        {"$set": {"is_active": False, "processed": True}}
    )
    return {"message": f"{result.modified_count} jornada(s) cerrada(s) correctamente",
            "modified": result.modified_count}


def _jornada_brief(j: dict) -> dict:
    return {
        "id": str(j["_id"]),
        "week_number": j.get("week_number"),
        "competition": j.get("competition"),
        "start_date": j["start_date"].isoformat() if j.get("start_date") else None,
        "is_active": j.get("is_active", False),
    }


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


@router.post("/admin/jornada/{jornada_id}/activate")
async def activate_jornada(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    """
    Activa una jornada específica por id: is_active=true, status="in_progress"
    y desbloquea todos sus partidos. Además desactiva cualquier otra jornada
    que haya quedado is_active=true en la MISMA competition (para no volver
    a terminar con dos jornadas activas del mismo torneo compitiendo).

    Útil cuando hay jornadas huérfanas de otro torneo con el mismo
    week_number (ej. liga_mx y world_cup_2026 ambas con week_number=3) —
    fix-active-jornada no puede decidir automáticamente en ese caso, así
    que aquí se activa por id explícito sin ambigüedad.
    """
    try:
        jornada_oid = ObjectId(jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")

    jornada = await db.jornadas.find_one({"_id": jornada_oid})
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    competition = jornada.get("competition")
    others = await db.jornadas.find(
        {"is_active": True, "competition": competition, "_id": {"$ne": jornada_oid}}
    ).to_list(50)
    if others:
        await db.jornadas.update_many(
            {"_id": {"$in": [o["_id"] for o in others]}},
            {"$set": {"is_active": False}},
        )

    await db.jornadas.update_one(
        {"_id": jornada_oid},
        {"$set": {"is_active": True, "status": "in_progress"}},
    )
    unlock_result = await db.matches.update_many(
        {"jornada_id": jornada_oid}, {"$set": {"locked": False}}
    )

    logger.info(
        f"activate-jornada: {jornada_id} (week_number={jornada.get('week_number')}, "
        f"competition={competition}) activada, {unlock_result.modified_count} partido(s) "
        f"desbloqueados, {len(others)} otra(s) jornada(s) de la misma competition desactivada(s)"
    )
    return {
        "message": (
            f"✅ Jornada {jornada.get('week_number')} ({competition}) activada, "
            f"{unlock_result.modified_count} partido(s) desbloqueados"
        ),
        "activated": {
            "id": jornada_id,
            "week_number": jornada.get("week_number"),
            "competition": competition,
        },
        "matches_unlocked": unlock_result.modified_count,
        "other_active_deactivated": [
            {"id": str(o["_id"]), "week_number": o.get("week_number"), "competition": o.get("competition")}
            for o in others
        ],
    }


_LIGA_MX_SHIELD_FALLBACK = {
    "AME": "https://a.espncdn.com/i/teamlogos/soccer/500/227.png",
    "GDL": "https://a.espncdn.com/i/teamlogos/soccer/500/228.png",
    "CAZ": "https://a.espncdn.com/i/teamlogos/soccer/500/232.png",
    "TIG": "https://a.espncdn.com/i/teamlogos/soccer/500/233.png",
    "MTY": "https://a.espncdn.com/i/teamlogos/soccer/500/238.png",
    "PUM": "https://a.espncdn.com/i/teamlogos/soccer/500/241.png",
    "SAN": "https://a.espncdn.com/i/teamlogos/soccer/500/242.png",
    "TOL": "https://a.espncdn.com/i/teamlogos/soccer/500/236.png",
    "LEO": "https://a.espncdn.com/i/teamlogos/soccer/500/235.png",
    "ATL": "https://a.espncdn.com/i/teamlogos/soccer/500/244.png",
    "PAC": "https://a.espncdn.com/i/teamlogos/soccer/500/239.png",
    "TIJ": "https://a.espncdn.com/i/teamlogos/soccer/500/2020.png",
    "NEC": "https://a.espncdn.com/i/teamlogos/soccer/500/243.png",
    "QRO": "https://a.espncdn.com/i/teamlogos/soccer/500/6678.png",
    "PUE": "https://a.espncdn.com/i/teamlogos/soccer/500/240.png",
    "JUA": "https://a.espncdn.com/i/teamlogos/soccer/500/5942.png",
    "ASL": "https://a.espncdn.com/i/teamlogos/soccer/500/5930.png",
    "ATE": "https://a.espncdn.com/i/teamlogos/soccer/500/226.png",
}


def _shield_is_broken(url) -> bool:
    return not isinstance(url, str) or not url.strip() or not url.strip().lower().startswith("http")


@router.post("/admin/audit-and-fix-jornadas")
async def audit_and_fix_jornadas(current_user: dict = Depends(get_admin_user)):
    """
    Recalcula status/is_active de TODAS las jornadas de temporada regular
    (competition="liga_mx", excluye liguilla) a partir de la fecha real
    (datetime.utcnow(), no una fecha fija) comparada contra start_date/
    end_date de cada una, desbloquea los partidos de la que quede
    in_progress y bloquea los de las upcoming. Los matches solo se
    vinculan por jornada_id — los documentos de match no tienen un campo
    week_number propio — así que ese es el único criterio usado para no
    perder ninguno.

    Si ninguna jornada califica como in_progress por fecha (la anterior ya
    cerró pero la siguiente todavía no arranca según su start_date),
    promueve a in_progress la "upcoming" de week_number más bajo que ya
    tenga partidos cargados — nunca debe quedar un hueco sin jornada
    activa entre jornadas, mismo criterio que ya aplica
    /admin/quiniela/cerrar-jornada al activar la siguiente de inmediato.

    Además revisa shield_url de los 18 equipos liga_mx: si está vacío,
    null o no es una URL http(s), lo repara con el fallback de ESPN. Los
    que ya tienen una URL válida (aunque no sea de ESPN, ej. TheSportsDB)
    NO se tocan — sobreescribir una URL que ya funciona por asumir que
    "debería" ser la de ESPN es exactamente el tipo de error de IDs
    cruzados que ya se dio una vez con estos escudos (ver comentario en
    apertura_2026_data.py).
    """
    now = datetime.utcnow()

    # ── Jornadas ────────────────────────────────────────────────────────────
    jornadas = await db.jornadas.find(
        {"competition": "liga_mx", "type": {"$ne": "liguilla"}}
    ).sort("week_number", 1).to_list(100)

    if not jornadas:
        raise HTTPException(status_code=404, detail="No hay jornadas con competition='liga_mx'")

    computed = []
    for j in jornadas:
        start, end = j.get("start_date"), j.get("end_date")
        if not start or not end:
            computed.append({"jornada": j, "new_status": None, "new_is_active": None,
                              "reason": "sin start_date/end_date, no se pudo evaluar"})
        elif end < now:
            computed.append({"jornada": j, "new_status": "finished", "new_is_active": False, "reason": None})
        elif start <= now <= end:
            computed.append({"jornada": j, "new_status": "in_progress", "new_is_active": True, "reason": None})
        else:
            computed.append({"jornada": j, "new_status": "upcoming", "new_is_active": False, "reason": None})

    # Fechas superpuestas entre jornadas podrían calificar a más de una como
    # in_progress — solo puede haber una activa, se conserva la de
    # week_number más alto (la más avanzada) y el resto baja a upcoming.
    in_progress_items = [c for c in computed if c["new_status"] == "in_progress"]
    overlap_warning = None
    if len(in_progress_items) > 1:
        keep = max(in_progress_items, key=lambda c: c["jornada"]["week_number"])
        for c in in_progress_items:
            if c is not keep:
                c["new_status"] = "upcoming"
                c["new_is_active"] = False
        overlap_warning = (
            f"{len(in_progress_items)} jornadas calificaban como in_progress por fechas "
            f"superpuestas — se conservó week_number={keep['jornada']['week_number']} como activa."
        )

    # Si ninguna jornada calificó como in_progress por fecha (ej. la anterior
    # ya cerró pero la siguiente todavía no arranca según su start_date),
    # activamos la "upcoming" de week_number más bajo que ya tenga partidos
    # cargados — evita el hueco "sin jornada activa" entre jornadas, mismo
    # criterio que ya usa /admin/quiniela/cerrar-jornada.
    promoted_week = None
    if not any(c["new_status"] == "in_progress" for c in computed):
        upcoming_sorted = sorted(
            (c for c in computed if c["new_status"] == "upcoming"),
            key=lambda c: c["jornada"]["week_number"],
        )
        for c in upcoming_sorted:
            match_count = await db.matches.count_documents({"jornada_id": c["jornada"]["_id"]})
            if match_count > 0:
                c["new_status"] = "in_progress"
                c["new_is_active"] = True
                promoted_week = c["jornada"]["week_number"]
                break

    jornadas_report = []
    active_week = None
    for c in computed:
        j = c["jornada"]
        jid = j["_id"]
        old_status = j.get("status")
        old_is_active = bool(j.get("is_active", False))

        if c["new_status"] is None:
            jornadas_report.append({
                "week_number": j.get("week_number"), "id": str(jid), "changed": False,
                "skipped_reason": c["reason"], "status": old_status, "is_active": old_is_active,
            })
            continue

        changed = old_status != c["new_status"] or old_is_active != c["new_is_active"]
        if changed:
            await db.jornadas.update_one(
                {"_id": jid},
                {"$set": {"status": c["new_status"], "is_active": c["new_is_active"]}},
            )

        matches_unlocked = matches_locked = 0
        if c["new_status"] == "in_progress":
            active_week = j.get("week_number")
            result = await db.matches.update_many({"jornada_id": jid}, {"$set": {"locked": False}})
            matches_unlocked = result.modified_count
        elif c["new_status"] == "upcoming":
            result = await db.matches.update_many({"jornada_id": jid}, {"$set": {"locked": True}})
            matches_locked = result.modified_count

        jornadas_report.append({
            "week_number": j.get("week_number"), "id": str(jid), "changed": changed,
            "status": {"before": old_status, "after": c["new_status"]},
            "is_active": {"before": old_is_active, "after": c["new_is_active"]},
            "matches_unlocked": matches_unlocked, "matches_locked": matches_locked,
        })

    # ── Escudos ─────────────────────────────────────────────────────────────
    teams = await db.teams.find({"competition": "liga_mx"}).to_list(30)
    shields_report = []
    for t in teams:
        short_name = t.get("short_name")
        current_url = t.get("shield_url")
        if not _shield_is_broken(current_url):
            shields_report.append({
                "short_name": short_name, "name": t.get("name"), "fixed": False, "already_ok": True,
            })
            continue

        fallback_url = _LIGA_MX_SHIELD_FALLBACK.get(short_name)
        if not fallback_url:
            shields_report.append({
                "short_name": short_name, "name": t.get("name"), "fixed": False,
                "before": current_url, "reason": "sin URL de respaldo para este short_name",
            })
            continue

        await db.teams.update_one({"_id": t["_id"]}, {"$set": {"shield_url": fallback_url}})
        shields_report.append({
            "short_name": short_name, "name": t.get("name"), "fixed": True,
            "before": current_url, "after": fallback_url,
        })

    jornadas_changed = sum(1 for r in jornadas_report if r.get("changed"))
    shields_fixed = sum(1 for r in shields_report if r.get("fixed"))

    logger.info(
        f"audit-and-fix-jornadas: {jornadas_changed} jornada(s) corregidas, "
        f"active_week={active_week}, promoted_week_no_date_match={promoted_week}, "
        f"{shields_fixed} escudo(s) reparados"
    )
    return {
        "message": (
            f"✅ Auditoría completada — {jornadas_changed} jornada(s) corregidas, "
            f"jornada activa=semana {active_week}, {shields_fixed} escudo(s) reparados"
        ),
        "active_week": active_week,
        "overlap_warning": overlap_warning,
        "promoted_week_no_date_match": promoted_week,
        "jornadas": jornadas_report,
        "shields": shields_report,
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


@router.post("/admin/fix-negative-scores")
async def fix_negative_scores(current_user: dict = Depends(get_admin_user)):
    """
    Corrige matches con marcador -1/-1 guardado por el scheduler viejo
    (bug ya arreglado) — los deja en score=null y status="scheduled"
    para que el scheduler corregido los vuelva a procesar desde cero.
    """
    query = {"$or": [{"home_score": -1}, {"away_score": -1}]}
    affected = await db.matches.find(query).to_list(200)

    result = await db.matches.update_many(
        query,
        {"$set": {"home_score": None, "away_score": None, "status": "scheduled"}},
    )
    logger.info(f"fix-negative-scores: {result.modified_count} partido(s) corregidos")
    return {
        "message": f"✅ {result.modified_count} partido(s) corregidos (score=null, status=scheduled)",
        "matched": result.matched_count,
        "modified": result.modified_count,
        "match_ids": [str(m["_id"]) for m in affected],
    }


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


@router.get("/admin/debug/points-log/{user_id}")
async def debug_points_log(user_id: str, current_user: dict = Depends(get_admin_user)):
    """
    Diagnóstico: TODOS los points_log de un usuario, con jornada_id,
    week_number/competition resueltos (para ver si el punto realmente
    pertenece a la jornada que debería), source, points y created_at.
    user_id acepta un ObjectId válido o un email — así no hace falta
    buscar el _id primero en /admin/stats (que solo trae los 5 usuarios
    más recientes, no sirve para encontrar cuentas viejas como la del
    admin).
    """
    try:
        user_oid = ObjectId(user_id)
        user = await db.users.find_one({"_id": user_oid})
    except Exception:
        user = await db.users.find_one({"email": user_id})

    if not user:
        raise HTTPException(status_code=404, detail=f"Usuario no encontrado: {user_id}")

    user_oid = user["_id"]
    points = await db.points_log.find({"user_id": user_oid}).sort("created_at", 1).to_list(1000)

    jornada_ids = [p["jornada_id"] for p in points if p.get("jornada_id")]
    jornadas = await db.jornadas.find({"_id": {"$in": jornada_ids}}).to_list(len(jornada_ids) or 1)
    jornada_by_id = {j["_id"]: j for j in jornadas}

    entries = []
    total_all_sources = 0
    for p in points:
        jornada_id = p.get("jornada_id")
        jornada = jornada_by_id.get(jornada_id) if jornada_id else None
        pts = p.get("points", 0)
        total_all_sources += pts
        entries.append({
            "id": str(p["_id"]),
            "jornada_id": str(jornada_id) if jornada_id else None,
            "jornada_found": jornada is not None,
            "week_number": jornada.get("week_number") if jornada else None,
            "competition": jornada.get("competition") if jornada else None,
            "source": p.get("source"),
            "points": pts,
            "matches_sin_pick": p.get("matches_sin_pick"),
            "created_at": p.get("created_at").isoformat() if p.get("created_at") else None,
        })

    return {
        "user": {
            "id": str(user_oid),
            "email": user.get("email"),
            "display_name": user.get("display_name"),
            "total_points_field": user.get("total_points", 0),
        },
        "points_log_count": len(entries),
        "points_log_sum_all_sources": total_all_sources,
        "entries": entries,
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
