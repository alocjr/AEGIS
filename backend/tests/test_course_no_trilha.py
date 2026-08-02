"""Usuários sem trilha atribuída (ex.: membro de organização criado pelo admin de organização)
nunca devem cair no fallback antigo `COURSE_SLUG` — devem receber 404 `NO_TRILHA_ASSIGNED`."""

from __future__ import annotations

import unittest

from bson import ObjectId
from fastapi import HTTPException

from app.routes import admin as admin_routes
from app.routes import course as course_routes
from app.routes import progress as progress_routes
from app.schemas import AdminCreateUserRequest, AdminUpdateUserRequest, LiberarEncontroRequest


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


def _user(**overrides) -> dict:
    doc = {"_id": ObjectId(), "name": "U", "email": "u@x.com"}
    doc.update(overrides)
    return doc


def _course(slug: str) -> dict:
    return {
        "slug": slug,
        "programa_formacao_executiva": {
            "jornada_aprendizagem": [
                {"semana": 1, "encontros": [{"id": 1, "titulo": "Enc 1", "material_suporte": []}]}
            ]
        },
    }


class PrimaryCourseSlugTests(unittest.TestCase):
    def test_none_when_no_course_slug_or_slugs(self) -> None:
        self.assertIsNone(course_routes._primary_course_slug(_user()))

    def test_legacy_course_slug_field(self) -> None:
        user = _user(course_slug="trilha-legado")
        self.assertEqual(course_routes._primary_course_slug(user), "trilha-legado")

    def test_first_of_course_slugs(self) -> None:
        user = _user(course_slugs=["trilha-a", "trilha-b"])
        self.assertEqual(course_routes._primary_course_slug(user), "trilha-a")

    def test_require_raises_no_trilha_assigned(self) -> None:
        with self.assertRaises(course_routes.NoTrilhaAssignedError) as ctx:
            course_routes._require_primary_course_slug(_user())
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail["code"], "NO_TRILHA_ASSIGNED")

    def test_require_returns_slug_when_present(self) -> None:
        user = _user(course_slugs=["trilha-a"])
        self.assertEqual(course_routes._require_primary_course_slug(user), "trilha-a")


class GetCurrentCourseTests(unittest.TestCase):
    def test_courseless_user_gets_no_trilha_assigned(self) -> None:
        db = _FakeDb()
        user = _user()

        with self.assertRaises(course_routes.NoTrilhaAssignedError) as ctx:
            course_routes.get_current_course(user=user, db=db, course_slug=None)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail["code"], "NO_TRILHA_ASSIGNED")

    def test_user_with_trilha_resolves_normally(self) -> None:
        db = _FakeDb()
        user = _user(course_slugs=["trilha-a"])
        db.courses.insert_one(_course("trilha-a"))
        db.quiz.docs = []

        result = course_routes.get_current_course(user=user, db=db, course_slug=None)

        self.assertIsInstance(result, dict)

    def test_explicit_slug_without_access_still_403s(self) -> None:
        db = _FakeDb()
        user = _user()
        db.courses.insert_one(_course("trilha-x"))

        with self.assertRaises(HTTPException) as ctx:
            course_routes.get_current_course(user=user, db=db, course_slug="trilha-x")
        self.assertEqual(ctx.exception.status_code, 403)


class ResolveCourseSlugTests(unittest.TestCase):
    def test_courseless_user_without_slug_param_raises(self) -> None:
        db = _FakeDb()
        user = _user()

        with self.assertRaises(course_routes.NoTrilhaAssignedError):
            progress_routes._resolve_course_slug(user, db, None)

    def test_user_with_trilha_and_no_slug_param_resolves(self) -> None:
        db = _FakeDb()
        user = _user(course_slugs=["trilha-a"])

        self.assertEqual(progress_routes._resolve_course_slug(user, db, None), "trilha-a")

    def test_explicit_unauthorized_slug_param_still_403s(self) -> None:
        db = _FakeDb()
        user = _user(course_slugs=["trilha-a"])

        with self.assertRaises(HTTPException) as ctx:
            progress_routes._resolve_course_slug(user, db, "trilha-outra")
        self.assertEqual(ctx.exception.status_code, 403)


class AdminGetUserCourseAndProgressTests(unittest.TestCase):
    def test_courseless_target_user_raises_no_trilha_assigned(self) -> None:
        db = _FakeDb()
        admin = _user(is_admin=True)
        target = _user()
        db.users.insert_one(target)

        with self.assertRaises(course_routes.NoTrilhaAssignedError) as ctx:
            admin_routes.get_user_course_and_progress(
                str(target["_id"]), admin=admin, db=db, course_slug=None
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail["code"], "NO_TRILHA_ASSIGNED")

    def test_target_user_with_trilha_resolves(self) -> None:
        db = _FakeDb()
        admin = _user(is_admin=True)
        target = _user(course_slugs=["trilha-a"])
        db.users.insert_one(target)
        db.courses.insert_one(_course("trilha-a"))

        result = admin_routes.get_user_course_and_progress(
            str(target["_id"]), admin=admin, db=db, course_slug=None
        )
        self.assertIsInstance(result, dict)


class AdminLiberarEncontroTests(unittest.TestCase):
    def test_courseless_target_user_raises_no_trilha_assigned(self) -> None:
        db = _FakeDb()
        admin = _user(is_admin=True)
        target = _user()
        db.users.insert_one(target)

        with self.assertRaises(course_routes.NoTrilhaAssignedError) as ctx:
            admin_routes.liberar_encontro(
                str(target["_id"]), LiberarEncontroRequest(encontro_id=1), admin=admin, db=db
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail["code"], "NO_TRILHA_ASSIGNED")

    def test_target_user_with_course_slugs_plural_resolves(self) -> None:
        db = _FakeDb()
        admin = _user(is_admin=True)
        target = _user(course_slugs=["trilha-a"])
        db.users.insert_one(target)
        db.courses.insert_one(_course("trilha-a"))

        admin_routes.liberar_encontro(
            str(target["_id"]), LiberarEncontroRequest(encontro_id=1), admin=admin, db=db
        )

        progress = db.progress.find_one({"user_id": target["_id"], "course_slug": "trilha-a"})
        self.assertIsNotNone(progress)
        self.assertIn(1, progress.get("encontros_liberados") or [])


class AdminCreateUserWithoutTrilhaTests(unittest.TestCase):
    """Admin da plataforma também pode criar um usuário sem nenhuma trilha (ex.: dono de
    organização que só vai usar as ferramentas do AI Hub)."""

    def test_creates_user_with_no_course_slugs(self) -> None:
        db = _FakeDb()
        admin = _user(is_admin=True)
        org_id = ObjectId()
        db.organizations.insert_one({"_id": org_id, "name": "Empresa X"})

        result = admin_routes.create_user(
            AdminCreateUserRequest(
                name="Sem Trilha",
                email="semtrilha@empresa.com",
                password="senha123",
                course_slugs=[],
                organization_id=str(org_id),
            ),
            admin=admin,
            db=db,
        )

        self.assertEqual(result["course_slugs"], [])
        stored = db.users.find_one({"email": "semtrilha@empresa.com"})
        self.assertEqual(stored["course_slugs"], [])
        self.assertNotIn("course_slug", stored)
        self.assertEqual(db.progress.count_documents({"user_id": stored["_id"]}), 0)


class AdminUpdateUserClearTrilhaTests(unittest.TestCase):
    def test_clearing_course_slugs_to_empty_list_succeeds(self) -> None:
        db = _FakeDb()
        admin = _user(is_admin=True)
        member = _user(course_slugs=["trilha-a"], course_slug="trilha-a")
        db.users.insert_one(member)

        updated = admin_routes.update_user(
            str(member["_id"]),
            AdminUpdateUserRequest(course_slugs=[]),
            admin=admin,
            db=db,
        )

        self.assertIsInstance(updated, dict)
        stored = db.users.find_one({"_id": member["_id"]})
        self.assertEqual(stored["course_slugs"], [])
        self.assertIsNone(stored["course_slug"])


if __name__ == "__main__":
    unittest.main()
