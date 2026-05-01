"""
player_stats_service.py
Obtiene stats individuales de jugadores desde ESPN Summary API.
Fallback 1: FBref para minutos exactos de sustitución.
"""
import logging
import httpx
import re
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

logger = logging.getLogger(__name__)

_ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard"
    "?dates={date}&limit=20"
)
_ESPN_SUMMARY_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/summary"
    "?event={event_id}"
)

# ESPN position abbreviations → our internal positions
_POS_MAP = {
    "GK": "POR", "G": "POR",
    "CB": "DEF", "LB": "DEF", "RB": "DEF",
    "CD": "DEF", "SW": "DEF",
    "CD-L": "DEF", "CD-R": "DEF",
    "CM": "MED", "AM": "MED", "DM": "MED",
    "LM": "MED", "RM": "MED", "LW": "MED", "RW": "MED",
    "CF": "DEL", "SS": "DEL", "FW": "DEL",
}


def _map_position(espn_pos: str) -> str:
    pos = espn_pos.upper().strip()
    if pos in _POS_MAP:
        return _POS_MAP[pos]
    # Fallback: first char
    if pos.startswith("G"):
        return "POR"
    if pos.startswith("D"):
        return "DEF"
    if pos.startswith("F") or pos.startswith("S"):
        return "DEL"
    return "MED"



_FBREF_FIXTURES_URL = (
    "https://fbref.com/en/comps/31/schedule/Liga-MX-Scores-and-Fixtures"
)
_FBREF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
}


async def _get_fbref_minutes(
    home_name: str, away_name: str, match_date: datetime
) -> dict[str, int]:
    """
    Consulta FBref para obtener minutos exactos de sustitución por jugador.
    Retorna dict {nombre_jugador_lower: minutos} o dict vacío si falla.
    Solo se usa cuando ESPN no tiene datos exactos (subbed_out/subbed_in).
    """
    if not _BS4_AVAILABLE:
        return {}
    try:
        date_str = match_date.strftime("%Y-%m-%d")
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=_FBREF_HEADERS,
        ) as client:
            resp = await client.get(_FBREF_FIXTURES_URL)

        if resp.status_code != 200:
            logger.warning(f"FBref fixtures → HTTP {resp.status_code}")
            return {}

        soup = BeautifulSoup(resp.text, "lxml")
        schedule_table = soup.find("table", id=lambda x: x and "sched" in x.lower())
        if not schedule_table:
            logger.warning("FBref: no schedule table found")
            return {}

        # Normalize helper
        def _norm(s: str) -> str:
            return re.sub(r"[^a-z]", "", s.lower())

        home_key = _norm(home_name[:5])
        away_key = _norm(away_name[:5])
        match_url = None

        for row in schedule_table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            row_text = " ".join(c.get_text(strip=True) for c in cells)
            # Match by date + partial team names
            if date_str not in row_text and match_date.strftime("%B") not in row_text:
                continue
            # Find match report link
            report_link = row.find("a", href=re.compile(r"/en/matches/"))
            if report_link:
                row_teams = _norm(row_text)
                if home_key in row_teams and away_key in row_teams:
                    match_url = "https://fbref.com" + report_link["href"]
                    break

        if not match_url:
            logger.info(
                f"FBref: no match URL found for {home_name} vs {away_name} on {date_str}"
            )
            return {}

        logger.info(f"FBref: found match URL {match_url}")

        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True, headers=_FBREF_HEADERS
        ) as client:
            resp2 = await client.get(match_url)

        if resp2.status_code != 200:
            return {}

        soup2 = BeautifulSoup(resp2.text, "lxml")

        # Parse "Events" table — contains minute for each goal/sub
        # Also look for lineup tables with substitution minutes
        minutes_map: dict[str, int] = {}

        # Method 1: parse sub events
        events_div = soup2.find("div", id=lambda x: x and "events_wrap" in (x or ""))
        if events_div:
            for ev in events_div.find_all("div", class_=lambda x: x and "event" in (x or "")):
                text = ev.get_text(separator=" ", strip=True)
                # Look for substitution pattern: "67' Player Name (sub in)"
                sub_match = re.search(r"(\d+)'\s+(.+?)(?:\s+Sub|$)", text)
                if sub_match:
                    minute = int(sub_match.group(1))
                    name = sub_match.group(2).strip()
                    minutes_map[_norm(name[:8])] = minute

        # Method 2: parse lineup tables (rows with data-stat="minutes")
        for lineup_table in soup2.find_all("table", id=re.compile(r"lineup")):
            for row in lineup_table.find_all("tr"):
                min_cell = row.find("td", {"data-stat": "minutes"})
                name_cell = row.find("td", {"data-stat": "player"})
                if min_cell and name_cell:
                    try:
                        m = int(min_cell.get_text(strip=True))
                        name = name_cell.get_text(strip=True)
                        if m > 0:
                            minutes_map[_norm(name[:8])] = m
                    except ValueError:
                        pass

        logger.info(
            f"FBref: got minutes for {len(minutes_map)} players "
            f"({home_name} vs {away_name})"
        )
        return minutes_map

    except Exception as exc:
        logger.warning(f"FBref minutes fallback error: {exc}")
        return {}


async def _get_espn_event_ids(
    start_date: datetime, end_date: datetime
) -> list[dict]:
    """Fetch ESPN event IDs for Liga MX in a date range."""
    event_ids = []
    try:
        current = start_date
        async with httpx.AsyncClient(timeout=12.0) as client:
            while current <= end_date:
                url = _ESPN_SCOREBOARD_URL.format(
                    date=current.strftime("%Y%m%d")
                )
                resp = await client.get(url)
                if resp.status_code == 200:
                    events = resp.json().get("events", [])
                    for ev in events:
                        comp = (ev.get("competitions") or [{}])[0]
                        competitors = comp.get("competitors", [])
                        if len(competitors) < 2:
                            continue
                        status_name = (
                            comp.get("status", {}).get("type", {}).get("name", "")
                        )
                        if "FULL" in status_name or "FINAL" in status_name:
                            match_status = "finished"
                        elif "IN" in status_name:
                            match_status = "live"
                        else:
                            match_status = "scheduled"

                        home = next(
                            (c for c in competitors if c.get("homeAway") == "home"),
                            competitors[0],
                        )
                        away = next(
                            (c for c in competitors if c.get("homeAway") == "away"),
                            competitors[1],
                        )
                        event_ids.append({
                            "event_id": ev["id"],
                            "home_name": home.get("team", {}).get("displayName", ""),
                            "away_name": away.get("team", {}).get("displayName", ""),
                            "status": match_status,
                            "date": current.strftime("%Y-%m-%d"),
                        })
                current += timedelta(days=1)
    except Exception as exc:
        logger.error(f"ESPN event IDs error: {exc}")
    return event_ids


async def _fetch_espn_player_stats(event_id: str) -> list[dict]:
    """
    Fetches player stats from ESPN match summary.
    Returns flat list of player stat dicts.
    """
    players = []
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(_ESPN_SUMMARY_URL.format(event_id=event_id))
        if resp.status_code != 200:
            return []

        data = resp.json()
        rosters = data.get("rosters", [])

        # Find MVP (highest goals+assists in the match)
        all_athletes = []
        for roster in rosters:
            team_id_espn = roster.get("team", {}).get("id")
            for athlete in roster.get("roster", []):
                stats_raw = {s["name"]: s.get("value", 0) for s in athlete.get("stats", [])}
                pos_abbr = athlete.get("position", {}).get("abbreviation", "MED")
                pos = _map_position(pos_abbr)

                # Infer minutes played
                # ESPN doesn't give minutes directly but subIns/subbedOut indicate substitutions
                subbed_in = athlete.get("subbedIn", False)
                subbed_out = athlete.get("subbedOut", False)
                is_starter = athlete.get("starter", False)
                is_active = athlete.get("active", False)

                if not is_active:
                    minutes = 0
                elif is_starter and not subbed_out:
                    minutes = 90
                elif is_starter and subbed_out:
                    minutes = 65  # estimate
                elif subbed_in:
                    minutes = 25  # estimate
                else:
                    minutes = 0

                goals = int(stats_raw.get("totalGoals", 0))
                assists = int(stats_raw.get("goalAssists", 0))

                all_athletes.append({
                    "espn_athlete_id": athlete.get("athlete", {}).get("id"),
                    "name":           athlete.get("athlete", {}).get("displayName", "?"),
                    "position":        pos,
                    "minutes":         minutes,
                    "goals":           goals,
                    "assists":         assists,
                    "yellow_cards":    int(stats_raw.get("yellowCards", 0)),
                    "red_cards":       int(stats_raw.get("redCards", 0)),
                    "saves":           int(stats_raw.get("saves", 0)),
                    "own_goals":       int(stats_raw.get("ownGoals", 0)),
                    "penalty_saved":   0,   # ESPN doesn't expose this separately
                    "penalty_missed":  0,
                    "is_mvp":          False,
                    "score_impact":    goals * 2 + assists,
                    "espn_event_id":   event_id,
                    "espn_team_id":    team_id_espn,
                    "starter":         is_starter,
                })

        # Determine MVP per match (player with highest score impact, then by saves for GK)
        if all_athletes:
            max_impact = max(a["score_impact"] + a["saves"] * 0.5 for a in all_athletes)
            if max_impact > 0:
                for a in all_athletes:
                    if a["score_impact"] + a["saves"] * 0.5 == max_impact:
                        a["is_mvp"] = True
                        break
            else:
                # No goals/saves: starter with most minutes is MVP
                starters = [a for a in all_athletes if a["starter"] and a["minutes"] >= 90]
                if starters:
                    starters[0]["is_mvp"] = True

        players.extend(all_athletes)

    except Exception as exc:
        logger.error(f"ESPN summary error for event {event_id}: {exc}")

    return players


def _normalize_team_name(name: str) -> str:
    MAPPING = {
        "Mazatlan FC":           "Mazatlán",
        "Mazatlán FC":           "Mazatlán",
        "Mazatlan":              "Mazatlán",
        "Queretaro":             "Querétaro",
        "San Luis":              "Atlético San Luis",
        "Atletico San Luis":     "Atlético San Luis",
        "Atlético de San Luis":  "Atlético San Luis",
        "Atl\u00e9tico San Luis": "Atlético San Luis",
        "Pumas":                 "Pumas UNAM",
        "UNAM":                  "Pumas UNAM",
        "Club Tijuana":          "Tijuana",
        "Xolos":                 "Tijuana",
        "Tigres":                "Tigres UANL",
        "Leon":                  "León",
        "Juarez":                "Juárez",
        "Club America":          "Club América",
        "Am\u00e9rica":           "Club América",
        "Santos":                "Santos Laguna",
        "Monterrey":             "Monterrey",
        "Guadalajara":           "Guadalajara",
        "Cruz Azul":             "Cruz Azul",
        "Pachuca":               "Pachuca",
        "Puebla":                "Puebla",
        "Toluca":                "Toluca",
        "Atlas":                 "Atlas",
        "Necaxa":                "Necaxa",
    }
    return MAPPING.get(name, name)


async def get_player_stats(jornada_id: str, db) -> dict:
    """
    Función principal.
    Obtiene stats de jugadores para todos los partidos de una jornada.
    Guarda en db.player_match_stats.
    Retorna resumen.
    """
    jornada_obj_id = ObjectId(jornada_id)
    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        return {"error": "Jornada no encontrada", "players_saved": 0}

    start_date = jornada.get("start_date", datetime.utcnow() - timedelta(days=7))
    end_date = jornada.get("end_date", datetime.utcnow())

    # Fetch matches from DB
    matches = await db.matches.find(
        {"jornada_id": jornada_obj_id, "status": "finished"}
    ).to_list(50)

    if not matches:
        logger.info(f"No finished matches for jornada {jornada_id} — skipping player stats")
        return {
            "jornada_id": jornada_id,
            "players_saved": 0,
            "message": "Sin partidos finalizados",
        }

    # Get ESPN event IDs for the date range
    espn_events = await _get_espn_event_ids(start_date, end_date)

    # Build lookup by normalized team name pair
    event_lookup: dict[tuple, str] = {}
    for ev in espn_events:
        home_n = _normalize_team_name(ev["home_name"])
        away_n = _normalize_team_name(ev["away_name"])
        event_lookup[(home_n, away_n)] = ev["event_id"]

    total_players = 0
    matches_processed = 0

    for match in matches:
        home_team = await db.teams.find_one({"_id": match["home_team_id"]})
        away_team = await db.teams.find_one({"_id": match["away_team_id"]})
        if not home_team or not away_team:
            continue

        home_name = _normalize_team_name(home_team.get("name", ""))
        away_name = _normalize_team_name(away_team.get("name", ""))

        # Find ESPN event
        event_id = event_lookup.get((home_name, away_name))
        if not event_id:
            # Try reverse (ESPN sometimes swaps home/away)
            event_id = event_lookup.get((away_name, home_name))
        if not event_id:
            # Fuzzy match
            for (k_h, k_a), eid in event_lookup.items():
                if (home_name[:4].lower() in k_h.lower() and
                        away_name[:4].lower() in k_a.lower()):
                    event_id = eid
                    break

        if not event_id:
            logger.warning(f"No ESPN event found for {home_name} vs {away_name}")
            continue

        # Store ESPN event_id on match for future use
        if not match.get("espn_event_id"):
            await db.matches.update_one(
                {"_id": match["_id"]},
                {"$set": {"espn_event_id": event_id}}
            )

        # Fetch player stats from ESPN
        players = await _fetch_espn_player_stats(event_id)
        if not players:
            continue

        # ── FBref fallback: obtener minutos exactos para jugadores con estimados ──
        # Solo si hay jugadores con minutos estimados (65 o 25 = estimados por ESPN)
        has_estimates = any(p["minutes"] in (65, 25) for p in players)
        fbref_minutes: dict[str, int] = {}
        if has_estimates:
            match_date = match.get("start_at", start_date)
            fbref_minutes = await _get_fbref_minutes(home_name, away_name, match_date)
            if fbref_minutes:
                logger.info(
                    f"FBref overriding estimated minutes for "
                    f"{home_name} vs {away_name}: {len(fbref_minutes)} players"
                )

        def _norm_key(name: str) -> str:
            import re as _re
            return _re.sub(r"[^a-z]", "", name.lower())[:8]

        # For each player: try to find in DB by name, save stats
        bulk_docs = []
        for p in players:
            # Apply FBref minutes if ESPN had an estimate
            if p["minutes"] in (65, 25) and fbref_minutes:
                key = _norm_key(p["name"])
                if key in fbref_minutes:
                    exact_mins = fbref_minutes[key]
                    logger.info(
                        f"FBref: {p['name']} → {p['minutes']} (ESPN est) "
                        f"→ {exact_mins} (FBref exact)"
                    )
                    p["minutes"] = exact_mins

            if p["minutes"] == 0:
                continue  # skip unused players

            # Find player in DB by name (partial match)
            player_doc = await db.players.find_one(
                {"name": {"$regex": p["name"].split(" ")[0], "$options": "i"}}
            )

            bulk_docs.append({
                "player_id":      player_doc["_id"] if player_doc else None,
                "player_name":    p["name"],
                "jornada_id":     jornada_obj_id,
                "match_id":       match["_id"],
                "espn_event_id":  p["espn_event_id"],
                "position":       p["position"],
                "minutes":        p["minutes"],
                "goals":          p["goals"],
                "assists":        p["assists"],
                "yellow_cards":   p["yellow_cards"],
                "red_cards":      p["red_cards"],
                "saves":          p["saves"],
                "penalty_saved":  p["penalty_saved"],
                "penalty_missed": p["penalty_missed"],
                "own_goals":      p["own_goals"],
                "is_mvp":         p["is_mvp"],
                "created_at":     datetime.utcnow(),
            })

        if bulk_docs:
            # Delete old stats for this match and re-insert
            await db.player_match_stats.delete_many(
                {"match_id": match["_id"]}
            )
            await db.player_match_stats.insert_many(bulk_docs)
            total_players += len(bulk_docs)
            matches_processed += 1
            logger.info(
                f"Saved {len(bulk_docs)} player stats for "
                f"{home_name} vs {away_name} (event {event_id})"
            )

    return {
        "jornada_id": jornada_id,
        "week_number": jornada.get("week_number"),
        "matches_processed": matches_processed,
        "players_saved": total_players,
        "source": "espn_summary",
    }
