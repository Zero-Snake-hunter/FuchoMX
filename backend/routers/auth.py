import logging
import secrets
from datetime import datetime, timedelta

import resend
from fastapi import APIRouter, Depends, HTTPException, status

from achievements import award_achievement
from auth_utils import create_access_token, hash_password, verify_password
from config import RESEND_API_KEY, FRONTEND_URL
from database import db
from dependencies import get_current_user
from models import (
    RecoverPasswordRequest,
    RegisterPushTokenRequest,
    ResetPasswordRequest,
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


def _recovery_email_html(display_name: str, reset_link: str) -> str:
    return f"""
    <div style="background:#0a0a0a;padding:40px;font-family:sans-serif;max-width:480px;margin:0 auto;border-radius:8px">
      <h2 style="color:#E63946;margin:0 0 4px;font-size:20px;letter-spacing:1px">FUCHO MX</h2>
      <p style="color:#ffffff;font-size:18px;font-weight:bold;margin:0 0 16px">Recupera tu contraseña</p>
      <p style="color:#aaaaaa;font-size:14px;line-height:1.6;margin:0 0 24px">
        Hola {display_name}, recibimos una solicitud para restablecer la contraseña de tu cuenta.
        Si no fuiste tú, ignora este correo.
      </p>
      <a href="{reset_link}"
         style="display:inline-block;background:#C02030;color:#ffffff;text-decoration:none;
                padding:14px 28px;border-radius:8px;font-weight:bold;font-size:15px">
        Restablecer contraseña
      </a>
      <p style="color:#555555;font-size:12px;margin:24px 0 0">
        Este enlace expira en 1 hora.<br>
        FuchoMX · Aguascalientes, México
      </p>
    </div>
    """


@router.post("/recover-password")
async def recover_password(request: RecoverPasswordRequest):
    _response = {"message": "Si el correo existe, recibirás instrucciones para recuperar tu contraseña"}
    user = await db.users.find_one({"email": request.email})
    if not user:
        return _response

    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_reset_token": token, "password_reset_expires": expires}},
    )

    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
    try:
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": "noreply@distrito.digital",
            "to": request.email,
            "subject": "Recupera tu contraseña de FuchoMX",
            "html": _recovery_email_html(user["display_name"], reset_link),
        })
        logger.info(f"Password recovery email sent to: {request.email}")
    except Exception as exc:
        logger.error(f"Error sending recovery email to {request.email}: {exc}")

    return _response


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    user = await db.users.find_one({"password_reset_token": request.token})
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido o expirado")
    if datetime.utcnow() > user.get("password_reset_expires", datetime.min):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido o expirado")

    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"password_hash": hash_password(request.new_password)},
            "$unset": {"password_reset_token": "", "password_reset_expires": ""},
        },
    )
    logger.info(f"Password reset successful for: {user['email']}")
    return {"message": "Contraseña actualizada correctamente"}


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
