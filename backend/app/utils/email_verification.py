from datetime import datetime, timedelta, timezone

from pymongo.database import Database

from app.config import settings
from app.security import create_password_reset_token, hash_password_reset_token
from app.utils.email import send_verification_email


def issue_and_send_verification(db: Database, user: dict) -> None:
    """Gera token de verificação, persiste hash e envia email."""
    now = datetime.now(timezone.utc)
    token = create_password_reset_token()
    token_hash = hash_password_reset_token(token)
    expires_at = now.replace(microsecond=0) + timedelta(minutes=settings.email_verification_expire_minutes)

    db.email_verifications.update_many(
        {"user_id": user["_id"], "used_at": None},
        {"$set": {"used_at": now, "invalidated_reason": "replaced_by_new_request"}},
    )
    db.email_verifications.insert_one(
        {
            "user_id": user["_id"],
            "token_hash": token_hash,
            "created_at": now,
            "expires_at": expires_at,
            "used_at": None,
        }
    )
    send_verification_email(user["email"], token)


def verify_email_token(db: Database, token: str) -> bool:
    """Valida token e marca email_verified=True. Retorna False se inválido."""
    now = datetime.now(timezone.utc)
    token_hash = hash_password_reset_token(token)
    verification_doc = db.email_verifications.find_one(
        {
            "token_hash": token_hash,
            "used_at": None,
            "expires_at": {"$gt": now},
        }
    )
    if not verification_doc:
        return False

    db.users.update_one(
        {"_id": verification_doc["user_id"]},
        {"$set": {"email_verified": True, "updated_at": now}},
    )
    db.email_verifications.update_one(
        {"_id": verification_doc["_id"]},
        {"$set": {"used_at": now}},
    )
    return True
