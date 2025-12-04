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
    """Create current jornada with matches"""
    # Get all teams
    teams = await db.teams.find().to_list(100)
    if len(teams) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes crear los equipos usando /api/admin/seed-teams"
        )
    
    # Create jornada
    jornada_data = {
        "week_number": 1,
        "start_date": datetime.utcnow() + timedelta(days=2),
        "end_date": datetime.utcnow() + timedelta(days=4),
        "status": "upcoming",  # upcoming, in_progress, finished
        "created_at": datetime.utcnow()
    }
    
    jornada_result = await db.jornadas.insert_one(jornada_data)
    jornada_id = jornada_result.inserted_id
    
    # Create matches (9 matches for 18 teams)
    matches = []
    for i in range(0, 18, 2):
        if i + 1 < len(teams):
            match = {
                "jornada_id": jornada_id,
                "home_team_id": teams[i]["_id"],
                "away_team_id": teams[i + 1]["_id"],
                "start_at": datetime.utcnow() + timedelta(days=2, hours=i),
                "status": "scheduled",  # scheduled, live, finished
                "home_score": None,
                "away_score": None,
                "created_at": datetime.utcnow()
            }
            matches.append(match)
    
    if matches:
        await db.matches.insert_many(matches)
    
    logger.info(f"Created jornada {jornada_data['week_number']} with {len(matches)} matches")
    
    return {
        "message": f"Se creó la jornada {jornada_data['week_number']} con {len(matches)} partidos",
        "jornada_id": str(jornada_id),
        "matches_count": len(matches)
    }

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
        match["home_team"] = {
            "id": str(home_team["_id"]),
            "name": home_team["name"],
            "short_name": home_team["short_name"],
            "shield_url": home_team["shield_url"]
        }
        match["away_team"] = {
            "id": str(away_team["_id"]),
            "name": away_team["name"],
            "short_name": away_team["short_name"],
            "shield_url": away_team["shield_url"]
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
