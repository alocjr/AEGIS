"""Listagem de canvas: busca por palavras em qualquer texto do projeto."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId

from app.routes.canvas_projects import _matches_canvas_query, list_projects
from tests.query_match import matches


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = list(docs)

    def sort(self, key, direction=-1):
        reverse = direction < 0
        self._docs.sort(key=lambda d: d.get(key) or datetime.min.replace(tzinfo=timezone.utc), reverse=reverse)
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
        return _Cursor([d for d in self.docs if matches(d, flt)])


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
        "area_negocio": "",
        "responsavel": "",
        "objetivo_estrategico": "",
        "dores": [],
        "proximo_passo": "",
        "cronograma": {"subtitulo": "", "atividades": [], "marcos": []},
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


class CanvasListSearchTests(unittest.TestCase):
    def test_empty_query_matches_everything(self) -> None:
        doc = _project(ObjectId(), title="Alpha")
        self.assertTrue(_matches_canvas_query(doc, ""))
        self.assertTrue(_matches_canvas_query(doc, "   "))

    def test_finds_word_in_title_ignoring_accent(self) -> None:
        doc = _project(ObjectId(), title="Gestão de faturamento")
        self.assertTrue(_matches_canvas_query(doc, "gestao"))
        self.assertTrue(_matches_canvas_query(doc, "FATURAMENTO"))
        self.assertFalse(_matches_canvas_query(doc, "folha"))

    def test_finds_word_in_dores_and_cronograma(self) -> None:
        org_id = ObjectId()
        doc = _project(
            org_id,
            title="Projeto X",
            dores=["Fila no atendimento de sinistros"],
            cronograma={
                "subtitulo": "Onda 1",
                "atividades": [{"titulo": "Mapear dados de apólices", "lideranca": "TI + Área"}],
                "marcos": [{"titulo": "Go no-go do recorte"}],
            },
        )
        self.assertTrue(_matches_canvas_query(doc, "sinistros"))
        self.assertTrue(_matches_canvas_query(doc, "apolices"))
        self.assertTrue(_matches_canvas_query(doc, "recorte"))
        self.assertTrue(_matches_canvas_query(doc, "sinistros apolices"))
        self.assertFalse(_matches_canvas_query(doc, "sinistros folha"))

    def test_list_projects_filters_by_query(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        other = ObjectId()
        db.canvas_projects.insert_one(_project(org_id, title="PoC de faturamento"))
        db.canvas_projects.insert_one(
            _project(org_id, title="Outro", dores=["Backlog de sinistros"])
        )
        db.canvas_projects.insert_one(_project(other, title="PoC de faturamento"))

        all_mine = list_projects(q="", user={"_id": ObjectId()}, org_id=org_id, db=db)
        self.assertEqual(len(all_mine["items"]), 2)

        fatura = list_projects(q="faturamento", user={"_id": ObjectId()}, org_id=org_id, db=db)
        self.assertEqual([i["title"] for i in fatura["items"]], ["PoC de faturamento"])

        none = list_projects(q="folha ponto", user={"_id": ObjectId()}, org_id=org_id, db=db)
        self.assertEqual(none["items"], [])


if __name__ == "__main__":
    unittest.main()
