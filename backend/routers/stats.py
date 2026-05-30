import logging
from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from config import ADMIN_EMAIL
from database import db
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats/my")
async def get_my_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user["_id"]

    quiniela_logs = await db.points_log.find(
        {"user_id": user_id, "source": "QUINIELA"}
    ).to_list(1000)

    total_quiniela_pts = sum(log.get("points", 0) for log in quiniela_logs)
    jornada_ids_quiniela = list(set(log["jornada_id"] for log in quiniela_logs))
    jornadas_quiniela = len(jornada_ids_quiniela)
    mejor_jornada = max((log.get("points", 0) for log in quiniela_logs), default=0)
    total_aciertos = total_quiniela_pts
    promedio_aciertos = round(total_aciertos / jornadas_quiniela, 1) if jornadas_quiniela > 0 else 0

    fantasy_jornadas = await db.fantasy_lineups.distinct("jornada_id", {"user_id": user_id})
    jornadas_fantasy = len(fantasy_jornadas)

    fantasy_pts_result = await db.fantasy_points_log.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$total_points"}}}
    ]).to_list(1)
    total_fantasy_pts = fantasy_pts_result[0]["total"] if fantasy_pts_result else 0
    total_puntos = total_quiniela_pts + total_fantasy_pts

    top3_count = 0
    mejor_posicion = None
    for jornada_id in jornada_ids_quiniela:
        all_for_jornada = await db.points_log.aggregate([
            {"$match": {"jornada_id": jornada_id, "source": "QUINIELA"}},
            {"$group": {"_id": "$user_id", "total": {"$sum": "$points"}}},
            {"$sort": {"total": -1}},
        ]).to_list(200)
        position = next(
            (i + 1 for i, p in enumerate(all_for_jornada) if str(p["_id"]) == str(user_id)),
            None
        )
        if position and position <= 3:
            top3_count += 1
        if position and (mejor_posicion is None or position < mejor_posicion):
            mejor_posicion = position

    win_rate = round((top3_count / jornadas_quiniela * 100)) if jornadas_quiniela > 0 else 0
    ligas_activas = await db.league_members.count_documents({"user_id": user_id})

    return {
        "total_puntos":      total_puntos,
        "jornadas_quiniela": jornadas_quiniela,
        "mejor_jornada":     mejor_jornada,
        "win_rate":          win_rate,
        "total_aciertos":    total_aciertos,
        "promedio_aciertos": promedio_aciertos,
        "jornadas_fantasy":  jornadas_fantasy,
        "mejor_posicion":    mejor_posicion,
        "ligas_activas":     ligas_activas,
    }


@router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    total_usuarios = await db.users.count_documents({})
    nuevos_hoy = await db.users.count_documents({"created_at": {"$gte": today_start}})
    nuevos_semana = await db.users.count_documents({"created_at": {"$gte": week_start}})
    nuevos_mes = await db.users.count_documents({"created_at": {"$gte": month_start}})

    total_jornadas = await db.jornadas.count_documents({})
    jornada_activa = await db.jornadas.find_one({"is_active": True})

    try:
        total_predicciones = await db.quiniela_selections.count_documents({})
    except Exception:
        total_predicciones = 0

    try:
        total_ligas = await db.private_leagues.count_documents({})
        ligas_raw = await db.private_leagues.find(
            {}, {"name": 1, "mode": 1, "code": 1, "owner_id": 1, "created_at": 1}
        ).sort("created_at", -1).limit(20).to_list(20)
        ligas_detalle = []
        for liga in ligas_raw:
            owner = await db.users.find_one({"_id": liga["owner_id"]}, {"display_name": 1, "email": 1})
            miembros = await db.league_members.count_documents({"league_id": liga["_id"]})
            ligas_detalle.append({
                "id":      str(liga["_id"]),
                "nombre":  liga.get("name", "Sin nombre"),
                "modo":    liga.get("mode", "quiniela"),
                "codigo":  liga.get("code", ""),
                "creador": owner.get("display_name", owner.get("email", "?")) if owner else "?",
                "miembros": miembros,
                "creada":  liga["created_at"].isoformat() if liga.get("created_at") else "",
            })
    except Exception:
        total_ligas = 0
        ligas_detalle = []

    try:
        total_fantasy = await db.fantasy_lineups.count_documents({})
    except Exception:
        total_fantasy = 0

    ultimos_usuarios = await db.users.find(
        {}, {"email": 1, "display_name": 1, "created_at": 1, "total_points": 1}
    ).sort("created_at", -1).limit(5).to_list(5)
    for u in ultimos_usuarios:
        u["_id"] = str(u["_id"])

    return {
        "usuarios": {
            "total":         total_usuarios,
            "nuevos_hoy":    nuevos_hoy,
            "nuevos_semana": nuevos_semana,
            "nuevos_mes":    nuevos_mes,
            "ultimos":       ultimos_usuarios,
        },
        "jornadas": {
            "total":  total_jornadas,
            "activa": jornada_activa.get("week_number") if jornada_activa else None,
        },
        "predicciones": {"total": total_predicciones},
        "ligas": {"total": total_ligas, "detalle": ligas_detalle},
        "fantasy": {"total_lineups": total_fantasy},
    }
