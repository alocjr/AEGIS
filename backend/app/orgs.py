"""Memberships multi-organização e visibilidade de artefatos.

`users.organization_id` continua sendo a organização **ativa** (o que a API
escopa). `organization_ids` lista todas as memberships; `org_admin_ids` as
orgs em que a pessoa é admin de organização.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

VISIBILITY_SHARED = "shared"
VISIBILITY_PRIVATE = "private"


def org_ids_of(user: dict) -> list[ObjectId]:
    """Memberships do usuário. Cai no `organization_id` legado se a lista ainda não existir."""
    raw = user.get("organization_ids")
    if isinstance(raw, list) and raw:
        return [oid for oid in raw if oid]
    oid = user.get("organization_id")
    return [oid] if oid else []


def org_admin_ids_of(user: dict) -> list[ObjectId]:
    raw = user.get("org_admin_ids")
    if isinstance(raw, list):
        return [oid for oid in raw if oid]
    oid = user.get("organization_id")
    if oid and user.get("is_org_admin"):
        return [oid]
    return []


def is_member_of(user: dict, org_id: ObjectId) -> bool:
    return org_id in org_ids_of(user)


def is_org_admin_of(user: dict, org_id: ObjectId) -> bool:
    if user.get("is_admin"):
        return True
    return org_id in org_admin_ids_of(user)


def members_of_org_query(org_id: ObjectId) -> dict:
    """Usuários que pertencem à org — ativos nela ou só membership."""
    return {
        "$or": [
            {"organization_ids": org_id},
            {"organization_id": org_id},
        ]
    }


def membership_set(
    org_ids: list[ObjectId],
    org_admin_ids: list[ObjectId],
    active_id: ObjectId | None,
) -> dict:
    """Campos `$set` consistentes de membership + org ativa."""
    ids = []
    seen: set[ObjectId] = set()
    for oid in org_ids:
        if oid and oid not in seen:
            seen.add(oid)
            ids.append(oid)
    admin_set = {oid for oid in org_admin_ids if oid in seen}
    admin_ids = [oid for oid in ids if oid in admin_set]
    active = active_id if active_id in seen else (ids[0] if ids else None)
    return {
        "organization_ids": ids,
        "org_admin_ids": admin_ids,
        "organization_id": active,
        "is_org_admin": bool(active and active in admin_set),
    }


def parse_object_ids(raw_ids: list[str] | None, *, label: str) -> list[ObjectId]:
    if not raw_ids:
        return []
    out: list[ObjectId] = []
    seen: set[ObjectId] = set()
    for raw in raw_ids:
        text = (raw or "").strip()
        if not text:
            continue
        if not ObjectId.is_valid(text):
            raise HTTPException(status_code=400, detail=f"{label} inválida")
        oid = ObjectId(text)
        if oid not in seen:
            seen.add(oid)
            out.append(oid)
    return out


def require_orgs_exist(db: Database, org_ids: list[ObjectId]) -> None:
    if not org_ids:
        return
    found = {doc["_id"] for doc in db.organizations.find({"_id": {"$in": org_ids}}, {"_id": 1})}
    missing = [oid for oid in org_ids if oid not in found]
    if missing:
        raise HTTPException(status_code=404, detail="Organizacao nao encontrada")


def apply_memberships(
    db: Database,
    user_id: ObjectId,
    org_ids: list[ObjectId],
    org_admin_ids: list[ObjectId],
    active_id: ObjectId | None = None,
) -> dict:
    if not org_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O usuário precisa pertencer a pelo menos uma organização.",
        )
    require_orgs_exist(db, org_ids)
    fields = membership_set(org_ids, org_admin_ids, active_id)
    fields["updated_at"] = datetime.now(timezone.utc)
    db.users.update_one({"_id": user_id}, {"$set": fields})
    return fields


def backfill_memberships(db: Database) -> int:
    """Preenche organization_ids/org_admin_ids a partir do organization_id legado."""
    n = 0
    for user in db.users.find({"organization_ids": {"$exists": False}}):
        oid = user.get("organization_id")
        ids = [oid] if oid else []
        admin_ids = [oid] if oid and user.get("is_org_admin") else []
        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": membership_set(ids, admin_ids, oid)},
        )
        n += 1
    return n


def organizations_payload(user: dict, db: Database) -> list[dict]:
    ids = org_ids_of(user)
    if not ids:
        return []
    names = {
        doc["_id"]: doc.get("name") or ""
        for doc in db.organizations.find({"_id": {"$in": ids}}, {"name": 1})
    }
    admin_ids = set(org_admin_ids_of(user))
    return [
        {
            "id": str(oid),
            "name": names.get(oid, ""),
            "is_org_admin": oid in admin_ids,
        }
        for oid in ids
    ]


def clean_visibility(value) -> str:
    raw = str(value or "").strip().lower()
    return VISIBILITY_PRIVATE if raw == VISIBILITY_PRIVATE else VISIBILITY_SHARED


def visibility_of(doc: dict | None) -> str:
    if not doc:
        return VISIBILITY_SHARED
    return VISIBILITY_PRIVATE if doc.get("visibility") == VISIBILITY_PRIVATE else VISIBILITY_SHARED


def can_view_artifact(doc: dict | None, user_id) -> bool:
    if not doc:
        return False
    if visibility_of(doc) != VISIBILITY_PRIVATE:
        return True
    return doc.get("created_by_user_id") == user_id


def visible_query(org_id, user_id) -> dict:
    """Artefatos da org visíveis: compartilhados (ou sem campo) + privados do autor."""
    return {
        "organization_id": org_id,
        "$or": [
            {"visibility": {"$ne": VISIBILITY_PRIVATE}},
            {"created_by_user_id": user_id},
        ],
    }


def deny_if_hidden(doc: dict | None, user_id, *, detail: str = "Nao encontrado"):
    if not can_view_artifact(doc, user_id):
        raise HTTPException(status_code=404, detail=detail)
    return doc
