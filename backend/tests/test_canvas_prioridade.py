"""Prioridade C-level (P0–P4) e mês de início no canvas."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app.routes.canvas_projects import (
    _clean_mes_inicio,
    _clean_prioridade,
    _to_item,
    list_projects,
    update_project,
)
from app.schemas import CanvasProjectUpdateRequest


def _matches(doc: dict, flt: dict | None) -> bool:
    for key, expected in (flt or {}).items():
        if doc.get(key) != expected:
            return False
    return True


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = list(docs)

    def sort(self, key, direction=-1):
        reverse = direction < 0
        self._docs.sort(
            key=lambda d: d.get(key) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=reverse,
        )
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

    def find(self, flt: dict | None = None, projection=None):
        return _Cursor([d for d in self.docs if _matches(d, flt)])

    def find_one(self, flt: dict | None = None, projection=None, sort=None) -> dict | None:
        candidates = [d for d in self.docs if _matches(d, flt)]
        return dict(candidates[0]) if candidates else None

    def update_one(self, flt: dict, update: dict) -> None:
        for d in self.docs:
            if _matches(d, flt):
                d.update(update.get("$set", {}))
                break


class _FakeDb:
    def __init__(self) -> None:
        self._collections: dict[str, _Collection] = {}

    def _col(self, name: str) -> _Collection:
        return self._collections.setdefault(name, _Collection())

    def __getattr__(self, name: str) -> _Collection:
        return self._col(name)

    def __getitem__(self, name: str) -> _Collection:
        return self._col(name)


def _project(org_id: ObjectId, **overrides) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "_id": ObjectId(),
        "organization_id": org_id,
        "created_by_user_id": ObjectId(),
        "title": "Novo projeto",
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


class CanvasPrioridadeTests(unittest.TestCase):
    def test_defaults_missing_priority_to_p4(self) -> None:
        self.assertEqual(_clean_prioridade(None), "P4")
        self.assertEqual(_clean_prioridade(""), "P4")
        self.assertEqual(_clean_prioridade("urgente"), "P4")
        self.assertEqual(_clean_prioridade("p0"), "P0")
        self.assertEqual(_clean_mes_inicio(None), "")
        self.assertEqual(_clean_mes_inicio("Marco"), "")
        self.assertEqual(_clean_mes_inicio("MAR"), "mar")

    def test_to_item_exposes_priority_and_month(self) -> None:
        item = _to_item(_project(ObjectId(), prioridade="P1", mes_inicio="jun"))
        self.assertEqual(item["prioridade"], "P1")
        self.assertEqual(item["mes_inicio"], "jun")
        legacy = _to_item(_project(ObjectId()))
        self.assertEqual(legacy["prioridade"], "P4")
        self.assertEqual(legacy["mes_inicio"], "")

    def test_list_orders_p0_to_p4(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        t0 = datetime.now(timezone.utc)
        db.canvas_projects.insert_one(_project(org_id, title="Baixa", prioridade="P4", updated_at=t0))
        db.canvas_projects.insert_one(
            _project(org_id, title="Imediato", prioridade="P0", updated_at=t0 - timedelta(days=2))
        )
        db.canvas_projects.insert_one(
            _project(org_id, title="Planejado", prioridade="P2", updated_at=t0 - timedelta(days=1))
        )
        listed = list_projects(q="", user={"_id": ObjectId()}, org_id=org_id, db=db)
        self.assertEqual(
            [i["title"] for i in listed["items"]],
            ["Imediato", "Planejado", "Baixa"],
        )

    def test_update_round_trips_priority_and_month(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = _project(org_id)
        db.canvas_projects.insert_one(project)
        update_project(
            str(project["_id"]),
            CanvasProjectUpdateRequest(prioridade="P0", mes_inicio="jan"),
            user={"_id": ObjectId()},
            org_id=org_id,
            db=db,
        )
        stored = db.canvas_projects.find_one({"_id": project["_id"]})
        self.assertEqual(stored["prioridade"], "P0")
        self.assertEqual(stored["mes_inicio"], "jan")
        update_project(
            str(project["_id"]),
            CanvasProjectUpdateRequest(mes_inicio=""),
            user={"_id": ObjectId()},
            org_id=org_id,
            db=db,
        )
        stored = db.canvas_projects.find_one({"_id": project["_id"]})
        self.assertEqual(stored["mes_inicio"], "")
        self.assertEqual(stored["prioridade"], "P0")


if __name__ == "__main__":
    unittest.main()
