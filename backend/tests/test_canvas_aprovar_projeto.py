"""Aprovação executiva do canvas: comentário, data real e periodicidade."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from app.routes.canvas_projects import _to_item, aprovar_projeto
from app.schemas import CanvasAprovarProjetoRequest


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


class CanvasAprovarProjetoTests(unittest.TestCase):
    def test_approves_with_required_fields(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = {
            "_id": ObjectId(),
            "organization_id": org_id,
            "title": "Copiloto",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        db.canvas_projects.insert_one(project)
        item = aprovar_projeto(
            str(project["_id"]),
            CanvasAprovarProjetoRequest(
                comentario="Ana (CEO) e Bruno (CFO)",
                data_inicio_real="2026-04-09",
                periodicidade="mensal",
            ),
            user={"_id": ObjectId()},
            org_id=org_id,
            db=db,
        )
        self.assertTrue(item["projeto_aprovado"])
        self.assertEqual(item["aprovacao_comentario"], "Ana (CEO) e Bruno (CFO)")
        self.assertEqual(item["data_inicio_real"], "2026-04-09")
        self.assertEqual(item["mes_inicio"], "abr")
        self.assertEqual(item["periodicidade"], "mensal")
        self.assertTrue(item["aprovado_em"])
        stored = db.canvas_projects.find_one({"_id": project["_id"]})
        self.assertTrue(stored["projeto_aprovado"])
        self.assertEqual(stored["mes_inicio"], "abr")

    def test_rejects_invalid_date(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = {"_id": ObjectId(), "organization_id": org_id, "title": "X"}
        db.canvas_projects.insert_one(project)
        with self.assertRaises(HTTPException) as ctx:
            aprovar_projeto(
                str(project["_id"]),
                CanvasAprovarProjetoRequest(
                    comentario="Comitê",
                    data_inicio_real="09/04/2026",
                    periodicidade="quinzenal",
                ),
                user={"_id": ObjectId()},
                org_id=org_id,
                db=db,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_to_item_defaults_unapproved(self) -> None:
        item = _to_item({"_id": ObjectId(), "title": "Novo"})
        self.assertFalse(item["projeto_aprovado"])
        self.assertEqual(item["periodicidade"], "")
        self.assertEqual(item["aprovacao_comentario"], "")


if __name__ == "__main__":
    unittest.main()
