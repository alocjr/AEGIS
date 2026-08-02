"""Hook Canvas → Inventário: POST /api/canvas-projects/{id}/aprovar-portfolio."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId

from app.routes.canvas_projects import aprovar_portfolio


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


def _project(org_id: ObjectId, **overrides) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "_id": ObjectId(),
        "organization_id": org_id,
        "created_by_user_id": ObjectId(),
        "title": "Agente de triagem",
        "area_negocio": "Atendimento",
        "objetivo_estrategico": "Reduzir tempo de resposta",
        "oportunidade": ["Automatizar triagem"],
        "oportunidade_tipos": [],
        "dados_estruturado": {"descricao": "Dados de tickets", "sensibilidade": "pessoal"},
        "riscos_estruturado": {"descricao": "", "regulatorio": [], "human_in_the_loop": "nenhum"},
        "status": "rascunho",
        "ai_system_id": None,
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


class AprovarPortfolioTests(unittest.TestCase):
    def test_creates_ai_system_and_marks_project_approved(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = _project(org_id)
        db.canvas_projects.insert_one(project)
        user = {"_id": ObjectId()}

        result = aprovar_portfolio(str(project["_id"]), user=user, org_id=org_id, db=db)

        self.assertTrue(result["created"])
        self.assertEqual(result["status"], "aguardando_avaliacao")
        self.assertIn(result["risco_preliminar"], ("baixo", "medio", "alto", "critico"))

        refreshed = db.canvas_projects.find_one({"_id": project["_id"]})
        self.assertEqual(refreshed["status"], "aprovado_portfolio")
        self.assertEqual(str(refreshed["ai_system_id"]), result["ai_system_id"])

        system = db.ai_systems.find_one({"_id": ObjectId(result["ai_system_id"])})
        self.assertEqual(system["canvas_project_id"], project["_id"])
        self.assertEqual(system["nome"], "Agente de triagem")

    def test_idempotent_on_second_call(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = _project(org_id)
        db.canvas_projects.insert_one(project)
        user = {"_id": ObjectId()}

        first = aprovar_portfolio(str(project["_id"]), user=user, org_id=org_id, db=db)
        second = aprovar_portfolio(str(project["_id"]), user=user, org_id=org_id, db=db)

        self.assertFalse(second["created"])
        self.assertEqual(first["ai_system_id"], second["ai_system_id"])
        self.assertEqual(db.ai_systems.count_documents({"organization_id": org_id}), 1)

    def test_agente_sem_hitl_e_regulatorio_da_risco_critico(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        project = _project(
            org_id,
            oportunidade_tipos=["Agente autônomo"],
            dados_estruturado={"descricao": "", "sensibilidade": "sensivel"},
            riscos_estruturado={"descricao": "", "regulatorio": ["LGPD art.11"], "human_in_the_loop": "nenhum"},
        )
        db.canvas_projects.insert_one(project)
        user = {"_id": ObjectId()}

        result = aprovar_portfolio(str(project["_id"]), user=user, org_id=org_id, db=db)

        self.assertEqual(result["risco_preliminar"], "critico")


if __name__ == "__main__":
    unittest.main()
