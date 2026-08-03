"""Gestão de membros da organização pelo admin de organização (ou admin da plataforma).

Escopo deliberadamente menor que `routes/admin.py`: cria/edita/remove nome, e-mail, telefone
e senha de membros da própria organização — nunca atribui trilha/mentoria (`course_slugs`,
`encontro_agendas`) nem mexe em `is_admin`/`is_org_admin`/`organization_id`, que continuam
exclusivos do admin da plataforma. Também não pode gerenciar uma conta com `is_admin=True`,
mesmo que ela pertença à mesma organização (protege contas de staff da Valorian).
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.database import get_db
from app.deps import get_current_org_admin, get_current_organization_id
from app.schemas import OrgMemberCreateRequest, OrgMemberUpdateRequest
from app.security import hash_password
from app.tools import default_tools

router = APIRouter(prefix="/api/org-admin", tags=["org-admin"])


def _serialize_member(doc: dict) -> dict:
    created_at = doc.get("created_at")
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name") or "",
        "email": doc.get("email") or "",
        "phone": doc.get("phone") or "",
        "is_org_admin": bool(doc.get("is_org_admin")),
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else None,
    }


def _get_org_member(db: Database, org_id: ObjectId, user_id: str) -> dict:
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    member = db.users.find_one({"_id": ObjectId(user_id), "organization_id": org_id})
    if not member:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    return member


def _forbid_platform_admin(member: dict, action: str) -> None:
    if member.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "CANNOT_MANAGE_PLATFORM_ADMIN",
                "message": f"Nao e possivel {action} um administrador da plataforma",
            },
        )


@router.get("/members")
def list_members(
    org_admin=Depends(get_current_org_admin),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Lista os membros da própria organização."""
    members = db.users.find({"organization_id": org_id}).sort("created_at", 1)
    return {"items": [_serialize_member(m) for m in members]}


@router.post("/members")
def create_member(
    payload: OrgMemberCreateRequest,
    org_admin=Depends(get_current_org_admin),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Cria um usuário na própria organização — sem trilha (só o admin da plataforma atribui)."""
    email = payload.email.strip().lower()
    if db.users.find_one({"email": email}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")

    now = datetime.now(timezone.utc)
    user_doc = {
        "name": payload.name.strip(),
        "email": email,
        "password_hash": hash_password(payload.password),
        "course_slugs": [],
        "organization_id": org_id,
        "created_at": now,
        "updated_at": now,
        "email_verified": True,
        # Mesmo padrão do registro público: tudo liberado; o admin da plataforma restringe
        # depois (inclusive em lote na organização). Org-admin não gerencia ferramentas.
        "tools": default_tools(),
    }
    if payload.phone is not None and payload.phone.strip():
        user_doc["phone"] = payload.phone.strip()
    result = db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    return _serialize_member(user_doc)


@router.patch("/members/{user_id}")
def update_member(
    user_id: str,
    payload: OrgMemberUpdateRequest,
    org_admin=Depends(get_current_org_admin),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    member = _get_org_member(db, org_id, user_id)
    _forbid_platform_admin(member, "editar")

    updates: dict = {"updated_at": datetime.now(timezone.utc)}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.email is not None:
        email = payload.email.strip().lower()
        other = db.users.find_one({"email": email, "_id": {"$ne": member["_id"]}})
        if other:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja em uso")
        updates["email"] = email
    if payload.password is not None and payload.password.strip():
        updates["password_hash"] = hash_password(payload.password)
    if payload.phone is not None:
        updates["phone"] = payload.phone.strip() if payload.phone.strip() else ""

    db.users.update_one({"_id": member["_id"]}, {"$set": updates})
    refreshed = db.users.find_one({"_id": member["_id"]})
    return _serialize_member(refreshed)


@router.delete("/members/{user_id}")
def delete_member(
    user_id: str,
    org_admin=Depends(get_current_org_admin),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    member = _get_org_member(db, org_id, user_id)
    if member["_id"] == org_admin["_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nao e possivel remover seu proprio usuario"
        )
    _forbid_platform_admin(member, "remover")

    db.users.delete_one({"_id": member["_id"]})
    db.progress.delete_many({"user_id": member["_id"]})
    db.quiz_responses.delete_many({"user_id": member["_id"]})
    return {"message": "Usuario removido", "id": user_id}
