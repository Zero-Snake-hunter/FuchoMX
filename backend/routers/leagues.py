import logging
import random
import string
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from achievements import award_achievement
from database import db, get_active_competition, get_admin_user_id
from dependencies import get_current_user
from models import CreateLeagueRequest, JoinLeagueRequest, MAX_MEMBERS_FREE

logger = logging.getLogger(__name__)

# No prefix: este router maneja /leagues/* y los legacy /quiniela/league*
router = APIRouter()

# Fuentes de points_log que cuentan como "puntos de quiniela" — el acierto
# normal (3 pts c/u), la penalización por no seleccionar, y el bonus de
# nuevo usuario. Ver scoring_penalties.py.
QUINIELA_POINT_SOURCES = ["QUINIELA", "QUINIELA_PENALIZACION", "QUINIELA_BONUS_NUEVO"]

# El Apertura 2026 empieza a contar para el ranking desde J3 — J1/J2 y
# cualquier dato de World Cup 2026 no cuentan. Cuando arranque el próximo
# torneo (Clausura 2027), cambiar este número al week_number de su primera
# jornada — el ranking reinicia en 0 sin tocar nada más de esta función.
LIGA_MX_SEASON_START_WEEK = 3


async def _compute_quiniela_ranking_points(user_ids: list) -> dict:
    """
    Para cada user_id en user_ids, calcula:
    - total_points: suma de puntos de quiniela desde LIGA_MX_SEASON_START_WEEK
      en adelante (competition activa, excluye liguilla) — reemplaza leer
      user.total_points directo, que mezcla temporadas/torneos viejos
      (por eso el ranking general mostraba 0 o valores sin sentido).
    - jornada_anterior_points: puntos de quiniela solo de la jornada
      inmediatamente anterior a la activa (current_week - 1) — se calcula
      aparte del corte de temporada, por eso puede incluir una jornada
      anterior a LIGA_MX_SEASON_START_WEEK si estamos justo al inicio.
    - aciertos: total de partidos acertados desde LIGA_MX_SEASON_START_WEEK,
      derivado solo de source="QUINIELA" (points // 3, ya que cada acierto
      vale 3 puntos fijos — ver jornada_processor.py). QUINIELA_PENALIZACION
      y QUINIELA_BONUS_NUEVO no representan aciertos y quedan fuera de esta
      cuenta aunque sí sumen al total_points.

    El filtro es SIEMPRE por el week_number de la jornada real a la que
    pertenece cada punto (resuelto vía jornada_id) — nunca por created_at
    del documento en points_log. Una penalización aplicada tarde (ej. el
    cierre de J2 corrido varios días después) sigue siendo de J2 y se
    excluye del total igual que si se hubiera aplicado a tiempo.
    """
    competition = await get_active_competition()
    jornadas = await db.jornadas.find(
        {"competition": competition, "type": {"$ne": "liguilla"}}
    ).sort("week_number", 1).to_list(100)

    week_by_jornada_id = {j["_id"]: j.get("week_number") for j in jornadas}

    current = next((j for j in jornadas if j.get("is_active")), None)
    if not current and jornadas:
        current = jornadas[-1]
    previous_week = (current.get("week_number") - 1) if current else None

    result = {uid: {"total_points": 0, "jornada_anterior_points": 0, "aciertos": 0} for uid in user_ids}
    if not week_by_jornada_id:
        return result

    points = await db.points_log.find({
        "user_id": {"$in": user_ids},
        "jornada_id": {"$in": list(week_by_jornada_id.keys())},
        "source": {"$in": QUINIELA_POINT_SOURCES},
    }).to_list(10000)

    for p in points:
        uid = p["user_id"]
        if uid not in result:
            continue

        week = week_by_jornada_id.get(p["jornada_id"])
        if week is None:
            logger.warning(
                f"points_log {p.get('_id')} (user={uid}, source={p.get('source')}) referencia "
                f"jornada_id={p.get('jornada_id')} que no está en competition={competition} — se ignora"
            )
            continue

        # Filtro real: week_number de la jornada, no la fecha del log.
        if week >= LIGA_MX_SEASON_START_WEEK:
            result[uid]["total_points"] += p.get("points", 0)
            if p.get("source") == "QUINIELA":
                result[uid]["aciertos"] += p.get("points", 0) // 3
        if previous_week is not None and week == previous_week:
            result[uid]["jornada_anterior_points"] += p.get("points", 0)

    return result


# ── Ligas unificadas ──────────────────────────────────────────────────────────

@router.post("/leagues")
async def create_unified_league(
    league_data: CreateLeagueRequest,
    current_user: dict = Depends(get_current_user)
):
    if league_data.mode not in ["quiniela", "fantasy"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modo debe ser 'quiniela' o 'fantasy'"
        )

    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    while await db.private_leagues.find_one({"code": code}):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    league_doc = {
        "owner_id": current_user["_id"],
        "name": league_data.name,
        "mode": league_data.mode,
        "code": code,
        "max_members": MAX_MEMBERS_FREE,
        "created_at": datetime.utcnow()
    }
    result = await db.private_leagues.insert_one(league_doc)

    await award_achievement(current_user["_id"], "create_league")
    await db.league_members.insert_one({
        "league_id": result.inserted_id,
        "user_id": current_user["_id"],
        "joined_at": datetime.utcnow()
    })
    logger.info(f"User {current_user['email']} created {league_data.mode} league: {league_data.name} ({code})")

    return {
        "message": "Liga creada exitosamente",
        "league_id": str(result.inserted_id),
        "code": code,
        "name": league_data.name,
        "mode": league_data.mode
    }


@router.get("/leagues/validate/{code}")
async def validate_league_code(code: str):
    """
    Público (sin auth) — lo usa la pantalla /leagues/join/[code] antes de
    saber si hay sesión, para mostrar el nombre de la liga y decidir si
    manda al usuario a registro o lo une directo.
    """
    league = await db.private_leagues.find_one({"code": code.upper()})
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código de liga inválido")

    admin_id = await get_admin_user_id()
    count_query = {"league_id": league["_id"]}
    if admin_id:
        count_query["user_id"] = {"$ne": admin_id}
    member_count = await db.league_members.count_documents(count_query)
    max_members = league.get("max_members", MAX_MEMBERS_FREE)

    return {
        "valid": True,
        "code": league["code"],
        "name": league["name"],
        "mode": league.get("mode", "quiniela"),
        "member_count": member_count,
        "max_members": max_members,
        "is_full": member_count >= max_members,
    }


@router.post("/leagues/join")
async def join_unified_league(
    join_data: JoinLeagueRequest,
    current_user: dict = Depends(get_current_user)
):
    league = await db.private_leagues.find_one({"code": join_data.code.upper()})
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código de liga inválido")

    existing = await db.league_members.find_one({
        "league_id": league["_id"],
        "user_id": current_user["_id"]
    })
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya eres miembro de esta liga")

    max_members = league.get("max_members", MAX_MEMBERS_FREE)
    current_count = await db.league_members.count_documents({"league_id": league["_id"]})
    if current_count >= max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Esta liga está llena ({current_count}/{max_members} miembros)"
        )

    if league.get("mode") == "fantasy":
        fantasy_team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
        if not fantasy_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Necesitas crear tu equipo fantasy antes de unirte a una liga fantasy"
            )

    await db.league_members.insert_one({
        "league_id": league["_id"],
        "user_id": current_user["_id"],
        "joined_at": datetime.utcnow()
    })
    await award_achievement(current_user["_id"], "join_league")

    member_count = await db.league_members.count_documents({"league_id": league["_id"]})
    if member_count >= 5:
        await award_achievement(league["owner_id"], "invite_5")

    logger.info(f"User {current_user['email']} joined league: {league['name']}")

    return {
        "message": "Te has unido a la liga exitosamente",
        "league_id": str(league["_id"]),
        "league_name": league["name"],
        "mode": league.get("mode", "quiniela")
    }


@router.get("/leagues/my-leagues")
async def get_my_unified_leagues(current_user: dict = Depends(get_current_user)):
    memberships = await db.league_members.find({"user_id": current_user["_id"]}).to_list(100)
    admin_id = await get_admin_user_id()
    leagues = []
    for membership in memberships:
        league = await db.private_leagues.find_one({"_id": membership["league_id"]})
        if league:
            count_query = {"league_id": league["_id"]}
            if admin_id:
                count_query["user_id"] = {"$ne": admin_id}
            member_count = await db.league_members.count_documents(count_query)
            max_members = league.get("max_members", MAX_MEMBERS_FREE)
            leagues.append({
                "id": str(league["_id"]),
                "name": league["name"],
                "mode": league.get("mode", "quiniela"),
                "code": league["code"],
                "member_count": member_count,
                "max_members": max_members,
                "is_full": member_count >= max_members,
                "is_owner": str(league["owner_id"]) == str(current_user["_id"]),
                "created_at": league["created_at"]
            })
    return {"leagues": leagues}


@router.get("/leagues/{league_id}/availability")
async def get_league_availability(
    league_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        league_obj_id = ObjectId(league_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de liga inválido")

    league = await db.private_leagues.find_one({"_id": league_obj_id})
    if not league:
        raise HTTPException(status_code=404, detail="Liga no encontrada")

    admin_id = await get_admin_user_id()
    count_query = {"league_id": league_obj_id}
    if admin_id:
        count_query["user_id"] = {"$ne": admin_id}
    member_count = await db.league_members.count_documents(count_query)
    max_members = league.get("max_members", MAX_MEMBERS_FREE)

    return {
        "league_id": league_id,
        "name": league["name"],
        "member_count": member_count,
        "max_members": max_members,
        "is_full": member_count >= max_members,
        "spots_left": max(0, max_members - member_count)
    }


@router.get("/leagues/{league_id}/rankings/jornada/{jornada_id}")
async def get_league_jornada_rankings(
    league_id: str,
    jornada_id: str,
    current_user: dict = Depends(get_current_user)
):
    league_obj_id = ObjectId(league_id)
    jornada_obj_id = ObjectId(jornada_id)

    is_member = await db.league_members.find_one({
        "league_id": league_obj_id,
        "user_id": current_user["_id"]
    })
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No eres miembro de esta liga")

    league = await db.private_leagues.find_one({"_id": league_obj_id})
    if not league:
        raise HTTPException(status_code=404, detail="Liga no encontrada")

    mode = league.get("mode", "quiniela")
    memberships = await db.league_members.find({"league_id": league_obj_id}).to_list(100)
    admin_id = await get_admin_user_id()
    member_user_ids = [m["user_id"] for m in memberships if m["user_id"] != admin_id]
    rankings = []

    if mode == "fantasy":
        for user_id in member_user_ids:
            user = await db.users.find_one({"_id": user_id})
            fantasy_team = await db.fantasy_teams.find_one({"user_id": user_id})
            if fantasy_team:
                points_log = await db.fantasy_points_log.find_one({
                    "fantasy_team_id": fantasy_team["_id"],
                    "jornada_id": jornada_obj_id
                })
                rankings.append({
                    "user_id": str(user_id),
                    "display_name": user["display_name"] if user else "Unknown",
                    "team_name": fantasy_team["name"],
                    "jornada_points": points_log["total_points"] if points_log else 0,
                    "players_breakdown": points_log.get("players_breakdown", []) if points_log else []
                })
    else:
        for user_id in member_user_ids:
            user = await db.users.find_one({"_id": user_id})
            points_log = await db.points_log.find_one({
                "user_id": user_id,
                "jornada_id": jornada_obj_id,
                "source": "QUINIELA"
            })
            rankings.append({
                "user_id": str(user_id),
                "display_name": user["display_name"] if user else "Unknown",
                "jornada_points": points_log["points"] if points_log else 0
            })

    rankings.sort(key=lambda x: x["jornada_points"], reverse=True)
    for idx, r in enumerate(rankings):
        r["rank"] = idx + 1

    return {
        "league_id": league_id,
        "league_name": league["name"],
        "mode": mode,
        "jornada_id": jornada_id,
        "rankings": rankings
    }


@router.get("/leagues/{league_id}")
async def get_unified_league_details(
    league_id: str,
    current_user: dict = Depends(get_current_user)
):
    league_obj_id = ObjectId(league_id)
    league = await db.private_leagues.find_one({"_id": league_obj_id})
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liga no encontrada")

    is_member = await db.league_members.find_one({
        "league_id": league_obj_id,
        "user_id": current_user["_id"]
    })
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No eres miembro de esta liga")

    memberships = await db.league_members.find({"league_id": league_obj_id}).to_list(100)
    admin_id = await get_admin_user_id()
    # El admin (ADMIN_EMAIL) es solo para pruebas — se excluye de rankings,
    # listados de miembros y contadores visibles a otros usuarios, aunque
    # siga pudiendo ser miembro/dueño real de la liga para poder probar.
    visible_memberships = [m for m in memberships if m["user_id"] != admin_id]
    mode = league.get("mode", "quiniela")
    members = []

    # Para quiniela, los puntos se calculan una sola vez para todos los
    # miembros (no user.total_points, que mezcla temporadas/torneos viejos).
    quiniela_points_by_user = {}
    if mode != "fantasy":
        quiniela_points_by_user = await _compute_quiniela_ranking_points(
            [m["user_id"] for m in visible_memberships]
        )

    for membership in visible_memberships:
        user = await db.users.find_one({"_id": membership["user_id"]})
        if user:
            member_data = {
                "user_id": str(user["_id"]),
                "display_name": user["display_name"],
                "joined_at": membership["joined_at"]
            }
            if mode == "fantasy":
                fantasy_team = await db.fantasy_teams.find_one({"user_id": user["_id"]})
                if fantasy_team:
                    pipeline = [
                        {"$match": {"user_id": user["_id"]}},
                        {"$group": {"_id": None, "total": {"$sum": "$total_points"}}}
                    ]
                    result = await db.fantasy_points_log.aggregate(pipeline).to_list(1)
                    member_data["team_name"] = fantasy_team["name"]
                    member_data["total_points"] = result[0]["total"] if result else 0
                else:
                    member_data["team_name"] = "Sin equipo"
                    member_data["total_points"] = 0
            else:
                pts = quiniela_points_by_user.get(
                    user["_id"], {"total_points": 0, "jornada_anterior_points": 0, "aciertos": 0}
                )
                member_data["total_points"] = pts["total_points"]
                member_data["jornada_anterior_points"] = pts["jornada_anterior_points"]
                member_data["aciertos"] = pts["aciertos"]
            members.append(member_data)

    members.sort(key=lambda x: x["total_points"], reverse=True)
    for idx, member in enumerate(members):
        member["rank"] = idx + 1

    return {
        "league": {
            "id": str(league["_id"]),
            "name": league["name"],
            "mode": mode,
            "code": league["code"],
            "owner_id": str(league["owner_id"]),
            "is_owner": str(league["owner_id"]) == str(current_user["_id"]),
            "created_at": league["created_at"]
        },
        "members": members
    }


# ── Legacy /quiniela/league* (backwards compatibility) ───────────────────────

@router.post("/quiniela/league")
async def create_league(
    league_data: CreateLeagueRequest,
    current_user: dict = Depends(get_current_user)
):
    league_data.mode = "quiniela"
    return await create_unified_league(league_data, current_user)


@router.post("/quiniela/league/join")
async def join_league(
    join_data: JoinLeagueRequest,
    current_user: dict = Depends(get_current_user)
):
    return await join_unified_league(join_data, current_user)


@router.get("/quiniela/my-leagues")
async def get_my_leagues(current_user: dict = Depends(get_current_user)):
    return await get_my_unified_leagues(current_user)


@router.get("/quiniela/league/{league_id}")
async def get_league_details(
    league_id: str,
    current_user: dict = Depends(get_current_user)
):
    league_obj_id = ObjectId(league_id)
    league = await db.private_leagues.find_one({"_id": league_obj_id})
    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Liga no encontrada")

    is_member = await db.league_members.find_one({
        "league_id": league_obj_id,
        "user_id": current_user["_id"]
    })
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No eres miembro de esta liga")

    memberships = await db.league_members.find({"league_id": league_obj_id}).to_list(100)
    admin_id = await get_admin_user_id()
    members = []
    for membership in memberships:
        if membership["user_id"] == admin_id:
            continue
        user = await db.users.find_one({"_id": membership["user_id"]})
        if user:
            members.append({
                "user_id": str(user["_id"]),
                "display_name": user["display_name"],
                "total_points": user.get("total_points", 0),
                "joined_at": membership["joined_at"]
            })
    members.sort(key=lambda x: x["total_points"], reverse=True)

    return {
        "league": {
            "id": str(league["_id"]),
            "name": league["name"],
            "code": league["code"],
            "owner_id": str(league["owner_id"]),
            "is_owner": str(league["owner_id"]) == str(current_user["_id"]),
            "created_at": league["created_at"]
        },
        "members": members
    }


@router.get("/quiniela/league/{league_id}/results")
async def get_league_results(
    league_id: str,
    jornada_id: str,
    current_user: dict = Depends(get_current_user)
):
    league_obj_id = ObjectId(league_id)
    jornada_obj_id = ObjectId(jornada_id)

    is_member = await db.league_members.find_one({
        "league_id": league_obj_id,
        "user_id": current_user["_id"]
    })
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No eres miembro de esta liga")

    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jornada no encontrada")

    matches = await db.matches.find({"jornada_id": jornada_obj_id}).to_list(100)
    admin_id = await get_admin_user_id()
    memberships = [
        m for m in await db.league_members.find({"league_id": league_obj_id}).to_list(100)
        if m["user_id"] != admin_id
    ]

    results = []
    for match in matches:
        home_team = await db.teams.find_one({"_id": match["home_team_id"]})
        away_team = await db.teams.find_one({"_id": match["away_team_id"]})

        actual_result = None
        if match["status"] == "finished" and match["home_score"] is not None:
            if match["home_score"] > match["away_score"]:
                actual_result = "HOME"
            elif match["away_score"] > match["home_score"]:
                actual_result = "AWAY"
            else:
                actual_result = "DRAW"

        match_result = {
            "match_id": str(match["_id"]),
            "home_team": home_team["short_name"] if home_team else "???",
            "away_team": away_team["short_name"] if away_team else "???",
            "home_score": match.get("home_score"),
            "away_score": match.get("away_score"),
            "status": match["status"],
            "actual_result": actual_result,
            "predictions": []
        }

        for membership in memberships:
            user = await db.users.find_one({"_id": membership["user_id"]})
            selection = await db.quiniela_selections.find_one({
                "user_id": membership["user_id"],
                "match_id": match["_id"]
            })
            match_result["predictions"].append({
                "user_id": str(membership["user_id"]),
                "user_name": user["display_name"] if user else "???",
                "selection": selection["selection"] if selection else None,
                "is_correct": bool(selection and actual_result and selection["selection"] == actual_result)
            })

        results.append(match_result)

    user_points: dict = {}
    for mr in results:
        for pred in mr["predictions"]:
            uid = pred["user_id"]
            if uid not in user_points:
                user_points[uid] = {"user_name": pred["user_name"], "points": 0}
            if pred["is_correct"]:
                user_points[uid]["points"] += 1

    return {
        "jornada": {
            "id": str(jornada["_id"]),
            "week_number": jornada["week_number"],
            "status": jornada["status"]
        },
        "results": results,
        "user_points": user_points
    }


@router.get("/quiniela/league/{league_id}/ranking")
async def get_league_ranking(
    league_id: str,
    current_user: dict = Depends(get_current_user)
):
    league_obj_id = ObjectId(league_id)

    is_member = await db.league_members.find_one({
        "league_id": league_obj_id,
        "user_id": current_user["_id"]
    })
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No eres miembro de esta liga")

    memberships = await db.league_members.find({"league_id": league_obj_id}).to_list(100)
    admin_id = await get_admin_user_id()
    rankings = []
    for membership in memberships:
        if membership["user_id"] == admin_id:
            continue
        user = await db.users.find_one({"_id": membership["user_id"]})
        if user:
            rankings.append({
                "user_id": str(user["_id"]),
                "display_name": user["display_name"],
                "total_points": user.get("total_points", 0)
            })

    rankings.sort(key=lambda x: x["total_points"], reverse=True)
    for idx, r in enumerate(rankings, 1):
        r["position"] = idx

    return {"rankings": rankings}
