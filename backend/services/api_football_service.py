"""
Servicio de API-Football para FuchoMX.
Cubre: jugadores por equipo, fixtures en vivo, stats de jugadores.
"""
import httpx
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

BASE_URL = "https://v3.football.api-sports.io"
LIGA_MX_ID = 262
SEASON = 2025  # Clausura 2026 = season 2025

# Map nombres de equipos DB → IDs de API-Football
TEAM_IDS = {
    "Pumas UNAM":     3432,
    "Guadalajara":    3439,
    "Cruz Azul":      3435,
    "Pachuca":        3441,
    "Toluca":         3446,
    "Atlas":          3430,
    "Tigres UANL":    3445,
    "Club América":   3431,
    "Necaxa":         3440,
    "Querétaro":      3442,
    "León":           3438,
    "Mazatlán FC":    3448,
    "FC Juárez":      3447,
    "Monterrey":      3436,
    "Atlético de San Luis": 3449,
    "Tijuana":        3444,
}

async def _get(endpoint: str, params: dict, api_key: str) -> dict:
    headers = {
        "x-apisports-key": api_key,
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(f"{BASE_URL}{endpoint}", params=params, headers=headers)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"API-Football error {endpoint}: {e}")
            return {}


async def get_players_by_team(team_name: str, api_key: str) -> list:
    """Obtiene jugadores de un equipo de Liga MX."""
    team_id = TEAM_IDS.get(team_name)
    if not team_id:
        logger.warning(f"No team_id para: {team_name}")
        return []

    all_players = []
    page = 1
    while True:
        data = await _get("/players", {
            "team": team_id,
            "league": LIGA_MX_ID,
            "season": SEASON,
            "page": page,
        }, api_key)

        if not data or "response" not in data:
            break

        players = data["response"]
        if not players:
            break

        for p in players:
            player = p.get("player", {})
            stats = p.get("statistics", [{}])[0]
            all_players.append({
                "api_id":    player.get("id"),
                "name":      player.get("name", ""),
                "firstname": player.get("firstname", ""),
                "lastname":  player.get("lastname", ""),
                "age":       player.get("age"),
                "nationality": player.get("nationality", ""),
                "photo":     player.get("photo", ""),
                "position":  stats.get("games", {}).get("position", ""),
                "team_name": team_name,
                "team_id":   team_id,
                "appearances": stats.get("games", {}).get("appearences", 0),
                "goals":     stats.get("goals", {}).get("total", 0),
                "assists":   stats.get("goals", {}).get("assists", 0),
                "rating":    stats.get("games", {}).get("rating", "0"),
            })

        paging = data.get("paging", {})
        if page >= paging.get("total", 1):
            break
        page += 1

    logger.info(f"API-Football: {len(all_players)} jugadores para {team_name}")
    return all_players


async def get_live_fixtures(api_key: str) -> list:
    """Obtiene partidos en vivo de Liga MX."""
    data = await _get("/fixtures", {
        "live": "all",
        "league": LIGA_MX_ID,
        "season": SEASON,
    }, api_key)

    if not data or "response" not in data:
        return []

    fixtures = []
    for f in data["response"]:
        fix = f.get("fixture", {})
        teams = f.get("teams", {})
        goals = f.get("goals", {})
        score = f.get("score", {})
        status = fix.get("status", {})

        fixtures.append({
            "id":           fix.get("id"),
            "date":         fix.get("date"),
            "status":       status.get("short", ""),
            "elapsed":      status.get("elapsed", 0),
            "home_team":    teams.get("home", {}).get("name", ""),
            "away_team":    teams.get("away", {}).get("name", ""),
            "home_goals":   goals.get("home", 0),
            "away_goals":   goals.get("away", 0),
        })

    return fixtures


async def get_fixtures_by_date(match_date: date, api_key: str) -> list:
    """Obtiene partidos de Liga MX en una fecha específica."""
    data = await _get("/fixtures", {
        "league": LIGA_MX_ID,
        "season": SEASON,
        "date":   match_date.strftime("%Y-%m-%d"),
    }, api_key)

    if not data or "response" not in data:
        return []

    fixtures = []
    for f in data["response"]:
        fix = f.get("fixture", {})
        teams = f.get("teams", {})
        goals = f.get("goals", {})
        status = fix.get("status", {})

        fixtures.append({
            "id":           fix.get("id"),
            "date":         fix.get("date"),
            "status_short": status.get("short", "NS"),
            "status_long":  status.get("long", "Not Started"),
            "elapsed":      status.get("elapsed", 0),
            "home_team":    teams.get("home", {}).get("name", ""),
            "away_team":    teams.get("away", {}).get("name", ""),
            "home_goals":   goals.get("home"),
            "away_goals":   goals.get("away"),
        })

    return fixtures


async def get_player_stats(player_api_id: int, api_key: str) -> dict:
    """Obtiene stats detalladas de un jugador en Liga MX."""
    data = await _get("/players", {
        "id":     player_api_id,
        "league": LIGA_MX_ID,
        "season": SEASON,
    }, api_key)

    if not data or not data.get("response"):
        return {}

    p = data["response"][0]
    player = p.get("player", {})
    stats = p.get("statistics", [{}])[0]
    games = stats.get("games", {})
    goals_data = stats.get("goals", {})
    passes = stats.get("passes", {})
    tackles = stats.get("tackles", {})

    return {
        "api_id":      player.get("id"),
        "name":        player.get("name", ""),
        "position":    games.get("position", ""),
        "appearances": games.get("appearences", 0),
        "minutes":     games.get("minutes", 0),
        "rating":      float(games.get("rating") or 0),
        "goals":       goals_data.get("total", 0),
        "assists":     goals_data.get("assists", 0),
        "key_passes":  passes.get("key", 0),
        "tackles":     tackles.get("total", 0),
    }
