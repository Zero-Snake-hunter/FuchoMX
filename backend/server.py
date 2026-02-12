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
import bcrypt
import jwt
from bson import ObjectId

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
    
    for week in range(1, 18):  # 17 jornadas
        week_start = now + timedelta(weeks=week - 1)
        week_end = week_start + timedelta(days=2)
        
        jornada_data = {
            "week_number": week,
            "start_date": week_start,
            "end_date": week_end,
            "status": "upcoming" if week > 1 else "upcoming",
            "is_active": week == 1,  # Only first jornada is active
            "created_at": now
        }
        
        jornada_result = await db.jornadas.insert_one(jornada_data)
        jornada_id = jornada_result.inserted_id
        
        # Shuffle teams for this week
        shuffled_teams = list(teams)
        random.shuffle(shuffled_teams)
        
        matches = []
        for i in range(0, min(18, len(shuffled_teams)), 2):
            if i + 1 < len(shuffled_teams):
                match = {
                    "jornada_id": jornada_id,
                    "home_team_id": shuffled_teams[i]["_id"],
                    "away_team_id": shuffled_teams[i + 1]["_id"],
                    "start_at": week_start + timedelta(hours=i),
                    "status": "scheduled",
                    "home_score": None,
                    "away_score": None,
                    "created_at": now
                }
                matches.append(match)
        
        if matches:
            await db.matches.insert_many(matches)
        
        created_jornadas.append({
            "week_number": week,
            "jornada_id": str(jornada_id),
            "is_active": week == 1,
            "matches_count": len(matches)
        })
    
    logger.info(f"Created full season with {len(created_jornadas)} jornadas")
    
    return {
        "message": f"Se crearon {len(created_jornadas)} jornadas para la temporada completa",
        "jornadas": created_jornadas
    }

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
    """Get current jornada with matches"""
    # Find upcoming or in-progress jornada
    jornada = await db.jornadas.find_one(
        {"status": {"$in": ["upcoming", "in_progress"]}},
        sort=[("week_number", 1)]
    )
    
    if not jornada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay jornada activa. Usa /api/admin/seed-jornada para crear una."
        )
    
    # Get matches for this jornada
    matches = await db.matches.find({"jornada_id": jornada["_id"]}).to_list(100)
    
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
    
    # Check if any match has started
    now = datetime.utcnow()
    for match in matches:
        if match["start_at"] < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El partido {match.get('home_team_id')} vs {match.get('away_team_id')} ya comenzó"
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
        "created_at": datetime.utcnow()
    }
    
    result = await db.private_leagues.insert_one(league_doc)
    
    # Add creator as member
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
            is_owner = str(league["owner_id"]) == str(current_user["_id"])
            
            leagues.append({
                "id": str(league["_id"]),
                "name": league["name"],
                "mode": league.get("mode", "quiniela"),
                "code": league["code"],
                "member_count": member_count,
                "is_owner": is_owner,
                "created_at": league["created_at"]
            })
    
    return {"leagues": leagues}

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
            "jornadas_played": {"$count": {}}
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
    
    logger.info(f"User {current_user['email']} submitted fantasy lineup for jornada {lineup.jornada_id}")
    
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

@api_router.get("/fantasy/rankings")
async def get_fantasy_rankings():
    """Get fantasy rankings"""
    # Get all fantasy teams with their users
    teams = await db.fantasy_teams.find().to_list(1000)
    
    rankings = []
    for team in teams:
        user = await db.users.find_one({"_id": team["user_id"]})
        if user:
            # Get total fantasy points
            points = await db.points_log.find({
                "user_id": user["_id"],
                "source": "FANTASY"
            }).to_list(1000)
            
            total_points = sum(p["points"] for p in points)
            
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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
