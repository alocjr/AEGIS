from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pymongo.database import Database

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    GenericMessageResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.security import (
    create_access_token,
    create_password_reset_token,
    hash_password,
    hash_password_reset_token,
)
from app.utils.email import send_password_reset_email
from app.limiter import limiter
from app.utils.login_lockout import authenticate_login
from app.utils.rate_limit import enforce_email_rate_limit


logger = logging.getLogger("aegis")


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Database = Depends(get_db)):
    existing = db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")

    user_doc = {
        "name": payload.name.strip(),
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc),
    }
    result = db.users.insert_one(user_doc)
    token = create_access_token(str(result.inserted_id))

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": str(result.inserted_id), "name": user_doc["name"], "email": user_doc["email"], "is_admin": False},
    }


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Database = Depends(get_db)):
    enforce_email_rate_limit(db, payload.email, "login")
    user = authenticate_login(db, payload.email, payload.password)

    token = create_access_token(str(user["_id"]))
    is_admin = bool(user.get("is_admin", False))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": str(user["_id"]), "name": user["name"], "email": user["email"], "is_admin": is_admin},
    }


@router.get("/me")
def me(user=Depends(get_current_user), db: Database = Depends(get_db)):
    is_admin = bool(user.get("is_admin", False))
    from_progress = db.progress.distinct("course_slug", {"user_id": user["_id"]})
    from_user = user.get("course_slugs") or ([user.get("course_slug")] if user.get("course_slug") else [])
    course_slugs = list(dict.fromkeys(from_progress + from_user))  # união, ordem progress depois user
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "is_admin": is_admin,
        "course_slugs": course_slugs,
    }


@router.post("/forgot-password", response_model=GenericMessageResponse)
@limiter.limit("5/minute")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Database = Depends(get_db)):
    """Inicia reset de senha sem revelar se o email existe."""
    enforce_email_rate_limit(db, payload.email, "forgot_password")
    now = datetime.now(timezone.utc)
    message = "Se o email existir, enviaremos instruções para reset de senha."
    user = db.users.find_one({"email": payload.email.lower()})
    if not user:
        return {"message": message}

    token = create_password_reset_token()
    token_hash = hash_password_reset_token(token)
    expires_at = now.replace(microsecond=0) + timedelta(minutes=settings.password_reset_expire_minutes)

    # invalida tokens anteriores ainda ativos para o mesmo usuário
    db.password_resets.update_many(
        {"user_id": user["_id"], "used_at": None},
        {"$set": {"used_at": now, "invalidated_reason": "replaced_by_new_request"}},
    )
    db.password_resets.insert_one(
        {
            "user_id": user["_id"],
            "token_hash": token_hash,
            "created_at": now,
            "expires_at": expires_at,
            "used_at": None,
        }
    )

    send_password_reset_email(user["email"], token)

    return {"message": message}


@router.post("/reset-password", response_model=GenericMessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Database = Depends(get_db)):
    now = datetime.now(timezone.utc)
    token_hash = hash_password_reset_token(payload.token)
    reset_doc = db.password_resets.find_one(
        {
            "token_hash": token_hash,
            "used_at": None,
            "expires_at": {"$gt": now},
        }
    )
    if not reset_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou expirado")

    db.users.update_one(
        {"_id": reset_doc["user_id"]},
        {
            "$set": {
                "password_hash": hash_password(payload.new_password),
                "updated_at": now,
            }
        },
    )
    db.password_resets.update_one(
        {"_id": reset_doc["_id"]},
        {"$set": {"used_at": now}},
    )
    return {"message": "Senha atualizada com sucesso."}
