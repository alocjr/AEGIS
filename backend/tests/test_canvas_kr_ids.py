"""Canvas ↔ Key Result: `kr_ids` (Key Results de OKR que o projeto endereça) faz round-trip
pelo PUT do projeto do jeito que `swot_item_ids`/`tows_ids` já fazem."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId

from app.routes.canvas_projects import _to_item, update_project
from app.schemas import CanvasProjectUpdateRequest


def _matches(doc: dict, flt: dict | None) -> bool:
    for key, expected in (flt or {}).items():
        if doc.get(key) != expected:
            return False
    return True


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
        "title": "Agente de triagem",
        "kr_ids": [],
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


class CanvasKrIdsTests(unittest.TestCase):
    def test_round_trips_through_update(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = _project(org_id)
        db.canvas_projects.insert_one(project)
        user = {"_id": ObjectId()}

        update_project(
            str(project["_id"]),
            CanvasProjectUpdateRequest(kr_ids=["kr_abc123", "kr_def456", "kr_abc123"]),
            user=user, org_id=org_id, db=db,
        )

        stored = db.canvas_projects.find_one({"_id": project["_id"]})
        # dedupe preservando ordem, mesmo comportamento de swot_item_ids/tows_ids
        self.assertEqual(stored["kr_ids"], ["kr_abc123", "kr_def456"])
        self.assertEqual(_to_item(stored)["kr_ids"], ["kr_abc123", "kr_def456"])

    def test_defaults_to_empty_list_when_absent(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = _project(org_id)
        db.canvas_projects.insert_one(project)

        self.assertEqual(_to_item(db.canvas_projects.find_one({"_id": project["_id"]}))["kr_ids"], [])


if __name__ == "__main__":
    unittest.main()
