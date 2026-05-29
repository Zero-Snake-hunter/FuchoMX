import logging
from datetime import datetime

from bson import ObjectId

from database import db

logger = logging.getLogger(__name__)

# ── Catálogo ──────────────────────────────────────────────────────────────────

ACHIEVEMENTS_CATALOG = [
    # QUINIELA
    {"id": "first_quiniela",    "title": "Primer Envío",           "description": "Envía tu primera quiniela",                       "emoji": "📝", "category": "quiniela", "secret": False},
    {"id": "five_correct",      "title": "Buen Ojo",               "description": "Acierta 5 o más partidos en una jornada",         "emoji": "👁️", "category": "quiniela", "secret": False},
    {"id": "perfect_jornada",   "title": "Ojo de Águila",          "description": "Acierta TODOS los partidos de una jornada",       "emoji": "🎯", "category": "quiniela", "secret": False},
    {"id": "quiniela_streak_3", "title": "En Racha 🔥",            "description": "Juega 3 jornadas consecutivas sin faltar",        "emoji": "🔥", "category": "quiniela", "secret": False},
    {"id": "quiniela_streak_5", "title": "Imparable",              "description": "Juega 5 jornadas consecutivas sin faltar",        "emoji": "⚡", "category": "quiniela", "secret": False},
    {"id": "quiniela_streak_10","title": "Leyenda de la Quiniela", "description": "Juega 10 jornadas seguidas sin faltar",           "emoji": "👑", "category": "quiniela", "secret": False},
    {"id": "win_streak_3",      "title": "Racha Ganadora",         "description": "Gana 3 jornadas consecutivas en tu liga",        "emoji": "🏅", "category": "quiniela", "secret": False},
    {"id": "win_streak_5",      "title": "Dominador",              "description": "Gana 5 jornadas consecutivas en tu liga",        "emoji": "💥", "category": "quiniela", "secret": True},
    {"id": "top3_jornada",      "title": "Podio",                  "description": "Termina top 3 en tu liga en una jornada",        "emoji": "🏆", "category": "quiniela", "secret": False},
    {"id": "correct_5_streak",  "title": "5 Seguidas 🎯",          "description": "5 predicciones correctas consecutivas",          "emoji": "🎯", "category": "quiniela", "secret": False},
    # FANTASY
    {"id": "first_lineup",      "title": "Manager Debut",          "description": "Arma tu primera alineación fantasy",             "emoji": "⚽", "category": "fantasy",  "secret": False},
    {"id": "fantasy_streak_3",  "title": "Manager Constante",      "description": "Arma tu alineación 3 jornadas seguidas",        "emoji": "📋", "category": "fantasy",  "secret": False},
    {"id": "fantasy_100pts",    "title": "Centurión",              "description": "Acumula 100 puntos fantasy en total",            "emoji": "💯", "category": "fantasy",  "secret": False},
    {"id": "fantasy_top",       "title": "Manager del Momento",    "description": "Sé el mejor manager de una jornada",            "emoji": "⭐", "category": "fantasy",  "secret": False},
    # SOCIAL
    {"id": "first_login",       "title": "¡Bienvenido!",           "description": "Inicia sesión por primera vez",                  "emoji": "🎉", "category": "general",  "secret": False},
    {"id": "create_league",     "title": "El Convocador",          "description": "Crea tu primera liga privada",                   "emoji": "🏟️", "category": "social",   "secret": False},
    {"id": "join_league",       "title": "Un Equipo",              "description": "Únete a tu primera liga privada",               "emoji": "🤝", "category": "social",   "secret": False},
    {"id": "invite_5",          "title": "Influencer",             "description": "Tu liga tiene 5 o más miembros",                 "emoji": "📣", "category": "social",   "secret": False},
    # SECRETOS
    {"id": "veteran",           "title": "Veterano",               "description": "30 días en la app",                             "emoji": "🎖️", "category": "general",  "secret": True},
    {"id": "quiniela_leader",   "title": "Líder Invicto",          "description": "Primer lugar en tu liga 4 semanas seguidas",    "emoji": "🥇", "category": "quiniela", "secret": True},
]

ACHIEVEMENTS_BY_ID = {a["id"]: a for a in ACHIEVEMENTS_CATALOG}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def award_achievement(user_id, achievement_id: str) -> bool:
    """Otorga un logro. Retorna True si es nuevo, False si ya lo tenía."""
    if achievement_id not in ACHIEVEMENTS_BY_ID:
        return False
    existing = await db.user_achievements.find_one({
        "user_id": user_id, "achievement_id": achievement_id
    })
    if existing:
        return False
    await db.user_achievements.insert_one({
        "user_id": user_id,
        "achievement_id": achievement_id,
        "unlocked_at": datetime.utcnow()
    })
    logger.info(f"🏅 Logro '{achievement_id}' → user {user_id}")
    return True


async def update_participation_streak(user_id) -> dict:
    doc = await db.user_streaks.find_one({"user_id": user_id})
    if not doc:
        await db.user_streaks.insert_one({
            "user_id": user_id,
            "quiniela_streak":        1,
            "quiniela_streak_best":   1,
            "win_streak":             0,
            "win_streak_best":        0,
            "correct_answers_streak": 0,
            "correct_answers_best":   0,
            "fantasy_streak":         0,
            "fantasy_streak_best":    0,
            "updated_at": datetime.utcnow()
        })
        return {"current": 1, "best": 1, "is_new_record": True}

    new_streak = doc.get("quiniela_streak", 0) + 1
    best = max(new_streak, doc.get("quiniela_streak_best", 0))
    await db.user_streaks.update_one(
        {"user_id": user_id},
        {"$set": {
            "quiniela_streak":      new_streak,
            "quiniela_streak_best": best,
            "updated_at":           datetime.utcnow()
        }}
    )
    return {"current": new_streak, "best": best, "is_new_record": new_streak >= best}


async def reset_participation_streak(user_id):
    doc = await db.user_streaks.find_one({"user_id": user_id})
    previous = doc.get("quiniela_streak", 0) if doc else 0
    await db.user_streaks.update_one(
        {"user_id": user_id},
        {"$set": {"quiniela_streak": 0, "updated_at": datetime.utcnow()}},
        upsert=True
    )
    return previous


async def update_win_streak(user_id, won: bool) -> dict:
    doc = await db.user_streaks.find_one({"user_id": user_id})
    current = doc.get("win_streak", 0) if doc else 0
    best    = doc.get("win_streak_best", 0) if doc else 0

    if won:
        new_streak = current + 1
        new_best   = max(new_streak, best)
    else:
        new_streak = 0
        new_best   = best

    await db.user_streaks.update_one(
        {"user_id": user_id},
        {"$set": {
            "win_streak":      new_streak,
            "win_streak_best": new_best,
            "updated_at":      datetime.utcnow()
        }},
        upsert=True
    )
    return {"current": new_streak, "best": new_best, "won": won}


async def update_correct_streak(user_id, correct: bool) -> int:
    doc = await db.user_streaks.find_one({"user_id": user_id})
    current = doc.get("correct_answers_streak", 0) if doc else 0
    best    = doc.get("correct_answers_best",   0) if doc else 0

    new_streak = (current + 1) if correct else 0
    new_best   = max(new_streak, best)

    await db.user_streaks.update_one(
        {"user_id": user_id},
        {"$set": {
            "correct_answers_streak": new_streak,
            "correct_answers_best":   new_best,
            "updated_at":             datetime.utcnow()
        }},
        upsert=True
    )
    return new_streak


# ── Checker principal ─────────────────────────────────────────────────────────

async def check_and_award_achievements_after_jornada(user_id, jornada_id: str) -> list:
    jornada_obj_id = ObjectId(jornada_id)
    new_achievements = []

    # 1. Primer envío de quiniela
    total_q = await db.quiniela_selections.count_documents({"user_id": user_id})
    if total_q > 0:
        if await award_achievement(user_id, "first_quiniela"):
            new_achievements.append("first_quiniela")

    # 2. Partidos correctos esta jornada
    matches = await db.matches.find({
        "jornada_id": jornada_obj_id, "status": "finished"
    }).to_list(100)

    correct_this_jornada = 0
    for match in matches:
        sel = await db.quiniela_selections.find_one({
            "user_id": user_id, "match_id": match["_id"]
        })
        if not sel:
            continue
        home = match.get("home_score", 0) or 0
        away = match.get("away_score", 0) or 0
        actual = "HOME" if home > away else ("AWAY" if away > home else "DRAW")
        is_correct = sel["selection"] == actual
        await update_correct_streak(user_id, is_correct)
        if is_correct:
            correct_this_jornada += 1

    if correct_this_jornada >= 5:
        if await award_achievement(user_id, "five_correct"):
            new_achievements.append("five_correct")
    if len(matches) > 0 and correct_this_jornada == len(matches):
        if await award_achievement(user_id, "perfect_jornada"):
            new_achievements.append("perfect_jornada")

    # Racha de 5 correctas seguidas
    streak_doc = await db.user_streaks.find_one({"user_id": user_id})
    if streak_doc and streak_doc.get("correct_answers_streak", 0) >= 5:
        if await award_achievement(user_id, "correct_5_streak"):
            new_achievements.append("correct_5_streak")

    # 3. Racha de participación
    streak_info = await update_participation_streak(user_id)
    streak = streak_info["current"]
    for threshold, achievement_id in [
        (3,  "quiniela_streak_3"),
        (5,  "quiniela_streak_5"),
        (10, "quiniela_streak_10"),
    ]:
        if streak >= threshold:
            if await award_achievement(user_id, achievement_id):
                new_achievements.append(achievement_id)

    # 4. Racha de victorias en liga
    user_leagues = await db.league_members.find({"user_id": user_id}).to_list(100)
    for membership in user_leagues:
        league = await db.private_leagues.find_one({"_id": membership["league_id"]})
        if not league or league.get("mode") != "quiniela":
            continue

        all_members = await db.league_members.find(
            {"league_id": membership["league_id"]}
        ).to_list(100)

        member_points = []
        for m in all_members:
            pts_log = await db.points_log.find_one({
                "user_id": m["user_id"],
                "jornada_id": jornada_obj_id,
                "source": "QUINIELA"
            })
            member_points.append({
                "user_id": m["user_id"],
                "points": pts_log["points"] if pts_log else 0
            })

        member_points.sort(key=lambda x: x["points"], reverse=True)

        top3_ids = [mp["user_id"] for mp in member_points[:3]]
        if user_id in top3_ids:
            if await award_achievement(user_id, "top3_jornada"):
                new_achievements.append("top3_jornada")

        won = len(member_points) > 0 and member_points[0]["user_id"] == user_id
        win_info = await update_win_streak(user_id, won)
        if win_info["current"] >= 3:
            if await award_achievement(user_id, "win_streak_3"):
                new_achievements.append("win_streak_3")
        if win_info["current"] >= 5:
            if await award_achievement(user_id, "win_streak_5"):
                new_achievements.append("win_streak_5")

        # 4b. Líder Invicto: #1 en 4 jornadas consecutivas (últimas 4)
        recent_jornadas = await db.jornadas.find(
            {"status": "finished"}
        ).sort("week_number", -1).limit(4).to_list(4)

        if len(recent_jornadas) >= 4:
            was_first_in_all = True
            for rj in recent_jornadas:
                rj_pts = []
                for m in all_members:
                    pl = await db.points_log.find_one({
                        "user_id": m["user_id"],
                        "jornada_id": rj["_id"],
                        "source": "QUINIELA"
                    })
                    rj_pts.append({
                        "user_id": m["user_id"],
                        "points": pl["points"] if pl else 0
                    })
                rj_pts.sort(key=lambda x: x["points"], reverse=True)
                if not rj_pts or rj_pts[0]["user_id"] != user_id:
                    was_first_in_all = False
                    break

            if was_first_in_all:
                if await award_achievement(user_id, "quiniela_leader"):
                    new_achievements.append("quiniela_leader")

    # 5. Fantasy 100 puntos acumulados
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$total_points"}}}
    ]
    fantasy_pts = await db.fantasy_points_log.aggregate(pipeline).to_list(1)
    if fantasy_pts and fantasy_pts[0]["total"] >= 100:
        if await award_achievement(user_id, "fantasy_100pts"):
            new_achievements.append("fantasy_100pts")

    # 6. Fantasy streak 3 jornadas seguidas con alineación
    _ft = await db.fantasy_teams.find_one({"user_id": user_id})
    if _ft:
        _jornadas_con_lineup = await db.fantasy_lineups.distinct(
            "jornada_id", {"fantasy_team_id": _ft["_id"]}
        )
        if len(_jornadas_con_lineup) >= 3:
            if await award_achievement(user_id, "fantasy_streak_3"):
                new_achievements.append("fantasy_streak_3")

    # 7. fantasy_top: mejor manager de la jornada
    top_fantasy = await db.fantasy_points_log.find(
        {"jornada_id": jornada_obj_id}
    ).sort("total_points", -1).limit(1).to_list(1)
    if top_fantasy and top_fantasy[0]["user_id"] == user_id:
        if await award_achievement(user_id, "fantasy_top"):
            new_achievements.append("fantasy_top")

    return new_achievements
