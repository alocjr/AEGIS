"""Canvas cronograma: round-trip no PUT, sanitização de semanas e defaults."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId

from app.routes.canvas_projects import _clean_cronograma, _to_item, update_project
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
        "title": "Discovery executivo",
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


class CanvasCronogramaTests(unittest.TestCase):
    def test_defaults_when_absent(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = _project(org_id)
        db.canvas_projects.insert_one(project)
        item = _to_item(db.canvas_projects.find_one({"_id": project["_id"]}))
        self.assertEqual(item["cronograma"]["semanas"], 8)
        self.assertEqual(item["cronograma"]["atividades"], [])
        self.assertEqual(item["cronograma"]["marcos"], [])

    def test_round_trips_through_update(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = _project(org_id)
        db.canvas_projects.insert_one(project)

        update_project(
            str(project["_id"]),
            CanvasProjectUpdateRequest(
                cronograma={
                    "subtitulo": "Proposta de execução em 8 semanas",
                    "pre_requisito": "Agenda das diretorias confirmada.",
                    "criterio_aceite": "Roadmap aprovado.",
                    "semanas": 8,
                    "atividades": [
                        {
                            "id": "a01",
                            "titulo": "Kickoff e recorte de dores",
                            "lideranca": "Gestor + Área",
                            "semana_inicio": 1,
                            "semana_fim": 1,
                            "predecessor": "",
                        },
                        {
                            "id": "a02",
                            "titulo": "Mapeamento de dados",
                            "lideranca": "TI + Área",
                            "semana_inicio": 1,
                            "semana_fim": 2,
                            "predecessor": "01 SS",
                        },
                    ],
                    "marcos": [
                        {"id": "m01", "semana": 2, "titulo": "Dores validadas"},
                        {"id": "m02", "semana": 8, "titulo": "Go / no-go"},
                    ],
                }
            ),
            user={"_id": ObjectId()},
            org_id=org_id,
            db=db,
        )

        stored = db.canvas_projects.find_one({"_id": project["_id"]})
        crono = stored["cronograma"]
        self.assertEqual(crono["subtitulo"], "Proposta de execução em 8 semanas")
        self.assertEqual(len(crono["atividades"]), 2)
        self.assertEqual(crono["atividades"][1]["semana_fim"], 2)
        self.assertEqual([m["titulo"] for m in crono["marcos"]], ["Dores validadas", "Go / no-go"])
        self.assertEqual(_to_item(stored)["cronograma"]["atividades"][0]["titulo"], "Kickoff e recorte de dores")

    def test_swaps_inverted_weeks_and_clamps_to_horizon(self) -> None:
        cleaned = _clean_cronograma(
            {
                "semanas": 8,
                "atividades": [
                    {"id": "a01", "titulo": "X", "semana_inicio": 12, "semana_fim": 5},
                ],
                "marcos": [{"id": "m01", "semana": 20, "titulo": "Final"}],
            }
        )
        act = cleaned["atividades"][0]
        self.assertEqual(act["semana_inicio"], 5)
        self.assertEqual(act["semana_fim"], 8)
        self.assertEqual(cleaned["marcos"][0]["semana"], 8)

    def test_generates_ids_and_caps_lists(self) -> None:
        cleaned = _clean_cronograma(
            {
                "atividades": [{"titulo": f"A{i}", "semana_inicio": 1, "semana_fim": 1} for i in range(40)],
                "marcos": [{"semana": 1, "titulo": f"M{i}"} for i in range(20)],
            }
        )
        self.assertEqual(len(cleaned["atividades"]), 30)
        self.assertEqual(len(cleaned["marcos"]), 12)
        self.assertTrue(all(a["id"] for a in cleaned["atividades"]))
        self.assertTrue(all(m["id"] for m in cleaned["marcos"]))


if __name__ == "__main__":
    unittest.main()
