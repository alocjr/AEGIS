"""Clonar canvas para a organização de destino (membership)."""

from __future__ import annotations

import unittest

from bson import ObjectId
from fastapi import HTTPException

from app.orgs import membership_set
from app.routes.canvas_projects import _clone_title, clone_project
from app.schemas import CanvasProjectCloneRequest
from tests.query_match import matches


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = list(docs)

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

    def find_one(self, flt: dict | None = None, projection=None, sort=None) -> dict | None:
        for d in self.docs:
            if matches(d, flt):
                return dict(d)
        return None


class _FakeDb:
    def __init__(self) -> None:
        self.canvas_projects = _Collection()
        self.organizations = _Collection()


class CloneTitleTests(unittest.TestCase):
    def test_appends_copia(self) -> None:
        self.assertEqual(_clone_title("Atendimento", None), "Atendimento (cópia)")

    def test_does_not_stack_suffix(self) -> None:
        self.assertEqual(_clone_title("Atendimento (cópia)", None), "Atendimento (cópia)")

    def test_override_wins(self) -> None:
        self.assertEqual(_clone_title("Atendimento", "Novo nome"), "Novo nome")


class CloneProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = _FakeDb()
        self.src = ObjectId()
        self.dest = ObjectId()
        self.user_id = ObjectId()
        self.db.organizations.insert_one({"_id": self.src, "name": "Alpha"})
        self.db.organizations.insert_one({"_id": self.dest, "name": "Beta"})
        self.user = {
            "_id": self.user_id,
            **membership_set([self.src, self.dest], [], self.src),
        }
        self.source = {
            "_id": ObjectId(),
            "organization_id": self.src,
            "created_by_user_id": self.user_id,
            "title": "Copiloto de tickets",
            "area_negocio": "Comercial",
            "dores": ["Retrabalho"],
            "oportunidade": ["A IA triaria tickets"],
            "score_valor": 5,
            "score_viabilidade": 4,
            "swot_id": ObjectId(),
            "tows_ids": ["t1"],
            "kr_ids": ["k1"],
            "cronograma": {
                "subtitulo": "Onda 1",
                "semanas": 8,
                "atividades": [
                    {
                        "id": "a01",
                        "titulo": "Pacote de dados",
                        "lideranca": "TI + Área",
                        "semana_inicio": 1,
                        "semana_fim": 3,
                        "predecessor": "",
                    }
                ],
                "marcos": [{"id": "m01", "semana": 4, "titulo": "Go/no-go"}],
            },
            "status": "aprovado_portfolio",
            "ai_system_id": ObjectId(),
            "projeto_aprovado": True,
            "aprovacao_comentario": "Comitê 09/04",
            "visibility": "shared",
        }
        self.db.canvas_projects.insert_one(dict(self.source))

    def test_clone_same_org_keeps_swot_drops_approval(self) -> None:
        body = CanvasProjectCloneRequest(organization_id=str(self.src))
        cloned = clone_project(
            str(self.source["_id"]), body, user=self.user, org_id=self.src, db=self.db
        )
        self.assertNotEqual(cloned["id"], str(self.source["_id"]))
        self.assertEqual(cloned["title"], "Copiloto de tickets (cópia)")
        self.assertEqual(cloned["area_negocio"], "Comercial")
        self.assertEqual(cloned["status"], "rascunho")
        self.assertIsNone(cloned["ai_system_id"])
        self.assertFalse(cloned["projeto_aprovado"])
        self.assertEqual(cloned["swot_id"], str(self.source["swot_id"]))
        self.assertEqual(cloned["tows_ids"], ["t1"])
        self.assertEqual(cloned["cronograma"]["atividades"][0]["titulo"], "Pacote de dados")
        self.assertNotEqual(cloned["cronograma"]["atividades"][0]["id"], "a01")
        stored = self.db.canvas_projects.find_one({"_id": ObjectId(cloned["id"])})
        self.assertEqual(stored["organization_id"], self.src)

    def test_clone_other_org_drops_cross_org_links(self) -> None:
        body = CanvasProjectCloneRequest(organization_id=str(self.dest), title="Cópia na Beta")
        cloned = clone_project(
            str(self.source["_id"]), body, user=self.user, org_id=self.src, db=self.db
        )
        self.assertEqual(cloned["title"], "Cópia na Beta")
        self.assertIsNone(cloned["swot_id"])
        self.assertEqual(cloned["tows_ids"], [])
        self.assertEqual(cloned["kr_ids"], [])
        stored = self.db.canvas_projects.find_one({"_id": ObjectId(cloned["id"])})
        self.assertEqual(stored["organization_id"], self.dest)
        self.assertEqual(stored["created_by_user_id"], self.user_id)

    def test_rejects_non_member(self) -> None:
        outsider = ObjectId()
        self.db.organizations.insert_one({"_id": outsider, "name": "Gamma"})
        body = CanvasProjectCloneRequest(organization_id=str(outsider))
        with self.assertRaises(HTTPException) as ctx:
            clone_project(
                str(self.source["_id"]), body, user=self.user, org_id=self.src, db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 403)
