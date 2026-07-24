import logging
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from achievements import award_achievement
from database import db, get_active_competition
from dependencies import get_current_user
from fantasy_scoring import calculate_player_points
from models import FantasyLineupSubmit, FantasyTeamCreate

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Rankings ──────────────────────────────────────────────────────────────────

@router.get("/fantasy/rankings/jornada/{jornada_id}")
async def get_fantasy_jornada_rankings(jornada_id: str):
    jornada_obj_id = ObjectId(jornada_id)
    points_logs = await db.fantasy_points_log.find(
        {"jornada_id": jornada_obj_id}
    ).sort("total_points", -1).to_list(100)

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


@router.get("/fantasy/rankings/general")
async def get_fantasy_general_rankings():
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


# ── Team & lineup ──────────────────────────────────────────────────────────────

@router.post("/fantasy/team")
async def create_or_update_fantasy_team(
    team_data: FantasyTeamCreate,
    current_user: dict = Depends(get_current_user)
):
    existing_team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    if existing_team:
        await db.fantasy_teams.update_one(
            {"_id": existing_team["_id"]},
            {"$set": {"name": team_data.name}}
        )
        return {
            "message": "Nombre de equipo actualizado",
            "team_id": str(existing_team["_id"]),
            "name": team_data.name
        }

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


@router.get("/fantasy/my-team")
async def get_my_fantasy_team(current_user: dict = Depends(get_current_user)):
    team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    if not team:
        return {
            "exists": False,
            "default_name": f"{current_user['display_name']} - FC"
        }
    return {
        "exists": True,
        "team_id": str(team["_id"]),
        "name": team["name"],
        "created_at": team["created_at"]
    }


@router.get("/players")
async def get_players(
    position: Optional[str] = None,
    team_id: Optional[str] = None,
    team_name: Optional[str] = None
):
    competition = await get_active_competition()
    query: dict = {"competition": competition}

    if position:
        query["position"] = position
    if team_id:
        try:
            query["team_id"] = ObjectId(team_id)
        except Exception:
            query["team_id"] = team_id
    if team_name:
        query["team_name"] = {"$regex": team_name, "$options": "i"}

    players = await db.players.find(query).to_list(1000)

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
                    except Exception:
                        pass

            formatted_players.append({
                "id": str(player["_id"]),
                "name": player.get("name", ""),
                "number": player.get("number") or 0,
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


@router.post("/fantasy/lineup")
async def submit_fantasy_lineup(
    lineup: FantasyLineupSubmit,
    current_user: dict = Depends(get_current_user)
):
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

    existing = await db.fantasy_lineups.find_one({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_id
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya enviaste tu alineación para esta jornada"
        )

    if len(lineup.players) != 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes seleccionar exactamente 11 jugadores"
        )

    lineup_docs = [
        {
            "fantasy_team_id": team["_id"],
            "jornada_id": jornada_id,
            "player_id": ObjectId(p["player_id"]),
            "position_slot": p["position_slot"],
            "is_dt": False,
            "created_at": datetime.utcnow()
        }
        for p in lineup.players
    ]

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
    await award_achievement(current_user["_id"], "first_lineup")

    return {
        "message": "Alineación guardada exitosamente",
        "jornada_id": lineup.jornada_id,
        "players_count": len(lineup_docs)
    }


@router.get("/fantasy/lineup/{jornada_id}")
async def get_fantasy_lineup(
    jornada_id: str,
    current_user: dict = Depends(get_current_user)
):
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

    formatted_lineup = []
    for item in lineup:
        if item.get("is_dt"):
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
            player = await db.players.find_one({"_id": item["player_id"]})
            if player:
                player_team = await db.teams.find_one({"_id": player["team_id"]})
                formatted_lineup.append({
                    "position_slot": item["position_slot"],
                    "is_dt": False,
                    "player": {
                        "id": str(player["_id"]),
                        "name": player["name"],
                        "number": player.get("number") or 0,
                        "position": player["position"],
                        "team": {
                            "id": str(player_team["_id"]),
                            "name": player_team["name"],
                            "short_name": player_team["short_name"],
                            "shield_url": player_team["shield_url"]
                        } if player_team else None
                    }
                })

    return {"submitted": True, "lineup": formatted_lineup}


@router.get("/fantasy/results/{jornada_id}")
async def get_fantasy_results(
    jornada_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna la alineación del usuario con puntos desglosados.
    Usa fantasy_points_log si ya fue procesado, o calcula en tiempo real.
    """
    jornada_obj_id = ObjectId(jornada_id)
    team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    if not team:
        return {"has_lineup": False, "players": [], "total_points": 0}

    # 1. Buscar en fantasy_points_log (ya procesado)
    log = await db.fantasy_points_log.find_one({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_obj_id,
    })
    if log:
        return {
            "has_lineup":   True,
            "team_name":    team.get("name", "Mi Equipo"),
            "total_points": log.get("total_points", 0),
            "dt_points":    log.get("dt_points", 0),
            "players":      log.get("players_breakdown", []),
            "processed":    True,
            "jornada_id":   jornada_id,
        }

    # 2. Calcular en tiempo real si no está procesado
    lineup_items = await db.fantasy_lineups.find({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_obj_id,
    }).to_list(100)

    if not lineup_items:
        return {"has_lineup": False, "players": [], "total_points": 0}

    all_stats = await db.player_match_stats.find(
        {"jornada_id": jornada_obj_id}
    ).to_list(5000)
    stats_by_player_id = {s["player_id"]: s for s in all_stats}

    players_result = []
    total_pts = 0

    for item in lineup_items:
        if item.get("is_dt"):
            continue

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
