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
import json
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


# Apodos comunes en español que 365Scores y ESPN usan de forma inconsistente
# entre sí (uno reporta el apodo, el otro el nombre de pila) — verificado
# contra casos reales de J1/J2 (ej. "Danny Leyva" en 365Scores vs "Daniel
# Leyva" en el roster ESPN, "Nico Carrera" vs "Nicolás Carrera").
_NICKNAMES = {
    "tony": "antonio", "tono": "antonio",
    "nico": "nicolas", "nacho": "ignacio",
    "danny": "daniel", "dani": "daniel",
    "alex": "alejandro", "ale": "alejandro",
    "pepe": "jose",
    "chuy": "jesus",
    "memo": "guillermo", "willy": "guillermo",
    "beto": "alberto", "tito": "alberto",
    "lalo": "eduardo", "edu": "eduardo",
    "kike": "enrique", "quique": "enrique",
    "chicho": "francisco", "paco": "francisco", "pancho": "francisco",
    "lucho": "luis", "luisito": "luis",
    "fer": "fernando", "checo": "sergio", "vico": "victor",
    "fran": "francisco",
}


def _canon_tokens(name: str) -> frozenset:
    tokens = _normalize_player_name(name).split()
    return frozenset(_NICKNAMES.get(t, t) for t in tokens)


def _fuzzy_match_player(name: str, fuzzy_roster: list) -> tuple | None:
    """
    Fallback para cuando el nombre normalizado no matchea exacto contra el
    roster propio. Solo resuelve el caso de nombre truncado/con apodo donde
    el conjunto de tokens (con apodos canonizados) de una de las dos fuentes
    es subconjunto del de la otra — ej. "Frank Boya" (365Scores) ⊆ "Frank
    Thierry Boya" (ESPN), o "Tony Leone" -> {antonio, leone} == "Antonio
    Leone" -> {antonio, leone}.

    NO incluye fallback por apellido solo: se probó contra casos reales de
    J1/J2 y producía falsos positivos (ej. "Carlos Rotondi" emparejaba con
    "Rodolfo Rotondi", "Daniel Gonzalez" con "José González" — nombres de
    pila distintos, casi seguro personas distintas). Preferimos reportar
    unmatched a asignar stats al jugador equivocado.
    """
    incoming_tokens = _canon_tokens(name)
    if not incoming_tokens:
        return None

    candidates = [
        (pid, pos) for (tokens, pid, pos, _name) in fuzzy_roster
        if tokens and (tokens <= incoming_tokens or incoming_tokens <= tokens)
    ]
    if len(candidates) == 1:
        return candidates[0]
    return None  # sin match único (0 o ambiguo) -> se reporta unmatched


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
        # 365Scores no siempre declara charset en el Content-Type, y la
        # detección automática de httpx a veces decodifica como Latin-1
        # ("í" -> "Ã­"), rompiendo el match por nombre. Forzamos UTF-8 explícito.
        data = json.loads(resp.content.decode("utf-8"))
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

    # Índice de roster propio por equipo: exacto (nombre normalizado) +
    # fuzzy (tokens canonizados, para el fallback de _fuzzy_match_player).
    roster_index: dict = {}
    roster_fuzzy_index: dict = {}
    for team_id in (match["home_team_id"], match["away_team_id"]):
        players = await db.players.find({"team_id": team_id}).to_list(50)
        roster_index[team_id] = {
            _normalize_player_name(p["name"]): (p["_id"], p.get("position", "MED"))
            for p in players
        }
        roster_fuzzy_index[team_id] = [
            (_canon_tokens(p["name"]), p["_id"], p.get("position", "MED"), p["name"])
            for p in players
        ]

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
                match_entry = _fuzzy_match_player(name, roster_fuzzy_index.get(team_id, []))
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
