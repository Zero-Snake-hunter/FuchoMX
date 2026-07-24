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

    matches = await db.matches.find({"jornada_id": jornada_id}).to_list(100)
    if not matches:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta jornada no tiene partidos")

    if any(match.get("locked") for match in matches):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta jornada aún no se activa — todavía no puedes enviar tu quiniela"
        )

    matches_by_id = {str(m["_id"]): m for m in matches}
    team_ids = {m["home_team_id"] for m in matches} | {m["away_team_id"] for m in matches}
    teams = await db.teams.find({"_id": {"$in": list(team_ids)}}).to_list(100)
    team_names = {t["_id"]: t.get("short_name", t.get("name", "?")) for t in teams}

    valid_selection_values = {"HOME", "DRAW", "AWAY"}
    saved = []
    rejected = []

    for s in quiniela.selections:
        match_id_str = s.get("match_id")
        selection_val = s.get("selection")
        match = matches_by_id.get(match_id_str)

        if not match:
            rejected.append({"match_id": match_id_str, "reason": "El partido no pertenece a esta jornada"})
            continue

        home_name = team_names.get(match["home_team_id"], "Local")
        away_name = team_names.get(match["away_team_id"], "Visitante")
        label = f"{home_name} vs {away_name}"

        if match.get("status") in ["live", "finished"]:
            when = "ya está en vivo" if match["status"] == "live" else "ya finalizó"
            rejected.append({
                "match_id": match_id_str, "match": label,
                "reason": f"{label} {when} — no se puede guardar/cambiar el pick"
            })
            continue

        if selection_val not in valid_selection_values:
            rejected.append({
                "match_id": match_id_str, "match": label,
                "reason": "Selección inválida (debe ser HOME, DRAW o AWAY)"
            })
            continue

        await db.quiniela_selections.update_one(
            {
                "user_id": current_user["_id"],
                "jornada_id": jornada_id,
                "match_id": ObjectId(match_id_str),
            },
            {"$set": {"selection": selection_val, "submitted_at": datetime.utcnow()}},
            upsert=True
        )
        saved.append({"match_id": match_id_str, "match": label, "selection": selection_val})

    logger.info(
        f"User {current_user['email']} submitted quiniela for jornada {quiniela.jornada_id}: "
        f"{len(saved)} guardado(s), {len(rejected)} rechazado(s)"
    )

    return {
        "message": (
            f"✅ {len(saved)} pick(s) guardado(s)"
            + (f" · ⚠️ {len(rejected)} rechazado(s) por partido ya cerrado" if rejected else "")
        ),
        "jornada_id": quiniela.jornada_id,
        "saved": saved,
        "rejected": rejected,
        "saved_count": len(saved),
        "rejected_count": len(rejected),
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
