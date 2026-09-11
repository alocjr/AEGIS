"""MCP canvas cronograma: merge, CRUD de atividades/marcos e persistência via PUT."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId
from fastmcp.exceptions import ToolError

from app.mcp.tools_learner import (
    _add_cronograma_atividade,
    _add_cronograma_marco,
    _cronograma_of,
    _cronograma_pack,
    _delete_cronograma_atividade,
    _delete_cronograma_marco,
    _empty_cronograma,
    _merge_cronograma,
    _move_cronograma_atividade,
    _update_cronograma_atividade,
    _update_cronograma_marco,
)
from app.routes.canvas_projects import update_project
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


def _save(db, org_id, project_id: str, cronograma: dict) -> dict:
    return update_project(
        project_id,
        CanvasProjectUpdateRequest(cronograma=cronograma),
        user={"_id": ObjectId()},
        org_id=org_id,
        db=db,
    )


class McpCanvasCronogramaTests(unittest.TestCase):
    def test_empty_defaults(self) -> None:
        empty = _empty_cronograma()
        self.assertEqual(empty["semanas"], 8)
        self.assertEqual(empty["atividades"], [])
        self.assertEqual(empty["marcos"], [])

    def test_merge_keeps_atividades_unless_replaced(self) -> None:
        current = {
            "subtitulo": "Antes",
            "semanas": 8,
            "atividades": [{"id": "a01", "titulo": "Kickoff", "semana_inicio": 1, "semana_fim": 1}],
            "marcos": [{"id": "m01", "semana": 8, "titulo": "Go/no-go"}],
        }
        merged = _merge_cronograma(current, {"subtitulo": "Depois", "semanas": 12})
        self.assertEqual(merged["subtitulo"], "Depois")
        self.assertEqual(merged["semanas"], 12)
        self.assertEqual(len(merged["atividades"]), 1)
        self.assertEqual(merged["atividades"][0]["titulo"], "Kickoff")
        self.assertEqual(merged["marcos"][0]["titulo"], "Go/no-go")

    def test_merge_replaces_atividades_list(self) -> None:
        current = {
            "atividades": [{"id": "a01", "titulo": "Antiga", "semana_inicio": 1, "semana_fim": 1}],
        }
        merged = _merge_cronograma(
            current,
            {"atividades": [{"id": "a02", "titulo": "Nova", "semana_inicio": 2, "semana_fim": 3}]},
        )
        self.assertEqual([a["id"] for a in merged["atividades"]], ["a02"])
        self.assertEqual(merged["atividades"][0]["semana_fim"], 3)

    def test_add_update_delete_atividade(self) -> None:
        crono = _empty_cronograma()
        crono = _add_cronograma_atividade(
            crono,
            {"titulo": "Kickoff", "lideranca": "Gestor + Área", "semana_inicio": 1, "semana_fim": 1},
        )
        self.assertEqual(len(crono["atividades"]), 1)
        aid = crono["atividades"][0]["id"]
        crono = _update_cronograma_atividade(crono, aid, {"titulo": "Kickoff e recorte", "semana_fim": 2})
        self.assertEqual(crono["atividades"][0]["titulo"], "Kickoff e recorte")
        self.assertEqual(crono["atividades"][0]["semana_fim"], 2)
        crono = _delete_cronograma_atividade(crono, aid)
        self.assertEqual(crono["atividades"], [])

    def test_move_atividade_reorders(self) -> None:
        crono = _empty_cronograma()
        crono = _add_cronograma_atividade(crono, {"titulo": "A", "semana_inicio": 1, "semana_fim": 1})
        crono = _add_cronograma_atividade(crono, {"titulo": "B", "semana_inicio": 2, "semana_fim": 2})
        crono = _add_cronograma_atividade(crono, {"titulo": "C", "semana_inicio": 3, "semana_fim": 3})
        ids = [a["id"] for a in crono["atividades"]]
        moved = _move_cronograma_atividade(crono, ids[0], 2)
        self.assertEqual([a["titulo"] for a in moved["atividades"]], ["B", "C", "A"])
        moved = _move_cronograma_atividade(moved, ids[2], 0)
        self.assertEqual([a["titulo"] for a in moved["atividades"]], ["C", "B", "A"])

    def test_add_atividade_requires_titulo(self) -> None:
        with self.assertRaises(ToolError):
            _add_cronograma_atividade(_empty_cronograma(), {"semana_inicio": 1, "semana_fim": 1})

    def test_add_update_delete_marco(self) -> None:
        crono = _empty_cronograma()
        crono = _add_cronograma_marco(crono, {"semana": 2, "titulo": "Dores validadas"})
        mid = crono["marcos"][0]["id"]
        crono = _update_cronograma_marco(crono, mid, {"semana": 3, "titulo": "Dores e dados"})
        self.assertEqual(crono["marcos"][0]["semana"], 3)
        self.assertEqual(crono["marcos"][0]["titulo"], "Dores e dados")
        crono = _delete_cronograma_marco(crono, mid)
        self.assertEqual(crono["marcos"], [])

    def test_unknown_atividade_raises(self) -> None:
        with self.assertRaises(ToolError):
            _delete_cronograma_atividade(_empty_cronograma(), "a99")

    def test_persists_create_update_delete_round_trip(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = _project(org_id)
        db.canvas_projects.insert_one(project)
        pid = str(project["_id"])

        created = _save(
            db,
            org_id,
            pid,
            {
                "subtitulo": "Execução em 8 semanas",
                "semanas": 8,
                "atividades": [
                    {"id": "a01", "titulo": "Kickoff", "semana_inicio": 1, "semana_fim": 1},
                ],
                "marcos": [{"id": "m01", "semana": 8, "titulo": "Go / no-go"}],
            },
        )
        pack = _cronograma_pack(created)
        self.assertEqual(pack["title"], "Discovery executivo")
        self.assertEqual(pack["cronograma"]["atividades"][0]["titulo"], "Kickoff")

        current = _cronograma_of(created)
        added = _add_cronograma_atividade(
            current,
            {"titulo": "Mapeamento de dados", "semana_inicio": 1, "semana_fim": 2, "predecessor": "a01"},
        )
        stored = _save(db, org_id, pid, added)
        self.assertEqual(len(stored["cronograma"]["atividades"]), 2)

        emptied = _save(db, org_id, pid, _empty_cronograma())
        self.assertEqual(emptied["cronograma"]["atividades"], [])
        self.assertEqual(emptied["cronograma"]["marcos"], [])
        self.assertEqual(emptied["cronograma"]["subtitulo"], "")
        self.assertEqual(emptied["cronograma"]["semanas"], 8)


if __name__ == "__main__":
    unittest.main()
