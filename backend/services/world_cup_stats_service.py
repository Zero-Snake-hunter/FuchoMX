"""
world_cup_stats_service.py
Obtiene stats de jugadores de un partido del Mundial desde 365Scores
y los guarda en MongoDB para que el sistema de puntuación fantasy los procese.
"""
import logging
import httpx
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger(__name__)

_365SCORES_GAME_URL = (
    "https://webws.365scores.com/web/game/?gameId={game_id}"
)
_365SCORES_HEADERS = {
    "Origin": "https://www.365scores.com",
    "Referer": "https://www.365scores.com/",
    "User-Agent": "Mozilla/5.0 (compatible; FuchoMX/1.0)",
}

# 365Scores eventType.id
_EVENT_GOAL          = 1
_EVENT_YELLOW_CARD   = 2
_EVENT_RED_CARD      = 3

# 365Scores stats type IDs
_STAT_MINUTES_PLAYED = 30
_STAT_SAVES          = 23

# 365Scores lineup status
_STATUS_STARTER  = 1
_STATUS_SUB      = 2


def map_365_position(position_name: str) -> str:
    mapping = {
        "Goalkeeper": "POR",
        "Defender":   "DEF",
        "Midfielder": "MED",
        "Attacker":   "DEL",
    }
    return mapping.get(position_name, "MED")


def _parse_minutes(raw: str) -> int:
    """Convert '90\\'' or '75+2\\'' style string to int minutes."""
    if not raw:
        return 0
    try:
        clean = str(raw).replace("'", "").strip()
        # Handle extra time e.g. "90+3"
        if "+" in clean:
            parts = clean.split("+")
            return int(parts[0]) + int(parts[1])
        return int(clean)
    except (ValueError, IndexError):
        return 0


async def get_wc_match_stats(game_id: int, db) -> dict:
    """
    Obtiene stats de jugadores de un partido del Mundial desde 365Scores.
    Guarda en db.player_match_stats. Retorna resumen.
    """
    # ── Paso 1: Fetch del partido ─────────────────────────────────────────
    try:
        url = _365SCORES_GAME_URL.format(game_id=game_id)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_365SCORES_HEADERS)
        if resp.status_code != 200:
            logger.error(f"365Scores game API → HTTP {resp.status_code} for game {game_id}")
            return {"error": f"HTTP {resp.status_code}", "players_processed": 0, "game_id": game_id}
        data = resp.json()
    except Exception as exc:
        logger.error(f"365Scores fetch error (game {game_id}): {exc}")
        return {"error": str(exc), "players_processed": 0, "game_id": game_id}

    game = data.get("game", {})
    if not game:
        return {"error": "game not found in response", "players_processed": 0, "game_id": game_id}

    home = game.get("homeCompetitor", {})
    away = game.get("awayCompetitor", {})
    home_score = home.get("score", 0) or 0
    away_score = away.get("score", 0) or 0
    home_id = home.get("id")
    away_id = away.get("id")

    # ── Paso 2: Construir lookup de nombres por player_id desde game.members ──
    members_index: dict[int, dict] = {}
    for m in game.get("members", []):
        pid = m.get("id")
        if pid is not None:
            members_index[pid] = {
                "name":          m.get("name", ""),
                "jersey_number": m.get("jerseyNumber"),
                "competitor_id": m.get("competitorId"),
            }

    # ── Paso 3: Parsear eventos — goles, asistencias, tarjetas ───────────
    goals_map:   dict[int, int] = {}   # player_id → goals
    assists_map: dict[int, int] = {}   # player_id → assists
    yellow_map:  dict[int, int] = {}   # player_id → yellow cards
    red_map:     dict[int, int] = {}   # player_id → red cards

    for ev in game.get("events", []):
        etype = ev.get("eventType", {}).get("id")
        pid = ev.get("playerId")

        if etype == _EVENT_GOAL:
            if pid:
                goals_map[pid] = goals_map.get(pid, 0) + 1
            extra = ev.get("extraPlayers", [])
            if extra:
                assist_pid = extra[0].get("playerId") if isinstance(extra[0], dict) else extra[0]
                if assist_pid:
                    assists_map[assist_pid] = assists_map.get(assist_pid, 0) + 1

        elif etype == _EVENT_YELLOW_CARD:
            if pid:
                yellow_map[pid] = yellow_map.get(pid, 0) + 1

        elif etype == _EVENT_RED_CARD:
            if pid:
                red_map[pid] = red_map.get(pid, 0) + 1

    # ── Paso 4: Parsear lineups de cada equipo ────────────────────────────
    player_docs = []

    for competitor, opp_score in (
        (home, away_score),
        (away, home_score),
    ):
        comp_id = competitor.get("id")
        lineups = competitor.get("lineups", {})
        members_list = lineups.get("members", [])

        for member in members_list:
            status = member.get("status")

            # Solo titulares y suplentes que hayan entrado
            if status == _STATUS_STARTER:
                pass  # always include
            elif status == _STATUS_SUB:
                # Suplente solo cuenta si tiene datos de sustitución (jugó)
                if not member.get("substitution"):
                    continue
            else:
                continue

            pid = member.get("id")
            position_name = member.get("position", {}).get("name", "")
            position = map_365_position(position_name)

            # Minutos jugados desde stats type == 30
            minutes = 0
            saves = 0
            for stat in member.get("stats", []):
                stat_type = stat.get("type")
                if stat_type == _STAT_MINUTES_PLAYED:
                    minutes = _parse_minutes(stat.get("value", 0))
                elif stat_type == _STAT_SAVES:
                    try:
                        saves = int(stat.get("value", 0))
                    except (ValueError, TypeError):
                        saves = 0

            # Fallback de minutos si el campo stats no lo tiene
            if minutes == 0:
                if status == _STATUS_STARTER:
                    sub_data = member.get("substitution", {})
                    if sub_data:
                        out_min = _parse_minutes(sub_data.get("minute", "90"))
                        minutes = out_min if out_min > 0 else 90
                    else:
                        minutes = 90
                elif status == _STATUS_SUB:
                    sub_data = member.get("substitution", {})
                    in_min = _parse_minutes(sub_data.get("minute", "0")) if sub_data else 0
                    minutes = max(0, 90 - in_min)

            # Portería a cero: el equipo contrario no marcó
            clean_sheet = (opp_score == 0) and (minutes >= 60)

            # Lookup de nombre e info base
            base = members_index.get(pid, {})
            name = base.get("name") or member.get("name", "")
            jersey = base.get("jersey_number") or member.get("jerseyNumber")
            comp_id_final = base.get("competitor_id") or comp_id

            player_docs.append({
                "game_id":        game_id,
                "competition":    "world_cup_2026",
                "player_365_id":  pid,
                "player_name":    name,
                "jersey_number":  jersey,
                "competitor_id":  comp_id_final,
                "position":       position,
                "minutes":        minutes,
                "goals":          goals_map.get(pid, 0),
                "assists":        assists_map.get(pid, 0),
                "yellow_cards":   yellow_map.get(pid, 0),
                "red_cards":      red_map.get(pid, 0),
                "clean_sheet":    clean_sheet if position in ("POR", "DEF") else False,
                "goals_conceded": opp_score if position in ("POR", "DEF") else 0,
                "saves":          saves,
                "created_at":     datetime.utcnow(),
            })

    # ── Paso 5: Guardar en MongoDB ────────────────────────────────────────
    if player_docs:
        await db.player_match_stats.delete_many({"game_id": game_id})
        await db.player_match_stats.insert_many(player_docs)

    logger.info(
        f"get_wc_match_stats game {game_id}: "
        f"{len(player_docs)} jugadores procesados "
        f"({home.get('name', '?')} {home_score}-{away_score} {away.get('name', '?')})"
    )

    return {
        "game_id":           game_id,
        "competition":       "world_cup_2026",
        "players_processed": len(player_docs),
        "home":              home.get("name", "?"),
        "away":              away.get("name", "?"),
        "score":             f"{home_score}-{away_score}",
    }
