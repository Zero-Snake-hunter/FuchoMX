import logging
from datetime import datetime

from bson import ObjectId

from database import db

logger = logging.getLogger(__name__)

# ── Sistema de puntuación ─────────────────────────────────────────────────────

FANTASY_SCORING = {
    "minutes_played": {
        "threshold_60": 2,  # >= 60 minutos
        "under_60": 1       # < 60 minutos
    },
    "goals": {
        "POR": 6,
        "DEF": 6,
        "MED": 5,
        "DEL": 4
    },
    "assists": 3,
    "clean_sheet": {  # Portería a cero
        "POR": 5,
        "DEF": 4
    },
    "goals_conceded": {  # Por cada 2 goles recibidos (solo POR y DEF)
        "POR": -1,
        "DEF": -1
    },
    "yellow_card": -1,
    "red_card": -3,
    "penalty_saved": 5,
    "penalty_missed": -3,
    "own_goal": -2,
    "bonuses": {
        "man_of_the_match": 2,
        "brace": 1,          # 2 goles
        "hat_trick": 2,      # 3+ goles
        "keeper_4_saves": 1  # Portero con 4+ atajadas
    },
    "dt": {
        "team_win": 2,
        "team_draw": 1,
        "team_loss": 0
    }
}


def calculate_player_points(player_stats: dict, position: str) -> dict:
    """Calcula puntos fantasy de un jugador según sus estadísticas."""
    points = 0
    breakdown = {}

    # Minutos jugados
    minutes = player_stats.get("minutes", 0)
    if minutes >= 60:
        points += FANTASY_SCORING["minutes_played"]["threshold_60"]
        breakdown["minutes"] = {"value": minutes, "points": 2, "label": "Minutos (≥60)"}
    elif minutes > 0:
        points += FANTASY_SCORING["minutes_played"]["under_60"]
        breakdown["minutes"] = {"value": minutes, "points": 1, "label": "Minutos (<60)"}

    # Goles
    goals = player_stats.get("goals", 0)
    if goals > 0:
        goal_points = goals * FANTASY_SCORING["goals"].get(position, 4)
        points += goal_points
        breakdown["goals"] = {"value": goals, "points": goal_points, "label": f"Goles ({position})"}
        if goals == 2:
            points += FANTASY_SCORING["bonuses"]["brace"]
            breakdown["brace"] = {"value": 1, "points": 1, "label": "Doblete"}
        elif goals >= 3:
            points += FANTASY_SCORING["bonuses"]["hat_trick"]
            breakdown["hat_trick"] = {"value": 1, "points": 2, "label": "Hat-trick"}

    # Asistencias
    assists = player_stats.get("assists", 0)
    if assists > 0:
        assist_points = assists * FANTASY_SCORING["assists"]
        points += assist_points
        breakdown["assists"] = {"value": assists, "points": assist_points, "label": "Asistencias"}

    # Portería a cero (solo POR y DEF)
    if position in ["POR", "DEF"]:
        clean_sheet = player_stats.get("clean_sheet", False)
        if clean_sheet and minutes >= 60:
            cs_points = FANTASY_SCORING["clean_sheet"].get(position, 0)
            points += cs_points
            breakdown["clean_sheet"] = {"value": 1, "points": cs_points, "label": "Portería a cero"}

        goals_conceded = player_stats.get("goals_conceded", 0)
        if goals_conceded >= 2:
            gc_penalty = (goals_conceded // 2) * FANTASY_SCORING["goals_conceded"].get(position, -1)
            points += gc_penalty
            breakdown["goals_conceded"] = {"value": goals_conceded, "points": gc_penalty, "label": "Goles recibidos"}

    # Portero — atajadas
    if position == "POR":
        saves = player_stats.get("saves", 0)
        if saves >= 4:
            points += FANTASY_SCORING["bonuses"]["keeper_4_saves"]
            breakdown["saves"] = {"value": saves, "points": 1, "label": "4+ Atajadas"}

        penalty_saved = player_stats.get("penalty_saved", 0)
        if penalty_saved > 0:
            ps_points = penalty_saved * FANTASY_SCORING["penalty_saved"]
            points += ps_points
            breakdown["penalty_saved"] = {"value": penalty_saved, "points": ps_points, "label": "Penalti atajado"}

    # Tarjetas
    yellow = player_stats.get("yellow_card", 0)
    if yellow > 0:
        yellow_points = yellow * FANTASY_SCORING["yellow_card"]
        points += yellow_points
        breakdown["yellow_card"] = {"value": yellow, "points": yellow_points, "label": "Tarjeta amarilla"}

    red = player_stats.get("red_card", 0)
    if red > 0:
        red_points = red * FANTASY_SCORING["red_card"]
        points += red_points
        breakdown["red_card"] = {"value": red, "points": red_points, "label": "Tarjeta roja"}

    penalty_missed = player_stats.get("penalty_missed", 0)
    if penalty_missed > 0:
        pm_points = penalty_missed * FANTASY_SCORING["penalty_missed"]
        points += pm_points
        breakdown["penalty_missed"] = {"value": penalty_missed, "points": pm_points, "label": "Penalti fallado"}

    own_goal = player_stats.get("own_goal", 0)
    if own_goal > 0:
        og_points = own_goal * FANTASY_SCORING["own_goal"]
        points += og_points
        breakdown["own_goal"] = {"value": own_goal, "points": og_points, "label": "Autogol"}

    if player_stats.get("man_of_the_match", False):
        points += FANTASY_SCORING["bonuses"]["man_of_the_match"]
        breakdown["motm"] = {"value": 1, "points": 2, "label": "⭐ Jugador del partido"}

    return {"total_points": points, "breakdown": breakdown}


async def calculate_fantasy_points(jornada_id: str) -> dict:
    """Calcula puntos fantasy para todos los equipos de una jornada."""
    jornada_obj_id = ObjectId(jornada_id)

    all_lineups = await db.fantasy_lineups.find({"jornada_id": jornada_obj_id}).to_list(1000)

    team_lineups: dict = {}
    for lineup in all_lineups:
        team_id = lineup["fantasy_team_id"]
        team_lineups.setdefault(team_id, []).append(lineup)

    player_stats_map: dict = {}
    all_stats = await db.player_match_stats.find({"jornada_id": jornada_obj_id}).to_list(1000)
    for stat in all_stats:
        player_stats_map[stat["player_id"]] = stat

    team_results = []

    for fantasy_team_id, lineup_items in team_lineups.items():
        fantasy_team = await db.fantasy_teams.find_one({"_id": fantasy_team_id})
        if not fantasy_team:
            continue
        user = await db.users.find_one({"_id": fantasy_team["user_id"]})
        if not user:
            continue

        team_total_points = 0
        players_breakdown = []
        dt_points = 0

        for item in lineup_items:
            if item.get("is_dt"):
                dt_team_id = item.get("dt_team_id")
                if dt_team_id:
                    match = await db.matches.find_one({
                        "jornada_id": jornada_obj_id,
                        "$or": [
                            {"home_team_id": dt_team_id},
                            {"away_team_id": dt_team_id}
                        ]
                    })
                    if match and match.get("status") == "finished":
                        home_score = match.get("home_score", 0)
                        away_score = match.get("away_score", 0)
                        if match["home_team_id"] == dt_team_id:
                            if home_score > away_score:
                                dt_points = FANTASY_SCORING["dt"]["team_win"]
                            elif home_score == away_score:
                                dt_points = FANTASY_SCORING["dt"]["team_draw"]
                        else:
                            if away_score > home_score:
                                dt_points = FANTASY_SCORING["dt"]["team_win"]
                            elif away_score == home_score:
                                dt_points = FANTASY_SCORING["dt"]["team_draw"]
                        team_total_points += dt_points
            else:
                player_id = item.get("player_id")
                if player_id and player_id in player_stats_map:
                    stats = player_stats_map[player_id]
                    position = stats.get("position", "MED")
                    result = calculate_player_points(stats, position)
                    team_total_points += result["total_points"]
                    player = await db.players.find_one({"_id": player_id})
                    players_breakdown.append({
                        "player_id": str(player_id),
                        "player_name": player.get("name", "Unknown") if player else "Unknown",
                        "position": position,
                        "position_slot": item.get("position_slot"),
                        "points": result["total_points"],
                        "breakdown": result["breakdown"]
                    })

        # Guardar en fantasy_points_log
        await db.fantasy_points_log.delete_many({
            "fantasy_team_id": fantasy_team_id,
            "jornada_id": jornada_obj_id
        })
        await db.fantasy_points_log.insert_one({
            "fantasy_team_id": fantasy_team_id,
            "user_id": fantasy_team["user_id"],
            "jornada_id": jornada_obj_id,
            "total_points": team_total_points,
            "dt_points": dt_points,
            "players_breakdown": players_breakdown,
            "created_at": datetime.utcnow()
        })
        await db.users.update_one(
            {"_id": fantasy_team["user_id"]},
            {"$inc": {"fantasy_total_points": team_total_points}}
        )

        team_results.append({
            "fantasy_team_id": str(fantasy_team_id),
            "team_name": fantasy_team.get("name", "Unknown"),
            "user_name": user.get("display_name", "Unknown"),
            "user_email": user.get("email"),
            "total_points": team_total_points,
            "dt_points": dt_points,
            "players_count": len(players_breakdown),
            "players_breakdown": players_breakdown
        })

    team_results.sort(key=lambda x: x["total_points"], reverse=True)
    for idx, result in enumerate(team_results):
        result["rank"] = idx + 1

    return {"teams_processed": len(team_results), "rankings": team_results}
