"""Controle de tentativas falhas de login e bloqueio temporário de conta."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from pymongo.database import Database

from app.security import verify_password

# Hash bcrypt de "secret" — usado quando o email não existe (mitiga timing oracle).
_DUMMY_PASSWORD_HASH = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxnRGp3p9.qHkhUkOQNaWYzQdu6G"

MAX_FAILED_LOGIN_ATTEMPTS = 6
LOGIN_LOCKOUT_MINUTES = 15


def _is_locked(user: dict | None, now: datetime) -> bool:
    if not user:
        return False
    locked_until = user.get("locked_until")
    if locked_until is None:
        return False
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return locked_until > now


def authenticate_login(db: Database, email: str, password: str) -> dict:
    """Valida credenciais, aplica lockout e retorna o documento do usuário."""
    now = datetime.now(timezone.utc)
    normalized = email.strip().lower()
    user = db.users.find_one({"email": normalized})

    if _is_locked(user, now):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Conta temporariamente bloqueada. Tente novamente em alguns minutos.",
        )

    password_hash = user["password_hash"] if user else _DUMMY_PASSWORD_HASH
    valid = verify_password(password, password_hash)

    if not user or not valid:
        if user:
            attempts = int(user.get("failed_login_attempts") or 0) + 1
            update: dict = {
                "failed_login_attempts": attempts,
                "updated_at": now,
            }
            if attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                update["locked_until"] = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
            db.users.update_one({"_id": user["_id"]}, {"$set": update})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas",
        )

    db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"failed_login_attempts": 0, "updated_at": now},
            "$unset": {"locked_until": ""},
        },
    )
    return user
