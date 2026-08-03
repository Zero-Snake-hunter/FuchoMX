"""
scores_service.py
Obtiene resultados de partidos de Liga MX desde 365Scores.
Fallback: ESPN API (ya integrada).
"""
import json
import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId

logger = logging.getLogger(__name__)

# ── Constantes ─────────────────────────────────────────────────────────────
_365SCORES_GAMES_URL = (
    "https://webws.365scores.com/web/games/"
    "?appTypeId=5&langId=8&competitions={competition_id}"
    "&startDate={start}&endDate={end}"
)
_365SCORES_HEADERS = {
    "Origin": "https://www.365scores.com",
    "Referer": "https://www.365scores.com/",
    "User-Agent": "Mozilla/5.0 (compatible; FuchoMX/1.0)",
}

_ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/mex.1/scoreboard"
    "?dates={date}&limit=20"
)

# Status map 365Scores statusGroup → internal status.
# Verificado en vivo contra la API real (jul 2026): statusGroup=2 viene con
# statusText="Scheduled" para partidos que NO han arrancado (ej. J2 con
# fechas futuras) — el mapeo anterior lo marcaba como "live", causando que
# partidos sin empezar aparecieran en la sección EN VIVO con marcador -1
# (el sentinel de "sin resultado" de 365Scores, ver _sanitize_score).
# statusGroup=4 confirmado como "Ended". statusGroup=3 se deja como "live"
# sin confirmar en vivo (no hubo partido en curso al verificar) — por eso
# el consumidor de este mapa (routers/live.py) además cruza contra la hora
# real del partido antes de mostrarlo como en vivo.
_STATUS_MAP = {
    1: "scheduled",
    2: "scheduled",
    3: "live",
    4: "finished",
    5: "postponed",
    6: "cancelled",
}


def _sanitize_score(raw) -> int | None:
    """365Scores usa -1 como sentinel de 'sin resultado aún' (partido no
    iniciado) en vez de null — sin esto, un partido programado se ve como
    -1 - -1 en vez de sin marcador."""
    if raw is None:
        return None
    value = int(raw)
    return value if value >= 0 else None


def _normalize_name(name: str) -> str:
    """Normalize team name for fuzzy matching — 365Scores to DB."""
    MAPPING = {
        # 365Scores name        : DB name
        "Mazatlan FC":            "Mazatlán",
        "Mazatlán FC":            "Mazatlán",
        "Queretaro":              "Querétaro",
        "San Luis":               "Atlético San Luis",
        "Atletico San Luis":      "Atlético San Luis",
        "Atlético de San Luis":   "Atlético San Luis",
        "Pumas":                  "Pumas UNAM",
        "UNAM":                   "Pumas UNAM",
        "Club Tijuana":           "Tijuana",
        "Xolos":                  "Tijuana",
        "Tigres":                 "Tigres UANL",
        "Leon":                   "León",
        "Léon":                   "León",
        "Juarez":                 "Juárez",
        "Club America":           "Club América",
        "América":                "Club América",
        "Santos":                 "Santos Laguna",
        "Monterrey":              "Monterrey",
        "Guadalajara":            "Guadalajara",
        "Cruz Azul":              "Cruz Azul",
        "Pachuca":                "Pachuca",
        "Puebla":                 "Puebla",
        "Toluca":                 "Toluca",
        "Atlas":                  "Atlas",
        "Necaxa":                 "Necaxa",
        "Atlante":                "Atlante",
    }
    return MAPPING.get(name, name)


async def _fetch_365scores(
    start_date: datetime, end_date: datetime, competition_id: int = 141
) -> list[dict]:
    """Fetches games from 365Scores API for a date range. Default competition: Liga MX (141)."""
    try:
        url = _365SCORES_GAMES_URL.format(
            competition_id=competition_id,
            start=start_date.strftime("%d/%m/%Y"),
            end=end_date.strftime("%d/%m/%Y"),
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_365SCORES_HEADERS)
        if resp.status_code != 200:
            logger.warning(f"365Scores API → {resp.status_code}")
            return []

        # Ver nota en liga_mx_stats_service.py: forzamos UTF-8 explícito en vez
        # de confiar en la detección de charset de httpx (corrompía nombres
        # con tildes/ñ, ej. "León" -> "LeÃ³n", rompiendo el match por nombre).
        data = json.loads(resp.content.decode("utf-8"))
        games = data.get("games", [])
        logger.info(f"365Scores: {len(games)} games found for range")
        return games
    except Exception as exc:
        logger.error(f"365Scores fetch error: {exc}")
        return []


async def _fetch_espn_scores(
    start_date: datetime, end_date: datetime
) -> list[dict]:
    """
    Fallback: ESPN Scoreboard API.
    Returns list of normalized match dicts.
    """
    results = []
    try:
        current = start_date
        async with httpx.AsyncClient(timeout=10.0) as client:
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
                        home = next(
                            (c for c in competitors if c.get("homeAway") == "home"), competitors[0]
                        )
                        away = next(
                            (c for c in competitors if c.get("homeAway") == "away"), competitors[1]
                        )
                        status_name = (
                            comp.get("status", {})
                            .get("type", {})
                            .get("name", "STATUS_SCHEDULED")
                        )
                        if "FULL" in status_name or "FINAL" in status_name:
                            status = "finished"
                        elif "IN" in status_name:
                            status = "live"
                        else:
                            status = "scheduled"
                        results.append({
                            "home_name": home.get("team", {}).get("displayName", ""),
                            "away_name": away.get("team", {}).get("displayName", ""),
                            "home_score": float(home.get("score", 0)) if home.get("score") else None,
                            "away_score": float(away.get("score", 0)) if away.get("score") else None,
                            "status": status,
                            "espn_event_id": ev.get("id"),
                            "start_time": ev.get("date"),
                        })
                current += timedelta(days=1)
        logger.info(f"ESPN fallback: {len(results)} games found")
        return results
    except Exception as exc:
        logger.error(f"ESPN scores fallback error: {exc}")
        return []


async def get_match_results(jornada_id: str, db) -> dict:
    """
    Función principal.
    Obtiene resultados para todos los partidos de una jornada.
    Actualiza db.matches con scores y status.
    Retorna resumen.
    """
    jornada_obj_id = ObjectId(jornada_id)
    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        return {"error": "Jornada no encontrada", "updated": 0}

    # Fetch matches from DB
    matches = await db.matches.find({"jornada_id": jornada_obj_id}).to_list(50)
    if not matches:
        return {"error": "Sin partidos en esta jornada", "updated": 0}

    # Determine date range for this jornada a partir de los start_at reales
    # de sus partidos — NO de jornada.start_date/end_date. Esos campos se
    # cargan a mano (ver _JORNADA_DATE_FIXES en admin_migrations.py) y ya
    # causaron que un partido quedara fuera de la ventana de consulta a
    # 365Scores por estar un día corto (J3: end_date=2 de agosto, kickoff
    # real del último partido=3 de agosto). ±1 día de margen absorbe además
    # cualquier corrimiento de zona horaria en cómo 365Scores agrupa sus
    # partidos por fecha.
    match_start_ats = [m["start_at"] for m in matches if m.get("start_at")]
    if match_start_ats:
        start_date = min(match_start_ats) - timedelta(days=1)
        end_date = max(match_start_ats) + timedelta(days=1)
    else:
        start_date = jornada.get("start_date", datetime.utcnow() - timedelta(days=7))
        end_date = jornada.get("end_date", datetime.utcnow())

    # ── Paso 1: Obtener resultados de 365Scores ────────────────────────────
    ext_games = await _fetch_365scores(start_date, end_date)

    # Build lookup by (normalized_home_name, normalized_away_name)
    scores_lookup: dict[tuple, dict] = {}
    for g in ext_games:
        home_n = _normalize_name(g.get("homeCompetitor", {}).get("name", ""))
        away_n = _normalize_name(g.get("awayCompetitor", {}).get("name", ""))
        status_grp = g.get("statusGroup", 1)
        scores_lookup[(home_n, away_n)] = {
            "home_score": _sanitize_score(g.get("homeCompetitor", {}).get("score")),
            "away_score": _sanitize_score(g.get("awayCompetitor", {}).get("score")),
            "status": _STATUS_MAP.get(status_grp, "scheduled"),
            "source": "365scores",
            "ext_id": g.get("id"),
        }

    # ── Paso 2: Fallback ESPN si 365Scores no devolvió nada ───────────────
    if not scores_lookup:
        logger.warning("365Scores vacío, usando fallback ESPN...")
        espn_games = await _fetch_espn_scores(start_date, end_date)
        for g in espn_games:
            home_n = _normalize_name(g["home_name"])
            away_n = _normalize_name(g["away_name"])
            scores_lookup[(home_n, away_n)] = {
                "home_score": g["home_score"],
                "away_score": g["away_score"],
                "status": g["status"],
                "source": "espn_fallback",
                "espn_event_id": g.get("espn_event_id"),
            }

    # ── Paso 3: Actualizar cada partido en DB ─────────────────────────────
    updated = 0
    not_found = []
    results_list = []

    for match in matches:
        # Get team names
        home_team = await db.teams.find_one({"_id": match["home_team_id"]})
        away_team = await db.teams.find_one({"_id": match["away_team_id"]})
        if not home_team or not away_team:
            continue

        home_name = _normalize_name(home_team.get("name", ""))
        away_name = _normalize_name(away_team.get("name", ""))

        # Try exact match
        score_data = scores_lookup.get((home_name, away_name))

        # Fuzzy fallback: try partial name match
        if not score_data:
            for (k_home, k_away), v in scores_lookup.items():
                if (home_name[:4].lower() in k_home.lower() and
                        away_name[:4].lower() in k_away.lower()):
                    score_data = v
                    break

        if not score_data:
            not_found.append(f"{home_name} vs {away_name}")
            continue

        update_fields = {
            "status": score_data["status"],
            "updated_at": datetime.utcnow(),
        }
        if score_data["home_score"] is not None:
            update_fields["home_score"] = int(score_data["home_score"])
        if score_data["away_score"] is not None:
            update_fields["away_score"] = int(score_data["away_score"])
        if "espn_event_id" in score_data:
            update_fields["espn_event_id"] = score_data["espn_event_id"]
        if "ext_id" in score_data:
            update_fields["ext_id_365"] = score_data["ext_id"]

        await db.matches.update_one(
            {"_id": match["_id"]},
            {"$set": update_fields}
        )
        updated += 1
        results_list.append({
            "match_id": str(match["_id"]),
            "home": home_name,
            "away": away_name,
            "score": f"{update_fields.get('home_score', '?')}-{update_fields.get('away_score', '?')}",
            "status": score_data["status"],
            "source": score_data["source"],
        })

    logger.info(
        f"get_match_results jornada {jornada_id}: "
        f"{updated}/{len(matches)} actualizados, "
        f"no encontrados: {not_found}"
    )

    return {
        "jornada_id": jornada_id,
        "week_number": jornada.get("week_number"),
        "matches_total": len(matches),
        "matches_updated": updated,
        "matches_not_found": not_found,
        "results": results_list,
    }
