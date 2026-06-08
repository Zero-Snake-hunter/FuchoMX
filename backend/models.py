from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

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


def serialize_user(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        display_name=user["display_name"],
        avatar_base64=user.get("avatar_base64"),
        total_points=user.get("total_points", 0),
        created_at=user["created_at"],
    )


# ── Quiniela ──────────────────────────────────────────────────────────────────

class QuinielaSubmit(BaseModel):
    jornada_id: str
    selections: List[dict]  # [{match_id: str, selection: str}]


# ── Leagues ───────────────────────────────────────────────────────────────────

MAX_MEMBERS_FREE = 25


class CreateLeagueRequest(BaseModel):
    name: str
    mode: str = "quiniela"  # "quiniela" o "fantasy"


class JoinLeagueRequest(BaseModel):
    code: str


# ── Admin ─────────────────────────────────────────────────────────────────────

class UpdateScoreRequest(BaseModel):
    home_score: int
    away_score: int


# ── Fantasy ───────────────────────────────────────────────────────────────────

class FantasyTeamCreate(BaseModel):
    name: str


class FantasyLineupSubmit(BaseModel):
    jornada_id: str
    players: List[dict]  # [{player_id, position_slot}]
    dt_team_id: Optional[str] = None  # Director Técnico


# ── Liguilla ──────────────────────────────────────────────────────────────────

class BracketUpdateRequest(BaseModel):
    cuartos_winners: Optional[List[str]] = None
    semis_left_winner: Optional[str] = None
    semis_right_winner: Optional[str] = None
    champion: Optional[str] = None


# ── Push Notifications ────────────────────────────────────────────────────────

class RegisterPushTokenRequest(BaseModel):
    token: str
