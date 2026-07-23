"""
liga_mx_stats_service.py
Obtiene stats de jugadores de un partido de Liga MX desde 365Scores
(mismo endpoint que world_cup_stats_service.py) y las guarda en
db.player_match_stats con el schema que fantasy_scoring.calculate_fantasy_points
realmente espera (player_id, jornada_id, yellow_card/red_card en singular).

NOTA: world_cup_stats_service.get_wc_match_stats guarda "player_365_id" en vez
de "player_id" y nunca setea "jornada_id" — por eso las stats del Mundial
nunca llegaron a alimentar el cálculo de fantasy (bug preexistente, no se
tocó aquí porque el Mundial ya terminó y está fuera de alcance).

Los jugadores se emparejan por nombre normalizado contra el roster propio
(db.players, filtrado por team_id) — si un jugador de la alineación real no
existe en nuestro roster sembrado, se omite y se reporta en "unmatched".
"""
import logging
import re
import unicodedata
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

_365SCORES_GAME_URL = (
    "https://webws.365scores.com/web/game/?gameId={game_id}"
)
_365SCORES_HEADERS = {
    "Origin": "https://www.365scores.com",
    "Referer": "https://www.365scores.com/",
    "User-Agent": "Mozilla/5.0 (compatible; FuchoMX/1.0)",
}

_EVENT_GOAL        = 1
_EVENT_YELLOW_CARD = 2
_EVENT_RED_CARD    = 3

_STAT_MINUTES_PLAYED = 30
_STAT_SAVES          = 23

_STATUS_STARTER = 1
_STATUS_SUB     = 2


def _normalize_player_name(name: str) -> str:
    stripped = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z ]", "", stripped.lower()).strip()


def _parse_minutes(raw) -> int:
    if not raw:
        return 0
    try:
        clean = str(raw).replace("'", "").strip()
        if "+" in clean:
            parts = clean.split("+")
            return int(parts[0]) + int(parts[1])
        return int(clean)
    except (ValueError, IndexError):
        return 0


async def sync_match_stats_365(match: dict, db) -> dict:
    """
    Obtiene stats de un partido de Liga MX desde 365Scores usando el
    game_id guardado en match["ext_id_365"], empareja jugadores contra
    db.players (por team_id + nombre normalizado) y guarda en
    db.player_match_stats. Retorna resumen (incluye jugadores sin match).
    """
    game_id = match.get("ext_id_365")
    if not game_id:
        return {"error": "match sin ext_id_365", "match_id": str(match["_id"])}

    try:
        url = _365SCORES_GAME_URL.format(game_id=game_id)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_365SCORES_HEADERS)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "game_id": game_id}
        data = resp.json()
    except Exception as exc:
        logger.error(f"365Scores fetch error (game {game_id}): {exc}")
        return {"error": str(exc), "game_id": game_id}

    game = data.get("game", {})
    if not game:
        return {"error": "game not found in response", "game_id": game_id}

    home = game.get("homeCompetitor", {})
    away = game.get("awayCompetitor", {})
    home_score = home.get("score", 0) or 0
    away_score = away.get("score", 0) or 0

    members_index: dict[int, str] = {
        m.get("id"): m.get("name", "") for m in game.get("members", []) if m.get("id") is not None
    }

    goals_map: dict[int, int] = {}
    assists_map: dict[int, int] = {}
    yellow_map: dict[int, int] = {}
    red_map: dict[int, int] = {}

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

    jornada_id = match["jornada_id"]
    team_lookup = {
        home.get("id"): match["home_team_id"],
        away.get("id"): match["away_team_id"],
    }

    # Índice de roster propio por equipo: {team_id: {nombre_normalizado: (player_id, position)}}
    roster_index: dict = {}
    for team_id in (match["home_team_id"], match["away_team_id"]):
        players = await db.players.find({"team_id": team_id}).to_list(50)
        roster_index[team_id] = {
            _normalize_player_name(p["name"]): (p["_id"], p.get("position", "MED"))
            for p in players
        }

    player_docs = []
    unmatched = []

    for competitor, opp_score in ((home, away_score), (away, home_score)):
        comp_id = competitor.get("id")
        team_id = team_lookup.get(comp_id)
        if team_id is None:
            continue
        roster = roster_index.get(team_id, {})

        for member in competitor.get("lineups", {}).get("members", []):
            status = member.get("status")
            if status == _STATUS_STARTER:
                pass
            elif status == _STATUS_SUB:
                if not member.get("substitution"):
                    continue
            else:
                continue

            pid = member.get("id")
            name = members_index.get(pid) or member.get("name", "")
            if not name:
                continue

            match_entry = roster.get(_normalize_player_name(name))
            if not match_entry:
                unmatched.append(name)
                continue
            player_id, position = match_entry

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

            if minutes == 0:
                if status == _STATUS_STARTER:
                    sub_data = member.get("substitution", {})
                    out_min = _parse_minutes(sub_data.get("minute")) if sub_data else 0
                    minutes = out_min if out_min > 0 else 90
                elif status == _STATUS_SUB:
                    sub_data = member.get("substitution", {})
                    in_min = _parse_minutes(sub_data.get("minute")) if sub_data else 0
                    minutes = max(0, 90 - in_min)

            clean_sheet = (opp_score == 0) and (minutes >= 60)

            player_docs.append({
                "jornada_id":     jornada_id,
                "match_id":       match["_id"],
                "game_id":        game_id,
                "competition":    "liga_mx",
                "player_id":      player_id,
                "player_365_id":  pid,
                "player_name":    name,
                "team_id":        team_id,
                "position":       position,
                "minutes":        minutes,
                "goals":          goals_map.get(pid, 0),
                "assists":        assists_map.get(pid, 0),
                "yellow_card":    yellow_map.get(pid, 0),
                "red_card":       red_map.get(pid, 0),
                "clean_sheet":    clean_sheet if position in ("POR", "DEF") else False,
                "goals_conceded": opp_score if position in ("POR", "DEF") else 0,
                "saves":          saves,
                "penalty_saved":  0,
                "penalty_missed": 0,
                "own_goal":       0,
                "man_of_the_match": False,
                "created_at":     datetime.utcnow(),
            })

    if player_docs or unmatched:
        await db.player_match_stats.delete_many({"match_id": match["_id"]})
    if player_docs:
        await db.player_match_stats.insert_many(player_docs)

    logger.info(
        f"sync_match_stats_365 game {game_id}: {len(player_docs)} emparejados, "
        f"{len(unmatched)} sin match ({home.get('name','?')} {home_score}-{away_score} {away.get('name','?')})"
    )

    return {
        "match_id":          str(match["_id"]),
        "game_id":           game_id,
        "home":              home.get("name", "?"),
        "away":              away.get("name", "?"),
        "score":             f"{home_score}-{away_score}",
        "players_matched":   len(player_docs),
        "players_unmatched": len(unmatched),
        "unmatched_names":   unmatched,
    }
