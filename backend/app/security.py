from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any

import bcrypt
from jose import jwt
from passlib.context import CryptContext

from app.config import settings


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _normalize_password(password: str) -> str:
    # bcrypt aceita no maximo 72 bytes; para senhas maiores, usamos SHA-256
    # para gerar uma representacao curta e deterministica antes do bcrypt.
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) <= 72:
        return password
    return hashlib.sha256(pwd_bytes).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(_normalize_password(password))


def verify_password(password: str, password_hash: str) -> bool:
    normalized = _normalize_password(password)

    # Compatibilidade com hashes bcrypt antigos ja salvos no banco.
    if password_hash.startswith("$2a$") or password_hash.startswith("$2b$") or password_hash.startswith("$2y$"):
        try:
            return bcrypt.checkpw(normalized.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            return False

    return pwd_context.verify(normalized, password_hash)


def _jwt_key_bytes() -> bytes:
    """Chave JWT em bytes (UTF-8) para evitar erros de encoding em encode/decode."""
    k = settings.jwt_secret_key
    return k.encode("utf-8") if isinstance(k, str) else k


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": int(expire.timestamp())}
    return jwt.encode(payload, _jwt_key_bytes(), algorithm=settings.jwt_algorithm)
