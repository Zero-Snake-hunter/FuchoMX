import logging

from bson import ObjectId
from fastapi import APIRouter, Depends

from achievements import (
    ACHIEVEMENTS_CATALOG,
    check_and_award_achievements_after_jornada,
    reset_participation_streak,
)
from database import db
from dependencies import get_admin_user, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/achievements/catalog")
async def get_achievements_catalog():
    return {
        "achievements": [
            {
                **a,
                "description": "???" if a["secret"] else a["description"],
                "emoji": "🔒" if a["secret"] else a["emoji"],
            }
            for a in ACHIEVEMENTS_CATALOG
        ],
        "total": len(ACHIEVEMENTS_CATALOG)
    }


@router.get("/achievements/my")
async def get_my_achievements(current_user: dict = Depends(get_current_user)):
    user_id = current_user["_id"]

    unlocked_docs = await db.user_achievements.find({"user_id": user_id}).to_list(200)
    unlocked_map = {d["achievement_id"]: d["unlocked_at"] for d in unlocked_docs}
    streak_doc = await db.user_streaks.find_one({"user_id": user_id}) or {}

    result = []
    for a in ACHIEVEMENTS_CATALOG:
        unlocked = a["id"] in unlocked_map
        result.append({
            "id":          a["id"],
            "title":       a["title"],
            "description": a["description"] if (not a["secret"] or unlocked) else "Logro secreto — ¡sigue jugando!",
            "emoji":       a["emoji"]       if (not a["secret"] or unlocked) else "🔒",
            "category":    a["category"],
            "secret":      a["secret"],
            "unlocked":    unlocked,
            "unlocked_at": unlocked_map[a["id"]].isoformat() if unlocked else None,
        })

    result.sort(key=lambda x: (not x["unlocked"], x["category"]))

    return {
        "achievements":   result,
        "total":          len(result),
        "unlocked_count": len(unlocked_map),
        "streaks": {
            "quiniela_current":  streak_doc.get("quiniela_streak", 0),
            "quiniela_best":     streak_doc.get("quiniela_streak_best", 0),
            "win_current":       streak_doc.get("win_streak", 0),
            "win_best":          streak_doc.get("win_streak_best", 0),
            "correct_current":   streak_doc.get("correct_answers_streak", 0),
            "correct_best":      streak_doc.get("correct_answers_best", 0),
            "fantasy_current":   streak_doc.get("fantasy_streak", 0),
        }
    }


@router.post("/admin/achievements/check/{jornada_id}")
async def trigger_achievement_check(jornada_id: str, current_user: dict = Depends(get_admin_user)):
    all_users = await db.users.find().to_list(10000)
    summary = []

    for user in all_users:
        new = await check_and_award_achievements_after_jornada(user["_id"], jornada_id)
        if new:
            summary.append({"user": user.get("display_name"), "new_achievements": new})

    jornada_obj_id = ObjectId(jornada_id)
    participant_ids = set()
    async for sel in db.quiniela_selections.find({"jornada_id": jornada_obj_id}):
        participant_ids.add(sel["user_id"])

    reset_count = 0
    for user in all_users:
        if user["_id"] not in participant_ids:
            previous = await reset_participation_streak(user["_id"])
            if previous > 0:
                reset_count += 1
                logger.info(f"Racha reseteada: {user.get('display_name')} tenía {previous}")

    return {
        "message":                  f"Logros verificados: {len(all_users)} usuarios",
        "new_achievements_awarded": summary,
        "streaks_reset":            reset_count
    }
