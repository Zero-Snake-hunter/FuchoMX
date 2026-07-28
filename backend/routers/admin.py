import asyncio
import logging

_bg_tasks: set = set()

from datetime import datetime, timedelta

import httpx
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from config import API_FOOTBALL_KEY
from database import db, get_active_competition
from dependencies import get_admin_user
from fantasy_scoring import calculate_fantasy_points
from jornada_processor import _process_jornada_core, close_and_advance_jornada
from models import UpdateScoreRequest, UpdateRostersRequest
from services.liga_mx_stats_service import sync_match_stats_365, _normalize_player_name
from real_liga_mx_data import CLAUSURA_2026_DATES
from apertura_2026_data import APERTURA_2026_TEAMS
from services.api_football_service import get_players_by_team as _af_get_players
from services.push_service import notify_jornada_open

logger = logging.getLogger(__name__)

router = APIRouter()


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


# ── API-Football ──────────────────────────────────────────────────────────────

@router.post("/admin/sync-players-api-football")
async def sync_players_from_api_football(current_user: dict = Depends(get_admin_user)):
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
async def close_all_jornadas(current_user: dict = Depends(get_admin_user)):
    result = await db.jornadas.update_many(
        {"is_active": True},
        {"$set": {"is_active": False, "processed": True}}
    )
    return {"message": f"{result.modified_count} jornada(s) cerrada(s) correctamente",
            "modified": result.modified_count}


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
