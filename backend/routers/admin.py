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
from jornada_processor import _process_jornada_core
from models import UpdateScoreRequest
from real_liga_mx_data import (
    CLAUSURA_2026_DATES,
    CLAUSURA_2026_J13_MATCHES,
    LIGA_MX_TEAMS,
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
    last_jornada = await db.jornadas.find_one(sort=[("week_number", -1)])
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
    await db.jornadas.update_one({"_id": jornada_oid}, {"$set": {"status": "finished", "is_active": False}})

    jornada_competition = jornada.get("competition", "liga_mx")
    next_jornada = await db.jornadas.find_one(
        {"week_number": current_week + 1, "competition": jornada_competition}
    )

    next_info = None
    if next_jornada:
        await db.jornadas.update_one({"_id": next_jornada["_id"]}, {"$set": {
            "status": "upcoming", "is_active": True,
            "reminder_hours": reminder_hours, "notified_reminder": False,
        }})
        _task = asyncio.create_task(notify_jornada_open(next_jornada["week_number"]))
        _bg_tasks.add(_task)
        _task.add_done_callback(_bg_tasks.discard)
        next_info = {"id": str(next_jornada["_id"]), "week_number": next_jornada["week_number"]}
        logger.info(f"Closed jornada {current_week}, activated jornada {current_week + 1}")
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
