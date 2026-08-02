"""Endpoints do módulo de Governança — chamadas diretas aos handlers com fake-Mongo, no
mesmo padrão dos demais testes do repo (sem TestClient/HTTP real)."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from app.governance.schemas import (
    AiSystemCreateRequest,
    AvaliacaoRegua,
    EvidenceSnapshotCreateRequest,
    EvidenciaPeriodo,
    GateChecklistUpdateRequest,
    GateCondicao,
    GateDecisao,
    GateDecisionRequest,
    RiskAssessmentCreateRequest,
)
from app.routes import governance as gov_routes


def _matches(doc: dict, flt: dict | None) -> bool:
    for key, expected in (flt or {}).items():
        if isinstance(expected, dict) and "$exists" in expected:
            has = key in doc and doc.get(key) is not None
            if has != expected["$exists"]:
                return False
            continue
        if isinstance(expected, dict) and "$ne" in expected:
            if doc.get(key) == expected["$ne"]:
                return False
            continue
        if doc.get(key) != expected:
            return False
    return True


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs

    def sort(self, field: str, direction: int = 1) -> "_Cursor":
        self._docs = sorted(self._docs, key=lambda d: d.get(field) or 0, reverse=direction < 0)
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

    def find_one(self, flt: dict | None = None, projection=None, sort=None) -> dict | None:
        candidates = [d for d in self.docs if _matches(d, flt)]
        if sort:
            field, direction = sort[0]
            candidates.sort(key=lambda d: d.get(field) or 0, reverse=direction < 0)
        return dict(candidates[0]) if candidates else None

    def find(self, flt: dict | None = None, projection=None) -> _Cursor:
        return _Cursor([dict(d) for d in self.docs if _matches(d, flt)])

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


def _add_user(db: _FakeDb, org_id: ObjectId, *, is_admin: bool = False, is_org_admin: bool = False) -> dict:
    user = {
        "_id": ObjectId(),
        "organization_id": org_id,
        "is_admin": is_admin,
        "is_org_admin": is_org_admin,
        "name": "U",
    }
    db.users.insert_one(user)
    return user


class OrganizationMembersEndpointTests(unittest.TestCase):
    def test_lists_only_same_organization_members(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        admin = _add_user(db, org_id, is_admin=True)
        _add_user(db, ObjectId())  # outra organizacao

        result = gov_routes.list_organization_members(user=user, org_id=org_id, db=db)

        ids = {m["id"] for m in result["items"]}
        self.assertEqual(ids, {str(user["_id"]), str(admin["_id"])})
        admin_entry = next(m for m in result["items"] if m["id"] == str(admin["_id"]))
        self.assertTrue(admin_entry["is_admin"])


class SystemsEndpointTests(unittest.TestCase):
    def test_create_get_update_list_roundtrip(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)

        created = gov_routes.create_system(
            AiSystemCreateRequest(nome="Agente de agendas", area_negocio="Centro Cirúrgico"),
            user=user, org_id=org_id, db=db,
        )
        self.assertEqual(created["nome"], "Agente de agendas")
        self.assertEqual(created["status"], "rascunho")

        fetched = gov_routes.get_system(created["id"], user=user, org_id=org_id, db=db)
        self.assertEqual(fetched["id"], created["id"])

        listed = gov_routes.list_systems(user=user, org_id=org_id, db=db)
        self.assertEqual([s["id"] for s in listed["items"]], [created["id"]])

    def test_get_system_wrong_org_is_404(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        created = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema X"), user=user, org_id=org_id, db=db
        )
        with self.assertRaises(HTTPException) as ctx:
            gov_routes.get_system(created["id"], user=user, org_id=ObjectId(), db=db)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail["code"], "SYSTEM_NOT_FOUND")


class AssessmentEndpointTests(unittest.TestCase):
    def _system(self, db: _FakeDb, org_id: ObjectId, user: dict, **fields) -> dict:
        return gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema", **fields), user=user, org_id=org_id, db=db
        )

    def test_aia_required_for_alto_risco(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        system = self._system(db, org_id, user)

        body = RiskAssessmentCreateRequest(
            regua=AvaliacaoRegua(dados="alto", impacto_erro="baixo", autonomia="baixo", exposicao_juridica="baixo")
        )
        with self.assertRaises(HTTPException) as ctx:
            gov_routes.create_assessment(system["id"], body, user=user, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.detail["code"], "AIA_REQUIRED")

    def test_due_diligence_required_for_api_terceiros(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        system = self._system(db, org_id, user, origem_ia="api_terceiros")

        body = RiskAssessmentCreateRequest(
            regua=AvaliacaoRegua(dados="baixo", impacto_erro="baixo", autonomia="baixo", exposicao_juridica="baixo")
        )
        with self.assertRaises(HTTPException) as ctx:
            gov_routes.create_assessment(system["id"], body, user=user, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.detail["code"], "DUE_DILIGENCE_REQUIRED")

    def test_publish_updates_system_risk_and_status(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        system = self._system(db, org_id, user)

        body = RiskAssessmentCreateRequest(
            regua=AvaliacaoRegua(dados="medio", impacto_erro="baixo", autonomia="baixo", exposicao_juridica="baixo")
        )
        assessment = gov_routes.create_assessment(system["id"], body, user=user, org_id=org_id, db=db)
        self.assertEqual(assessment["payload"]["nivel_final"], "medio")

        refreshed = gov_routes.get_system(system["id"], user=user, org_id=org_id, db=db)
        self.assertEqual(refreshed["classificacao_risco"]["nivel"], "medio")
        self.assertEqual(refreshed["classificacao_risco"]["fonte"], "avaliacao")
        self.assertEqual(refreshed["status"], "avaliado")

        history = gov_routes.list_assessments(system["id"], user=user, org_id=org_id, db=db)
        self.assertEqual(len(history["items"]), 1)


class GateEndpointTests(unittest.TestCase):
    def _system_with_risk(self, db, org_id, user, nivel="baixo") -> dict:
        system = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema"), user=user, org_id=org_id, db=db
        )
        if nivel:
            from app.governance import repository as gov_repo
            gov_repo.set_ai_system_risk(
                db, org_id=org_id, system_id=ObjectId(system["id"]), nivel=nivel, fonte="preliminar_r3"
            )
        return system

    def test_gate_blocked_without_assessment_for_alto_risco(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        system = self._system_with_risk(db, org_id, user, nivel="alto")

        with self.assertRaises(HTTPException) as ctx:
            gov_routes.create_gate(system["id"], user=user, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.detail["code"], "ASSESSMENT_REQUIRED")

    def test_gate_includes_template_and_bloco_f_from_swot(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        system = self._system_with_risk(db, org_id, user, nivel="baixo")
        db.swot_analyses.insert_one(
            {
                "_id": ObjectId(),
                "organization_id": org_id,
                "fraquezas": [{"id": "fx_1", "texto": "Sem política", "pilar": "governanca", "impacto": 5}],
                "ameacas": [],
                "forcas": [],
                "oportunidades": [],
                "updated_at": datetime.now(timezone.utc),
            }
        )

        gate = gov_routes.create_gate(system["id"], user=user, org_id=org_id, db=db)

        blocos = {item["bloco"] for item in gate["checklist"]}
        self.assertIn("A", blocos)
        self.assertNotIn("B", blocos, "sem origem_ia=api_terceiros, bloco B fica de fora")
        self.assertIn("F", blocos)
        item_f = next(i for i in gate["checklist"] if i["bloco"] == "F")
        self.assertEqual(item_f["origem"]["swot_item_id"], "fx_1")

        refreshed = gov_routes.get_system(system["id"], user=user, org_id=org_id, db=db)
        self.assertEqual(refreshed["status"], "em_gate")

    def test_gate_includes_bloco_b_for_api_terceiros(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        system = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema", origem_ia="api_terceiros"), user=user, org_id=org_id, db=db
        )
        gate = gov_routes.create_gate(system["id"], user=user, org_id=org_id, db=db)
        self.assertIn("B", {item["bloco"] for item in gate["checklist"]})

    def _approve_all_critical(self, db, org_id, user, gate_id) -> None:
        gate = gov_routes.get_gate(gate_id, user=user, org_id=org_id, db=db)
        for item in gate["checklist"]:
            if item["critico"]:
                gov_routes.update_gate_item(
                    gate_id, item["item_id"], GateChecklistUpdateRequest(status="aprovado"),
                    user=user, org_id=org_id, db=db,
                )

    def test_decide_go_blocked_by_open_critical_item(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        admin = _add_user(db, org_id, is_admin=True)
        system = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema"), user=user, org_id=org_id, db=db
        )
        gate = gov_routes.create_gate(system["id"], user=user, org_id=org_id, db=db)

        body = GateDecisionRequest(decisao=GateDecisao(resultado="go", aprovador_user_id=str(admin["_id"])))
        with self.assertRaises(HTTPException) as ctx:
            gov_routes.decide_gate(gate["id"], body, user=user, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.detail["code"], "GATE_CRITICAL_ITEM_OPEN")

    def test_decide_go_requires_admin_approver(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        non_admin = _add_user(db, org_id, is_admin=False)
        system = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema"), user=user, org_id=org_id, db=db
        )
        gate = gov_routes.create_gate(system["id"], user=user, org_id=org_id, db=db)
        self._approve_all_critical(db, org_id, user, gate["id"])

        body = GateDecisionRequest(decisao=GateDecisao(resultado="go", aprovador_user_id=str(non_admin["_id"])))
        with self.assertRaises(HTTPException) as ctx:
            gov_routes.decide_gate(gate["id"], body, user=user, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.detail["code"], "SINGLE_APPROVER_VIOLATION")

    def test_decide_go_succeeds_and_moves_system_to_producao(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        admin = _add_user(db, org_id, is_admin=True)
        system = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema"), user=user, org_id=org_id, db=db
        )
        gate = gov_routes.create_gate(system["id"], user=user, org_id=org_id, db=db)
        self._approve_all_critical(db, org_id, user, gate["id"])

        body = GateDecisionRequest(decisao=GateDecisao(resultado="go", aprovador_user_id=str(admin["_id"])))
        decided = gov_routes.decide_gate(gate["id"], body, user=user, org_id=org_id, db=db)
        self.assertEqual(decided["decisao"]["resultado"], "go")

        refreshed = gov_routes.get_system(system["id"], user=user, org_id=org_id, db=db)
        self.assertEqual(refreshed["status"], "producao")

    def test_org_admin_can_also_approve(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        org_admin = _add_user(db, org_id, is_org_admin=True)
        system = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema"), user=user, org_id=org_id, db=db
        )
        gate = gov_routes.create_gate(system["id"], user=user, org_id=org_id, db=db)
        self._approve_all_critical(db, org_id, user, gate["id"])

        body = GateDecisionRequest(decisao=GateDecisao(resultado="go", aprovador_user_id=str(org_admin["_id"])))
        decided = gov_routes.decide_gate(gate["id"], body, user=user, org_id=org_id, db=db)
        self.assertEqual(decided["decisao"]["resultado"], "go")

    def test_decide_no_go_moves_system_back_to_avaliado(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        admin = _add_user(db, org_id, is_admin=True)
        system = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema"), user=user, org_id=org_id, db=db
        )
        gate = gov_routes.create_gate(system["id"], user=user, org_id=org_id, db=db)

        body = GateDecisionRequest(decisao=GateDecisao(resultado="no_go", aprovador_user_id=str(admin["_id"])))
        gov_routes.decide_gate(gate["id"], body, user=user, org_id=org_id, db=db)

        refreshed = gov_routes.get_system(system["id"], user=user, org_id=org_id, db=db)
        self.assertEqual(refreshed["status"], "avaliado")

    def test_decide_go_condicional_requires_condicoes(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        admin = _add_user(db, org_id, is_admin=True)
        system = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema"), user=user, org_id=org_id, db=db
        )
        gate = gov_routes.create_gate(system["id"], user=user, org_id=org_id, db=db)
        self._approve_all_critical(db, org_id, user, gate["id"])

        body = GateDecisionRequest(
            decisao=GateDecisao(resultado="go_condicional", aprovador_user_id=str(admin["_id"]), condicoes=[])
        )
        with self.assertRaises(HTTPException) as ctx:
            gov_routes.decide_gate(gate["id"], body, user=user, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.detail["code"], "CONDITION_REQUIRED")

    def test_decide_go_condicional_with_condicao_owner_outside_org_fails(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        admin = _add_user(db, org_id, is_admin=True)
        outsider = _add_user(db, ObjectId())  # outra organizacao
        system = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema"), user=user, org_id=org_id, db=db
        )
        gate = gov_routes.create_gate(system["id"], user=user, org_id=org_id, db=db)
        self._approve_all_critical(db, org_id, user, gate["id"])

        body = GateDecisionRequest(
            decisao=GateDecisao(
                resultado="go_condicional",
                aprovador_user_id=str(admin["_id"]),
                condicoes=[GateCondicao(texto="Corrigir X", dono_user_id=str(outsider["_id"]))],
            )
        )
        with self.assertRaises(HTTPException) as ctx:
            gov_routes.decide_gate(gate["id"], body, user=user, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.detail["code"], "USER_NOT_IN_ORGANIZATION")


class TraceabilityEndpointTests(unittest.TestCase):
    def test_resolves_canvas_and_swot_chain(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)

        swot_id = ObjectId()
        maturity_id = ObjectId()
        db.swot_analyses.insert_one(
            {
                "_id": swot_id,
                "organization_id": org_id,
                "maturity_response_id": maturity_id,
                "fraquezas": [{"id": "fx_1", "texto": "Sem política", "pilar": "governanca", "question_id": "GR1"}],
                "ameacas": [], "forcas": [], "oportunidades": [],
                "updated_at": datetime.now(timezone.utc),
            }
        )
        canvas_id = ObjectId()
        db.canvas_projects.insert_one(
            {
                "_id": canvas_id,
                "organization_id": org_id,
                "title": "Projeto X",
                "area_negocio": "TI",
                "swot_id": str(swot_id),
                "swot_item_ids": ["fx_1"],
            }
        )
        system = gov_routes.create_system(
            AiSystemCreateRequest(nome="Sistema", canvas_project_id=str(canvas_id)),
            user=user, org_id=org_id, db=db,
        )

        trace = gov_routes.get_traceability(system["id"], user=user, org_id=org_id, db=db)

        self.assertEqual(trace["canvas"]["canvas_project_id"], str(canvas_id))
        self.assertEqual(trace["canvas"]["swot_id"], str(swot_id))
        self.assertEqual(trace["maturity_response_id"], str(maturity_id))
        self.assertEqual([i["id"] for i in trace["swot_items"]], ["fx_1"])
        self.assertEqual(trace["csf_ids"], ["GR1"])


class EvidenceSnapshotEndpointTests(unittest.TestCase):
    def test_publish_and_read_metrics(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)

        empty = gov_routes.get_metrics(user=user, org_id=org_id, db=db)
        self.assertFalse(empty["published"])

        body = EvidenceSnapshotCreateRequest(
            pct_sistemas_inventariados=0.9, periodo=EvidenciaPeriodo(inicio="2026-01-01", fim="2026-01-31")
        )
        gov_routes.create_evidence_snapshot(body, user=user, org_id=org_id, db=db)

        metrics = gov_routes.get_metrics(user=user, org_id=org_id, db=db)
        self.assertTrue(metrics["published"])
        self.assertEqual(metrics["metrics"]["pct_sistemas_inventariados"], 0.9)


class ProfundidadeEndpointTests(unittest.TestCase):
    def test_recalcular_without_maturity_raises(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        with self.assertRaises(HTTPException) as ctx:
            gov_routes.recalcular_profundidade(user=user, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.detail["code"], "MATURITY_NOT_PUBLISHED")

    def test_recalcular_upgrade_applies_immediately(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        db.organizations.insert_one({"_id": org_id, "name": "Empresa"})
        db.maturity_responses.insert_one(
            {
                "_id": ObjectId(), "organization_id": org_id, "complete": True,
                "submitted_at": datetime.now(timezone.utc),
                "answers": {"GR1": 5, "GR2": 4},
            }
        )

        result = gov_routes.recalcular_profundidade(user=user, org_id=org_id, db=db)
        self.assertEqual(result["value"], "completo")
        self.assertEqual(result["suggested_value"], "completo")

    def test_recalcular_downgrade_only_suggests(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        db.organizations.insert_one(
            {"_id": org_id, "name": "Empresa", "governance_profundidade": {"value": "completo"}}
        )
        db.maturity_responses.insert_one(
            {
                "_id": ObjectId(), "organization_id": org_id, "complete": True,
                "submitted_at": datetime.now(timezone.utc),
                "answers": {"GR1": 1, "GR2": 4},
            }
        )

        result = gov_routes.recalcular_profundidade(user=user, org_id=org_id, db=db)
        self.assertEqual(result["value"], "completo", "nao rebaixa sozinho")
        self.assertEqual(result["suggested_value"], "fundacao")

        confirmed = gov_routes.confirmar_profundidade(user=user, org_id=org_id, db=db)
        self.assertEqual(confirmed["value"], "fundacao")
        self.assertEqual(confirmed["confirmed_by_user_id"], user["_id"])

    def test_confirmar_without_pending_suggestion_raises(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        user = _add_user(db, org_id)
        db.organizations.insert_one({"_id": org_id, "name": "Empresa"})
        with self.assertRaises(HTTPException) as ctx:
            gov_routes.confirmar_profundidade(user=user, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.detail["code"], "NO_PENDING_SUGGESTION")


if __name__ == "__main__":
    unittest.main()
