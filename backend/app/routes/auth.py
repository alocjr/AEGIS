from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.schemas import AuthResponse, LoginRequest, RegisterRequest
from app.security import create_access_token, hash_password, verify_password


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
def login(payload: LoginRequest, db: Database = Depends(get_db)):
    user = db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais invalidas")

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
    if not is_admin and settings.initial_admin_email:
        if (user.get("email") or "").strip().lower() == settings.initial_admin_email.strip().lower():
            is_admin = True
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
