import logging
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from config import ADMIN_EMAIL
from database import db, get_active_competition
from dependencies import get_admin_user, get_current_user, get_optional_user
from models import BracketUpdateRequest
from routers.teams import compute_standings
from world_cup_players_data import WC_SQUADS

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Datos liguilla ────────────────────────────────────────────────────────────
LIGUILLA_CUARTOS_MATCHES = [
    {"home": "Pumas UNAM",  "away": "Club América",  "home_score": 3, "away_score": 3, "leg": "ida",    "date": "2026-05-08"},
    {"home": "Pachuca",     "away": "Toluca",         "home_score": 1, "away_score": 0, "leg": "ida",    "date": "2026-05-08"},
    {"home": "Guadalajara", "away": "Tigres UANL",   "home_score": 1, "away_score": 3, "leg": "ida",    "date": "2026-05-09"},
    {"home": "Cruz Azul",   "away": "Atlas",          "home_score": 3, "away_score": 2, "leg": "ida",    "date": "2026-05-09"},
    {"home": "Club América",  "away": "Pumas UNAM",  "home_score": 3, "away_score": 3, "leg": "vuelta", "date": "2026-05-12"},
    {"home": "Toluca",        "away": "Pachuca",      "home_score": 0, "away_score": 2, "leg": "vuelta", "date": "2026-05-12"},
    {"home": "Tigres UANL",  "away": "Guadalajara",  "home_score": 0, "away_score": 2, "leg": "vuelta", "date": "2026-05-13"},
    {"home": "Atlas",         "away": "Cruz Azul",    "home_score": 0, "away_score": 1, "leg": "vuelta", "date": "2026-05-13"},
]

LIGUILLA_SEMIS_MATCHES = [
    {"home": "Cruz Azul",   "away": "Guadalajara",  "home_score": 2, "away_score": 2,    "leg": "ida",    "date": "2026-05-14"},
    {"home": "Pumas UNAM",  "away": "Pachuca",       "home_score": 0, "away_score": 1,    "leg": "ida",    "date": "2026-05-15"},
    {"home": "Guadalajara", "away": "Cruz Azul",    "home_score": 1, "away_score": 2,    "leg": "vuelta", "date": "2026-05-16"},
    {"home": "Pachuca",     "away": "Pumas UNAM",   "home_score": None, "away_score": None, "leg": "vuelta", "date": "2026-05-17"},
]


# ── User-facing bracket ───────────────────────────────────────────────────────

@router.get("/liguilla/bracket")
async def get_liguilla_bracket(current_user: dict = Depends(get_optional_user)):
    competition = await get_active_competition()

    standings = await compute_standings(competition)
    teams_data = [
        {
            "position":   row["position"],
            "id":         row["id"],
            "name":       row["name"],
            "short_name": row["short_name"],
            "shield_url": row["shield_url"],
        }
        for row in standings[:8]
    ]

    # Provisional hasta que J17 (última jornada de temporada regular) termine —
    # antes de eso, los 8 clasificados de nuestra propia tabla pueden cambiar.
    j17 = await db.jornadas.find_one({
        "competition": competition, "week_number": 17, "type": {"$ne": "liguilla"},
    })
    is_provisional = not (j17 and j17.get("status") == "finished")

    by_pos = {t["position"]: t for t in teams_data}

    results = await db.liguilla_results.find_one({"temporada": "Clausura 2026"})
    cuartos_winners    = results.get("cuartos_winners", []) if results else []
    semis_left_winner  = results.get("semis_left_winner")   if results else None
    semis_right_winner = results.get("semis_right_winner")  if results else None
    champion           = results.get("champion")            if results else None

    if champion:
        bracket_status = "finalizado"
    elif semis_left_winner or semis_right_winner:
        bracket_status = "semifinales"
    elif cuartos_winners:
        bracket_status = "semifinales"
    else:
        bracket_status = "cuartos"

    async def find_team_by_short(short_name):
        if not short_name:
            return None
        t = await db.teams.find_one({"short_name": short_name})
        if not t:
            t = await db.teams.find_one({"name": {"$regex": short_name, "$options": "i"}})
        if t:
            return {
                "id": str(t["_id"]), "name": t["name"],
                "short_name": t.get("short_name", short_name),
                "shield_url": t.get("shield_url", ""),
            }
        return {"id": "", "name": short_name, "short_name": short_name, "shield_url": ""}

    semi_left_home  = await find_team_by_short(cuartos_winners[0]) if len(cuartos_winners) > 0 else None
    semi_left_away  = await find_team_by_short(cuartos_winners[1]) if len(cuartos_winners) > 1 else None
    semi_right_home = await find_team_by_short(cuartos_winners[2]) if len(cuartos_winners) > 2 else None
    semi_right_away = await find_team_by_short(cuartos_winners[3]) if len(cuartos_winners) > 3 else None
    finalist_left   = await find_team_by_short(semis_left_winner)  if semis_left_winner  else None
    finalist_right  = await find_team_by_short(semis_right_winner) if semis_right_winner else None
    champion_team   = await find_team_by_short(champion)           if champion           else None

    bracket = {
        "temporada":      "Clausura 2026",
        "status":         bracket_status,
        "is_provisional": is_provisional,
        "teams":          teams_data,
        "cuartos": [
            {"match": 1, "side": "left",  "home": by_pos.get(1), "away": by_pos.get(8), "winner": cuartos_winners[0] if len(cuartos_winners) > 0 else None},
            {"match": 2, "side": "left",  "home": by_pos.get(4), "away": by_pos.get(5), "winner": cuartos_winners[1] if len(cuartos_winners) > 1 else None},
            {"match": 3, "side": "right", "home": by_pos.get(2), "away": by_pos.get(7), "winner": cuartos_winners[2] if len(cuartos_winners) > 2 else None},
            {"match": 4, "side": "right", "home": by_pos.get(3), "away": by_pos.get(6), "winner": cuartos_winners[3] if len(cuartos_winners) > 3 else None},
        ],
        "semifinales": {
            "left":  {"home": semi_left_home,  "away": semi_left_away,  "winner": semis_left_winner},
            "right": {"home": semi_right_home, "away": semi_right_away, "winner": semis_right_winner},
        },
        "final": {
            "home": finalist_left,
            "away": finalist_right,
            "champion": champion_team,
        },
        "scoring": {"cuartos": 5, "semis": 10, "campeon": 25},
        "my_prediction": None,
    }

    if current_user:
        pred = await db.bracket_predictions.find_one({"user_id": current_user["_id"]})
        if pred:
            bracket["my_prediction"] = {
                "cuartos_picks": pred.get("cuartos_picks", []),
                "semis_picks":   pred.get("semis_picks", []),
                "champion":      pred.get("champion"),
            }

    return bracket


@router.post("/liguilla/bracket/submit")
async def submit_bracket_prediction(
    prediction: dict,
    current_user: dict = Depends(get_current_user),
):
    await db.bracket_predictions.update_one(
        {"user_id": current_user["_id"]},
        {"$set": {
            "user_id":       current_user["_id"],
            "cuartos_picks": prediction.get("cuartos_picks", []),
            "semis_picks":   prediction.get("semis_picks", []),
            "champion":      prediction.get("champion"),
            "updated_at":    datetime.utcnow(),
        }},
        upsert=True,
    )
    return {"message": "✅ Bracket guardado exitosamente"}


@router.get("/liguilla/results")
async def get_liguilla_results():
    results = await db.liguilla_results.find_one({"temporada": "Clausura 2026"})
    if not results:
        return {
            "temporada": "Clausura 2026",
            "cuartos_winners": [],
            "semis_left_winner": None,
            "semis_right_winner": None,
            "champion": None
        }
    results["_id"] = str(results["_id"])
    return results


# ── Admin bracket update ──────────────────────────────────────────────────────

@router.post("/admin/bracket/update")
async def update_bracket_results(
    data: BracketUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    update_doc: dict = {"updated_at": datetime.utcnow()}
    if data.cuartos_winners:
        update_doc["cuartos_winners"] = data.cuartos_winners
    if data.semis_left_winner:
        update_doc["semis_left_winner"] = data.semis_left_winner
    if data.semis_right_winner:
        update_doc["semis_right_winner"] = data.semis_right_winner
    if data.champion:
        update_doc["champion"] = data.champion

    await db.liguilla_results.update_one(
        {"temporada": "Clausura 2026"},
        {"$set": update_doc},
        upsert=True
    )
    return {"message": "Bracket actualizado", "data": update_doc}


# ── Admin liguilla jornadas ───────────────────────────────────────────────────

@router.post("/admin/create-liguilla-jornadas")
async def create_liguilla_jornadas(current_user: dict = Depends(get_current_user)):
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    created = []
    teams = await db.teams.find().to_list(100)
    team_map = {t["name"]: t["_id"] for t in teams}

    # Cuartos
    if not await db.jornadas.find_one({"type": "liguilla", "phase": "cuartos"}):
        cuartos_id = (await db.jornadas.insert_one({
            "week_number": 18, "type": "liguilla", "phase": "cuartos",
            "title": "Liguilla Clausura 2026 — Cuartos",
            "active_teams": ["Pumas UNAM", "Guadalajara", "Cruz Azul", "Pachuca",
                             "Toluca", "Atlas", "Tigres UANL", "Club América"],
            "start_date": datetime(2026, 5, 8), "end_date": datetime(2026, 5, 13, 23, 59),
            "status": "finished", "is_active": False, "processed": True,
            "created_at": datetime.utcnow(),
        })).inserted_id
        for m in LIGUILLA_CUARTOS_MATCHES:
            home_id, away_id = team_map.get(m["home"]), team_map.get(m["away"])
            if home_id and away_id:
                await db.matches.insert_one({
                    "jornada_id": cuartos_id, "home_team_id": home_id, "away_team_id": away_id,
                    "home_score": m["home_score"], "away_score": m["away_score"],
                    "status": "finished", "leg": m["leg"],
                    "start_at": datetime.fromisoformat(m["date"]), "created_at": datetime.utcnow(),
                })
        created.append("cuartos")

    # Semis
    if not await db.jornadas.find_one({"type": "liguilla", "phase": "semis"}):
        semis_id = (await db.jornadas.insert_one({
            "week_number": 19, "type": "liguilla", "phase": "semis",
            "title": "Liguilla Clausura 2026 — Semifinales",
            "active_teams": ["Pumas UNAM", "Guadalajara", "Cruz Azul", "Pachuca"],
            "start_date": datetime(2026, 5, 14), "end_date": datetime(2026, 5, 17, 23, 59),
            "status": "in_progress", "is_active": True, "processed": False,
            "created_at": datetime.utcnow(),
        })).inserted_id
        for m in LIGUILLA_SEMIS_MATCHES:
            home_id, away_id = team_map.get(m["home"]), team_map.get(m["away"])
            if home_id and away_id:
                await db.matches.insert_one({
                    "jornada_id": semis_id, "home_team_id": home_id, "away_team_id": away_id,
                    "home_score": m["home_score"], "away_score": m["away_score"],
                    "status": "finished" if m["home_score"] is not None else "scheduled",
                    "leg": m["leg"], "start_at": datetime.fromisoformat(m["date"]),
                    "created_at": datetime.utcnow(),
                })
        created.append("semis")

    # Final
    if not await db.jornadas.find_one({"type": "liguilla", "phase": "final"}):
        await db.jornadas.insert_one({
            "week_number": 20, "type": "liguilla", "phase": "final",
            "title": "Liguilla Clausura 2026 — Final",
            "active_teams": ["Cruz Azul"],
            "start_date": datetime(2026, 5, 22), "end_date": datetime(2026, 5, 25, 23, 59),
            "status": "upcoming", "is_active": False, "processed": False,
            "created_at": datetime.utcnow(),
        })
        created.append("final (pendiente finalista)")

    return {
        "message": f"Jornadas de liguilla creadas: {', '.join(created) if created else 'ya existían'}",
        "created": created,
    }


@router.post("/admin/activate-liguilla-final")
async def activate_liguilla_final(
    finalist: str,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    await db.jornadas.update_one(
        {"type": "liguilla", "phase": "semis"},
        {"$set": {"is_active": False, "status": "finished", "processed": True}}
    )

    team_map = {"PUM": "Pumas UNAM", "PAC": "Pachuca"}
    finalist_name = team_map.get(finalist, finalist)

    await db.jornadas.update_one(
        {"type": "liguilla", "phase": "final"},
        {"$set": {
            "active_teams": ["Cruz Azul", finalist_name],
            "is_active": True, "status": "upcoming",
            "title": f"Liguilla Clausura 2026 — Final: Cruz Azul vs {finalist_name}",
        }}
    )

    teams = await db.teams.find({"name": {"$in": ["Cruz Azul", finalist_name]}}).to_list(2)
    final_jornada = await db.jornadas.find_one({"type": "liguilla", "phase": "final"})

    if len(teams) == 2 and final_jornada:
        caz = next((t for t in teams if t["name"] == "Cruz Azul"), None)
        fin = next((t for t in teams if t["name"] == finalist_name), None)
        if caz and fin:
            await db.matches.insert_one({
                "jornada_id": final_jornada["_id"],
                "home_team_id": caz["_id"], "away_team_id": fin["_id"],
                "home_score": None, "away_score": None, "status": "scheduled",
                "leg": "ida", "start_at": datetime(2026, 5, 22, 21, 0),
                "created_at": datetime.utcnow(),
            })
            await db.matches.insert_one({
                "jornada_id": final_jornada["_id"],
                "home_team_id": fin["_id"], "away_team_id": caz["_id"],
                "home_score": None, "away_score": None, "status": "scheduled",
                "leg": "vuelta", "start_at": datetime(2026, 5, 25, 21, 0),
                "created_at": datetime.utcnow(),
            })

    return {"message": f"Final activada: Cruz Azul vs {finalist_name}", "finalist": finalist_name}


@router.post("/admin/seed-final-players")
async def seed_final_players(current_user: dict = Depends(get_current_user)):
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    CRUZ_AZUL = [
        {"name": "Andrés Gudiño", "number": 1, "position": "POR", "nationality": "México", "age": 29, "appearances": 13, "goals": 0, "assists": 0, "yellow_cards": 3, "red_cards": 0},
        {"name": "Kevin Mier", "number": 23, "position": "POR", "nationality": "Colombia", "age": 26, "appearances": 8, "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0},
        {"name": "Jesús Orozco", "number": 2, "position": "DEF", "nationality": "México", "age": 24, "appearances": 1, "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0},
        {"name": "Omar Campos", "number": 3, "position": "DEF", "nationality": "México", "age": 23, "appearances": 19, "goals": 1, "assists": 2, "yellow_cards": 3, "red_cards": 0},
        {"name": "Willer Ditta", "number": 4, "position": "DEF", "nationality": "Colombia", "age": 29, "appearances": 20, "goals": 0, "assists": 2, "yellow_cards": 6, "red_cards": 0},
        {"name": "Jorge Rodarte", "number": 22, "position": "DEF", "nationality": "México", "age": 22, "appearances": 13, "goals": 0, "assists": 1, "yellow_cards": 2, "red_cards": 0},
        {"name": "Gonzalo Piovi", "number": 33, "position": "DEF", "nationality": "Argentina", "age": 31, "appearances": 20, "goals": 0, "assists": 0, "yellow_cards": 6, "red_cards": 0},
        {"name": "Erik Lira", "number": 6, "position": "MED", "nationality": "México", "age": 26, "appearances": 17, "goals": 0, "assists": 0, "yellow_cards": 4, "red_cards": 0},
        {"name": "Agustín Palavecino", "number": 8, "position": "MED", "nationality": "Argentina", "age": 29, "appearances": 20, "goals": 6, "assists": 3, "yellow_cards": 7, "red_cards": 0},
        {"name": "Andres Montaño", "number": 10, "position": "MED", "nationality": "México", "age": 23, "appearances": 12, "goals": 2, "assists": 0, "yellow_cards": 1, "red_cards": 0},
        {"name": "Ángel Márquez", "number": 16, "position": "MED", "nationality": "México", "age": 25, "appearances": 20, "goals": 3, "assists": 0, "yellow_cards": 1, "red_cards": 0},
        {"name": "Amaury García", "number": 17, "position": "MED", "nationality": "México", "age": 24, "appearances": 16, "goals": 0, "assists": 0, "yellow_cards": 2, "red_cards": 0},
        {"name": "Carlos Rodríguez", "number": 19, "position": "MED", "nationality": "México", "age": 29, "appearances": 21, "goals": 4, "assists": 1, "yellow_cards": 1, "red_cards": 0},
        {"name": "Amaury Morales", "number": 31, "position": "MED", "nationality": "México", "age": 20, "appearances": 15, "goals": 0, "assists": 1, "yellow_cards": 0, "red_cards": 0},
        {"name": "Nicolás Ibáñez", "number": 7, "position": "DEL", "nationality": "Argentina", "age": 31, "appearances": 12, "goals": 2, "assists": 1, "yellow_cards": 2, "red_cards": 0},
        {"name": "Osinachi Ebere", "number": 11, "position": "DEL", "nationality": "Nigeria", "age": 28, "appearances": 14, "goals": 4, "assists": 1, "yellow_cards": 1, "red_cards": 0},
        {"name": "Luka Romero", "number": 18, "position": "DEL", "nationality": "Argentina", "age": 21, "appearances": 18, "goals": 1, "assists": 0, "yellow_cards": 2, "red_cards": 0},
        {"name": "José Paradela", "number": 20, "position": "DEL", "nationality": "Argentina", "age": 27, "appearances": 21, "goals": 7, "assists": 5, "yellow_cards": 3, "red_cards": 0},
        {"name": "Gabriel Fernández", "number": 21, "position": "DEL", "nationality": "Uruguay", "age": 32, "appearances": 17, "goals": 5, "assists": 4, "yellow_cards": 0, "red_cards": 1},
        {"name": "Rodolfo Rotondi", "number": 29, "position": "DEL", "nationality": "Argentina", "age": 29, "appearances": 19, "goals": 3, "assists": 4, "yellow_cards": 2, "red_cards": 0},
    ]
    PUMAS = [
        {"name": "Keylor Navas", "number": 1, "position": "POR", "nationality": "Costa Rica", "age": 39, "appearances": 20, "goals": 0, "assists": 0, "yellow_cards": 5, "red_cards": 0},
        {"name": "Pablo Lara", "number": 35, "position": "POR", "nationality": "México", "age": 20, "appearances": 1, "goals": 0, "assists": 0, "yellow_cards": 0, "red_cards": 0},
        {"name": "Pablo Bennevendo", "number": 2, "position": "DEF", "nationality": "México", "age": 26, "appearances": 13, "goals": 0, "assists": 0, "yellow_cards": 1, "red_cards": 0},
        {"name": "Rubén Duarte", "number": 5, "position": "DEF", "nationality": "España", "age": 30, "appearances": 16, "goals": 1, "assists": 0, "yellow_cards": 3, "red_cards": 0},
        {"name": "Nathan Silva", "number": 6, "position": "DEF", "nationality": "Brasil", "age": 29, "appearances": 20, "goals": 1, "assists": 1, "yellow_cards": 4, "red_cards": 1},
        {"name": "Álvaro Angulo", "number": 77, "position": "DEF", "nationality": "Colombia", "age": 29, "appearances": 20, "goals": 3, "assists": 0, "yellow_cards": 3, "red_cards": 1},
        {"name": "Angel Azuaje", "number": 215, "position": "DEF", "nationality": "Venezuela", "age": 21, "appearances": 11, "goals": 0, "assists": 0, "yellow_cards": 2, "red_cards": 0},
        {"name": "Rodrigo López", "number": 7, "position": "MED", "nationality": "México", "age": 24, "appearances": 21, "goals": 0, "assists": 1, "yellow_cards": 4, "red_cards": 0},
        {"name": "Cesar Garza", "number": 14, "position": "MED", "nationality": "México", "age": 20, "appearances": 15, "goals": 0, "assists": 0, "yellow_cards": 3, "red_cards": 0},
        {"name": "Alan Medina", "number": 22, "position": "MED", "nationality": "Uruguay", "age": 28, "appearances": 16, "goals": 1, "assists": 4, "yellow_cards": 3, "red_cards": 0},
        {"name": "Adalberto Carrasquilla", "number": 28, "position": "MED", "nationality": "Panamá", "age": 27, "appearances": 19, "goals": 2, "assists": 2, "yellow_cards": 6, "red_cards": 0},
        {"name": "Jordan Carrillo", "number": 33, "position": "MED", "nationality": "México", "age": 24, "appearances": 20, "goals": 6, "assists": 3, "yellow_cards": 3, "red_cards": 0},
        {"name": "Pedro Vite", "number": 45, "position": "MED", "nationality": "Ecuador", "age": 24, "appearances": 21, "goals": 1, "assists": 1, "yellow_cards": 2, "red_cards": 0},
        {"name": "Guillermo Martínez", "number": 9, "position": "DEL", "nationality": "México", "age": 31, "appearances": 15, "goals": 5, "assists": 0, "yellow_cards": 3, "red_cards": 0},
        {"name": "José Macías", "number": 11, "position": "DEL", "nationality": "México", "age": 26, "appearances": 11, "goals": 4, "assists": 2, "yellow_cards": 0, "red_cards": 0},
        {"name": "Uriel Antuna", "number": 21, "position": "DEL", "nationality": "México", "age": 28, "appearances": 21, "goals": 3, "assists": 3, "yellow_cards": 1, "red_cards": 0},
        {"name": "Juninho", "number": 23, "position": "DEL", "nationality": "Brasil", "age": 29, "appearances": 21, "goals": 8, "assists": 4, "yellow_cards": 1, "red_cards": 0},
        {"name": "Robert Morales", "number": 31, "position": "DEL", "nationality": "Paraguay", "age": 27, "appearances": 21, "goals": 8, "assists": 2, "yellow_cards": 1, "red_cards": 0},
    ]

    caz = await db.teams.find_one({"short_name": "CAZ"})
    pum = await db.teams.find_one({"short_name": "PUM"})
    if not caz or not pum:
        raise HTTPException(status_code=404, detail="No se encontraron los equipos")

    await db.players.delete_many({"team_id": {"$in": [caz["_id"], pum["_id"]]}})
    total = 0
    for p in CRUZ_AZUL:
        await db.players.insert_one({**p, "team_id": caz["_id"], "team_name": "Cruz Azul", "photo": "", "rating": "0", "season": "2025-26", "updated_at": datetime.utcnow()})
        total += 1
    for p in PUMAS:
        await db.players.insert_one({**p, "team_id": pum["_id"], "team_name": "Pumas UNAM", "photo": "", "rating": "0", "season": "2025-26", "updated_at": datetime.utcnow()})
        total += 1

    return {"message": f"✅ {total} jugadores de la Final cargados correctamente", "total": total}


@router.post("/admin/seed-world-cup")
async def seed_world_cup(current_user: dict = Depends(get_current_user)):
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    TEAMS_WC = [
        {"name": "México", "short_name": "MEX", "group": "A", "priority": 1, "shield_url": "https://upload.wikimedia.org/wikipedia/en/thumb/3/3f/Mexico_national_football_team_crest.svg/500px-Mexico_national_football_team_crest.svg.png"},
        {"name": "Sudáfrica", "short_name": "RSA", "group": "A", "priority": 99, "shield_url": "https://flagcdn.com/w160/za.png"},
        {"name": "Corea del Sur", "short_name": "KOR", "group": "A", "priority": 99, "shield_url": "https://flagcdn.com/w160/kr.png"},
        {"name": "Rep. Checa", "short_name": "CZE", "group": "A", "priority": 99, "shield_url": "https://flagcdn.com/w160/cz.png"},
        {"name": "Canadá", "short_name": "CAN", "group": "B", "priority": 99, "shield_url": "https://flagcdn.com/w160/ca.png"},
        {"name": "Bosnia", "short_name": "BIH", "group": "B", "priority": 99, "shield_url": "https://flagcdn.com/w160/ba.png"},
        {"name": "Qatar", "short_name": "QAT", "group": "B", "priority": 99, "shield_url": "https://flagcdn.com/w160/qa.png"},
        {"name": "Suiza", "short_name": "SUI", "group": "B", "priority": 99, "shield_url": "https://flagcdn.com/w160/ch.png"},
        {"name": "Brasil", "short_name": "BRA", "group": "C", "priority": 99, "shield_url": "https://flagcdn.com/w160/br.png"},
        {"name": "Marruecos", "short_name": "MAR", "group": "C", "priority": 99, "shield_url": "https://flagcdn.com/w160/ma.png"},
        {"name": "Haití", "short_name": "HAI", "group": "C", "priority": 99, "shield_url": "https://flagcdn.com/w160/ht.png"},
        {"name": "Escocia", "short_name": "SCO", "group": "C", "priority": 99, "shield_url": "https://flagcdn.com/w160/gb-sct.png"},
        {"name": "USA", "short_name": "USA", "group": "D", "priority": 99, "shield_url": "https://flagcdn.com/w160/us.png"},
        {"name": "Paraguay", "short_name": "PAR", "group": "D", "priority": 99, "shield_url": "https://flagcdn.com/w160/py.png"},
        {"name": "Australia", "short_name": "AUS", "group": "D", "priority": 99, "shield_url": "https://flagcdn.com/w160/au.png"},
        {"name": "Turquía", "short_name": "TUR", "group": "D", "priority": 99, "shield_url": "https://flagcdn.com/w160/tr.png"},
        {"name": "Alemania", "short_name": "GER", "group": "E", "priority": 99, "shield_url": "https://flagcdn.com/w160/de.png"},
        {"name": "Curaçao", "short_name": "CUW", "group": "E", "priority": 99, "shield_url": "https://flagcdn.com/w160/cw.png"},
        {"name": "Costa de Marfil", "short_name": "CIV", "group": "E", "priority": 99, "shield_url": "https://flagcdn.com/w160/ci.png"},
        {"name": "Ecuador", "short_name": "ECU", "group": "E", "priority": 99, "shield_url": "https://flagcdn.com/w160/ec.png"},
        {"name": "Países Bajos", "short_name": "NED", "group": "F", "priority": 99, "shield_url": "https://flagcdn.com/w160/nl.png"},
        {"name": "Japón", "short_name": "JPN", "group": "F", "priority": 99, "shield_url": "https://flagcdn.com/w160/jp.png"},
        {"name": "Suecia", "short_name": "SWE", "group": "F", "priority": 99, "shield_url": "https://flagcdn.com/w160/se.png"},
        {"name": "Túnez", "short_name": "TUN", "group": "F", "priority": 99, "shield_url": "https://flagcdn.com/w160/tn.png"},
        {"name": "Bélgica", "short_name": "BEL", "group": "G", "priority": 99, "shield_url": "https://flagcdn.com/w160/be.png"},
        {"name": "Egipto", "short_name": "EGY", "group": "G", "priority": 99, "shield_url": "https://flagcdn.com/w160/eg.png"},
        {"name": "Irán", "short_name": "IRN", "group": "G", "priority": 99, "shield_url": "https://flagcdn.com/w160/ir.png"},
        {"name": "Nueva Zelanda", "short_name": "NZL", "group": "G", "priority": 99, "shield_url": "https://flagcdn.com/w160/nz.png"},
        {"name": "España", "short_name": "ESP", "group": "H", "priority": 99, "shield_url": "https://flagcdn.com/w160/es.png"},
        {"name": "Cabo Verde", "short_name": "CPV", "group": "H", "priority": 99, "shield_url": "https://flagcdn.com/w160/cv.png"},
        {"name": "Arabia Saudita", "short_name": "KSA", "group": "H", "priority": 99, "shield_url": "https://flagcdn.com/w160/sa.png"},
        {"name": "Uruguay", "short_name": "URU", "group": "H", "priority": 99, "shield_url": "https://flagcdn.com/w160/uy.png"},
        {"name": "Francia", "short_name": "FRA", "group": "I", "priority": 99, "shield_url": "https://flagcdn.com/w160/fr.png"},
        {"name": "Senegal", "short_name": "SEN", "group": "I", "priority": 99, "shield_url": "https://flagcdn.com/w160/sn.png"},
        {"name": "Irak", "short_name": "IRQ", "group": "I", "priority": 99, "shield_url": "https://flagcdn.com/w160/iq.png"},
        {"name": "Noruega", "short_name": "NOR", "group": "I", "priority": 99, "shield_url": "https://flagcdn.com/w160/no.png"},
        {"name": "Argentina", "short_name": "ARG", "group": "J", "priority": 99, "shield_url": "https://flagcdn.com/w160/ar.png"},
        {"name": "Argelia", "short_name": "ALG", "group": "J", "priority": 99, "shield_url": "https://flagcdn.com/w160/dz.png"},
        {"name": "Austria", "short_name": "AUT", "group": "J", "priority": 99, "shield_url": "https://flagcdn.com/w160/at.png"},
        {"name": "Jordania", "short_name": "JOR", "group": "J", "priority": 99, "shield_url": "https://flagcdn.com/w160/jo.png"},
        {"name": "Portugal", "short_name": "POR", "group": "K", "priority": 99, "shield_url": "https://flagcdn.com/w160/pt.png"},
        {"name": "DR Congo", "short_name": "COD", "group": "K", "priority": 99, "shield_url": "https://flagcdn.com/w160/cd.png"},
        {"name": "Uzbekistán", "short_name": "UZB", "group": "K", "priority": 99, "shield_url": "https://flagcdn.com/w160/uz.png"},
        {"name": "Colombia", "short_name": "COL", "group": "K", "priority": 99, "shield_url": "https://flagcdn.com/w160/co.png"},
        {"name": "Inglaterra", "short_name": "ENG", "group": "L", "priority": 99, "shield_url": "https://flagcdn.com/w160/gb-eng.png"},
        {"name": "Croacia", "short_name": "CRO", "group": "L", "priority": 99, "shield_url": "https://flagcdn.com/w160/hr.png"},
        {"name": "Ghana", "short_name": "GHA", "group": "L", "priority": 99, "shield_url": "https://flagcdn.com/w160/gh.png"},
        {"name": "Panamá", "short_name": "PAN", "group": "L", "priority": 99, "shield_url": "https://flagcdn.com/w160/pa.png"},
    ]
    MATCHES_WC = [
        # JORNADA 1
        {"j": 1, "home": "México", "away": "Sudáfrica", "date": "2026-06-11T19:00:00", "venue": "Estadio Azteca"},
        {"j": 1, "home": "Corea del Sur", "away": "Rep. Checa", "date": "2026-06-12T02:00:00", "venue": "Estadio Akron"},
        {"j": 1, "home": "Canadá", "away": "Bosnia", "date": "2026-06-12T19:00:00", "venue": "BMO Field"},
        {"j": 1, "home": "Qatar", "away": "Suiza", "date": "2026-06-13T19:00:00", "venue": "Levi's Stadium"},
        {"j": 1, "home": "Brasil", "away": "Marruecos", "date": "2026-06-13T22:00:00", "venue": "MetLife Stadium"},
        {"j": 1, "home": "Haití", "away": "Escocia", "date": "2026-06-14T01:00:00", "venue": "Gillette Stadium"},
        {"j": 1, "home": "USA", "away": "Paraguay", "date": "2026-06-13T01:00:00", "venue": "SoFi Stadium"},
        {"j": 1, "home": "Australia", "away": "Turquía", "date": "2026-06-14T04:00:00", "venue": "BC Place"},
        {"j": 1, "home": "Alemania", "away": "Curaçao", "date": "2026-06-14T17:00:00", "venue": "NRG Stadium"},
        {"j": 1, "home": "Costa de Marfil", "away": "Ecuador", "date": "2026-06-14T23:00:00", "venue": "Lincoln Financial Field"},
        {"j": 1, "home": "Países Bajos", "away": "Japón", "date": "2026-06-14T20:00:00", "venue": "AT&T Stadium"},
        {"j": 1, "home": "Suecia", "away": "Túnez", "date": "2026-06-15T02:00:00", "venue": "Estadio BBVA"},
        {"j": 1, "home": "Bélgica", "away": "Egipto", "date": "2026-06-15T19:00:00", "venue": "Lumen Field"},
        {"j": 1, "home": "Irán", "away": "Nueva Zelanda", "date": "2026-06-16T01:00:00", "venue": "SoFi Stadium"},
        {"j": 1, "home": "España", "away": "Cabo Verde", "date": "2026-06-15T16:00:00", "venue": "Mercedes-Benz Stadium"},
        {"j": 1, "home": "Arabia Saudita", "away": "Uruguay", "date": "2026-06-15T22:00:00", "venue": "Hard Rock Stadium"},
        {"j": 1, "home": "Francia", "away": "Senegal", "date": "2026-06-16T19:00:00", "venue": "MetLife Stadium"},
        {"j": 1, "home": "Irak", "away": "Noruega", "date": "2026-06-16T22:00:00", "venue": "Gillette Stadium"},
        {"j": 1, "home": "Argentina", "away": "Argelia", "date": "2026-06-17T01:00:00", "venue": "Arrowhead Stadium"},
        {"j": 1, "home": "Austria", "away": "Jordania", "date": "2026-06-17T04:00:00", "venue": "Levi's Stadium"},
        {"j": 1, "home": "Portugal", "away": "DR Congo", "date": "2026-06-17T17:00:00", "venue": "NRG Stadium"},
        {"j": 1, "home": "Uzbekistán", "away": "Colombia", "date": "2026-06-18T02:00:00", "venue": "Estadio Azteca"},
        {"j": 1, "home": "Inglaterra", "away": "Croacia", "date": "2026-06-17T20:00:00", "venue": "AT&T Stadium"},
        {"j": 1, "home": "Ghana", "away": "Panamá", "date": "2026-06-17T23:00:00", "venue": "BMO Field"},
        # JORNADA 2
        {"j": 2, "home": "Rep. Checa", "away": "Sudáfrica", "date": "2026-06-18T16:00:00", "venue": "Mercedes-Benz Stadium"},
        {"j": 2, "home": "México", "away": "Corea del Sur", "date": "2026-06-19T01:00:00", "venue": "Estadio Akron"},
        {"j": 2, "home": "Suiza", "away": "Bosnia", "date": "2026-06-18T19:00:00", "venue": "SoFi Stadium"},
        {"j": 2, "home": "Canadá", "away": "Qatar", "date": "2026-06-18T22:00:00", "venue": "BC Place"},
        {"j": 2, "home": "Escocia", "away": "Marruecos", "date": "2026-06-19T22:00:00", "venue": "Gillette Stadium"},
        {"j": 2, "home": "Brasil", "away": "Haití", "date": "2026-06-20T00:30:00", "venue": "Lincoln Financial Field"},
        {"j": 2, "home": "USA", "away": "Australia", "date": "2026-06-19T19:00:00", "venue": "Lumen Field"},
        {"j": 2, "home": "Turquía", "away": "Paraguay", "date": "2026-06-20T03:00:00", "venue": "Levi's Stadium"},
        {"j": 2, "home": "Alemania", "away": "Costa de Marfil", "date": "2026-06-20T20:00:00", "venue": "BMO Field"},
        {"j": 2, "home": "Ecuador", "away": "Curaçao", "date": "2026-06-21T00:00:00", "venue": "Arrowhead Stadium"},
        {"j": 2, "home": "Países Bajos", "away": "Suecia", "date": "2026-06-20T17:00:00", "venue": "NRG Stadium"},
        {"j": 2, "home": "Túnez", "away": "Japón", "date": "2026-06-21T04:00:00", "venue": "Estadio BBVA"},
        {"j": 2, "home": "Bélgica", "away": "Irán", "date": "2026-06-21T19:00:00", "venue": "SoFi Stadium"},
        {"j": 2, "home": "Nueva Zelanda", "away": "Egipto", "date": "2026-06-22T01:00:00", "venue": "BC Place"},
        {"j": 2, "home": "España", "away": "Arabia Saudita", "date": "2026-06-21T16:00:00", "venue": "Mercedes-Benz Stadium"},
        {"j": 2, "home": "Uruguay", "away": "Cabo Verde", "date": "2026-06-21T22:00:00", "venue": "Hard Rock Stadium"},
        {"j": 2, "home": "Francia", "away": "Irak", "date": "2026-06-22T21:00:00", "venue": "Lincoln Financial Field"},
        {"j": 2, "home": "Noruega", "away": "Senegal", "date": "2026-06-23T00:00:00", "venue": "MetLife Stadium"},
        {"j": 2, "home": "Argentina", "away": "Austria", "date": "2026-06-22T17:00:00", "venue": "AT&T Stadium"},
        {"j": 2, "home": "Jordania", "away": "Argelia", "date": "2026-06-23T03:00:00", "venue": "Levi's Stadium"},
        {"j": 2, "home": "Portugal", "away": "Uzbekistán", "date": "2026-06-23T17:00:00", "venue": "NRG Stadium"},
        {"j": 2, "home": "Colombia", "away": "DR Congo", "date": "2026-06-24T02:00:00", "venue": "Estadio Akron"},
        {"j": 2, "home": "Inglaterra", "away": "Ghana", "date": "2026-06-23T20:00:00", "venue": "Gillette Stadium"},
        {"j": 2, "home": "Panamá", "away": "Croacia", "date": "2026-06-23T23:00:00", "venue": "BMO Field"},
        # JORNADA 3
        {"j": 3, "home": "Rep. Checa", "away": "México", "date": "2026-06-25T01:00:00", "venue": "Estadio Azteca"},
        {"j": 3, "home": "Sudáfrica", "away": "Corea del Sur", "date": "2026-06-25T01:00:00", "venue": "Estadio BBVA"},
        {"j": 3, "home": "Suiza", "away": "Canadá", "date": "2026-06-24T19:00:00", "venue": "BC Place"},
        {"j": 3, "home": "Bosnia", "away": "Qatar", "date": "2026-06-24T19:00:00", "venue": "Lumen Field"},
        {"j": 3, "home": "Escocia", "away": "Brasil", "date": "2026-06-24T22:00:00", "venue": "Hard Rock Stadium"},
        {"j": 3, "home": "Marruecos", "away": "Haití", "date": "2026-06-24T22:00:00", "venue": "Mercedes-Benz Stadium"},
        {"j": 3, "home": "Turquía", "away": "USA", "date": "2026-06-26T01:00:00", "venue": "SoFi Stadium"},
        {"j": 3, "home": "Paraguay", "away": "Australia", "date": "2026-06-26T01:00:00", "venue": "Levi's Stadium"},
        {"j": 3, "home": "Curaçao", "away": "Costa de Marfil", "date": "2026-06-25T20:00:00", "venue": "Lincoln Financial Field"},
        {"j": 3, "home": "Ecuador", "away": "Alemania", "date": "2026-06-25T20:00:00", "venue": "MetLife Stadium"},
        {"j": 3, "home": "Japón", "away": "Suecia", "date": "2026-06-25T23:00:00", "venue": "AT&T Stadium"},
        {"j": 3, "home": "Túnez", "away": "Países Bajos", "date": "2026-06-25T23:00:00", "venue": "Arrowhead Stadium"},
        {"j": 3, "home": "Egipto", "away": "Irán", "date": "2026-06-27T03:00:00", "venue": "Lumen Field"},
        {"j": 3, "home": "Nueva Zelanda", "away": "Bélgica", "date": "2026-06-27T03:00:00", "venue": "BC Place"},
        {"j": 3, "home": "Cabo Verde", "away": "Arabia Saudita", "date": "2026-06-27T00:00:00", "venue": "NRG Stadium"},
        {"j": 3, "home": "Uruguay", "away": "España", "date": "2026-06-27T01:00:00", "venue": "Estadio Akron"},
        {"j": 3, "home": "Noruega", "away": "Francia", "date": "2026-06-26T19:00:00", "venue": "Gillette Stadium"},
        {"j": 3, "home": "Senegal", "away": "Irak", "date": "2026-06-26T19:00:00", "venue": "BMO Field"},
        {"j": 3, "home": "Argelia", "away": "Austria", "date": "2026-06-28T02:00:00", "venue": "Arrowhead Stadium"},
        {"j": 3, "home": "Jordania", "away": "Argentina", "date": "2026-06-28T02:00:00", "venue": "AT&T Stadium"},
        {"j": 3, "home": "Colombia", "away": "Portugal", "date": "2026-06-28T23:30:00", "venue": "Hard Rock Stadium"},
        {"j": 3, "home": "DR Congo", "away": "Uzbekistán", "date": "2026-06-28T23:30:00", "venue": "Mercedes-Benz Stadium"},
        {"j": 3, "home": "Panamá", "away": "Inglaterra", "date": "2026-06-27T21:00:00", "venue": "MetLife Stadium"},
        {"j": 3, "home": "Croacia", "away": "Ghana", "date": "2026-06-27T21:00:00", "venue": "Lincoln Financial Field"},
    ]
    JORNADAS_WC = [
        {"wn": 1, "title": "Fase de Grupos — Jornada 1", "start": "2026-06-11", "end": "2026-06-17"},
        {"wn": 2, "title": "Fase de Grupos — Jornada 2", "start": "2026-06-18", "end": "2026-06-23"},
        {"wn": 3, "title": "Fase de Grupos — Jornada 3", "start": "2026-06-24", "end": "2026-06-27"},
        {"wn": 4, "title": "Round of 32",       "start": "2026-06-28", "end": "2026-07-03"},
        {"wn": 5, "title": "Round of 16",       "start": "2026-07-04", "end": "2026-07-07"},
        {"wn": 6, "title": "Cuartos de Final",  "start": "2026-07-09", "end": "2026-07-11"},
        {"wn": 7, "title": "Semifinales",       "start": "2026-07-14", "end": "2026-07-15"},
        {"wn": 8, "title": "Final Mundial",     "start": "2026-07-19", "end": "2026-07-19"},
    ]

    await db.teams.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})
    await db.players.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})
    await db.jornadas.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})
    await db.matches.update_many({"competition": {"$exists": False}}, {"$set": {"competition": "liga_mx"}})

    await db.config.update_one(
        {"key": "active_competition"},
        {"$set": {"key": "active_competition", "value": "liga_mx"}},
        upsert=True
    )

    await db.teams.delete_many({"competition": "world_cup_2026"})
    await db.jornadas.delete_many({"competition": "world_cup_2026"})
    await db.matches.delete_many({"competition": "world_cup_2026"})

    team_ids: dict = {}
    for t in TEAMS_WC:
        result = await db.teams.insert_one({
            "name": t["name"], "short_name": t["short_name"],
            "shield_url": t["shield_url"], "competition": "world_cup_2026",
            "group": t["group"], "priority": t["priority"],
            "created_at": datetime.utcnow()
        })
        team_ids[t["name"]] = result.inserted_id

    jornada_ids: dict = {}
    for j in JORNADAS_WC:
        result = await db.jornadas.insert_one({
            "week_number": j["wn"], "title": j["title"],
            "type": "world_cup", "competition": "world_cup_2026",
            "status": "upcoming", "is_active": False, "processed": False,
            "start_date": datetime.fromisoformat(j["start"]),
            "end_date": datetime.fromisoformat(j["end"]),
            "created_at": datetime.utcnow()
        })
        jornada_ids[j["wn"]] = result.inserted_id

    matches_count = 0
    for m in MATCHES_WC:
        ht = await db.teams.find_one({"name": m["home"], "competition": "world_cup_2026"})
        at = await db.teams.find_one({"name": m["away"], "competition": "world_cup_2026"})
        if ht and at:
            await db.matches.insert_one({
                "jornada_id": jornada_ids[m["j"]],
                "home_team_id": ht["_id"], "away_team_id": at["_id"],
                "home_team_name": m["home"], "away_team_name": m["away"],
                "home_score": None, "away_score": None,
                "status": "upcoming", "match_date": datetime.fromisoformat(m["date"]),
                "venue": m["venue"], "competition": "world_cup_2026",
                "created_at": datetime.utcnow()
            })
            matches_count += 1

    return {
        "message": "✅ Mundial 2026 cargado correctamente",
        "teams": len(TEAMS_WC),
        "jornadas": len(JORNADAS_WC),
        "matches": matches_count
    }


@router.post("/admin/seed-world-cup-players")
async def seed_world_cup_players(current_user: dict = Depends(get_current_user)):
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    await db.players.delete_many({"competition": "world_cup_2026"})
    inserted = 0
    skipped_teams = []

    for team_name, squad in WC_SQUADS.items():
        team = await db.teams.find_one({"name": team_name, "competition": "world_cup_2026"})
        if not team:
            skipped_teams.append(team_name)
            continue
        for p in squad:
            await db.players.insert_one({
                "name": p["name"], "team_id": team["_id"], "team_name": team_name,
                "position": p["position"], "number": p["number"],
                "competition": "world_cup_2026",
                "stats": {"minutes_played": 0, "goals": 0, "assists": 0, "saves": 0,
                          "clean_sheets": 0, "defensive_actions": 0,
                          "yellow_cards": 0, "red_cards": 0},
                "created_at": datetime.utcnow()
            })
            inserted += 1

    return {
        "message": f"✅ Plantillas del Mundial cargadas: {inserted} jugadores de {len(WC_SQUADS) - len(skipped_teams)} selecciones",
        "players_inserted": inserted,
        "teams_loaded": len(WC_SQUADS) - len(skipped_teams),
        "skipped_teams": skipped_teams
    }


@router.post("/admin/activate-competition")
async def activate_competition(body: dict, current_user: dict = Depends(get_current_user)):
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")
    competition = body.get("competition")
    if competition not in ["liga_mx", "world_cup_2026"]:
        raise HTTPException(status_code=400, detail="Competición inválida")
    await db.config.update_one(
        {"key": "active_competition"},
        {"$set": {"value": competition}},
        upsert=True
    )
    return {"message": f"✅ Competición activa: {competition}"}
