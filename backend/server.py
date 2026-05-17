from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from real_liga_mx_data import LIGA_MX_TEAMS, CLAUSURA_2026_DATES, CLAUSURA_2026_J13_MATCHES, LIGUILLA_CLAUSURA_2026_TEAMS
import bcrypt
import jwt
from bson import ObjectId
import httpx
from services.scores_service import get_match_results as _svc_get_match_results
from services.player_stats_service import get_player_stats as _svc_get_player_stats

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'quiniela_db')]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 días

# Create the main app
app = FastAPI(title="Quiniela Liga MX API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ MODELS ============

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    display_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    avatar_base64: Optional[str] = None
    total_points: int = 0
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class RecoverPasswordRequest(BaseModel):
    email: EmailStr

# ============ HELPER FUNCTIONS ============

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ha expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado"
        )
    
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """Optional auth — retorna None si no hay token en lugar de lanzar error."""
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        return await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None

def serialize_user(user: dict) -> UserResponse:
    """Serialize user document to response model"""
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        display_name=user["display_name"],
        avatar_base64=user.get("avatar_base64"),
        total_points=user.get("total_points", 0),
        created_at=user["created_at"]
    )

# ============ AUTH ROUTES ============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register a new user"""
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado"
        )
    
    # Create new user
    user_dict = {
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "display_name": user_data.display_name,
        "avatar_base64": None,
        "total_points": 0,
        "created_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    # Award first login achievement
    await award_achievement(result.inserted_id, "first_login")
    
    # Create access token
    access_token = create_access_token({"sub": str(result.inserted_id)})
    
    logger.info(f"New user registered: {user_data.email}")
    
    return TokenResponse(
        access_token=access_token,
        user=serialize_user(user_dict)
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login user"""
    # Find user
    user = await db.users.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # Create access token
    access_token = create_access_token({"sub": str(user["_id"])})
    
    # Veteran: 30 días en la app
    if user.get("created_at"):
        days = (datetime.utcnow() - user["created_at"]).days
        if days >= 30:
            await award_achievement(user["_id"], "veteran")
    
    logger.info(f"User logged in: {credentials.email}")
    
    return TokenResponse(
        access_token=access_token,
        user=serialize_user(user)
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return serialize_user(current_user)

@api_router.post("/auth/recover-password")
async def recover_password(request: RecoverPasswordRequest):
    """Send password recovery email (mock for now)"""
    user = await db.users.find_one({"email": request.email})
    if not user:
        # Don't reveal if email exists
        return {"message": "Si el correo existe, recibirás instrucciones para recuperar tu contraseña"}
    
    # TODO: Implement email sending
    logger.info(f"Password recovery requested for: {request.email}")
    
    return {"message": "Si el correo existe, recibirás instrucciones para recuperar tu contraseña"}

# ============ ADMIN/SEED ROUTES ============

@api_router.post("/admin/seed-teams")
async def seed_teams():
    """Seed Liga MX teams (mock data)"""
    teams_data = [
        {"name": "Club América", "short_name": "AME", "shield_url": "https://via.placeholder.com/100/FFD700/000000?text=AME"},
        {"name": "Guadalajara", "short_name": "GDL", "shield_url": "https://via.placeholder.com/100/FF0000/FFFFFF?text=GDL"},
        {"name": "Cruz Azul", "short_name": "CAZ", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=CAZ"},
        {"name": "Tigres UANL", "short_name": "TIG", "shield_url": "https://via.placeholder.com/100/FFD700/000000?text=TIG"},
        {"name": "Monterrey", "short_name": "MTY", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=MTY"},
        {"name": "Pumas UNAM", "short_name": "PUM", "shield_url": "https://via.placeholder.com/100/003D79/FFD700?text=PUM"},
        {"name": "Santos Laguna", "short_name": "SAN", "shield_url": "https://via.placeholder.com/100/00A551/FFFFFF?text=SAN"},
        {"name": "Toluca", "short_name": "TOL", "shield_url": "https://via.placeholder.com/100/DC143C/FFFFFF?text=TOL"},
        {"name": "León", "short_name": "LEO", "shield_url": "https://via.placeholder.com/100/00A551/FFFFFF?text=LEO"},
        {"name": "Atlas", "short_name": "ATL", "shield_url": "https://via.placeholder.com/100/DC143C/000000?text=ATL"},
        {"name": "Pachuca", "short_name": "PAC", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=PAC"},
        {"name": "Tijuana", "short_name": "TIJ", "shield_url": "https://via.placeholder.com/100/DC143C/000000?text=TIJ"},
        {"name": "Necaxa", "short_name": "NEC", "shield_url": "https://via.placeholder.com/100/DC143C/FFFFFF?text=NEC"},
        {"name": "Querétaro", "short_name": "QRO", "shield_url": "https://via.placeholder.com/100/000000/0047AB?text=QRO"},
        {"name": "Mazatlán", "short_name": "MAZ", "shield_url": "https://via.placeholder.com/100/663399/FFFFFF?text=MAZ"},
        {"name": "Puebla", "short_name": "PUE", "shield_url": "https://via.placeholder.com/100/0047AB/FFFFFF?text=PUE"},
        {"name": "Juárez", "short_name": "JUA", "shield_url": "https://via.placeholder.com/100/008000/FFFFFF?text=JUA"},
        {"name": "Atlético San Luis", "short_name": "ASL", "shield_url": "https://via.placeholder.com/100/DC143C/FFFFFF?text=ASL"},
    ]
    
    # Clear existing teams
    await db.teams.delete_many({})
    
    # Insert teams
    for team in teams_data:
        team["created_at"] = datetime.utcnow()
    
    result = await db.teams.insert_many(teams_data)
    
    logger.info(f"Seeded {len(result.inserted_ids)} teams")
    
    return {"message": f"Se crearon {len(result.inserted_ids)} equipos", "count": len(result.inserted_ids)}

@api_router.post("/admin/seed-jornada")
async def seed_current_jornada():
    """Create current jornada with matches - auto-increments week_number"""
    # Get all teams
    teams = await db.teams.find().to_list(100)
    if len(teams) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes crear los equipos usando /api/admin/seed-teams"
        )
    
    # Find the highest week_number to auto-increment
    last_jornada = await db.jornadas.find_one(sort=[("week_number", -1)])
    next_week = (last_jornada["week_number"] + 1) if last_jornada else 1
    
    # Deactivate any currently active jornada
    await db.jornadas.update_many(
        {"is_active": True},
        {"$set": {"is_active": False, "status": "finished"}}
    )
    
    # Create jornada with robust state fields
    jornada_data = {
        "week_number": next_week,
        "start_date": datetime.utcnow() + timedelta(days=2),
        "end_date": datetime.utcnow() + timedelta(days=4),
        "status": "upcoming",  # upcoming, in_progress, finished
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    jornada_result = await db.jornadas.insert_one(jornada_data)
    jornada_id = jornada_result.inserted_id
    
    # Create matches (9 matches for 18 teams) - shuffle teams for variety
    import random
    shuffled_teams = list(teams)
    random.shuffle(shuffled_teams)
    
    matches = []
    for i in range(0, min(18, len(shuffled_teams)), 2):
        if i + 1 < len(shuffled_teams):
            match = {
                "jornada_id": jornada_id,
                "home_team_id": shuffled_teams[i]["_id"],
                "away_team_id": shuffled_teams[i + 1]["_id"],
                "start_at": datetime.utcnow() + timedelta(days=2, hours=i),
                "status": "scheduled",  # scheduled, live, finished
                "home_score": None,
                "away_score": None,
                "created_at": datetime.utcnow()
            }
            matches.append(match)
    
    if matches:
        await db.matches.insert_many(matches)
    
    logger.info(f"Created jornada {next_week} (is_active=True) with {len(matches)} matches")
    
    return {
        "message": f"Se creó la jornada {next_week} con {len(matches)} partidos (activa)",
        "jornada_id": str(jornada_id),
        "week_number": next_week,
        "matches_count": len(matches)
    }

@api_router.post("/admin/seed-season")
async def seed_full_season():
    """Create multiple jornadas for a full season (17 jornadas)"""
    teams = await db.teams.find().to_list(100)
    if len(teams) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes crear los equipos usando /api/admin/seed-teams"
        )
    
    import random
    
    # Delete existing jornadas and matches
    await db.jornadas.delete_many({})
    await db.matches.delete_many({})
    
    created_jornadas = []
    now = datetime.utcnow()
    ACTIVE_WEEK = 13  # Clausura 2026 — Jornada 13 activa (18-20 abril 2026)

    # Construir lookup de equipos por nombre para J13
    teams_by_name = {t["name"]: t["_id"] for t in teams}

    for week in range(1, 18):  # 17 jornadas
        # Usar fechas reales del Clausura 2026
        week_start = CLAUSURA_2026_DATES.get(week, now + timedelta(weeks=week - ACTIVE_WEEK))
        week_end   = week_start + timedelta(days=7)

        is_past    = week < ACTIVE_WEEK
        is_current = week == ACTIVE_WEEK
        week_status    = "finished" if is_past else ("in_progress" if is_current else "upcoming")
        match_status_val = "finished" if is_past else "scheduled"

        jornada_data = {
            "week_number": week,
            "start_date":  week_start,
            "end_date":    week_end,
            "status":      week_status,
            "is_active":   is_current,
            "created_at":  now
        }

        jornada_result = await db.jornadas.insert_one(jornada_data)
        jornada_id = jornada_result.inserted_id

        # ── Jornada 13: partidos reales del Clausura 2026 ──
        if is_current:
            matches = []
            for (home_name, away_name, match_dt) in CLAUSURA_2026_J13_MATCHES:
                home_id = teams_by_name.get(home_name)
                away_id = teams_by_name.get(away_name)
                if home_id and away_id:
                    matches.append({
                        "jornada_id": jornada_id,
                        "home_team_id": home_id,
                        "away_team_id": away_id,
                        "start_at": match_dt,
                        "status":   "scheduled",
                        "home_score": None,
                        "away_score": None,
                        "created_at": now
                    })
        else:
            # ── Otras jornadas: sorteo aleatorio ──
            shuffled_teams = list(teams)
            random.shuffle(shuffled_teams)
            matches = []
            for i in range(0, min(18, len(shuffled_teams)), 2):
                if i + 1 < len(shuffled_teams):
                    matches.append({
                        "jornada_id": jornada_id,
                        "home_team_id": shuffled_teams[i]["_id"],
                        "away_team_id": shuffled_teams[i + 1]["_id"],
                        "start_at": week_start + timedelta(hours=i),
                        "status":   match_status_val,
                        "home_score": None,
                        "away_score": None,
                        "created_at": now
                    })

        if matches:
            await db.matches.insert_many(matches)

        created_jornadas.append({
            "week_number": week,
            "jornada_id": str(jornada_id),
            "is_active":  is_current,
            "status":     week_status,
            "matches_count": len(matches)
        })
    
    logger.info(f"Created full season with {len(created_jornadas)} jornadas")
    
    return {
        "message": f"Se crearon {len(created_jornadas)} jornadas para la temporada completa",
        "jornadas": created_jornadas
    }


@api_router.post("/admin/reset-jornada")
async def reset_jornada(week: int = None):
    """
    Utilidad para demos y pruebas.
    - Sin parámetros: cierra la jornada activa y activa la siguiente.
    - ?week=N: activa directamente la jornada N (desactiva cualquier otra).
    """
    now = datetime.utcnow()

    if week is not None:
        # Modo directo: activar jornada específica
        target = await db.jornadas.find_one({"week_number": week})
        if not target:
            raise HTTPException(
                status_code=404,
                detail=f"Jornada {week} no encontrada"
            )
        # Desactivar todas
        await db.jornadas.update_many({}, {"$set": {"is_active": False}})
        # Activar la pedida
        await db.jornadas.update_one(
            {"_id": target["_id"]},
            {"$set": {
                "is_active": True,
                "status": "in_progress",
                "start_date": now,
                "end_date": now + timedelta(days=7)
            }}
        )
        logger.info(f"Admin reset-jornada: jornada {week} activada directamente")
        return {
            "message": f"✅ Jornada {week} activada",
            "week_number": week,
            "jornada_id": str(target["_id"])
        }

    # Modo avance: cerrar activa → activar siguiente
    current = await db.jornadas.find_one({"is_active": True})
    if not current:
        # Fallback: buscar la de menor week_number con status != finished
        current = await db.jornadas.find_one(
            {"status": {"$ne": "finished"}},
            sort=[("week_number", 1)]
        )
    if not current:
        raise HTTPException(
            status_code=404,
            detail="No hay jornadas disponibles. Ejecuta /api/admin/seed-season primero."
        )

    closed_week = current["week_number"]

    # Cerrar jornada actual
    await db.jornadas.update_one(
        {"_id": current["_id"]},
        {"$set": {"is_active": False, "status": "finished"}}
    )

    # Buscar y activar la siguiente
    next_j = await db.jornadas.find_one({"week_number": closed_week + 1})
    if not next_j:
        raise HTTPException(
            status_code=404,
            detail=f"No hay jornada después de la {closed_week}. Esa era la última."
        )

    await db.jornadas.update_one(
        {"_id": next_j["_id"]},
        {"$set": {
            "is_active": True,
            "status": "in_progress",
            "start_date": now,
            "end_date": now + timedelta(days=7)
        }}
    )

    logger.info(f"Admin reset-jornada: {closed_week} → {closed_week + 1}")
    return {
        "message": f"✅ Jornada {closed_week} cerrada → Jornada {closed_week + 1} activa",
        "closed_week": closed_week,
        "active_week": closed_week + 1,
        "jornada_id": str(next_j["_id"])
    }


# ─────────────────────────────────────────────────────────────────────────
#  LIGUILLA CLAUSURA 2026
# ─────────────────────────────────────────────────────────────────────────

# ESPN → DB name mapping (names that differ)
_ESPN_TO_DB: dict = {
    "América": "Club América",
    "Atlético de San Luis": "Atlético San Luis",
    "San Luis": "Atlético San Luis",
    "Xolos": "Tijuana",
}

# Module-level cache for ESPN standings (1 hour TTL)
_espn_cache: dict = {"data": None, "fetched_at": None}
_ESPN_CACHE_TTL = 3600  # seconds


async def _fetch_espn_standings() -> Optional[List[dict]]:
    """Fetch Liga MX top-8 from ESPN API; returns list of dicts or None on failure."""
    global _espn_cache
    now = datetime.utcnow()

    # Check cache
    if _espn_cache["data"] and _espn_cache["fetched_at"]:
        age = (now - _espn_cache["fetched_at"]).total_seconds()
        if age < _ESPN_CACHE_TTL:
            logger.info(f"ESPN cache hit (age {age:.0f}s)")
            return _espn_cache["data"]

    try:
        url = "https://site.api.espn.com/apis/v2/sports/soccer/mex.1/standings"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            logger.warning(f"ESPN API → {resp.status_code}")
            return None

        data = resp.json()
        entries = data["children"][0]["standings"]["entries"]
        top8 = []
        for i, entry in enumerate(entries[:8]):
            team = entry["team"]
            espn_name = team.get("displayName", "")
            db_name = _ESPN_TO_DB.get(espn_name, espn_name)
            top8.append({"position": i + 1, "espn_name": espn_name, "db_name": db_name})

        _espn_cache["data"] = top8
        _espn_cache["fetched_at"] = now
        logger.info(f"✅ ESPN standings: {[t['espn_name'] for t in top8]}")
        return top8

    except Exception as exc:
        logger.error(f"❌ ESPN standings error: {exc}")
        return None

@api_router.get("/liguilla/bracket")
async def get_liguilla_bracket(current_user: dict = Depends(get_optional_user)):
    """Retorna la estructura del bracket de liguilla con los 8 equipos clasificados.
    Intenta obtener la tabla en vivo desde la ESPN API; si falla usa la lista provisional hardcodeada.
    """
    is_provisional = True
    teams_data = []

    # ── Intento 1: ESPN API (datos en vivo) ──────────────────────────────
    espn_top8 = await _fetch_espn_standings()
    if espn_top8:
        for entry in espn_top8:
            # Buscar en DB por nombre exacto, luego parcial
            team = await db.teams.find_one({"name": entry["db_name"]})
            if not team:
                team = await db.teams.find_one(
                    {"name": {"$regex": entry["db_name"][:4], "$options": "i"}}
                )
            if team:
                teams_data.append({
                    "position":  entry["position"],
                    "id":        str(team["_id"]),
                    "name":      team["name"],
                    "short_name": team.get("short_name", team["name"][:3].upper()),
                    "shield_url": team.get("shield_url", ""),
                })
        if len(teams_data) >= 8:
            is_provisional = False
            logger.info("✅ Bracket usando datos ESPN en vivo")
        else:
            logger.warning(f"ESPN incompleto ({len(teams_data)}/8), usando fallback")
            teams_data = []

    # ── Fallback: lista hardcodeada provisional ───────────────────────────
    if not teams_data:
        for entry in LIGUILLA_CLAUSURA_2026_TEAMS:
            team = await db.teams.find_one({"name": entry["name"]})
            if team:
                teams_data.append({
                    "position":  entry["position"],
                    "id":        str(team["_id"]),
                    "name":      team["name"],
                    "short_name": team.get("short_name", team["name"][:3].upper()),
                    "shield_url": team.get("shield_url", ""),
                })
        is_provisional = True

    # Mapear por posición para construir cuartos
    by_pos = {t["position"]: t for t in teams_data}

    # Obtener resultados guardados en DB
    results = await db.liguilla_results.find_one({"temporada": "Clausura 2026"})
    cuartos_winners   = results.get("cuartos_winners", []) if results else []
    semis_left_winner = results.get("semis_left_winner") if results else None
    semis_right_winner= results.get("semis_right_winner") if results else None
    champion          = results.get("champion") if results else None

    # Determinar status
    if champion:
        bracket_status = "finalizado"
    elif semis_left_winner or semis_right_winner:
        bracket_status = "semifinales"
    elif cuartos_winners:
        bracket_status = "semifinales"
    else:
        bracket_status = "cuartos"

    # Buscar equipos semifinalistas en DB
    async def find_team_by_short(short_name):
        if not short_name:
            return None
        t = await db.teams.find_one({"short_name": short_name})
        if not t:
            t = await db.teams.find_one({"name": {"$regex": short_name, "$options": "i"}})
        if t:
            return {
                "id": str(t["_id"]),
                "name": t["name"],
                "short_name": t.get("short_name", short_name),
                "shield_url": t.get("shield_url", ""),
            }
        return {"id": "", "name": short_name, "short_name": short_name, "shield_url": ""}

    # Semifinalistas (ganadores de cuartos)
    semi_left_home  = await find_team_by_short(cuartos_winners[0]) if len(cuartos_winners) > 0 else None
    semi_left_away  = await find_team_by_short(cuartos_winners[1]) if len(cuartos_winners) > 1 else None
    semi_right_home = await find_team_by_short(cuartos_winners[2]) if len(cuartos_winners) > 2 else None
    semi_right_away = await find_team_by_short(cuartos_winners[3]) if len(cuartos_winners) > 3 else None

    # Finalistas
    finalist_left  = await find_team_by_short(semis_left_winner) if semis_left_winner else None
    finalist_right = await find_team_by_short(semis_right_winner) if semis_right_winner else None
    champion_team  = await find_team_by_short(champion) if champion else None

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
        "scoring": {
            "cuartos": 5,
            "semis":   10,
            "campeon": 25,
        },
        "my_prediction": None,
    }

    # Predicción guardada del usuario (si hay sesión)
    if current_user:
        pred = await db.bracket_predictions.find_one({"user_id": current_user["_id"]})
        if pred:
            bracket["my_prediction"] = {
                "cuartos_picks": pred.get("cuartos_picks", []),
                "semis_picks":   pred.get("semis_picks", []),
                "champion":      pred.get("champion"),
            }

    return bracket


@api_router.post("/liguilla/bracket/submit")
async def submit_bracket_prediction(
    prediction: dict,
    current_user: dict = Depends(get_current_user),
):
    """Guarda o actualiza la predicción de bracket del usuario."""
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


@api_router.post("/admin/quiniela/cerrar-jornada/{jornada_id}")
async def close_jornada(jornada_id: str):
    """Admin: Close a jornada and activate the next one"""
    try:
        jornada_oid = ObjectId(jornada_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de jornada inválido")
    
    jornada = await db.jornadas.find_one({"_id": jornada_oid})
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")
    
    current_week = jornada["week_number"]
    
    # Close the current jornada
    await db.jornadas.update_one(
        {"_id": jornada_oid},
        {"$set": {"status": "finished", "is_active": False}}
    )
    
    # Activate the next jornada
    next_jornada = await db.jornadas.find_one(
        {"week_number": current_week + 1}
    )
    
    next_info = None
    if next_jornada:
        await db.jornadas.update_one(
            {"_id": next_jornada["_id"]},
            {"$set": {"status": "upcoming", "is_active": True}}
        )
        next_info = {
            "id": str(next_jornada["_id"]),
            "week_number": next_jornada["week_number"]
        }
        logger.info(f"Closed jornada {current_week}, activated jornada {current_week + 1}")
    else:
        logger.info(f"Closed jornada {current_week}. No next jornada found (season ended)")
    
    return {
        "message": f"Jornada {current_week} cerrada exitosamente",
        "closed_jornada": {
            "id": jornada_id,
            "week_number": current_week
        },
        "next_jornada": next_info
    }


@api_router.post("/admin/sync-fixtures")
async def sync_fixtures():
    """
    Sync Liga MX fixtures from TheSportsDB (ID: 4350).
    Falls back to Clausura 2025 real calendar dates if API is unavailable.
    """
    import httpx

    LEAGUE_ID = "4350"
    BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    # Map TheSportsDB team names -> our DB team names
    NAME_MAP = {
        "CF America": "Club América", "Club América": "Club América", "América": "Club América",
        "CD Guadalajara": "Guadalajara", "Chivas": "Guadalajara", "Guadalajara": "Guadalajara",
        "Cruz Azul": "Cruz Azul",
        "Tigres UANL": "Tigres UANL", "Tigres": "Tigres UANL",
        "CF Monterrey": "Monterrey", "Monterrey": "Monterrey", "Rayados": "Monterrey",
        "UNAM Pumas": "Pumas UNAM", "Pumas UNAM": "Pumas UNAM", "Pumas": "Pumas UNAM",
        "Santos Laguna": "Santos Laguna", "Santos": "Santos Laguna",
        "Deportivo Toluca": "Toluca", "Toluca": "Toluca",
        "Club León": "León", "León": "León", "Leon": "León",
        "Atlas FC": "Atlas", "Atlas": "Atlas",
        "CF Pachuca": "Pachuca", "Pachuca": "Pachuca",
        "Xolos Tijuana": "Tijuana", "FC Tijuana": "Tijuana", "Tijuana": "Tijuana",
        "Club Necaxa": "Necaxa", "Necaxa": "Necaxa",
        "Queretaro": "Querétaro", "Querétaro": "Querétaro",
        "Mazatlan FC": "Mazatlán", "Mazatlán": "Mazatlán",
        "Club Puebla": "Puebla", "Puebla": "Puebla",
        "FC Juarez": "Juárez", "Juárez": "Juárez", "Juarez": "Juárez",
        "Atletico de San Luis": "Atlético San Luis", "Atlético San Luis": "Atlético San Luis",
        "Atletico San Luis": "Atlético San Luis",
    }

    # Clausura 2026 real jornada start dates
    CLAUSURA_2025_DATES = CLAUSURA_2026_DATES

    events_fetched = 0
    matches_updated = 0
    source = "thesportsdb"
    api_error = None

    teams_list = await db.teams.find().to_list(100)
    team_by_name = {t["name"]: t["_id"] for t in teams_list}

    # --- Attempt TheSportsDB ---
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            next_r = await client.get(
                f"{BASE_URL}/eventsnextleague.php?id={LEAGUE_ID}", headers=HEADERS
            )
            past_r = await client.get(
                f"{BASE_URL}/eventspastleague.php?id={LEAGUE_ID}", headers=HEADERS
            )

        all_events = []
        if next_r.status_code == 200 and next_r.text.strip().startswith("{"):
            all_events += (next_r.json().get("events") or [])
        if past_r.status_code == 200 and past_r.text.strip().startswith("{"):
            all_events += (past_r.json().get("results") or [])

        if not all_events:
            raise ValueError(f"No events — HTTP {next_r.status_code} (posiblemente rate-limited)")

        # Verify we got Liga MX events, not another league
        sample_league = (all_events[0].get("strLeague") or "").lower()
        if "mexico" not in sample_league and "liga mx" not in sample_league and "primera" not in sample_league:
            raise ValueError(f"Eventos no son de Liga MX — liga recibida: '{all_events[0].get('strLeague')}'. Usando fallback.")

        events_fetched = len(all_events)
        now = datetime.utcnow()

        for ev in all_events:
            home_raw = ev.get("strHomeTeam", "")
            away_raw = ev.get("strAwayTeam", "")
            home_name = NAME_MAP.get(home_raw, home_raw)
            away_name = NAME_MAP.get(away_raw, away_raw)
            home_id = team_by_name.get(home_name)
            away_id = team_by_name.get(away_name)
            if not home_id or not away_id:
                continue

            date_str = ev.get("dateEvent") or ""
            time_str = (ev.get("strTime") or "00:00:00")[:5]
            start_at = None
            if date_str:
                try:
                    start_at = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                except Exception:
                    pass

            home_sc = ev.get("intHomeScore")
            away_sc = ev.get("intAwayScore")
            str_status = (ev.get("strStatus") or "").lower()
            if home_sc is not None and away_sc is not None:
                match_status = "finished"
            elif "live" in str_status or "in progress" in str_status:
                match_status = "live"
            else:
                match_status = "upcoming"

            round_num = ev.get("intRound")
            match_filter: dict = {"home_team_id": home_id, "away_team_id": away_id}
            if round_num:
                try:
                    j = await db.jornadas.find_one({"week_number": int(round_num)})
                    if j:
                        match_filter["jornada_id"] = j["_id"]
                except Exception:
                    pass

            update_fields: dict = {"status": match_status}
            if start_at:
                update_fields["start_at"] = start_at
            if home_sc is not None:
                update_fields["home_score"] = int(home_sc)
            if away_sc is not None:
                update_fields["away_score"] = int(away_sc)

            res = await db.matches.update_one(match_filter, {"$set": update_fields})
            if res.modified_count:
                matches_updated += 1

        logger.info(f"sync-fixtures: TheSportsDB OK — {events_fetched} eventos, {matches_updated} actualizados")

    except Exception as exc:
        source = "fallback_clausura2025"
        api_error = str(exc)
        logger.warning(f"sync-fixtures: TheSportsDB falló ({exc}). Usando fallback Clausura 2025.")

        now = datetime.utcnow()
        jornadas = await db.jornadas.find().sort("week_number", 1).to_list(17)

        for j in jornadas:
            week = j["week_number"]
            base_date = CLAUSURA_2025_DATES.get(week, datetime(2025, 1, 10) + timedelta(weeks=week - 1))
            matches = await db.matches.find({"jornada_id": j["_id"]}).to_list(20)

            for i, m in enumerate(matches):
                day_offset = i % 3
                hour = 19 + (i % 3)
                match_date = base_date + timedelta(days=day_offset, hours=hour)
                st = "finished" if match_date < now else "upcoming"
                update: dict = {"start_at": match_date, "status": st}
                await db.matches.update_one({"_id": m["_id"]}, {"$set": update})
                matches_updated += 1

    return {
        "message": f"✅ Sync completado — {matches_updated} partidos actualizados",
        "source": source,
        "events_fetched": events_fetched,
        "matches_updated": matches_updated,
        "api_error": api_error,
    }


@api_router.get("/admin/jornadas")
async def list_all_jornadas():
    """Admin: List all jornadas with their status"""
    jornadas = await db.jornadas.find().sort("week_number", 1).to_list(100)
    result = []
    for j in jornadas:
        result.append({
            "id": str(j["_id"]),
            "week_number": j["week_number"],
            "start_date": j["start_date"].isoformat() if j.get("start_date") else None,
            "end_date": j["end_date"].isoformat() if j.get("end_date") else None,
            "status": j.get("status", "unknown"),
            "is_active": j.get("is_active", False)
        })
    return {"jornadas": result, "total": len(result)}

@api_router.get("/teams")
async def get_teams():
    """Get all teams"""
    teams = await db.teams.find().to_list(100)
    for team in teams:
        team["id"] = str(team.pop("_id"))
    return {"teams": teams}

@api_router.get("/jornadas/current")
async def get_current_jornada():
    """Get current active jornada with matches - implements automatic state transition"""
    now = datetime.utcnow()
    
    # Step 1: Find jornada with is_active = true
    jornada = await db.jornadas.find_one({"is_active": True})
    
    # Step 2: If active jornada exists and its end_date has passed, transition to next
    if jornada and jornada.get("end_date") and jornada["end_date"] < now:
        logger.info(f"Jornada {jornada['week_number']} expirada (end_date: {jornada['end_date']}). Transitando...")

        # ── Auto-process si no fue procesada antes ────────────────────────
        if not jornada.get("processed", False):
            logger.info(
                f"Jornada {jornada['week_number']} no procesada. "
                f"Ejecutando process_jornada automáticamente..."
            )
            try:
                proc_result = await _process_jornada_core(str(jornada["_id"]))
                logger.info(
                    f"✅ Auto-proceso completado: "
                    f"scores={proc_result.get('scores_updated')}, "
                    f"quiniela={proc_result.get('quiniela_updated')} usuarios, "
                    f"fantasy={proc_result.get('fantasy_updated')} equipos, "
                    f"logros={proc_result.get('achievements_awarded')}"
                )
            except Exception as proc_exc:
                logger.error(f"❌ Auto-proceso falló: {proc_exc}")

        # Close expired jornada
        await db.jornadas.update_one(
            {"_id": jornada["_id"]},
            {"$set": {"status": "finished", "is_active": False}}
        )
        
        # Activate next jornada
        next_jornada = await db.jornadas.find_one(
            {"week_number": jornada["week_number"] + 1}
        )
        
        if next_jornada:
            await db.jornadas.update_one(
                {"_id": next_jornada["_id"]},
                {"$set": {"status": "upcoming", "is_active": True}}
            )
            jornada = next_jornada
            jornada["status"] = "upcoming"
            jornada["is_active"] = True
            logger.info(f"Jornada {next_jornada['week_number']} activada automáticamente")
        else:
            jornada = None
            logger.info("No hay siguiente jornada disponible. Temporada terminada.")
    
    # Step 3: Fallback - if no is_active found, try legacy status-based lookup
    if not jornada:
        jornada = await db.jornadas.find_one(
            {"status": {"$in": ["upcoming", "in_progress"]}},
            sort=[("week_number", 1)]
        )
        # If found via fallback, set is_active for consistency
        if jornada:
            await db.jornadas.update_one(
                {"_id": jornada["_id"]},
                {"$set": {"is_active": True}}
            )
            jornada["is_active"] = True
            logger.info(f"Jornada {jornada['week_number']} activada via fallback (legacy status)")
    
    if not jornada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay jornada activa. Usa /api/admin/seed-jornada para crear una."
        )
    
    # Step 4: Update status based on dates
    if jornada.get("start_date") and jornada["start_date"] <= now and jornada.get("status") == "upcoming":
        await db.jornadas.update_one(
            {"_id": jornada["_id"]},
            {"$set": {"status": "in_progress"}}
        )
        jornada["status"] = "in_progress"
    
    # Step 5: Get matches for this jornada
    matches = await db.matches.find({"jornada_id": jornada["_id"]}).to_list(100)
    
    # Step 5b: Auto-advance if ALL matches are finished AND end_date has passed
    if matches:
        finished_count = sum(1 for m in matches if m.get("status") == "finished")
        total_count = len(matches)
        end_date_passed = jornada.get("end_date") and jornada["end_date"] < now
        
        if total_count > 0 and finished_count == total_count and end_date_passed:
            logger.info(
                f"Jornada {jornada['week_number']}: todos {total_count} partidos finalizados "
                f"y fecha fin pasada. Avanzando automáticamente..."
            )
            # ── Auto-process si no fue procesada antes ────────────────────
            if not jornada.get("processed", False):
                logger.info(
                    f"Jornada {jornada['week_number']} no procesada aún. "
                    f"Ejecutando process_jornada automáticamente..."
                )
                try:
                    proc_result = await _process_jornada_core(str(jornada["_id"]))
                    logger.info(
                        f"✅ Auto-proceso completado: "
                        f"quiniela={proc_result.get('quiniela_updated')} usuarios, "
                        f"fantasy={proc_result.get('fantasy_updated')} equipos, "
                        f"logros={proc_result.get('achievements_awarded')}"
                    )
                except Exception as proc_exc:
                    logger.error(f"❌ Auto-proceso falló: {proc_exc}")

            # Mark current jornada as finished
            await db.jornadas.update_one(
                {"_id": jornada["_id"]},
                {"$set": {"is_active": False, "status": "finished"}}
            )
            # Activate next jornada
            next_j = await db.jornadas.find_one(
                {"week_number": jornada["week_number"] + 1}
            )
            if next_j:
                await db.jornadas.update_one(
                    {"_id": next_j["_id"]},
                    {"$set": {"is_active": True, "status": "upcoming"}}
                )
                jornada = next_j
                logger.info(
                    f"Jornada {next_j['week_number']} activada porque todos los partidos de "
                    f"Jornada {next_j['week_number'] - 1} terminaron"
                )
                # Reload matches for the new active jornada
                matches = await db.matches.find({"jornada_id": jornada["_id"]}).to_list(100)
            else:
                logger.info("No hay siguiente jornada — temporada completada.")
    
    # Get team details for each match
    for match in matches:
        home_team = await db.teams.find_one({"_id": match["home_team_id"]})
        away_team = await db.teams.find_one({"_id": match["away_team_id"]})
        
        match["id"] = str(match.pop("_id"))
        match["jornada_id"] = str(match["jornada_id"])
        
        if home_team:
            match["home_team"] = {
                "id": str(home_team["_id"]),
                "name": home_team["name"],
                "short_name": home_team["short_name"],
                "shield_url": home_team["shield_url"]
            }
        else:
            match["home_team"] = {
                "id": "unknown",
                "name": "Equipo Local",
                "short_name": "LOC",
                "shield_url": "https://via.placeholder.com/100"
            }
        
        if away_team:
            match["away_team"] = {
                "id": str(away_team["_id"]),
                "name": away_team["name"],
                "short_name": away_team["short_name"],
                "shield_url": away_team["shield_url"]
            }
        else:
            match["away_team"] = {
                "id": "unknown",
                "name": "Equipo Visitante",
                "short_name": "VIS",
                "shield_url": "https://via.placeholder.com/100"
            }
        
        match.pop("home_team_id")
        match.pop("away_team_id")
    
    jornada["id"] = str(jornada.pop("_id"))
    jornada["matches"] = matches
    
    return {"jornada": jornada}

# ============ QUINIELA ROUTES ============

class QuinielaSubmit(BaseModel):
    jornada_id: str
    selections: List[dict]  # [{match_id: str, selection: str}]

@api_router.post("/quiniela/submit")
async def submit_quiniela(
    quiniela: QuinielaSubmit,
    current_user: dict = Depends(get_current_user)
):
    """Submit quiniela selections for a jornada"""
    jornada_id = ObjectId(quiniela.jornada_id)
    
    # Check if jornada exists
    jornada = await db.jornadas.find_one({"_id": jornada_id})
    if not jornada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jornada no encontrada"
        )
    
    # Check if user already submitted for this jornada
    existing = await db.quiniela_selections.find_one({
        "user_id": current_user["_id"],
        "jornada_id": jornada_id
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya enviaste tu quiniela para esta jornada"
        )
    
    # Get all matches for this jornada
    matches = await db.matches.find({"jornada_id": jornada_id}).to_list(100)
    
    # Check if any match has already started (por status, NO por fecha)
    for match in matches:
        if match.get("status") in ["live", "finished"]:
            # Look up team names for readable error message
            home_team = await db.teams.find_one({"_id": match.get("home_team_id")})
            away_team = await db.teams.find_one({"_id": match.get("away_team_id")})
            home_name = home_team.get("short_name", "Local") if home_team else "Local"
            away_name = away_team.get("short_name", "Visitante") if away_team else "Visitante"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El partido {home_name} vs {away_name} ya comenzó"
            )
    
    # Validate selections
    match_ids = {str(m["_id"]) for m in matches}
    submitted_match_ids = {s["match_id"] for s in quiniela.selections}
    
    if match_ids != submitted_match_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes seleccionar un resultado para cada partido"
        )
    
    # Validate selection values
    valid_selections = {"HOME", "DRAW", "AWAY"}
    for selection in quiniela.selections:
        if selection["selection"] not in valid_selections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selección inválida. Debe ser HOME, DRAW o AWAY"
            )
    
    # Save selections
    selections_to_insert = []
    for selection in quiniela.selections:
        selections_to_insert.append({
            "user_id": current_user["_id"],
            "jornada_id": jornada_id,
            "match_id": ObjectId(selection["match_id"]),
            "selection": selection["selection"],
            "submitted_at": datetime.utcnow()
        })
    
    await db.quiniela_selections.insert_many(selections_to_insert)
    
    logger.info(f"User {current_user['email']} submitted quiniela for jornada {quiniela.jornada_id}")
    
    return {
        "message": "Quiniela enviada exitosamente",
        "jornada_id": quiniela.jornada_id,
        "selections_count": len(selections_to_insert)
    }

@api_router.get("/quiniela/my-picks/{jornada_id}")
async def get_my_picks(
    jornada_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user's selections for a specific jornada"""
    jornada_obj_id = ObjectId(jornada_id)
    
    # Get selections
    selections = await db.quiniela_selections.find({
        "user_id": current_user["_id"],
        "jornada_id": jornada_obj_id
    }).to_list(100)
    
    if not selections:
        return {
            "submitted": False,
            "selections": []
        }
    
    # Format selections
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

@api_router.get("/quiniela/rankings/general")
async def get_general_rankings():
    """Get general rankings ordered by total points"""
    users = await db.users.find().sort("total_points", -1).limit(100).to_list(100)
    
    rankings = []
    for idx, user in enumerate(users, 1):
        rankings.append({
            "position": idx,
            "user_id": str(user["_id"]),
            "display_name": user["display_name"],
            "total_points": user.get("total_points", 0),
            "avatar_base64": user.get("avatar_base64")
        })
    
    return {"rankings": rankings}

@api_router.get("/quiniela/jornada/{jornada_id}/rankings")
async def get_jornada_rankings(jornada_id: str):
    """Get rankings for a specific jornada"""
    jornada_obj_id = ObjectId(jornada_id)
    
    # Get all points for this jornada
    points = await db.points_log.find({
        "jornada_id": jornada_obj_id,
        "source": "QUINIELA"
    }).to_list(1000)
    
    # Group by user
    user_points = {}
    for point in points:
        user_id = str(point["user_id"])
        if user_id not in user_points:
            user_points[user_id] = 0
        user_points[user_id] += point["points"]
    
    # Get user details and sort
    rankings = []
    for user_id, points in user_points.items():
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            rankings.append({
                "user_id": user_id,
                "display_name": user["display_name"],
                "points": points,
                "avatar_base64": user.get("avatar_base64")
            })
    
    rankings.sort(key=lambda x: x["points"], reverse=True)
    
    # Add positions
    for idx, ranking in enumerate(rankings, 1):
        ranking["position"] = idx
    
    return {"rankings": rankings, "jornada_id": jornada_id}

# ============ PRIVATE LEAGUES (QUINIELA) ============

class CreateLeagueRequest(BaseModel):
    name: str
    mode: str = "quiniela"  # "quiniela" o "fantasy"

class JoinLeagueRequest(BaseModel):
    code: str

MAX_MEMBERS_FREE = 25

@api_router.post("/leagues")
async def create_unified_league(
    league_data: CreateLeagueRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a unified private league (quiniela or fantasy)"""
    import random
    import string
    
    # Validate mode
    if league_data.mode not in ["quiniela", "fantasy"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modo debe ser 'quiniela' o 'fantasy'"
        )
    
    # Generate unique 6-char code
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    # Check if code exists
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
    
    # Award create league achievement
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

@api_router.post("/leagues/join")
async def join_unified_league(
    join_data: JoinLeagueRequest,
    current_user: dict = Depends(get_current_user)
):
    """Join a private league by code"""
    league = await db.private_leagues.find_one({"code": join_data.code.upper()})
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código de liga inválido"
        )
    
    # Check if already member
    existing = await db.league_members.find_one({
        "league_id": league["_id"],
        "user_id": current_user["_id"]
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya eres miembro de esta liga"
        )
    
    # Check league capacity
    max_members = league.get("max_members", MAX_MEMBERS_FREE)
    current_count = await db.league_members.count_documents({"league_id": league["_id"]})
    if current_count >= max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Esta liga está llena ({current_count}/{max_members} miembros)"
        )
    
    # For fantasy leagues, check if user has a fantasy team
    if league.get("mode") == "fantasy":
        fantasy_team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
        if not fantasy_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Necesitas crear tu equipo fantasy antes de unirte a una liga fantasy"
            )
    
    # Add as member
    await db.league_members.insert_one({
        "league_id": league["_id"],
        "user_id": current_user["_id"],
        "joined_at": datetime.utcnow()
    })
    
    # Award join league achievement
    await award_achievement(current_user["_id"], "join_league")
    
    # Check invite_5: si la liga ahora tiene 5+ miembros, el owner gana el logro
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

@api_router.get("/leagues/my-leagues")
async def get_my_unified_leagues(current_user: dict = Depends(get_current_user)):
    """Get all leagues user is member of (both quiniela and fantasy)"""
    memberships = await db.league_members.find({"user_id": current_user["_id"]}).to_list(100)
    
    leagues = []
    for membership in memberships:
        league = await db.private_leagues.find_one({"_id": membership["league_id"]})
        if league:
            member_count = await db.league_members.count_documents({"league_id": league["_id"]})
            max_members = league.get("max_members", MAX_MEMBERS_FREE)
            is_owner = str(league["owner_id"]) == str(current_user["_id"])
            
            leagues.append({
                "id": str(league["_id"]),
                "name": league["name"],
                "mode": league.get("mode", "quiniela"),
                "code": league["code"],
                "member_count": member_count,
                "max_members": max_members,
                "is_full": member_count >= max_members,
                "is_owner": is_owner,
                "created_at": league["created_at"]
            })
    
    return {"leagues": leagues}

@api_router.get("/leagues/{league_id}/availability")
async def get_league_availability(
    league_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get availability info for a league (capacity, spots left)"""
    try:
        league_obj_id = ObjectId(league_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de liga inválido")
    
    league = await db.private_leagues.find_one({"_id": league_obj_id})
    if not league:
        raise HTTPException(status_code=404, detail="Liga no encontrada")
    
    member_count = await db.league_members.count_documents({"league_id": league_obj_id})
    max_members = league.get("max_members", MAX_MEMBERS_FREE)
    
    return {
        "league_id": league_id,
        "name": league["name"],
        "member_count": member_count,
        "max_members": max_members,
        "is_full": member_count >= max_members,
        "spots_left": max(0, max_members - member_count)
    }

@api_router.get("/leagues/{league_id}")
async def get_unified_league_details(
    league_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get league details including members and rankings"""
    league_obj_id = ObjectId(league_id)
    league = await db.private_leagues.find_one({"_id": league_obj_id})
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Liga no encontrada"
        )
    
    # Check if user is member
    is_member = await db.league_members.find_one({
        "league_id": league_obj_id,
        "user_id": current_user["_id"]
    })
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres miembro de esta liga"
        )
    
    # Get all members with their points
    memberships = await db.league_members.find({"league_id": league_obj_id}).to_list(100)
    mode = league.get("mode", "quiniela")
    
    members = []
    for membership in memberships:
        user = await db.users.find_one({"_id": membership["user_id"]})
        if user:
            member_data = {
                "user_id": str(user["_id"]),
                "display_name": user["display_name"],
                "joined_at": membership["joined_at"]
            }
            
            if mode == "fantasy":
                # Get fantasy team and total points
                fantasy_team = await db.fantasy_teams.find_one({"user_id": user["_id"]})
                if fantasy_team:
                    # Sum all fantasy points for this user
                    pipeline = [
                        {"$match": {"user_id": user["_id"]}},
                        {"$group": {"_id": None, "total": {"$sum": "$total_points"}}}
                    ]
                    result = await db.fantasy_points_log.aggregate(pipeline).to_list(1)
                    total_fantasy_points = result[0]["total"] if result else 0
                    
                    member_data["team_name"] = fantasy_team["name"]
                    member_data["total_points"] = total_fantasy_points
                else:
                    member_data["team_name"] = "Sin equipo"
                    member_data["total_points"] = 0
            else:
                member_data["total_points"] = user.get("total_points", 0)
            
            members.append(member_data)
    
    # Sort by points
    members.sort(key=lambda x: x["total_points"], reverse=True)
    
    # Add ranking position
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

@api_router.get("/leagues/{league_id}/rankings/jornada/{jornada_id}")
async def get_league_jornada_rankings(
    league_id: str,
    jornada_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get league rankings for a specific jornada"""
    league_obj_id = ObjectId(league_id)
    jornada_obj_id = ObjectId(jornada_id)
    
    # Verify membership
    is_member = await db.league_members.find_one({
        "league_id": league_obj_id,
        "user_id": current_user["_id"]
    })
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres miembro de esta liga"
        )
    
    league = await db.private_leagues.find_one({"_id": league_obj_id})
    if not league:
        raise HTTPException(status_code=404, detail="Liga no encontrada")
    
    mode = league.get("mode", "quiniela")
    memberships = await db.league_members.find({"league_id": league_obj_id}).to_list(100)
    member_user_ids = [m["user_id"] for m in memberships]
    
    rankings = []
    
    if mode == "fantasy":
        # Get fantasy points for this jornada for league members
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
        # Get quiniela points for this jornada for league members
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
    
    # Sort by jornada points
    rankings.sort(key=lambda x: x["jornada_points"], reverse=True)
    
    # Add ranking position
    for idx, r in enumerate(rankings):
        r["rank"] = idx + 1
    
    return {
        "league_id": league_id,
        "league_name": league["name"],
        "mode": mode,
        "jornada_id": jornada_id,
        "rankings": rankings
    }

# Keep legacy endpoints for backwards compatibility
@api_router.post("/quiniela/league")
async def create_league(
    league_data: CreateLeagueRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a private league (legacy - use /leagues instead)"""
    league_data.mode = "quiniela"
    return await create_unified_league(league_data, current_user)

@api_router.post("/quiniela/league/join")
async def join_league(
    join_data: JoinLeagueRequest,
    current_user: dict = Depends(get_current_user)
):
    """Join a private league by code (legacy - use /leagues/join instead)"""
    return await join_unified_league(join_data, current_user)

@api_router.get("/quiniela/my-leagues")
async def get_my_leagues(current_user: dict = Depends(get_current_user)):
    """Get all leagues user is member of (legacy - use /leagues/my-leagues instead)"""
    return await get_my_unified_leagues(current_user)

@api_router.get("/quiniela/league/{league_id}")
async def get_league_details(
    league_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get league details including members"""
    league_obj_id = ObjectId(league_id)
    league = await db.private_leagues.find_one({"_id": league_obj_id})
    
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Liga no encontrada"
        )
    
    # Check if user is member
    is_member = await db.league_members.find_one({
        "league_id": league_obj_id,
        "user_id": current_user["_id"]
    })
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres miembro de esta liga"
        )
    
    # Get all members with their points
    memberships = await db.league_members.find({"league_id": league_obj_id}).to_list(100)
    
    members = []
    for membership in memberships:
        user = await db.users.find_one({"_id": membership["user_id"]})
        if user:
            members.append({
                "user_id": str(user["_id"]),
                "display_name": user["display_name"],
                "total_points": user.get("total_points", 0),
                "joined_at": membership["joined_at"]
            })
    
    # Sort by points
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

@api_router.get("/quiniela/league/{league_id}/results")
async def get_league_results(
    league_id: str,
    jornada_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get results matrix for a league and jornada"""
    league_obj_id = ObjectId(league_id)
    jornada_obj_id = ObjectId(jornada_id)
    
    # Verify membership
    is_member = await db.league_members.find_one({
        "league_id": league_obj_id,
        "user_id": current_user["_id"]
    })
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres miembro de esta liga"
        )
    
    # Get jornada with matches
    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jornada no encontrada"
        )
    
    # Get all matches
    matches = await db.matches.find({"jornada_id": jornada_obj_id}).to_list(100)
    
    # Get all members
    memberships = await db.league_members.find({"league_id": league_obj_id}).to_list(100)
    
    # Build results matrix
    results = []
    for match in matches:
        home_team = await db.teams.find_one({"_id": match["home_team_id"]})
        away_team = await db.teams.find_one({"_id": match["away_team_id"]})
        
        # Calculate actual result
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
        
        # Get predictions for each member
        for membership in memberships:
            user = await db.users.find_one({"_id": membership["user_id"]})
            selection = await db.quiniela_selections.find_one({
                "user_id": membership["user_id"],
                "match_id": match["_id"]
            })
            
            prediction = {
                "user_id": str(membership["user_id"]),
                "user_name": user["display_name"] if user else "???",
                "selection": selection["selection"] if selection else None,
                "is_correct": selection and actual_result and selection["selection"] == actual_result
            }
            
            match_result["predictions"].append(prediction)
        
        results.append(match_result)
    
    # Calculate total points per user
    user_points = {}
    for match_result in results:
        for pred in match_result["predictions"]:
            user_id = pred["user_id"]
            if user_id not in user_points:
                user_points[user_id] = {
                    "user_name": pred["user_name"],
                    "points": 0
                }
            if pred["is_correct"]:
                user_points[user_id]["points"] += 1
    
    return {
        "jornada": {
            "id": str(jornada["_id"]),
            "week_number": jornada["week_number"],
            "status": jornada["status"]
        },
        "results": results,
        "user_points": user_points
    }

@api_router.get("/quiniela/league/{league_id}/ranking")
async def get_league_ranking(
    league_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get general ranking for a league"""
    league_obj_id = ObjectId(league_id)
    
    # Verify membership
    is_member = await db.league_members.find({
        "league_id": league_obj_id,
        "user_id": current_user["_id"]
    }).to_list(1)
    
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres miembro de esta liga"
        )
    
    # Get all members with points
    memberships = await db.league_members.find({"league_id": league_obj_id}).to_list(100)
    
    rankings = []
    for membership in memberships:
        user = await db.users.find_one({"_id": membership["user_id"]})
        if user:
            rankings.append({
                "user_id": str(user["_id"]),
                "display_name": user["display_name"],
                "total_points": user.get("total_points", 0)
            })
    
    # Sort by points
    rankings.sort(key=lambda x: x["total_points"], reverse=True)
    
    # Add positions
    for idx, ranking in enumerate(rankings, 1):
        ranking["position"] = idx
    
    return {"rankings": rankings}

# ============ ADMIN ROUTES FOR QUINIELA ============

class UpdateScoreRequest(BaseModel):
    home_score: int
    away_score: int

@api_router.put("/admin/match/{match_id}/score")
async def update_match_score(match_id: str, scores: UpdateScoreRequest):
    """Update match score (admin only)"""
    match = await db.matches.find_one({"_id": ObjectId(match_id)})
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partido no encontrado"
        )
    
    # Update scores
    await db.matches.update_one(
        {"_id": ObjectId(match_id)},
        {"$set": {
            "home_score": scores.home_score,
            "away_score": scores.away_score,
            "status": "finished"
        }}
    )
    
    logger.info(f"Match {match_id} score updated: {scores.home_score}-{scores.away_score}")
    
    return {
        "message": "Resultado actualizado",
        "match_id": match_id,
        "score": f"{scores.home_score}-{scores.away_score}"
    }

@api_router.post("/admin/jornada/{jornada_id}/calculate-points")
async def calculate_jornada_points(jornada_id: str):
    """Calculate points for all users in a jornada"""
    jornada_obj_id = ObjectId(jornada_id)
    
    # Get jornada
    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jornada no encontrada"
        )
    
    # Get all matches with results
    matches = await db.matches.find({
        "jornada_id": jornada_obj_id,
        "status": "finished"
    }).to_list(100)
    
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay partidos finalizados en esta jornada"
        )
    
    # Calculate actual results
    match_results = {}
    for match in matches:
        match_id = match["_id"]
        home = match["home_score"]
        away = match["away_score"]
        
        if home > away:
            result = "HOME"
        elif away > home:
            result = "AWAY"
        else:
            result = "DRAW"
        
        match_results[match_id] = result
    
    # Get all selections for this jornada
    all_selections = await db.quiniela_selections.find({
        "jornada_id": jornada_obj_id
    }).to_list(10000)
    
    # Group by user
    user_selections = {}
    for sel in all_selections:
        user_id = sel["user_id"]
        if user_id not in user_selections:
            user_selections[user_id] = []
        user_selections[user_id].append(sel)
    
    # Calculate points for each user
    users_updated = 0
    total_points_awarded = 0
    
    for user_id, selections in user_selections.items():
        points = 0
        for sel in selections:
            match_id = sel["match_id"]
            if match_id in match_results:
                if sel["selection"] == match_results[match_id]:
                    points += 1  # 1 point per correct prediction
        
        if points > 0:
            # Save points log
            await db.points_log.insert_one({
                "user_id": user_id,
                "jornada_id": jornada_obj_id,
                "source": "QUINIELA",
                "points": points,
                "created_at": datetime.utcnow()
            })
            
            # Update user total points
            await db.users.update_one(
                {"_id": user_id},
                {"$inc": {"total_points": points}}
            )
            
            users_updated += 1
            total_points_awarded += points
    
    # Update jornada status
    await db.jornadas.update_one(
        {"_id": jornada_obj_id},
        {"$set": {"status": "finished"}}
    )
    
    logger.info(f"Calculated points for jornada {jornada_id}: {users_updated} users, {total_points_awarded} points")
    
    return {
        "message": "Puntos calculados exitosamente",
        "jornada_id": jornada_id,
        "users_updated": users_updated,
        "total_points_awarded": total_points_awarded
    }


# ──────────────────────────────────────────────────────────────────────────────
#  PROCESS JORNADA — Orquestador completo
# ──────────────────────────────────────────────────────────────────────────────

async def _process_jornada_core(jornada_id: str) -> dict:
    """
    Orquesta el procesamiento completo de una jornada:
    1. Obtiene resultados de partidos (365Scores → ESPN fallback)
    2. Calcula puntos de Quiniela
    3. Obtiene stats de jugadores (ESPN Summary)
    4. Calcula puntos de Fantasy
    5. Verifica y otorga logros
    Marca la jornada como processed=True al finalizar.
    """
    jornada_obj_id = ObjectId(jornada_id)
    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        return {"error": "Jornada no encontrada"}

    logger.info(f"🔄 Procesando jornada {jornada.get('week_number')} ({jornada_id})")

    # ── Paso 1: Actualizar resultados de partidos ─────────────────────────
    scores_result = await _svc_get_match_results(jornada_id, db)
    logger.info(f"  ✅ Scores: {scores_result.get('matches_updated')}/{scores_result.get('matches_total')} actualizados")

    # ── Paso 2: Calcular puntos de Quiniela ───────────────────────────────
    quiniela_updated = 0
    try:
        matches_done = await db.matches.find(
            {"jornada_id": jornada_obj_id, "status": "finished"}
        ).to_list(100)

        if matches_done:
            match_results_map = {}
            for m in matches_done:
                h, a = m.get("home_score", 0), m.get("away_score", 0)
                if h > a:
                    result_val = "HOME"
                elif a > h:
                    result_val = "AWAY"
                else:
                    result_val = "DRAW"
                match_results_map[m["_id"]] = result_val

            all_selections = await db.quiniela_selections.find(
                {"jornada_id": jornada_obj_id}
            ).to_list(10000)

            user_sels: dict = {}
            for sel in all_selections:
                user_sels.setdefault(sel["user_id"], []).append(sel)

            for uid, sels in user_sels.items():
                pts = sum(
                    1 for s in sels
                    if s.get("match_id") in match_results_map
                    and s["selection"] == match_results_map[s["match_id"]]
                )
                if pts > 0:
                    existing = await db.points_log.find_one({
                        "user_id": uid, "jornada_id": jornada_obj_id, "source": "QUINIELA",
                    })
                    if not existing:
                        await db.points_log.insert_one({
                            "user_id": uid, "jornada_id": jornada_obj_id,
                            "source": "QUINIELA", "points": pts,
                            "created_at": datetime.utcnow(),
                        })
                        await db.users.update_one(
                            {"_id": uid}, {"$inc": {"total_points": pts}}
                        )
                        quiniela_updated += 1
    except Exception as exc:
        logger.error(f"  ❌ Quiniela points error: {exc}")

    # ── Paso 3: Stats de jugadores ────────────────────────────────────────
    stats_result = await _svc_get_player_stats(jornada_id, db)
    logger.info(f"  ✅ Player stats: {stats_result.get('players_saved')} jugadores guardados")

    # ── Paso 4: Calcular puntos Fantasy ───────────────────────────────────
    fantasy_updated = 0
    try:
        f_result = await calculate_fantasy_points(jornada_id)
        fantasy_updated = f_result.get("teams_processed", 0)
    except Exception as exc:
        logger.error(f"  ❌ Fantasy points error: {exc}")

    # ── Paso 5: Logros ────────────────────────────────────────────────────
    achievements_awarded = 0
    try:
        user_ids = await db.users.distinct("_id", {})
        for uid in user_ids:
            awarded = await check_and_award_achievements_after_jornada(str(uid), jornada_id)
            achievements_awarded += len(awarded)
    except Exception as exc:
        logger.error(f"  ❌ Achievements error: {exc}")

    # ── Marcar jornada como procesada ─────────────────────────────────────
    await db.jornadas.update_one(
        {"_id": jornada_obj_id},
        {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
    )

    summary = {
        "jornada_id":           jornada_id,
        "week_number":          jornada.get("week_number"),
        "scores_updated":       scores_result.get("matches_updated", 0),
        "scores_not_found":     scores_result.get("matches_not_found", []),
        "quiniela_updated":     quiniela_updated,
        "player_stats_saved":   stats_result.get("players_saved", 0),
        "fantasy_updated":      fantasy_updated,
        "achievements_awarded": achievements_awarded,
        "processed_at":         datetime.utcnow().isoformat(),
    }
    logger.info(f"✅ Jornada {jornada.get('week_number')} procesada: {summary}")
    return summary


@api_router.post("/admin/process-jornada/{jornada_id}")
async def process_jornada_endpoint(jornada_id: str):
    """
    Procesa completamente una jornada:
    1. Resultados de partidos (365Scores → ESPN fallback)
    2. Puntos de FuchoQuiniela
    3. Stats de jugadores (ESPN)
    4. Puntos de FuchoOnce (Fantasy)
    5. Logros y achievements
    """
    result = await _process_jornada_core(jornada_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ============ FANTASY SCORING SYSTEM ============

# Sistema de puntuación por posición
FANTASY_SCORING = {
    "minutes_played": {
        "threshold_60": 2,  # >= 60 minutos
        "under_60": 1       # < 60 minutos
    },
    "goals": {
        "POR": 6,
        "DEF": 6,
        "MED": 5,
        "DEL": 4
    },
    "assists": 3,
    "clean_sheet": {  # Portería a cero
        "POR": 5,
        "DEF": 4
    },
    "goals_conceded": {  # Por cada 2 goles recibidos (solo POR y DEF)
        "POR": -1,
        "DEF": -1
    },
    "yellow_card": -1,
    "red_card": -3,
    "penalty_saved": 5,
    "penalty_missed": -3,
    "own_goal": -2,
    # Bonos especiales
    "bonuses": {
        "man_of_the_match": 2,
        "brace": 1,          # 2 goles
        "hat_trick": 2,      # 3+ goles
        "keeper_4_saves": 1  # Portero con 4+ atajadas
    },
    "dt": {
        "team_win": 2,
        "team_draw": 1,
        "team_loss": 0
    }
}

def calculate_player_points(player_stats: dict, position: str) -> dict:
    """Calculate fantasy points for a single player based on their stats"""
    points = 0
    breakdown = {}
    
    # Minutos jugados
    minutes = player_stats.get("minutes", 0)
    if minutes >= 60:
        points += FANTASY_SCORING["minutes_played"]["threshold_60"]
        breakdown["minutes"] = {"value": minutes, "points": 2, "label": "Minutos (≥60)"}
    elif minutes > 0:
        points += FANTASY_SCORING["minutes_played"]["under_60"]
        breakdown["minutes"] = {"value": minutes, "points": 1, "label": "Minutos (<60)"}
    
    # Goles
    goals = player_stats.get("goals", 0)
    if goals > 0:
        goal_points = goals * FANTASY_SCORING["goals"].get(position, 4)
        points += goal_points
        breakdown["goals"] = {"value": goals, "points": goal_points, "label": f"Goles ({position})"}
        
        # Bonus por doblete/hat-trick
        if goals == 2:
            points += FANTASY_SCORING["bonuses"]["brace"]
            breakdown["brace"] = {"value": 1, "points": 1, "label": "Doblete"}
        elif goals >= 3:
            points += FANTASY_SCORING["bonuses"]["hat_trick"]
            breakdown["hat_trick"] = {"value": 1, "points": 2, "label": "Hat-trick"}
    
    # Asistencias
    assists = player_stats.get("assists", 0)
    if assists > 0:
        assist_points = assists * FANTASY_SCORING["assists"]
        points += assist_points
        breakdown["assists"] = {"value": assists, "points": assist_points, "label": "Asistencias"}
    
    # Portería a cero (solo para POR y DEF)
    if position in ["POR", "DEF"]:
        clean_sheet = player_stats.get("clean_sheet", False)
        if clean_sheet and minutes >= 60:
            cs_points = FANTASY_SCORING["clean_sheet"].get(position, 0)
            points += cs_points
            breakdown["clean_sheet"] = {"value": 1, "points": cs_points, "label": "Portería a cero"}
        
        # Goles recibidos (penalización por cada 2)
        goals_conceded = player_stats.get("goals_conceded", 0)
        if goals_conceded >= 2:
            gc_penalty = (goals_conceded // 2) * FANTASY_SCORING["goals_conceded"].get(position, -1)
            points += gc_penalty
            breakdown["goals_conceded"] = {"value": goals_conceded, "points": gc_penalty, "label": "Goles recibidos"}
    
    # Portero - atajadas
    if position == "POR":
        saves = player_stats.get("saves", 0)
        if saves >= 4:
            points += FANTASY_SCORING["bonuses"]["keeper_4_saves"]
            breakdown["saves"] = {"value": saves, "points": 1, "label": "4+ Atajadas"}
        
        # Penalti atajado
        penalty_saved = player_stats.get("penalty_saved", 0)
        if penalty_saved > 0:
            ps_points = penalty_saved * FANTASY_SCORING["penalty_saved"]
            points += ps_points
            breakdown["penalty_saved"] = {"value": penalty_saved, "points": ps_points, "label": "Penalti atajado"}
    
    # Tarjeta amarilla
    yellow = player_stats.get("yellow_card", 0)
    if yellow > 0:
        yellow_points = yellow * FANTASY_SCORING["yellow_card"]
        points += yellow_points
        breakdown["yellow_card"] = {"value": yellow, "points": yellow_points, "label": "Tarjeta amarilla"}
    
    # Tarjeta roja
    red = player_stats.get("red_card", 0)
    if red > 0:
        red_points = red * FANTASY_SCORING["red_card"]
        points += red_points
        breakdown["red_card"] = {"value": red, "points": red_points, "label": "Tarjeta roja"}
    
    # Penalti fallado
    penalty_missed = player_stats.get("penalty_missed", 0)
    if penalty_missed > 0:
        pm_points = penalty_missed * FANTASY_SCORING["penalty_missed"]
        points += pm_points
        breakdown["penalty_missed"] = {"value": penalty_missed, "points": pm_points, "label": "Penalti fallado"}
    
    # Autogol
    own_goal = player_stats.get("own_goal", 0)
    if own_goal > 0:
        og_points = own_goal * FANTASY_SCORING["own_goal"]
        points += og_points
        breakdown["own_goal"] = {"value": own_goal, "points": og_points, "label": "Autogol"}
    
    # Jugador del partido
    if player_stats.get("man_of_the_match", False):
        points += FANTASY_SCORING["bonuses"]["man_of_the_match"]
        breakdown["motm"] = {"value": 1, "points": 2, "label": "⭐ Jugador del partido"}
    
    return {
        "total_points": points,
        "breakdown": breakdown
    }

@api_router.post("/admin/fantasy/simulate-jornada/{jornada_id}")
async def simulate_fantasy_jornada(jornada_id: str):
    """
    Simula una jornada completa de Fantasy con estadísticas mock.
    Genera stats para todos los jugadores y calcula puntos.
    """
    import random
    
    jornada_obj_id = ObjectId(jornada_id)
    
    # Verificar jornada
    jornada = await db.jornadas.find_one({"_id": jornada_obj_id})
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")
    
    # Obtener partidos de esta jornada
    matches = await db.matches.find({"jornada_id": jornada_obj_id}).to_list(20)
    if not matches:
        raise HTTPException(status_code=400, detail="No hay partidos en esta jornada")
    
    # Generar resultados y estadísticas mock para cada partido
    match_results = []
    player_stats_bulk = []
    
    for match in matches:
        home_team_id = match["home_team_id"]
        away_team_id = match["away_team_id"]
        
        # Generar marcador realista
        home_score = random.choices([0, 1, 2, 3, 4], weights=[20, 35, 25, 15, 5])[0]
        away_score = random.choices([0, 1, 2, 3, 4], weights=[25, 35, 25, 12, 3])[0]
        
        # Actualizar partido
        await db.matches.update_one(
            {"_id": match["_id"]},
            {"$set": {
                "home_score": home_score,
                "away_score": away_score,
                "status": "finished"
            }}
        )
        
        match_results.append({
            "match_id": str(match["_id"]),
            "home_team_id": str(home_team_id),
            "away_team_id": str(away_team_id),
            "home_score": home_score,
            "away_score": away_score
        })
        
        # Generar estadísticas para jugadores de ambos equipos
        for team_id, is_home, goals_scored, goals_conceded in [
            (home_team_id, True, home_score, away_score),
            (away_team_id, False, away_score, home_score)
        ]:
            # Obtener jugadores del equipo
            players = await db.players.find({"team_id": team_id}).to_list(30)
            
            # Distribuir goles entre jugadores
            goals_to_assign = goals_scored
            
            for player in players:
                position = player.get("position", "MED")
                
                # Generar estadísticas realistas
                played = random.random() > 0.1  # 90% juegan
                minutes = random.randint(60, 90) if played else random.randint(0, 45) if random.random() > 0.5 else 0
                
                stats = {
                    "match_id": match["_id"],
                    "jornada_id": jornada_obj_id,
                    "player_id": player["_id"],
                    "team_id": team_id,
                    "position": position,
                    "minutes": minutes,
                    "goals": 0,
                    "assists": 0,
                    "clean_sheet": goals_conceded == 0 and minutes >= 60,
                    "goals_conceded": goals_conceded if position in ["POR", "DEF"] else 0,
                    "yellow_card": 1 if random.random() < 0.15 else 0,
                    "red_card": 1 if random.random() < 0.02 else 0,
                    "saves": random.randint(0, 6) if position == "POR" else 0,
                    "penalty_saved": 1 if position == "POR" and random.random() < 0.05 else 0,
                    "penalty_missed": 0,
                    "own_goal": 1 if random.random() < 0.01 else 0,
                    "man_of_the_match": False,
                    "created_at": datetime.utcnow()
                }
                
                # Asignar goles a delanteros/medios principalmente
                if goals_to_assign > 0 and minutes >= 45:
                    if position == "DEL" and random.random() < 0.5:
                        stats["goals"] = min(goals_to_assign, random.randint(1, 2))
                        goals_to_assign -= stats["goals"]
                    elif position == "MED" and random.random() < 0.3:
                        stats["goals"] = min(goals_to_assign, 1)
                        goals_to_assign -= stats["goals"]
                    elif position == "DEF" and random.random() < 0.1:
                        stats["goals"] = min(goals_to_assign, 1)
                        goals_to_assign -= stats["goals"]
                
                # Asignar asistencias
                if stats["goals"] == 0 and random.random() < 0.2 and minutes >= 45:
                    stats["assists"] = 1
                
                player_stats_bulk.append(stats)
        
        # Asignar jugador del partido a uno al azar
        if player_stats_bulk:
            match_players = [p for p in player_stats_bulk if p["match_id"] == match["_id"]]
            if match_players:
                motm_idx = random.randint(0, len(match_players) - 1)
                match_players[motm_idx]["man_of_the_match"] = True
    
    # Guardar todas las estadísticas
    if player_stats_bulk:
        # Eliminar stats anteriores de esta jornada
        await db.player_match_stats.delete_many({"jornada_id": jornada_obj_id})
        await db.player_match_stats.insert_many(player_stats_bulk)
    
    # Ahora calcular puntos para todos los equipos fantasy
    fantasy_results = await calculate_fantasy_points(jornada_id)
    
    return {
        "message": "Jornada simulada exitosamente",
        "jornada_id": jornada_id,
        "matches_simulated": len(match_results),
        "match_results": match_results,
        "fantasy_results": fantasy_results
    }

async def calculate_fantasy_points(jornada_id: str) -> dict:
    """Calcula puntos fantasy para todos los equipos de una jornada"""
    jornada_obj_id = ObjectId(jornada_id)
    
    # Obtener todas las alineaciones de esta jornada
    all_lineups = await db.fantasy_lineups.find({
        "jornada_id": jornada_obj_id
    }).to_list(1000)
    
    # Agrupar por fantasy_team_id
    team_lineups = {}
    for lineup in all_lineups:
        team_id = lineup["fantasy_team_id"]
        if team_id not in team_lineups:
            team_lineups[team_id] = []
        team_lineups[team_id].append(lineup)
    
    # Obtener stats de jugadores para esta jornada
    player_stats_map = {}
    all_stats = await db.player_match_stats.find({"jornada_id": jornada_obj_id}).to_list(1000)
    for stat in all_stats:
        player_stats_map[stat["player_id"]] = stat
    
    # Calcular puntos por equipo
    team_results = []
    
    for fantasy_team_id, lineup_items in team_lineups.items():
        # Obtener info del equipo fantasy
        fantasy_team = await db.fantasy_teams.find_one({"_id": fantasy_team_id})
        if not fantasy_team:
            continue
        
        user = await db.users.find_one({"_id": fantasy_team["user_id"]})
        if not user:
            continue
        
        team_total_points = 0
        players_breakdown = []
        dt_points = 0
        
        for item in lineup_items:
            if item.get("is_dt"):
                # Calcular puntos del DT
                dt_team_id = item.get("dt_team_id")
                if dt_team_id:
                    # Buscar resultado del partido del equipo del DT
                    match = await db.matches.find_one({
                        "jornada_id": jornada_obj_id,
                        "$or": [
                            {"home_team_id": dt_team_id},
                            {"away_team_id": dt_team_id}
                        ]
                    })
                    
                    if match and match.get("status") == "finished":
                        home_score = match.get("home_score", 0)
                        away_score = match.get("away_score", 0)
                        
                        if match["home_team_id"] == dt_team_id:
                            if home_score > away_score:
                                dt_points = FANTASY_SCORING["dt"]["team_win"]
                            elif home_score == away_score:
                                dt_points = FANTASY_SCORING["dt"]["team_draw"]
                        else:
                            if away_score > home_score:
                                dt_points = FANTASY_SCORING["dt"]["team_win"]
                            elif away_score == home_score:
                                dt_points = FANTASY_SCORING["dt"]["team_draw"]
                        
                        team_total_points += dt_points
            else:
                # Calcular puntos del jugador
                player_id = item.get("player_id")
                if player_id and player_id in player_stats_map:
                    stats = player_stats_map[player_id]
                    position = stats.get("position", "MED")
                    
                    result = calculate_player_points(stats, position)
                    team_total_points += result["total_points"]
                    
                    # Obtener info del jugador
                    player = await db.players.find_one({"_id": player_id})
                    
                    players_breakdown.append({
                        "player_id": str(player_id),
                        "player_name": player.get("name", "Unknown") if player else "Unknown",
                        "position": position,
                        "position_slot": item.get("position_slot"),
                        "points": result["total_points"],
                        "breakdown": result["breakdown"]
                    })
        
        # Guardar en points_log
        await db.fantasy_points_log.delete_many({
            "fantasy_team_id": fantasy_team_id,
            "jornada_id": jornada_obj_id
        })
        
        await db.fantasy_points_log.insert_one({
            "fantasy_team_id": fantasy_team_id,
            "user_id": fantasy_team["user_id"],
            "jornada_id": jornada_obj_id,
            "total_points": team_total_points,
            "dt_points": dt_points,
            "players_breakdown": players_breakdown,
            "created_at": datetime.utcnow()
        })
        
        # Actualizar puntos totales del usuario (fantasy)
        await db.users.update_one(
            {"_id": fantasy_team["user_id"]},
            {"$inc": {"fantasy_total_points": team_total_points}}
        )
        
        team_results.append({
            "fantasy_team_id": str(fantasy_team_id),
            "team_name": fantasy_team.get("name", "Unknown"),
            "user_name": user.get("display_name", "Unknown"),
            "user_email": user.get("email"),
            "total_points": team_total_points,
            "dt_points": dt_points,
            "players_count": len(players_breakdown),
            "players_breakdown": players_breakdown
        })
    
    # Ordenar por puntos
    team_results.sort(key=lambda x: x["total_points"], reverse=True)
    
    # Añadir posición en ranking
    for idx, result in enumerate(team_results):
        result["rank"] = idx + 1
    
    return {
        "teams_processed": len(team_results),
        "rankings": team_results
    }

@api_router.get("/fantasy/rankings/jornada/{jornada_id}")
async def get_fantasy_jornada_rankings(jornada_id: str):
    """Obtener ranking de Fantasy para una jornada específica"""
    jornada_obj_id = ObjectId(jornada_id)
    
    # Obtener puntos de la jornada
    points_logs = await db.fantasy_points_log.find({
        "jornada_id": jornada_obj_id
    }).sort("total_points", -1).to_list(100)
    
    rankings = []
    for idx, log in enumerate(points_logs):
        fantasy_team = await db.fantasy_teams.find_one({"_id": log["fantasy_team_id"]})
        user = await db.users.find_one({"_id": log["user_id"]})
        
        rankings.append({
            "rank": idx + 1,
            "team_name": fantasy_team.get("name", "Unknown") if fantasy_team else "Unknown",
            "user_name": user.get("display_name", "Unknown") if user else "Unknown",
            "total_points": log["total_points"],
            "dt_points": log.get("dt_points", 0),
            "players_breakdown": log.get("players_breakdown", [])
        })
    
    return {"rankings": rankings, "jornada_id": jornada_id}

@api_router.get("/fantasy/rankings/general")
async def get_fantasy_general_rankings():
    """Obtener ranking general de Fantasy (acumulado)"""
    # Agregar puntos de todas las jornadas por equipo
    pipeline = [
        {"$group": {
            "_id": "$fantasy_team_id",
            "total_points": {"$sum": "$total_points"},
            "jornadas_played": {"$sum": 1}
        }},
        {"$sort": {"total_points": -1}},
        {"$limit": 100}
    ]
    
    aggregated = await db.fantasy_points_log.aggregate(pipeline).to_list(100)
    
    rankings = []
    for idx, item in enumerate(aggregated):
        fantasy_team = await db.fantasy_teams.find_one({"_id": item["_id"]})
        if fantasy_team:
            user = await db.users.find_one({"_id": fantasy_team["user_id"]})
            rankings.append({
                "rank": idx + 1,
                "team_name": fantasy_team.get("name", "Unknown"),
                "user_name": user.get("display_name", "Unknown") if user else "Unknown",
                "total_points": item["total_points"],
                "jornadas_played": item["jornadas_played"]
            })
    
    return {"rankings": rankings}

# ============ FANTASY ROUTES ============

class FantasyTeamCreate(BaseModel):
    name: str

@api_router.post("/fantasy/team")
async def create_or_update_fantasy_team(
    team_data: FantasyTeamCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create or update user's fantasy team name"""
    # Check if user already has a team
    existing_team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    
    if existing_team:
        # Update name
        await db.fantasy_teams.update_one(
            {"_id": existing_team["_id"]},
            {"$set": {"name": team_data.name}}
        )
        return {
            "message": "Nombre de equipo actualizado",
            "team_id": str(existing_team["_id"]),
            "name": team_data.name
        }
    else:
        # Create new team
        team_doc = {
            "user_id": current_user["_id"],
            "name": team_data.name,
            "created_at": datetime.utcnow()
        }
        result = await db.fantasy_teams.insert_one(team_doc)
        
        logger.info(f"User {current_user['email']} created fantasy team: {team_data.name}")
        
        return {
            "message": "Equipo fantasy creado",
            "team_id": str(result.inserted_id),
            "name": team_data.name
        }

@api_router.get("/fantasy/my-team")
async def get_my_fantasy_team(current_user: dict = Depends(get_current_user)):
    """Get user's fantasy team"""
    team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    
    if not team:
        # Return default name
        default_name = f"{current_user['display_name']} - FC"
        return {
            "exists": False,
            "default_name": default_name
        }
    
    return {
        "exists": True,
        "team_id": str(team["_id"]),
        "name": team["name"],
        "created_at": team["created_at"]
    }

@api_router.get("/players")
async def get_players(
    position: Optional[str] = None,
    team_id: Optional[str] = None
):
    """Get players filtered by position and/or team"""
    query = {}
    
    if position:
        query["position"] = position
    
    if team_id:
        query["team_id"] = ObjectId(team_id)
    
    players = await db.players.find(query).to_list(1000)
    
    # Format response
    formatted_players = []
    for player in players:
        team = await db.teams.find_one({"_id": player["team_id"]})
        formatted_players.append({
            "id": str(player["_id"]),
            "name": player["name"],
            "number": player.get("number", 0),
            "position": player["position"],
            "team": {
                "id": str(team["_id"]),
                "name": team["name"],
                "short_name": team["short_name"],
                "shield_url": team["shield_url"]
            } if team else None,
            "stats": player.get("stats", {})
        })
    
    return {"players": formatted_players}

class FantasyLineupSubmit(BaseModel):
    jornada_id: str
    players: List[dict]  # [{player_id, position_slot}]
    dt_team_id: Optional[str] = None  # Director Técnico

@api_router.post("/fantasy/lineup")
async def submit_fantasy_lineup(
    lineup: FantasyLineupSubmit,
    current_user: dict = Depends(get_current_user)
):
    """Submit fantasy lineup for a jornada"""
    # Get user's fantasy team
    team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    if not team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes crear tu equipo fantasy"
        )
    
    jornada_id = ObjectId(lineup.jornada_id)
    
    # Check if lineup already exists
    existing = await db.fantasy_lineups.find_one({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_id
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya enviaste tu alineación para esta jornada"
        )
    
    # Validate 11 players + optional DT
    if len(lineup.players) != 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes seleccionar exactamente 11 jugadores"
        )
    
    # Save lineup
    lineup_docs = []
    for player_data in lineup.players:
        lineup_docs.append({
            "fantasy_team_id": team["_id"],
            "jornada_id": jornada_id,
            "player_id": ObjectId(player_data["player_id"]),
            "position_slot": player_data["position_slot"],
            "is_dt": False,
            "created_at": datetime.utcnow()
        })
    
    # Add DT if provided
    if lineup.dt_team_id:
        lineup_docs.append({
            "fantasy_team_id": team["_id"],
            "jornada_id": jornada_id,
            "dt_team_id": ObjectId(lineup.dt_team_id),
            "position_slot": "DT",
            "is_dt": True,
            "created_at": datetime.utcnow()
        })
    
    await db.fantasy_lineups.insert_many(lineup_docs)
    
    # Award first lineup achievement
    await award_achievement(current_user["_id"], "first_lineup")
    
    return {
        "message": "Alineación guardada exitosamente",
        "jornada_id": lineup.jornada_id,
        "players_count": len(lineup_docs)
    }

@api_router.get("/fantasy/lineup/{jornada_id}")
async def get_fantasy_lineup(
    jornada_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user's fantasy lineup for a jornada"""
    team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    if not team:
        return {"submitted": False, "lineup": []}
    
    jornada_obj_id = ObjectId(jornada_id)
    
    lineup = await db.fantasy_lineups.find({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_obj_id
    }).to_list(100)
    
    if not lineup:
        return {"submitted": False, "lineup": []}
    
    # Format lineup with player details
    formatted_lineup = []
    for item in lineup:
        if item.get("is_dt"):
            # DT item
            dt_team = await db.teams.find_one({"_id": item.get("dt_team_id")})
            formatted_lineup.append({
                "position_slot": "DT",
                "is_dt": True,
                "team": {
                    "id": str(dt_team["_id"]),
                    "name": dt_team["name"],
                    "short_name": dt_team["short_name"],
                    "shield_url": dt_team["shield_url"]
                } if dt_team else None
            })
        else:
            # Player item
            player = await db.players.find_one({"_id": item["player_id"]})
            if player:
                player_team = await db.teams.find_one({"_id": player["team_id"]})
                formatted_lineup.append({
                    "position_slot": item["position_slot"],
                    "is_dt": False,
                    "player": {
                        "id": str(player["_id"]),
                        "name": player["name"],
                        "number": player.get("number", 0),
                        "position": player["position"],
                        "team": {
                            "id": str(player_team["_id"]),
                            "name": player_team["name"],
                            "short_name": player_team["short_name"],
                            "shield_url": player_team["shield_url"]
                        } if player_team else None
                    }
                })
    
    return {
        "submitted": True,
        "lineup": formatted_lineup
    }


@api_router.get("/fantasy/results/{jornada_id}")
async def get_fantasy_results(
    jornada_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retorna la alineación del usuario con puntos desglosados por jugador
    para la jornada especificada.
    Usa fantasy_points_log si ya fue procesado, o calcula en tiempo real.
    """
    jornada_obj_id = ObjectId(jornada_id)
    team = await db.fantasy_teams.find_one({"user_id": current_user["_id"]})
    if not team:
        return {"has_lineup": False, "players": [], "total_points": 0}

    # ── 1. Buscar en fantasy_points_log (ya procesado) ───────────────────
    log = await db.fantasy_points_log.find_one({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_obj_id,
    })
    if log:
        return {
            "has_lineup":    True,
            "team_name":     team.get("name", "Mi Equipo"),
            "total_points":  log.get("total_points", 0),
            "dt_points":     log.get("dt_points", 0),
            "players":       log.get("players_breakdown", []),
            "processed":     True,
            "jornada_id":    jornada_id,
        }

    # ── 2. Calcular en tiempo real si no está procesado ──────────────────
    lineup_items = await db.fantasy_lineups.find({
        "fantasy_team_id": team["_id"],
        "jornada_id": jornada_obj_id,
    }).to_list(100)

    if not lineup_items:
        return {"has_lineup": False, "players": [], "total_points": 0}

    # Load all player stats for the jornada
    all_stats = await db.player_match_stats.find(
        {"jornada_id": jornada_obj_id}
    ).to_list(5000)
    stats_by_player_id = {s["player_id"]: s for s in all_stats}

    players_result = []
    total_pts = 0

    for item in lineup_items:
        if item.get("is_dt"):
            continue  # Skip DT for per-player breakdown

        player_id = item.get("player_id")
        player = await db.players.find_one({"_id": player_id}) if player_id else None
        if not player:
            continue

        player_team = await db.teams.find_one({"_id": player["team_id"]})
        position = player.get("position", "MED")
        stats = stats_by_player_id.get(player_id, {})

        result = calculate_player_points(stats, position)
        total_pts += result["total_points"]

        players_result.append({
            "player_id":     str(player_id),
            "player_name":   player.get("name", "?"),
            "position":      position,
            "position_slot": item.get("position_slot"),
            "points":        result["total_points"],
            "breakdown":     result["breakdown"],
            "is_mvp":        stats.get("is_mvp", False),
            "minutes":       stats.get("minutes", 0),
            "goals":         stats.get("goals", 0),
            "assists":       stats.get("assists", 0),
            "team_shield":   player_team.get("shield_url", "") if player_team else "",
            "team_name":     player_team.get("short_name", "") if player_team else "",
        })

    return {
        "has_lineup":   True,
        "team_name":    team.get("name", "Mi Equipo"),
        "total_points": total_pts,
        "dt_points":    0,
        "players":      players_result,
        "processed":    len(all_stats) > 0,
        "jornada_id":   jornada_id,
    }

# ──────────────────────────────────────────────────────────────────────────────
#  LIVE SCORES — Caché 55 segundos
# ──────────────────────────────────────────────────────────────────────────────
_live_scores_cache: dict = {"data": None, "fetched_at": None}
_LIVE_CACHE_TTL = 55  # seconds

@api_router.get("/jornadas/current/live-scores")
async def get_live_scores():
    """
    Retorna los partidos en curso o de hoy.
    Llama a 365Scores API y cachea 55 segundos.
    """
    global _live_scores_cache
    now = datetime.utcnow()

    # Check cache
    if _live_scores_cache["data"] is not None and _live_scores_cache["fetched_at"]:
        age = (now - _live_scores_cache["fetched_at"]).total_seconds()
        if age < _LIVE_CACHE_TTL:
            return _live_scores_cache["data"]

    # Fetch today's games from 365Scores
    today_start = now.replace(hour=0, minute=0, second=0)
    today_end = now.replace(hour=23, minute=59, second=59)

    from services.scores_service import _fetch_365scores, _normalize_name, _STATUS_MAP

    games = await _fetch_365scores(today_start, today_end)

    live_matches = []
    all_matches = []

    for g in games:
        status_grp = g.get("statusGroup", 1)
        status = _STATUS_MAP.get(status_grp, "scheduled")

        home_name = _normalize_name(g.get("homeCompetitor", {}).get("name", ""))
        away_name = _normalize_name(g.get("awayCompetitor", {}).get("name", ""))
        home_score = g.get("homeCompetitor", {}).get("score")
        away_score = g.get("awayCompetitor", {}).get("score")
        game_time = g.get("gameTimeDisplay", "")
        start_time = g.get("startTime", "")

        match_data = {
            "home_name": home_name,
            "away_name": away_name,
            "home_score": int(home_score) if home_score is not None else None,
            "away_score": int(away_score) if away_score is not None else None,
            "status": status,
            "game_time": game_time,
            "start_time": start_time,
        }
        all_matches.append(match_data)
        if status == "live":
            live_matches.append(match_data)

    # ── Fallback a DB cuando 365Scores no devuelve datos ─────────────────────
    # Si la API externa no tiene partidos hoy, consultar DB por matches "live"
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
        "live_matches":  live_matches,
        "all_today":   all_matches,
        "fetched_at":  now.isoformat(),
        "source":      "365scores" if games else ("db_fallback" if live_matches else "empty"),
    }

    _live_scores_cache["data"] = result
    _live_scores_cache["fetched_at"] = now
    return result



async def get_fantasy_rankings():
    """Get fantasy rankings"""
    # Get all fantasy teams with their users
    teams = await db.fantasy_teams.find().to_list(1000)
    
    rankings = []
    for team in teams:
        user = await db.users.find_one({"_id": team["user_id"]})
        if user:
            # Get total fantasy points from fantasy_points_log
            points = await db.fantasy_points_log.find({
                "user_id": user["_id"]
            }).to_list(1000)
            
            total_points = sum(p.get("total_points", 0) for p in points)
            
            rankings.append({
                "user_id": str(user["_id"]),
                "team_name": team["name"],
                "display_name": user["display_name"],
                "points": total_points
            })
    
    # Sort by points
    rankings.sort(key=lambda x: x["points"], reverse=True)
    
    # Add positions
    for idx, ranking in enumerate(rankings, 1):
        ranking["position"] = idx
    
    return {"rankings": rankings}

# ============ ADMIN ROUTES FOR FANTASY ============

@api_router.post("/admin/seed-players")
async def seed_players():
    """Seed players for all teams"""
    teams = await db.teams.find().to_list(100)
    
    if len(teams) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes crear los equipos"
        )
    
    # Clear existing players
    await db.players.delete_many({})
    
    positions = ["POR", "DEF", "MED", "DEL"]
    position_names = {
        "POR": ["Portero", "Arquero"],
        "DEF": ["Defensa Central", "Lateral Derecho", "Lateral Izquierdo"],
        "MED": ["Mediocampista", "Volante", "Medio Centro"],
        "DEL": ["Delantero", "Extremo", "Punta"]
    }
    
    players_created = 0
    
    for team in teams:
        # Create players for each position
        # Porteros (2)
        for i in range(2):
            player = {
                "name": f"{position_names['POR'][i % len(position_names['POR'])]} {i+1}",
                "team_id": team["_id"],
                "position": "POR",
                "number": i + 1,
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0
                },
                "created_at": datetime.utcnow()
            }
            await db.players.insert_one(player)
            players_created += 1
        
        # Defensas (6)
        for i in range(6):
            player = {
                "name": f"{position_names['DEF'][i % len(position_names['DEF'])]} {i+1}",
                "team_id": team["_id"],
                "position": "DEF",
                "number": i + 3,
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0
                },
                "created_at": datetime.utcnow()
            }
            await db.players.insert_one(player)
            players_created += 1
        
        # Mediocampistas (8)
        for i in range(8):
            player = {
                "name": f"{position_names['MED'][i % len(position_names['MED'])]} {i+1}",
                "team_id": team["_id"],
                "position": "MED",
                "number": i + 9,
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0
                },
                "created_at": datetime.utcnow()
            }
            await db.players.insert_one(player)
            players_created += 1
        
        # Delanteros (5)
        for i in range(5):
            player = {
                "name": f"{position_names['DEL'][i % len(position_names['DEL'])]} {i+1}",
                "team_id": team["_id"],
                "position": "DEL",
                "number": i + 17,
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0
                },
                "created_at": datetime.utcnow()
            }
            await db.players.insert_one(player)
            players_created += 1
    
    logger.info(f"Seeded {players_created} players for {len(teams)} teams")
    
    return {
        "message": f"Se crearon {players_created} jugadores para {len(teams)} equipos",
        "players_count": players_created,
        "teams_count": len(teams)
    }

@api_router.post("/admin/seed-real-data")
async def seed_real_data():
    """Seed database with REAL Liga MX teams and players from real_liga_mx_data.py"""
    import random
    
    logger.info("🏟️ Seeding REAL Liga MX data...")
    
    # Clear existing data
    await db.teams.delete_many({})
    await db.players.delete_many({})
    await db.jornadas.delete_many({})
    await db.matches.delete_many({})
    
    teams_created = 0
    players_created = 0
    team_ids = []
    
    for team_data in LIGA_MX_TEAMS:
        # Insert team
        team_doc = {
            "name": team_data["name"],
            "short_name": team_data["short_name"],
            "color": team_data.get("color", "#000000"),
            "shield_url": team_data["shield_url"],
            "created_at": datetime.utcnow()
        }
        team_result = await db.teams.insert_one(team_doc)
        team_id = team_result.inserted_id
        team_ids.append(team_id)
        teams_created += 1
        
        # Insert players for this team
        for player_data in team_data.get("players", []):
            player_doc = {
                "name": player_data["name"],
                "team_id": team_id,
                "position": player_data["position"],
                "number": player_data["number"],
                "stats": {
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "defensive_actions": 0
                },
                "created_at": datetime.utcnow()
            }
            await db.players.insert_one(player_doc)
            players_created += 1
    
    # Create 17 jornadas for the season with dates relative to TODAY
    now = datetime.utcnow()
    ACTIVE_WEEK = 11  # La temporada va por la jornada 11 (mitad de temporada)
    jornadas_created = 0
    
    for week in range(1, 18):
        # Fechas relativas a hoy: jornada 11 = esta semana, anteriores = pasadas, siguientes = futuras
        weeks_from_active = week - ACTIVE_WEEK
        week_start = now + timedelta(weeks=weeks_from_active)
        week_end = week_start + timedelta(days=7)
        
        is_past = weeks_from_active < 0
        is_current = weeks_from_active == 0
        week_status = "finished" if is_past else ("in_progress" if is_current else "upcoming")
        match_status_val = "finished" if is_past else "scheduled"
        
        jornada_data = {
            "week_number": week,
            "start_date": week_start,
            "end_date": week_end,
            "status": week_status,
            "is_active": is_current,  # Solo jornada 11 activa
            "created_at": now
        }
        
        jornada_result = await db.jornadas.insert_one(jornada_data)
        jornada_id = jornada_result.inserted_id
        
        # Shuffle teams and create 9 matches per jornada
        shuffled = list(team_ids)
        random.shuffle(shuffled)
        
        matches = []
        for i in range(0, min(len(shuffled), 18), 2):
            if i + 1 < len(shuffled):
                match = {
                    "jornada_id": jornada_id,
                    "home_team_id": shuffled[i],
                    "away_team_id": shuffled[i + 1],
                    "start_at": week_start + timedelta(hours=i),
                    "status": match_status_val,
                    "home_score": None,
                    "away_score": None,
                    "created_at": now
                }
                matches.append(match)
        
        if matches:
            await db.matches.insert_many(matches)
        
        jornadas_created += 1
    
    logger.info(f"✅ REAL data seeded: {teams_created} teams, {players_created} players, {jornadas_created} jornadas")
    
    return {
        "message": f"🏟️ Datos REALES de Liga MX cargados exitosamente",
        "teams_created": teams_created,
        "players_created": players_created,
        "jornadas_created": jornadas_created,
        "teams": [t["name"] for t in LIGA_MX_TEAMS]
    }

# ============ ACHIEVEMENTS & STREAKS SYSTEM ============

# ─── CATÁLOGO DE LOGROS ─────────────────────────────────────────────────────
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


# ─── HELPER: otorgar un logro ────────────────────────────────────────────────
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


# ─── HELPER: actualizar racha de participación ───────────────────────────────
async def update_participation_streak(user_id) -> dict:
    doc = await db.user_streaks.find_one({"user_id": user_id})
    if not doc:
        await db.user_streaks.insert_one({
            "user_id": user_id,
            "quiniela_streak":       1,
            "quiniela_streak_best":  1,
            "win_streak":            0,
            "win_streak_best":       0,
            "correct_answers_streak":0,
            "correct_answers_best":  0,
            "fantasy_streak":        0,
            "fantasy_streak_best":   0,
            "updated_at": datetime.utcnow()
        })
        return {"current": 1, "best": 1, "is_new_record": True}

    new_streak = doc.get("quiniela_streak", 0) + 1
    best       = max(new_streak, doc.get("quiniela_streak_best", 0))
    await db.user_streaks.update_one(
        {"user_id": user_id},
        {"$set": {
            "quiniela_streak":       new_streak,
            "quiniela_streak_best":  best,
            "updated_at":            datetime.utcnow()
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


# ─── HELPER: actualizar racha de victorias en liga ───────────────────────────
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


# ─── HELPER: actualizar racha de predicciones correctas ─────────────────────
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


# ─── FUNCIÓN PRINCIPAL: calcular logros post-jornada ────────────────────────
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
        # Busca las 4 jornadas más recientes con partidos terminados
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
    fantasy_lineup_count = await db.fantasy_teams.count_documents({"user_id": user_id})
    if fantasy_lineup_count >= 3:
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


# ─── ENDPOINTS ───────────────────────────────────────────────────────────────

@api_router.get("/achievements/catalog")
async def get_achievements_catalog():
    """Catálogo público de logros."""
    return {
        "achievements": [
            {**a, "description": "???" if a["secret"] else a["description"],
                  "emoji": "🔒" if a["secret"] else a["emoji"]}
            for a in ACHIEVEMENTS_CATALOG
        ],
        "total": len(ACHIEVEMENTS_CATALOG)
    }


@api_router.get("/achievements/my")
async def get_my_achievements(current_user: dict = Depends(get_current_user)):
    """Logros + rachas del usuario autenticado."""
    user_id = current_user["_id"]

    unlocked_docs = await db.user_achievements.find({"user_id": user_id}).to_list(200)
    unlocked_map  = {d["achievement_id"]: d["unlocked_at"] for d in unlocked_docs}

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

    # Desbloqueados primero
    result.sort(key=lambda x: (not x["unlocked"], x["category"]))

    return {
        "achievements":    result,
        "total":           len(result),
        "unlocked_count":  len(unlocked_map),
        "streaks": {
            "quiniela_current":       streak_doc.get("quiniela_streak", 0),
            "quiniela_best":          streak_doc.get("quiniela_streak_best", 0),
            "win_current":            streak_doc.get("win_streak", 0),
            "win_best":               streak_doc.get("win_streak_best", 0),
            "correct_current":        streak_doc.get("correct_answers_streak", 0),
            "correct_best":           streak_doc.get("correct_answers_best", 0),
            "fantasy_current":        streak_doc.get("fantasy_streak", 0),
        }
    }


@api_router.post("/admin/achievements/check/{jornada_id}")
async def trigger_achievement_check(jornada_id: str):
    """Admin: verifica y otorga logros a TODOS los usuarios tras una jornada."""
    all_users = await db.users.find().to_list(10000)
    summary = []

    for user in all_users:
        new = await check_and_award_achievements_after_jornada(user["_id"], jornada_id)
        if new:
            summary.append({
                "user":             user.get("display_name"),
                "new_achievements": new
            })

    # Resetear rachas de usuarios que NO participaron esta jornada
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


# ============ USER STATS ============

@api_router.get("/stats/my")
async def get_my_stats(current_user: dict = Depends(get_current_user)):
    """Retorna estadísticas completas del usuario autenticado para la temporada."""
    user_id = current_user["_id"]

    # 1. Quiniela points logs
    quiniela_logs = await db.points_log.find(
        {"user_id": user_id, "source": "QUINIELA"}
    ).to_list(1000)

    total_quiniela_pts = sum(log.get("points", 0) for log in quiniela_logs)
    jornada_ids_quiniela = list(set(log["jornada_id"] for log in quiniela_logs))
    jornadas_quiniela = len(jornada_ids_quiniela)
    mejor_jornada = max((log.get("points", 0) for log in quiniela_logs), default=0)
    # Cada punto = 1 acierto en quiniela
    total_aciertos = total_quiniela_pts
    promedio_aciertos = round(total_aciertos / jornadas_quiniela, 1) if jornadas_quiniela > 0 else 0

    # 2. Fantasy participation
    fantasy_jornadas = await db.fantasy_lineups.distinct("jornada_id", {"user_id": user_id})
    jornadas_fantasy = len(fantasy_jornadas)

    # 3. Fantasy points
    fantasy_pts_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$total_points"}}}
    ]
    fantasy_pts_result = await db.fantasy_points_log.aggregate(fantasy_pts_pipeline).to_list(1)
    total_fantasy_pts = fantasy_pts_result[0]["total"] if fantasy_pts_result else 0

    # 4. Total de puntos acumulados (quiniela + fantasy)
    total_puntos = total_quiniela_pts + total_fantasy_pts

    # 5. Win rate - % de jornadas donde quedó en Top 3 (global)
    top3_count = 0
    mejor_posicion = None
    if jornada_ids_quiniela:
        for jornada_id in jornada_ids_quiniela:
            user_pts = sum(
                log.get("points", 0)
                for log in quiniela_logs
                if log["jornada_id"] == jornada_id
            )
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

    # 6. Ligas activas
    ligas_activas = await db.league_members.count_documents({"user_id": user_id})

    return {
        "total_puntos": total_puntos,
        "jornadas_quiniela": jornadas_quiniela,
        "mejor_jornada": mejor_jornada,
        "win_rate": win_rate,
        "total_aciertos": total_aciertos,
        "promedio_aciertos": promedio_aciertos,
        "jornadas_fantasy": jornadas_fantasy,
        "mejor_posicion": mejor_posicion,
        "ligas_activas": ligas_activas,
    }

# ============ ADMIN STATS DASHBOARD ============

ADMIN_EMAIL = "contacto@distrito.digital"

@api_router.get("/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Dashboard de métricas para el admin de FuchoMX"""
    if current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso restringido")

    from datetime import datetime, timedelta
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # Usuarios
    total_usuarios = await db.users.count_documents({})
    nuevos_hoy = await db.users.count_documents({"created_at": {"$gte": today_start.isoformat()}})
    nuevos_semana = await db.users.count_documents({"created_at": {"$gte": week_start.isoformat()}})
    nuevos_mes = await db.users.count_documents({"created_at": {"$gte": month_start.isoformat()}})

    # Jornadas
    total_jornadas = await db.jornadas.count_documents({})
    jornada_activa = await db.jornadas.find_one({"is_active": True})

    # Quinielas / predicciones
    total_predicciones = await db.quiniela_selections.count_documents({}) if hasattr(db, 'quiniela_selections') else 0
    try:
        total_predicciones = await db.quiniela_selections.count_documents({})
    except:
        total_predicciones = 0

    # Ligas
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
                "id": str(liga["_id"]),
                "nombre": liga.get("name", "Sin nombre"),
                "modo": liga.get("mode", "quiniela"),
                "codigo": liga.get("code", ""),
                "creador": owner.get("display_name", owner.get("email", "?")) if owner else "?",
                "miembros": miembros,
                "creada": liga["created_at"].isoformat() if liga.get("created_at") else "",
            })
    except Exception as e:
        total_ligas = 0
        ligas_detalle = []

    # Fantasy
    try:
        total_fantasy = await db.fantasy_lineups.count_documents({})
    except:
        total_fantasy = 0

    # Últimos 5 usuarios registrados
    ultimos_usuarios = await db.users.find(
        {}, {"email": 1, "display_name": 1, "created_at": 1, "total_points": 1}
    ).sort("created_at", -1).limit(5).to_list(5)

    for u in ultimos_usuarios:
        u["_id"] = str(u["_id"])

    return {
        "usuarios": {
            "total": total_usuarios,
            "nuevos_hoy": nuevos_hoy,
            "nuevos_semana": nuevos_semana,
            "nuevos_mes": nuevos_mes,
            "ultimos": ultimos_usuarios,
        },
        "jornadas": {
            "total": total_jornadas,
            "activa": jornada_activa.get("week_number") if jornada_activa else None,
        },
        "predicciones": {
            "total": total_predicciones,
        },
        "ligas": {
            "total": total_ligas,
            "detalle": ligas_detalle,
        },
        "fantasy": {
            "total_lineups": total_fantasy,
        },
    }



# ============ ADMIN BRACKET UPDATE ============

class BracketUpdateRequest(BaseModel):
    cuartos_winners: Optional[List[str]] = None  # ["PUM", "GDL", "CAZ", "PAC"] en orden
    semis_left_winner: Optional[str] = None      # Ganador SF Izquierda
    semis_right_winner: Optional[str] = None     # Ganador SF Derecha
    champion: Optional[str] = None               # Campeón

@api_router.post("/admin/bracket/update")
async def update_bracket_results(
    data: BracketUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Actualiza los resultados del bracket de liguilla (solo admin)"""
    if current_user.get("email") != "contacto@distrito.digital":
        raise HTTPException(status_code=403, detail="Acceso restringido")

    update_doc = {"updated_at": datetime.utcnow()}

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


@api_router.get("/liguilla/results")
async def get_liguilla_results():
    """Obtiene los resultados actuales del bracket"""
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


# ============ ROOT ============

@api_router.get("/")
async def root():
    return {
        "message": "Quiniela Liga MX API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth/*",
            "teams": "/api/teams",
            "jornadas": "/api/jornadas/*",
            "quiniela": "/api/quiniela/*",
            "fantasy": "/api/fantasy/*",
            "players": "/api/players",
            "admin": "/api/admin/*"
        }
    }

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[
        "https://fuchomx.pages.dev",
        "https://fucho.com.mx",
        "https://www.fucho.com.mx",
        "https://quiniela-fantasy.preview.emergentagent.com",
        "http://localhost:3000",
        "http://localhost:8081",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    logger.info("🛑 MongoDB connection closed")

# ============ AUTO-SCHEDULER ============
import asyncio

_scheduler_task: asyncio.Task | None = None

async def _auto_update_scores():
    """
    Scheduler que corre en background continuamente.
    - Si hay partidos hoy: actualiza scores cada 60 segundos
    - Si hay partido live: actualiza cada 45 segundos
    - Si no hay partidos hoy: revisa cada 10 minutos
    - Al terminar todos los partidos: procesa jornada automáticamente
    """
    logger.info("🤖 Auto-scheduler iniciado")
    
    while True:
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)

            from services.scores_service import _fetch_365scores, _normalize_name, _STATUS_MAP

            # ── Verificar si hay partidos hoy ─────────────────────────────
            games = await _fetch_365scores(today_start, today_end)
            
            if not games:
                # Sin partidos hoy — revisar cada 10 minutos
                logger.debug("📅 Sin partidos hoy. Próxima revisión en 10 min.")
                await asyncio.sleep(600)
                continue

            # ── Clasificar partidos ───────────────────────────────────────
            live_games    = [g for g in games if _STATUS_MAP.get(g.get("statusGroup", 1)) == "live"]
            finished_games = [g for g in games if _STATUS_MAP.get(g.get("statusGroup", 1)) == "finished"]
            scheduled_games = [g for g in games if _STATUS_MAP.get(g.get("statusGroup", 1)) == "scheduled"]

            logger.info(
                f"⚽ Partidos hoy: {len(games)} total | "
                f"{len(live_games)} live | {len(finished_games)} terminados | {len(scheduled_games)} pendientes"
            )

            # ── Actualizar scores en DB si hay partidos live o terminados ─
            if live_games or finished_games:
                jornada = await db.jornadas.find_one({"is_active": True})
                if jornada:
                    jornada_id = str(jornada["_id"])
                    try:
                        scores_result = await _svc_get_match_results(jornada_id, db)
                        updated = scores_result.get("matches_updated", 0)
                        if updated > 0:
                            logger.info(f"✅ Scheduler: {updated} partidos actualizados en jornada {jornada.get('week_number')}")
                    except Exception as e:
                        logger.error(f"❌ Scheduler scores error: {e}")

            # ── Verificar si todos los partidos terminaron ─────────────────
            if finished_games and not live_games and not scheduled_games:
                logger.info("🏁 Todos los partidos del día terminaron — verificando proceso de jornada")
                jornada = await db.jornadas.find_one({"is_active": True})
                if jornada and not jornada.get("processed", False):
                    try:
                        proc_result = await _process_jornada_core(str(jornada["_id"]))
                        logger.info(
                            f"🎉 Jornada {jornada.get('week_number')} procesada automáticamente: "
                            f"quiniela={proc_result.get('quiniela_updated')} usuarios, "
                            f"fantasy={proc_result.get('fantasy_updated')} equipos"
                        )
                    except Exception as e:
                        logger.error(f"❌ Scheduler process_jornada error: {e}")

            # ── Intervalo según estado ─────────────────────────────────────
            if live_games:
                sleep_secs = 45   # Partido en curso: actualizar cada 45s
            elif scheduled_games:
                sleep_secs = 120  # Partidos pendientes hoy: revisar cada 2 min
            else:
                sleep_secs = 300  # Solo terminados: revisar cada 5 min

            logger.debug(f"⏱ Próxima actualización en {sleep_secs}s")
            await asyncio.sleep(sleep_secs)

        except asyncio.CancelledError:
            logger.info("🛑 Auto-scheduler cancelado")
            break
        except Exception as e:
            logger.error(f"❌ Error inesperado en scheduler: {e}")
            await asyncio.sleep(60)  # En caso de error, reintentar en 1 min


@app.on_event("startup")
async def start_scheduler():
    global _scheduler_task
    _scheduler_task = asyncio.create_task(_auto_update_scores())
    logger.info("🚀 Auto-scheduler registrado en startup")


@app.on_event("shutdown")
async def stop_scheduler():
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    logger.info("🛑 Auto-scheduler detenido")
