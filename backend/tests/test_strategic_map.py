"""Mapa Estratégico: árvore maturidade → SWOT → TOWS → projetos e vínculos de projeto."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId

from app.routes.strategic_map import get_strategic_map
from app.swot_from_maturity import build_swot_fields_from_maturity

_SEED = Path(__file__).resolve().parents[1] / "data" / "ai_maturity_model.json"


def _matches(doc: dict, flt: dict | None) -> bool:
    for key, expected in (flt or {}).items():
        if doc.get(key) != expected:
            return False
    return True


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs

    def sort(self, *_args, **_kwargs) -> "_Cursor":
        return self

    def __iter__(self):
        return iter(self._docs)


class _Collection:
    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs

    def find(self, flt: dict | None = None, projection=None) -> _Cursor:
        return _Cursor([d for d in self.docs if _matches(d, flt)])

    def find_one(self, flt: dict | None = None, projection=None, sort=None) -> dict | None:
        for doc in self.docs:
            if _matches(doc, flt):
                return doc
        return None


class _FakeDb:
    def __init__(self, **collections: list[dict]) -> None:
        for name, docs in collections.items():
            setattr(self, name, _Collection(docs))

    def __getattr__(self, name: str) -> _Collection:
        # Coleção não passada no fixture (ex.: okr_cycles quando o teste não usa OKR) —
        # se comporta como vazia, em vez de AttributeError.
        col = _Collection([])
        setattr(self, name, col)
        return col


def _map_for(db: _FakeDb, user: dict, org_id: ObjectId) -> dict:
    """Chama a rota fora do FastAPI (os defaults `Query` precisam ser explícitos)."""
    return get_strategic_map(
        maturity_response_id=None,
        swot_id=None,
        user=user,
        org_id=org_id,
        db=db,
    )


class StrategicMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(_SEED.read_text(encoding="utf-8"))
        cls.questions = {
            q["id"]: q for dim in cls.model["dimensions"] for q in dim["questions"]
        }

    def _fixture(self, *, drop_question_id: bool = False) -> tuple[_FakeDb, dict, ObjectId, dict, dict]:
        """Autoavaliação completa + SWOT gerada + um projeto vinculado."""
        user_id = ObjectId()
        org_id = ObjectId()
        model_id = ObjectId()
        maturity_id = ObjectId()
        swot_id = ObjectId()
        now = datetime.now(timezone.utc)

        answers = {qid: 4 for qid in self.questions}
        answers["EV1"] = 5
        answers["DI3"] = 1
        result = {
            "total_score": 45,
            "max_score": 60,
            "percent_score": 75,
            "level": {"label": "Estruturado", "description": "d"},
            "dimension_scores": {
                dim["id"]: {"name": dim["name"], "score": 20, "max": 25, "avg": 4.0}
                for dim in self.model["dimensions"]
            },
            "tier": "basico",
        }
        fields = build_swot_fields_from_maturity(
            model=self.model, answers=answers, tier="basico", result=result
        )
        if drop_question_id:
            for field in ("forcas", "fraquezas", "oportunidades", "ameacas"):
                for item in fields[field]:
                    item.pop("question_id", None)

        force = next(item for item in fields["forcas"] if item["id"] == "f_ev1")
        initiative = next(
            init for init in fields["tows_fo"] if force["id"] in init["itens_internos"]
        )
        project = {
            "_id": ObjectId(),
            "organization_id": org_id,
            "created_by_user_id": user_id,
            "title": "Copiloto de atendimento",
            "swot_id": str(swot_id),
            "swot_item_ids": [force["id"]],
            "tows_ids": [initiative["id"]],
            "score_valor": 5,
            "score_viabilidade": 4,
            "created_at": now,
            "updated_at": now,
        }
        orphan_project = {
            "_id": ObjectId(),
            "organization_id": org_id,
            "created_by_user_id": user_id,
            "title": "Projeto solto",
            "created_at": now,
            "updated_at": now,
        }

        db = _FakeDb(
            ai_maturity_model=[{**self.model, "_id": model_id}],
            maturity_responses=[
                {
                    "_id": maturity_id,
                    "organization_id": org_id,
                    "created_by_user_id": user_id,
                    "model_id": model_id,
                    "assessment_title": "Diagnóstico",
                    "tier": "basico",
                    "answers": answers,
                    "result": result,
                    "complete": True,
                    "submitted_at": now,
                }
            ],
            swot_analyses=[
                {
                    "_id": swot_id,
                    "organization_id": org_id,
                    "created_by_user_id": user_id,
                    "maturity_response_id": maturity_id,
                    **fields,
                    "created_at": now,
                    "updated_at": now,
                }
            ],
            canvas_projects=[project, orphan_project],
        )
        return db, {"_id": user_id}, org_id, project, initiative

    def test_tree_links_question_to_swot_item_to_project(self) -> None:
        db, user, org_id, project, initiative = self._fixture()
        payload = _map_for(db, user, org_id)

        self.assertTrue(payload["dimensions"], "árvore sem dimensões")
        question = next(
            q
            for dim in payload["dimensions"]
            for q in dim["questions"]
            if q["id"] == "EV1"
        )
        self.assertEqual(question["answer"], 5)

        force = next(item for item in question["items"] if item["id"] == "f_ev1")
        self.assertEqual(force["quadrant"], "forcas")
        self.assertEqual(force["question_id"].lower(), "ev1")
        self.assertEqual([p["id"] for p in force["projects"]], [str(project["_id"])])

        linked = next(
            init for init in force["initiatives"] if init["id"] == initiative["id"]
        )
        self.assertEqual(linked["field"], "tows_fo")
        self.assertEqual([p["id"] for p in linked["projects"]], [str(project["_id"])])
        self.assertTrue(linked["counterparts"], "iniciativa sem contraparte externa")

    def test_external_items_report_tows_usage(self) -> None:
        """Oportunidade/ameaça entra no TOWS como contraparte — `used_in` sustenta o filtro."""
        db, user, org_id, _project, _initiative = self._fixture()
        payload = _map_for(db, user, org_id)
        items = {
            item["id"]: item
            for dim in payload["dimensions"]
            for question in dim["questions"]
            for item in question["items"]
        }
        opportunity = items["o_ev1"]
        self.assertEqual(opportunity["initiatives"], [])
        self.assertGreater(opportunity["used_in"], 0)
        self.assertEqual(items["f_ev1"]["used_in"], 0)

    def test_question_id_falls_back_to_item_id_convention(self) -> None:
        db, user, org_id, _project, _initiative = self._fixture(drop_question_id=True)
        payload = _map_for(db, user, org_id)
        question = next(
            q
            for dim in payload["dimensions"]
            for q in dim["questions"]
            if q["id"] == "EV1"
        )
        self.assertIn("f_ev1", [item["id"] for item in question["items"]])
        self.assertEqual(payload["unlinked"]["swot_items"], [])

    def test_stats_and_unlinked_projects(self) -> None:
        db, user, org_id, project, _initiative = self._fixture()
        payload = _map_for(db, user, org_id)

        stats = payload["stats"]
        self.assertEqual(stats["projects_total"], 2)
        self.assertEqual(stats["projects_linked"], 1)
        self.assertGreater(stats["questions"], 0)
        self.assertGreater(stats["swot_items"], 0)

        orphans = payload["unlinked"]["projects"]
        self.assertEqual([o["title"] for o in orphans], ["Projeto solto"])
        self.assertFalse(orphans[0]["linked_to_swot"])
        self.assertNotIn(str(project["_id"]), [o["id"] for o in orphans])

    def test_source_head_and_sources_list(self) -> None:
        db, user, org_id, _project, _initiative = self._fixture()
        payload = _map_for(db, user, org_id)
        head = payload["source"]
        self.assertEqual(head["tier"], "basico")
        self.assertEqual(head["tier_label"], "Básico")
        self.assertTrue(head["swot_id"])
        self.assertTrue(head["maturity_response_id"])
        self.assertEqual(head["result"]["level_label"], "Estruturado")
        self.assertEqual(len(payload["sources"]), 1)
        self.assertEqual(payload["sources"][0]["swot_id"], head["swot_id"])

    def test_no_active_okr_cycle_does_not_crash(self) -> None:
        db, user, org_id, _project, _initiative = self._fixture()
        payload = _map_for(db, user, org_id)
        self.assertIsNone(payload["okr_cycle"])
        self.assertEqual(payload["unlinked"]["objectives"], [])
        self.assertEqual(payload["unlinked"]["key_results"], [])
        self.assertEqual(payload["stats"]["objectives"], 0)
        self.assertEqual(payload["stats"]["key_results"], 0)

    def test_objective_linked_to_tows_appears_nested_under_initiative(self) -> None:
        db, user, org_id, project, initiative = self._fixture()
        kr = {
            "id": "kr_abc", "titulo": "Reduzir TMA", "descricao": "", "unidade": "min",
            "baseline": 40.0, "current": 25.0, "target": 10.0, "direction": "decrease", "dono": "",
        }
        objective = {
            "id": "obj_1", "titulo": "Atendimento mais rápido", "descricao": "", "dono": "",
            "pilar": "", "swot_id": None, "swot_item_ids": [], "tows_ids": [initiative["id"]],
            "key_results": [kr],
        }
        project["kr_ids"] = ["kr_abc"]
        db.okr_cycles = _Collection([
            {
                "_id": ObjectId(), "organization_id": org_id, "status": "ativo",
                "tipo": "ano", "ano": 2026, "trimestre": None, "nome": "",
                "objectives": [objective], "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ])

        payload = _map_for(db, user, org_id)

        self.assertEqual(payload["okr_cycle"]["status"], "ativo")
        self.assertEqual(payload["stats"]["objectives"], 1)
        self.assertEqual(payload["stats"]["objectives_linked"], 1)
        self.assertEqual(payload["stats"]["key_results"], 1)
        self.assertEqual(payload["stats"]["key_results_linked"], 1)
        self.assertEqual(payload["unlinked"]["objectives"], [])
        self.assertEqual(payload["unlinked"]["key_results"], [])

        force = next(
            item
            for dim in payload["dimensions"]
            for q in dim["questions"]
            for item in q["items"]
            if item["id"] == "f_ev1"
        )
        linked_initiative = next(i for i in force["initiatives"] if i["id"] == initiative["id"])
        self.assertEqual(len(linked_initiative["objectives"]), 1)
        obj_node = linked_initiative["objectives"][0]
        self.assertEqual(obj_node["id"], "obj_1")
        self.assertEqual(obj_node["key_results"][0]["progress_pct"], 50.0)
        self.assertEqual([p["id"] for p in obj_node["key_results"][0]["projects"]], [str(project["_id"])])

    def test_objective_with_no_valid_link_is_orphan(self) -> None:
        db, user, org_id, _project, _initiative = self._fixture()
        objective = {
            "id": "obj_orfao", "titulo": "Objetivo solto", "descricao": "", "dono": "",
            "pilar": "", "swot_id": None, "swot_item_ids": [], "tows_ids": ["tows_inexistente"],
            "key_results": [],
        }
        db.okr_cycles = _Collection([
            {
                "_id": ObjectId(), "organization_id": org_id, "status": "ativo",
                "tipo": "ano", "ano": 2026, "trimestre": None, "nome": "",
                "objectives": [objective], "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ])

        payload = _map_for(db, user, org_id)

        self.assertEqual(len(payload["unlinked"]["objectives"]), 1)
        self.assertEqual(payload["unlinked"]["objectives"][0]["id"], "obj_orfao")
        self.assertEqual(payload["stats"]["objectives_linked"], 0)

    def test_key_result_without_project_link_is_orphan(self) -> None:
        db, user, org_id, _project, initiative = self._fixture()
        kr = {
            "id": "kr_sem_projeto", "titulo": "Meta sem projeto", "descricao": "", "unidade": "",
            "baseline": 0.0, "current": 0.0, "target": 100.0, "direction": "increase", "dono": "",
        }
        objective = {
            "id": "obj_2", "titulo": "Objetivo com KR órfão", "descricao": "", "dono": "",
            "pilar": "", "swot_id": None, "swot_item_ids": [], "tows_ids": [initiative["id"]],
            "key_results": [kr],
        }
        db.okr_cycles = _Collection([
            {
                "_id": ObjectId(), "organization_id": org_id, "status": "ativo",
                "tipo": "ano", "ano": 2026, "trimestre": None, "nome": "",
                "objectives": [objective], "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ])

        payload = _map_for(db, user, org_id)

        self.assertEqual([kr["id"] for kr in payload["unlinked"]["key_results"]], ["kr_sem_projeto"])
        self.assertEqual(payload["stats"]["key_results_linked"], 0)

    def test_maturity_without_swot_keeps_questions(self) -> None:
        db, user, org_id, _project, _initiative = self._fixture()
        db.swot_analyses = _Collection([])
        payload = _map_for(db, user, org_id)
        self.assertIsNone(payload["source"]["swot_id"])
        self.assertTrue(payload["dimensions"])
        for dim in payload["dimensions"]:
            for question in dim["questions"]:
                self.assertEqual(question["items"], [])
        self.assertEqual(payload["stats"]["swot_items"], 0)
        self.assertEqual(payload["stats"]["projects_linked"], 0)


if __name__ == "__main__":
    unittest.main()
