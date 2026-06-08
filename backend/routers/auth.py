import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from achievements import award_achievement
from auth_utils import create_access_token, hash_password, verify_password
from database import db
from dependencies import get_current_user
from models import (
    RecoverPasswordRequest,
    RegisterPushTokenRequest,
    TokenResponse,
    UserRegister,
    UserLogin,
    UserResponse,
    serialize_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado"
        )

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

    await award_achievement(result.inserted_id, "first_login")
    access_token = create_access_token({"sub": str(result.inserted_id)})
    logger.info(f"New user registered: {user_data.email}")

    return TokenResponse(
        access_token=access_token,
        user=serialize_user(user_dict)
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )

    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )

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


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return serialize_user(current_user)


@router.post("/recover-password")
async def recover_password(request: RecoverPasswordRequest):
    user = await db.users.find_one({"email": request.email})
    if not user:
        return {"message": "Si el correo existe, recibirás instrucciones para recuperar tu contraseña"}

    # TODO: Implement email sending
    logger.info(f"Password recovery requested for: {request.email}")

    return {"message": "Si el correo existe, recibirás instrucciones para recuperar tu contraseña"}


@router.post("/push-token")
async def register_push_token(
    request: RegisterPushTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    token = request.token.strip()
    if not token.startswith("ExponentPushToken["):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de push inválido. Debe empezar con 'ExponentPushToken['",
        )
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$addToSet": {"push_tokens": token}},
    )
    logger.info(f"Push token registrado para {current_user['email']}")
    return {"message": "Token registrado"}
