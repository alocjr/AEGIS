"""Persistência OAuth MCP (clientes DCR, codes, tokens, pending login)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database import get_db

COL_CLIENTS = "mcp_oauth_clients"
COL_CODES = "mcp_oauth_codes"
COL_TOKENS = "mcp_oauth_tokens"
COL_PENDING = "mcp_oauth_pending"
COL_REFRESH = "mcp_oauth_refresh"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_oauth_indexes() -> None:
    db = get_db()
    db[COL_CLIENTS].create_index("client_id", unique=True)
    db[COL_CODES].create_index("code", unique=True)
    db[COL_CODES].create_index("expires_at", expireAfterSeconds=0)
    db[COL_TOKENS].create_index("token", unique=True)
    db[COL_TOKENS].create_index("expires_at", expireAfterSeconds=0)
    db[COL_REFRESH].create_index("token", unique=True)
    db[COL_PENDING].create_index("sid", unique=True)
    db[COL_PENDING].create_index("expires_at", expireAfterSeconds=0)


def save_client(doc: dict[str, Any]) -> None:
    get_db()[COL_CLIENTS].update_one(
        {"client_id": doc["client_id"]},
        {"$set": {**doc, "updated_at": _now()}},
        upsert=True,
    )


def get_client(client_id: str) -> dict[str, Any] | None:
    return get_db()[COL_CLIENTS].find_one({"client_id": client_id}, {"_id": 0})


def save_pending(sid: str, payload: dict[str, Any], expires_at: datetime) -> None:
    get_db()[COL_PENDING].update_one(
        {"sid": sid},
        {"$set": {**payload, "sid": sid, "expires_at": expires_at}},
        upsert=True,
    )


def pop_pending(sid: str) -> dict[str, Any] | None:
    return get_db()[COL_PENDING].find_one_and_delete({"sid": sid})


def get_pending(sid: str) -> dict[str, Any] | None:
    doc = get_db()[COL_PENDING].find_one({"sid": sid})
    if not doc:
        return None
    exp = doc.get("expires_at")
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < _now():
            get_db()[COL_PENDING].delete_one({"sid": sid})
            return None
    return doc


def save_code(doc: dict[str, Any]) -> None:
    get_db()[COL_CODES].insert_one(doc)


def get_code(code: str) -> dict[str, Any] | None:
    return get_db()[COL_CODES].find_one({"code": code})


def delete_code(code: str) -> None:
    get_db()[COL_CODES].delete_one({"code": code})


def save_access_token(doc: dict[str, Any]) -> None:
    get_db()[COL_TOKENS].insert_one(doc)


def get_access_token_doc(token: str) -> dict[str, Any] | None:
    doc = get_db()[COL_TOKENS].find_one({"token": token})
    if not doc or doc.get("revoked"):
        return None
    return doc


def save_refresh_token(doc: dict[str, Any]) -> None:
    get_db()[COL_REFRESH].insert_one(doc)


def get_refresh_token_doc(token: str) -> dict[str, Any] | None:
    doc = get_db()[COL_REFRESH].find_one({"token": token})
    if not doc or doc.get("revoked"):
        return None
    return doc


def revoke_token_string(token: str) -> None:
    db = get_db()
    db[COL_TOKENS].update_one({"token": token}, {"$set": {"revoked": True}})
    db[COL_REFRESH].update_one({"token": token}, {"$set": {"revoked": True}})
