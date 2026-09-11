"""Análise executiva: notas ponderadas do método de seleção e priorização."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId

from app.routes.canvas_projects import _clean_analise_executiva, _to_item, update_project
from app.schemas import CanvasProjectUpdateRequest
from tests.query_match import matches


class _Collection:
    def __init__(self) -> None:
        self.docs: list[dict] = []

    def insert_one(self, doc: dict):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.docs.append(doc)
        return type("Result", (), {"inserted_id": doc["_id"]})()

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


class CleanAnaliseTests(unittest.TestCase):
    def test_keeps_valid_scores_and_drops_unknown(self) -> None:
        cleaned = _clean_analise_executiva(
            {
                "scores": {
                    "valor_economico": 5,
                    "urgencia_risco": 1,
                    "viabilidade_dados": 9,
                    "inventado": 4,
                },
                "observacao": "Comitê de abril",
            }
        )
        self.assertEqual(cleaned["scores"]["valor_economico"], 5)
        self.assertEqual(cleaned["scores"]["urgencia_risco"], 1)
        self.assertIsNone(cleaned["scores"]["viabilidade_dados"])
        self.assertNotIn("inventado", cleaned["scores"])
        self.assertEqual(cleaned["observacao"], "Comitê de abril")
        self.assertEqual(len(cleaned["scores"]), 7)

    def test_empty_input(self) -> None:
        cleaned = _clean_analise_executiva(None)
        self.assertEqual(cleaned["observacao"], "")
        self.assertTrue(all(v is None for v in cleaned["scores"].values()))


class PersistAnaliseTests(unittest.TestCase):
    def test_update_persists_scores(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user_id = ObjectId()
        project = {
            "_id": ObjectId(),
            "organization_id": org_id,
            "created_by_user_id": user_id,
            "title": "Copiloto",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        db.canvas_projects.insert_one(project)
        updated = update_project(
            str(project["_id"]),
            CanvasProjectUpdateRequest(
                analise_executiva={
                    "scores": {"valor_economico": 4, "risco_residual": 3},
                    "observacao": "Priorizar no trimestre",
                }
            ),
            user={"_id": user_id},
            org_id=org_id,
            db=db,
        )
        self.assertEqual(updated["analise_executiva"]["scores"]["valor_economico"], 4)
        self.assertEqual(updated["analise_executiva"]["scores"]["risco_residual"], 3)
        self.assertIsNone(updated["analise_executiva"]["scores"]["tempo_evidencia"])
        stored = db.canvas_projects.find_one({"_id": project["_id"]})
        self.assertEqual(stored["analise_executiva"]["observacao"], "Priorizar no trimestre")

    def test_to_item_defaults(self) -> None:
        item = _to_item({"_id": ObjectId(), "title": "Novo"})
        self.assertIn("analise_executiva", item)
        self.assertEqual(item["analise_executiva"]["observacao"], "")


if __name__ == "__main__":
    unittest.main()
