"""Rate limiting por email persistido no MongoDB."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from pymongo.database import Database

_AUTH_RATE_SCOPES = ("login", "forgot_password", "resend_verification")


def enforce_email_rate_limit(
    db: Database,
    email: str,
    scope: str,
    *,
    limit: int = 5,
    window_minutes: int = 1,
) -> None:
    if scope not in _AUTH_RATE_SCOPES:
        raise ValueError(f"scope inválido: {scope}")

    normalized = email.strip().lower()
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)
    count = db.auth_rate_limits.count_documents(
        {"email": normalized, "scope": scope, "at": {"$gte": window_start}}
    )
    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Aguarde um momento e tente novamente.",
        )
    db.auth_rate_limits.insert_one({"email": normalized, "scope": scope, "at": now})
