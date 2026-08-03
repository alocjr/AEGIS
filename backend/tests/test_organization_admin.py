"""Gestão de membros da organização (admin de organização), incluindo `get_current_org_admin`."""

from __future__ import annotations

import unittest

from bson import ObjectId
from fastapi import HTTPException

from app.deps import get_current_org_admin
from app.routes import organization_admin as org_routes
from app.schemas import OrgMemberCreateRequest, OrgMemberUpdateRequest


def _matches(doc: dict, flt: dict | None) -> bool:
    for key, expected in (flt or {}).items():
        if isinstance(expected, dict) and "$ne" in expected:
            if doc.get(key) == expected["$ne"]:
                return False
            continue
        if doc.get(key) != expected:
            return False
    return True


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs

    def sort(self, field: str, direction: int = 1) -> "_Cursor":
        self._docs = sorted(self._docs, key=lambda d: d.get(field) or 0, reverse=direction < 0)
        return self

    def __iter__(self):
        return iter(self._docs)


class _Collection:
    def __init__(self) -> None:
        self.docs: list[dict] = []

    def insert_one(self, doc: dict):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.docs.append(doc)
        return type("Result", (), {"inserted_id": doc["_id"]})()

    def find_one(self, flt: dict | None = None, projection=None, sort=None) -> dict | None:
        candidates = [d for d in self.docs if _matches(d, flt)]
        return dict(candidates[0]) if candidates else None

    def find(self, flt: dict | None = None, projection=None) -> _Cursor:
        return _Cursor([dict(d) for d in self.docs if _matches(d, flt)])

    def update_one(self, flt: dict, update: dict) -> None:
        for d in self.docs:
            if _matches(d, flt):
                d.update(update.get("$set", {}))
                break

    def delete_one(self, flt: dict) -> None:
        for d in list(self.docs):
            if _matches(d, flt):
                self.docs.remove(d)
                break

    def delete_many(self, flt: dict) -> None:
        self.docs = [d for d in self.docs if not _matches(d, flt)]

    def count_documents(self, flt: dict | None = None) -> int:
        return len([d for d in self.docs if _matches(d, flt)])


class _FakeDb:
    def __init__(self) -> None:
        self._collections: dict[str, _Collection] = {}

    def _col(self, name: str) -> _Collection:
        return self._collections.setdefault(name, _Collection())

    def __getattr__(self, name: str) -> _Collection:
        return self._col(name)

    def __getitem__(self, name: str) -> _Collection:
        return self._col(name)


def _user(org_id: ObjectId, **overrides) -> dict:
    doc = {"_id": ObjectId(), "organization_id": org_id, "is_admin": False, "is_org_admin": False, "name": "U"}
    doc.update(overrides)
    return doc


class GetCurrentOrgAdminTests(unittest.TestCase):
    def test_accepts_platform_admin(self) -> None:
        user = _user(ObjectId(), is_admin=True)
        self.assertIs(get_current_org_admin(user), user)

    def test_accepts_org_admin(self) -> None:
        user = _user(ObjectId(), is_org_admin=True)
        self.assertIs(get_current_org_admin(user), user)

    def test_rejects_regular_member(self) -> None:
        user = _user(ObjectId())
        with self.assertRaises(HTTPException) as ctx:
            get_current_org_admin(user)
        self.assertEqual(ctx.exception.status_code, 403)


class ListMembersTests(unittest.TestCase):
    def test_lists_only_own_organization(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        admin = _user(org_id, is_org_admin=True)
        colleague = _user(org_id, name="Colega")
        outsider = _user(ObjectId(), name="Outra org")
        for u in (admin, colleague, outsider):
            db.users.insert_one(u)

        result = org_routes.list_members(org_admin=admin, org_id=org_id, db=db)

        names = {m["name"] for m in result["items"]}
        self.assertEqual(names, {"U", "Colega"})


class CreateMemberTests(unittest.TestCase):
    def test_creates_member_without_trilha_or_admin_flags(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        admin = _user(org_id, is_org_admin=True)
        db.users.insert_one(admin)

        created = org_routes.create_member(
            OrgMemberCreateRequest(name="Novo Membro", email="novo@empresa.com", password="senha123"),
            org_admin=admin, org_id=org_id, db=db,
        )

        self.assertEqual(created["name"], "Novo Membro")
        stored = db.users.find_one({"email": "novo@empresa.com"})
        self.assertEqual(stored["organization_id"], org_id)
        self.assertEqual(stored["course_slugs"], [])
        self.assertNotIn("is_admin", stored)
        self.assertNotIn("is_org_admin", stored)
        # Org-admin não gerencia ferramentas — membro nasce com o catálogo completo
        # (mesmo padrão do registro público); o admin da plataforma restringe depois.
        from app.tools import default_tools
        self.assertEqual(stored["tools"], default_tools())

    def test_rejects_duplicate_email(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        admin = _user(org_id, is_org_admin=True)
        db.users.insert_one(admin)
        db.users.insert_one(_user(org_id, email="ja@existe.com"))

        with self.assertRaises(HTTPException) as ctx:
            org_routes.create_member(
                OrgMemberCreateRequest(name="Xy", email="ja@existe.com", password="senha123"),
                org_admin=admin, org_id=org_id, db=db,
            )
        self.assertEqual(ctx.exception.status_code, 409)


class UpdateMemberTests(unittest.TestCase):
    def test_updates_name_and_phone(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        admin = _user(org_id, is_org_admin=True)
        member = _user(org_id, name="Antigo")
        db.users.insert_one(admin)
        db.users.insert_one(member)

        updated = org_routes.update_member(
            str(member["_id"]), OrgMemberUpdateRequest(name="Novo Nome", phone="11999999999"),
            org_admin=admin, org_id=org_id, db=db,
        )

        self.assertEqual(updated["name"], "Novo Nome")
        self.assertEqual(updated["phone"], "11999999999")

    def test_cannot_edit_member_from_another_org(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        admin = _user(org_id, is_org_admin=True)
        outsider = _user(ObjectId())
        db.users.insert_one(admin)
        db.users.insert_one(outsider)

        with self.assertRaises(HTTPException) as ctx:
            org_routes.update_member(
                str(outsider["_id"]), OrgMemberUpdateRequest(name="Xy"),
                org_admin=admin, org_id=org_id, db=db,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_cannot_edit_platform_admin(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        admin = _user(org_id, is_org_admin=True)
        platform_admin = _user(org_id, is_admin=True)
        db.users.insert_one(admin)
        db.users.insert_one(platform_admin)

        with self.assertRaises(HTTPException) as ctx:
            org_routes.update_member(
                str(platform_admin["_id"]), OrgMemberUpdateRequest(name="Xy"),
                org_admin=admin, org_id=org_id, db=db,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], "CANNOT_MANAGE_PLATFORM_ADMIN")

    def test_rejects_email_conflict(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        admin = _user(org_id, is_org_admin=True)
        member = _user(org_id, email="a@b.com")
        other = _user(org_id, email="c@d.com")
        db.users.insert_one(admin)
        db.users.insert_one(member)
        db.users.insert_one(other)

        with self.assertRaises(HTTPException) as ctx:
            org_routes.update_member(
                str(member["_id"]), OrgMemberUpdateRequest(email="c@d.com"),
                org_admin=admin, org_id=org_id, db=db,
            )
        self.assertEqual(ctx.exception.status_code, 409)


class DeleteMemberTests(unittest.TestCase):
    def test_removes_member_and_cleans_progress(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        admin = _user(org_id, is_org_admin=True)
        member = _user(org_id)
        db.users.insert_one(admin)
        db.users.insert_one(member)
        db.progress.insert_one({"_id": ObjectId(), "user_id": member["_id"], "course_slug": "x"})
        db.quiz_responses.insert_one({"_id": ObjectId(), "user_id": member["_id"], "encontro": 1})

        org_routes.delete_member(str(member["_id"]), org_admin=admin, org_id=org_id, db=db)

        self.assertIsNone(db.users.find_one({"_id": member["_id"]}))
        self.assertEqual(db.progress.count_documents({"user_id": member["_id"]}), 0)
        self.assertEqual(db.quiz_responses.count_documents({"user_id": member["_id"]}), 0)

    def test_cannot_self_delete(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        admin = _user(org_id, is_org_admin=True)
        db.users.insert_one(admin)

        with self.assertRaises(HTTPException) as ctx:
            org_routes.delete_member(str(admin["_id"]), org_admin=admin, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_cannot_delete_platform_admin(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        admin = _user(org_id, is_org_admin=True)
        platform_admin = _user(org_id, is_admin=True)
        db.users.insert_one(admin)
        db.users.insert_one(platform_admin)

        with self.assertRaises(HTTPException) as ctx:
            org_routes.delete_member(str(platform_admin["_id"]), org_admin=admin, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], "CANNOT_MANAGE_PLATFORM_ADMIN")


if __name__ == "__main__":
    unittest.main()
