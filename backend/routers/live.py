import logging
from datetime import datetime, date

from fastapi import APIRouter, HTTPException

from config import API_FOOTBALL_KEY
from database import db
from services.api_football_service import (
    get_fixtures_by_date as _af_get_by_date,
    get_live_fixtures as _af_get_live,
)
from services.scores_service import _fetch_365scores, _normalize_name, _STATUS_MAP, _sanitize_score

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level cache — 55 segundos TTL
_live_scores_cache: dict = {"data": None, "fetched_at": None}
_LIVE_CACHE_TTL = 55


@router.get("/jornadas/current/live-scores")
async def get_live_scores():
    """Partidos en curso o de hoy. Llama 365Scores y cachea 55 s."""
    global _live_scores_cache
    now = datetime.utcnow()

    if _live_scores_cache["data"] is not None and _live_scores_cache["fetched_at"]:
        age = (now - _live_scores_cache["fetched_at"]).total_seconds()
        if age < _LIVE_CACHE_TTL:
            return _live_scores_cache["data"]

    today_start = now.replace(hour=0, minute=0, second=0)
    today_end = now.replace(hour=23, minute=59, second=59)

    games = await _fetch_365scores(today_start, today_end)

    live_matches = []
    all_matches = []

    for g in games:
        status_grp = g.get("statusGroup", 1)
        st = _STATUS_MAP.get(status_grp, "scheduled")

        home_name = _normalize_name(g.get("homeCompetitor", {}).get("name", ""))
        away_name = _normalize_name(g.get("awayCompetitor", {}).get("name", ""))
        start_time_raw = g.get("startTime", "")

        match_data = {
            "home_name": home_name,
            "away_name": away_name,
            "home_score": _sanitize_score(g.get("homeCompetitor", {}).get("score")),
            "away_score": _sanitize_score(g.get("awayCompetitor", {}).get("score")),
            "status": st,
            "game_time": g.get("gameTimeDisplay", ""),
            "start_time": start_time_raw,
        }
        all_matches.append(match_data)

        # No confiar solo en statusGroup para marcar "en vivo" — verificado
        # que 365Scores reporta partidos sin arrancar con statusGroup
        # equivocado en algunos casos. Cruza contra la hora real: solo
        # cuenta como en vivo si ya pasó su start_time.
        if st == "live":
            already_started = True
            if start_time_raw:
                try:
                    start_dt = datetime.fromisoformat(start_time_raw.replace("Z", "+00:00"))
                    already_started = now >= start_dt.replace(tzinfo=None)
                except ValueError:
                    pass
            if already_started:
                live_matches.append(match_data)

    # Fallback a DB cuando 365Scores no devuelve datos
    if not all_matches:
        try:
            db_live = await db.matches.find({"status": "live"}).to_list(20)
            for dm in db_live:
                ht = await db.teams.find_one({"_id": dm["home_team_id"]})
                at = await db.teams.find_one({"_id": dm["away_team_id"]})
                if not ht or not at:
                    continue
                m = {
                    "home_name": ht.get("name", "?"),
                    "away_name": at.get("name", "?"),
                    "home_score": dm.get("home_score"),
                    "away_score": dm.get("away_score"),
                    "status": "live",
                    "game_time": str(dm.get("game_time", "")),
                    "start_time": "",
                }
                all_matches.append(m)
                live_matches.append(m)
        except Exception as exc:
            logger.warning(f"DB live fallback error: {exc}")

    result = {
        "has_live":    len(live_matches) > 0,
        "live_count":  len(live_matches),
        "live_matches": live_matches,
        "all_today":   all_matches,
        "fetched_at":  now.isoformat(),
        "source":      "365scores" if games else ("db_fallback" if live_matches else "empty"),
    }

    _live_scores_cache["data"] = result
    _live_scores_cache["fetched_at"] = now
    return result


@router.get("/fixtures/live")
async def get_live_fixtures_api_football():
    try:
        fixtures = await _af_get_live(API_FOOTBALL_KEY)
        return {"fixtures": fixtures, "source": "api-football"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fixtures/today")
async def get_today_fixtures():
    try:
        fixtures = await _af_get_by_date(date.today(), API_FOOTBALL_KEY)
        return {"fixtures": fixtures, "source": "api-football", "date": date.today().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
