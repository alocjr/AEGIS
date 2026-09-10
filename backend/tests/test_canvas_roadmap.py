"""Roadmap: projetos aprovados com data de início, reagendamento."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from app.routes.canvas_projects import list_roadmap, move_roadmap_project
from app.schemas import CanvasRoadmapMoveRequest
from tests.query_match import matches


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = list(docs)

    def __iter__(self):
        return iter(self._docs)

    def sort(self, *args, **kwargs):
        return self


class _Collection:
    def __init__(self) -> None:
        self.docs: list[dict] = []

    def insert_one(self, doc: dict):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.docs.append(doc)
        return type("Result", (), {"inserted_id": doc["_id"]})()

    def find(self, flt: dict | None = None, projection=None):
        return _Cursor([d for d in self.docs if matches(d, flt)])

    def find_one(self, flt: dict | None = None, projection=None, sort=None) -> dict | None:
        for d in self.docs:
            if matches(d, flt):
                return dict(d)
        return None

    def update_one(self, flt: dict, update: dict) -> None:
        for d in self.docs:
            if matches(d, flt):
                d.update(update.get("$set", {}))
                break


class _FakeDb:
    def __init__(self) -> None:
        self.canvas_projects = _Collection()


def _project(org_id: ObjectId, **overrides) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "_id": ObjectId(),
        "organization_id": org_id,
        "created_by_user_id": ObjectId(),
        "title": "Projeto",
        "projeto_aprovado": True,
        "data_inicio_real": "2026-09-10",
        "mes_inicio": "set",
        "cronograma": {"semanas": 8, "atividades": [], "marcos": []},
        "created_at": now,
        "updated_at": now,
        "visibility": "shared",
    }
    doc.update(overrides)
    return doc


class ListRoadmapTests(unittest.TestCase):
    def test_lists_only_approved_with_valid_start(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user_id = ObjectId()
        db.canvas_projects.insert_one(
            _project(org_id, title="Com data", created_by_user_id=user_id)
        )
        db.canvas_projects.insert_one(
            _project(
                org_id,
                title="Sem data",
                data_inicio_real="",
                created_by_user_id=user_id,
            )
        )
        db.canvas_projects.insert_one(
            _project(
                org_id,
                title="Rascunho",
                projeto_aprovado=False,
                created_by_user_id=user_id,
            )
        )
        listed = list_roadmap(user={"_id": user_id}, org_id=org_id, db=db)
        titles = [i["title"] for i in listed["items"]]
        self.assertEqual(titles, ["Com data"])
        self.assertEqual(listed["items"][0]["semanas"], 8)
        self.assertEqual(listed["items"][0]["data_inicio_real"], "2026-09-10")

    def test_hides_private_of_other_authors(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        viewer = ObjectId()
        db.canvas_projects.insert_one(
            _project(
                org_id,
                title="Privado alheio",
                visibility="private",
                created_by_user_id=ObjectId(),
            )
        )
        listed = list_roadmap(user={"_id": viewer}, org_id=org_id, db=db)
        self.assertEqual(listed["items"], [])


class MoveRoadmapTests(unittest.TestCase):
    def test_moves_start_and_syncs_mes_inicio(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user_id = ObjectId()
        project = _project(org_id, created_by_user_id=user_id)
        db.canvas_projects.insert_one(project)
        updated = move_roadmap_project(
            str(project["_id"]),
            CanvasRoadmapMoveRequest(data_inicio_real="2026-11-03"),
            user={"_id": user_id},
            org_id=org_id,
            db=db,
        )
        self.assertEqual(updated["data_inicio_real"], "2026-11-03")
        self.assertEqual(updated["mes_inicio"], "nov")
        stored = db.canvas_projects.find_one({"_id": project["_id"]})
        self.assertEqual(stored["data_inicio_real"], "2026-11-03")
        self.assertEqual(stored["mes_inicio"], "nov")

    def test_rejects_unapproved(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user_id = ObjectId()
        project = _project(org_id, projeto_aprovado=False, created_by_user_id=user_id)
        db.canvas_projects.insert_one(project)
        with self.assertRaises(HTTPException) as ctx:
            move_roadmap_project(
                str(project["_id"]),
                CanvasRoadmapMoveRequest(data_inicio_real="2026-12-01"),
                user={"_id": user_id},
                org_id=org_id,
                db=db,
            )
        self.assertEqual(ctx.exception.status_code, 409)
