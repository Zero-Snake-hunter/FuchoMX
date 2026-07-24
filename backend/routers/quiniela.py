import logging
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from database import db
from dependencies import get_current_user
from models import QuinielaSubmit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiniela")


@router.post("/submit")
async def submit_quiniela(
    quiniela: QuinielaSubmit,
    current_user: dict = Depends(get_current_user)
):
    try:
        jornada_id = ObjectId(quiniela.jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")

    jornada = await db.jornadas.find_one({"_id": jornada_id})
    if not jornada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jornada no encontrada")

    existing = await db.quiniela_selections.find_one({
        "user_id": current_user["_id"],
        "jornada_id": jornada_id
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya enviaste tu quiniela para esta jornada"
        )

    matches = await db.matches.find({"jornada_id": jornada_id}).to_list(100)

    if any(match.get("locked") for match in matches):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta jornada aún no se activa — todavía no puedes enviar tu quiniela"
        )

    for match in matches:
        if match.get("status") in ["live", "finished"]:
            home_team = await db.teams.find_one({"_id": match.get("home_team_id")})
            away_team = await db.teams.find_one({"_id": match.get("away_team_id")})
            home_name = home_team.get("short_name", "Local") if home_team else "Local"
            away_name = away_team.get("short_name", "Visitante") if away_team else "Visitante"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El partido {home_name} vs {away_name} ya comenzó"
            )

    match_ids = {str(m["_id"]) for m in matches}
    submitted_match_ids = {s["match_id"] for s in quiniela.selections}
    if match_ids != submitted_match_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes seleccionar un resultado para cada partido"
        )

    valid_selections = {"HOME", "DRAW", "AWAY"}
    for selection in quiniela.selections:
        if selection["selection"] not in valid_selections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selección inválida. Debe ser HOME, DRAW o AWAY"
            )

    selections_to_insert = [
        {
            "user_id": current_user["_id"],
            "jornada_id": jornada_id,
            "match_id": ObjectId(s["match_id"]),
            "selection": s["selection"],
            "submitted_at": datetime.utcnow()
        }
        for s in quiniela.selections
    ]
    await db.quiniela_selections.insert_many(selections_to_insert)
    logger.info(f"User {current_user['email']} submitted quiniela for jornada {quiniela.jornada_id}")

    return {
        "message": "Quiniela enviada exitosamente",
        "jornada_id": quiniela.jornada_id,
        "selections_count": len(selections_to_insert)
    }


@router.get("/my-picks/{jornada_id}")
async def get_my_picks(
    jornada_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        jornada_obj_id = ObjectId(jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")

    selections = await db.quiniela_selections.find({
        "user_id": current_user["_id"],
        "jornada_id": jornada_obj_id
    }).to_list(100)

    if not selections:
        return {"submitted": False, "selections": []}

    formatted_selections = []
    for sel in selections:
        match = await db.matches.find_one({"_id": sel["match_id"]})
        if match:
            formatted_selections.append({
                "match_id": str(sel["match_id"]),
                "selection": sel["selection"],
                "submitted_at": sel["submitted_at"]
            })

    return {
        "submitted": True,
        "selections": formatted_selections,
        "submitted_at": selections[0]["submitted_at"] if selections else None
    }


@router.get("/rankings/general")
async def get_general_rankings():
    users = await db.users.find().sort("total_points", -1).limit(100).to_list(100)
    rankings = [
        {
            "position": idx,
            "user_id": str(user["_id"]),
            "display_name": user["display_name"],
            "total_points": user.get("total_points", 0),
            "avatar_base64": user.get("avatar_base64")
        }
        for idx, user in enumerate(users, 1)
    ]
    return {"rankings": rankings}


@router.get("/jornada/{jornada_id}/rankings")
async def get_jornada_rankings(jornada_id: str):
    jornada_obj_id = ObjectId(jornada_id)

    points = await db.points_log.find({
        "jornada_id": jornada_obj_id,
        "source": "QUINIELA"
    }).to_list(1000)

    user_points: dict = {}
    for point in points:
        uid = str(point["user_id"])
        user_points[uid] = user_points.get(uid, 0) + point["points"]

    rankings = []
    for uid, pts in user_points.items():
        user = await db.users.find_one({"_id": ObjectId(uid)})
        if user:
            rankings.append({
                "user_id": uid,
                "display_name": user["display_name"],
                "points": pts,
                "avatar_base64": user.get("avatar_base64")
            })

    rankings.sort(key=lambda x: x["points"], reverse=True)
    for idx, r in enumerate(rankings, 1):
        r["position"] = idx

    return {"rankings": rankings, "jornada_id": jornada_id}
