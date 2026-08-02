"""Repositório do módulo de Governança: ai_systems (mutável+audit) e artefatos versionados."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId

from app.governance import repository as gov_repo
from app.governance.schemas import AvaliacaoRegua, nivel_final_da_regua


def _matches(doc: dict, flt: dict | None) -> bool:
    for key, expected in (flt or {}).items():
        if isinstance(expected, dict) and "$exists" in expected:
            has = key in doc and doc.get(key) is not None
            if has != expected["$exists"]:
                return False
            continue
        if doc.get(key) != expected:
            return False
    return True


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs

    def sort(self, field: str, direction: int = 1) -> "_Cursor":
        self._docs = sorted(
            self._docs, key=lambda d: d.get(field) or 0, reverse=direction < 0
        )
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
        # Cópia rasa — como o driver real, isolada de mutações posteriores via update_one.
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


class AiSystemsTests(unittest.TestCase):
    def test_create_sets_defaults_and_writes_audit_log(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        actor_id = ObjectId()

        doc = gov_repo.create_ai_system(
            db, org_id=org_id, actor_user_id=actor_id, data={"nome": "Agente de agendas"}
        )

        self.assertEqual(doc["organization_id"], org_id)
        self.assertEqual(doc["status"], "rascunho")
        self.assertEqual(doc["created_by_user_id"], actor_id)
        self.assertIsNone(doc["canvas_project_id"])
        self.assertEqual(doc["classificacao_risco"], {"nivel": None, "fonte": None, "avaliacao_id": None})

        logs = db.ai_governance_audit_log.docs
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["action"], "create")
        self.assertEqual(logs[0]["entity_id"], doc["_id"])
        self.assertEqual(logs[0]["organization_id"], org_id)

    def test_create_links_canvas_project_and_normalizes_user_refs(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        canvas_id = ObjectId()
        owner_id = ObjectId()

        doc = gov_repo.create_ai_system(
            db,
            org_id=org_id,
            actor_user_id=ObjectId(),
            data={
                "nome": "Copiloto",
                "canvas_project_id": str(canvas_id),
                "responsavel_negocio_user_id": str(owner_id),
            },
        )

        self.assertEqual(doc["canvas_project_id"], canvas_id)
        self.assertEqual(doc["responsavel_negocio_user_id"], owner_id)

    def test_update_writes_diff_only_for_changed_fields(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        actor_id = ObjectId()
        created = gov_repo.create_ai_system(
            db, org_id=org_id, actor_user_id=actor_id, data={"nome": "Sistema X", "area_negocio": "TI"}
        )

        updated = gov_repo.update_ai_system(
            db,
            org_id=org_id,
            actor_user_id=actor_id,
            system_id=str(created["_id"]),
            updates={"area_negocio": "TI", "finalidade": "Nova finalidade"},
        )

        self.assertEqual(updated["finalidade"], "Nova finalidade")
        logs = [l for l in db.ai_governance_audit_log.docs if l["action"] == "update"]
        self.assertEqual(len(logs), 1)
        self.assertIn("finalidade", logs[0]["diff"])
        self.assertNotIn("area_negocio", logs[0]["diff"], "campo sem mudança não deve virar diff")

    def test_mutating_modelo_of_system_in_producao_triggers_reavaliacao(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        actor_id = ObjectId()
        created = gov_repo.create_ai_system(db, org_id=org_id, actor_user_id=actor_id, data={"nome": "X", "modelo": "gpt-4"})
        gov_repo.update_ai_system(
            db, org_id=org_id, actor_user_id=actor_id, system_id=str(created["_id"]), updates={"status": "producao"}
        )

        updated = gov_repo.update_ai_system(
            db, org_id=org_id, actor_user_id=actor_id, system_id=str(created["_id"]), updates={"modelo": "gpt-5"}
        )

        self.assertEqual(updated["status"], "reavaliacao_pendente")

    def test_mutating_unrelated_field_of_system_in_producao_keeps_status(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        actor_id = ObjectId()
        created = gov_repo.create_ai_system(db, org_id=org_id, actor_user_id=actor_id, data={"nome": "X"})
        gov_repo.update_ai_system(
            db, org_id=org_id, actor_user_id=actor_id, system_id=str(created["_id"]), updates={"status": "producao"}
        )

        updated = gov_repo.update_ai_system(
            db, org_id=org_id, actor_user_id=actor_id, system_id=str(created["_id"]),
            updates={"area_negocio": "Nova área"},
        )

        self.assertEqual(updated["status"], "producao")

    def test_explicit_status_change_is_not_overridden_by_trigger(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        actor_id = ObjectId()
        created = gov_repo.create_ai_system(db, org_id=org_id, actor_user_id=actor_id, data={"nome": "X"})
        gov_repo.update_ai_system(
            db, org_id=org_id, actor_user_id=actor_id, system_id=str(created["_id"]), updates={"status": "producao"}
        )

        updated = gov_repo.update_ai_system(
            db, org_id=org_id, actor_user_id=actor_id, system_id=str(created["_id"]),
            updates={"modelo": "gpt-5", "status": "descontinuado"},
        )

        self.assertEqual(updated["status"], "descontinuado")

    def test_mutating_modelo_outside_producao_does_not_trigger(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        actor_id = ObjectId()
        created = gov_repo.create_ai_system(db, org_id=org_id, actor_user_id=actor_id, data={"nome": "X"})

        updated = gov_repo.update_ai_system(
            db, org_id=org_id, actor_user_id=actor_id, system_id=str(created["_id"]), updates={"modelo": "gpt-5"}
        )

        self.assertEqual(updated["status"], "rascunho")

    def test_update_noop_writes_no_audit_log(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        actor_id = ObjectId()
        created = gov_repo.create_ai_system(db, org_id=org_id, actor_user_id=actor_id, data={"nome": "X"})

        gov_repo.update_ai_system(
            db, org_id=org_id, actor_user_id=actor_id, system_id=str(created["_id"]), updates={}
        )

        logs = [l for l in db.ai_governance_audit_log.docs if l["action"] == "update"]
        self.assertEqual(len(logs), 0)

    def test_get_ai_system_scoped_to_organization(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        other_org_id = ObjectId()
        created = gov_repo.create_ai_system(db, org_id=org_id, actor_user_id=ObjectId(), data={"nome": "X"})

        with self.assertRaises(gov_repo.GovernanceError) as ctx:
            gov_repo.get_ai_system(db, org_id=other_org_id, system_id=str(created["_id"]))
        self.assertEqual(ctx.exception.code, "SYSTEM_NOT_FOUND")

    def test_get_ai_system_invalid_id(self) -> None:
        db = _FakeDb()
        with self.assertRaises(gov_repo.GovernanceError) as ctx:
            gov_repo.get_ai_system(db, org_id=ObjectId(), system_id="not-an-id")
        self.assertEqual(ctx.exception.code, "INVALID_ID")

    def test_find_ai_system_by_canvas_project(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        canvas_id = ObjectId()
        created = gov_repo.create_ai_system(
            db, org_id=org_id, actor_user_id=ObjectId(),
            data={"nome": "X", "canvas_project_id": str(canvas_id)},
        )

        found = gov_repo.find_ai_system_by_canvas_project(db, org_id=org_id, canvas_project_id=canvas_id)
        self.assertEqual(found["_id"], created["_id"])
        self.assertIsNone(
            gov_repo.find_ai_system_by_canvas_project(db, org_id=org_id, canvas_project_id=ObjectId())
        )

    def test_list_ai_systems_scoped_and_sorted(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        first = gov_repo.create_ai_system(db, org_id=org_id, actor_user_id=ObjectId(), data={"nome": "A"})
        second = gov_repo.create_ai_system(db, org_id=org_id, actor_user_id=ObjectId(), data={"nome": "B"})
        gov_repo.create_ai_system(db, org_id=ObjectId(), actor_user_id=ObjectId(), data={"nome": "Outra org"})
        second["updated_at"] = datetime(2030, 1, 1, tzinfo=timezone.utc)

        items = gov_repo.list_ai_systems(db, org_id=org_id)

        self.assertEqual({d["_id"] for d in items}, {first["_id"], second["_id"]})
        self.assertEqual(items[0]["_id"], second["_id"], "mais recente primeiro")

    def test_set_ai_system_risk_bypasses_field_audit(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        created = gov_repo.create_ai_system(db, org_id=org_id, actor_user_id=ObjectId(), data={"nome": "X"})

        gov_repo.set_ai_system_risk(
            db, org_id=org_id, system_id=created["_id"], nivel="alto", fonte="preliminar_r3"
        )

        refreshed = gov_repo.get_ai_system(db, org_id=org_id, system_id=str(created["_id"]))
        self.assertEqual(refreshed["classificacao_risco"]["nivel"], "alto")
        self.assertEqual(refreshed["classificacao_risco"]["fonte"], "preliminar_r3")


class VersionedArtifactsTests(unittest.TestCase):
    def test_risk_assessment_revisions_never_mutate_prior_version(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        system_id = ObjectId()

        first = gov_repo.publish_risk_assessment(
            db, org_id=org_id, system_id=system_id, payload={"nivel_final": "medio"},
            actor_user_id=ObjectId(),
        )
        second = gov_repo.publish_risk_assessment(
            db, org_id=org_id, system_id=system_id, payload={"nivel_final": "alto"},
            actor_user_id=ObjectId(),
        )

        self.assertEqual(first["revision"], 1)
        self.assertEqual(second["revision"], 2)
        self.assertNotEqual(first["_id"], second["_id"])
        # o documento da 1ª publicação continua intacto
        self.assertEqual(db.ai_risk_assessments.docs[0]["payload"]["nivel_final"], "medio")

        latest = gov_repo.latest_risk_assessment(db, org_id=org_id, system_id=system_id)
        self.assertEqual(latest["_id"], second["_id"])
        self.assertEqual(
            [d["revision"] for d in gov_repo.list_risk_assessments(db, org_id=org_id, system_id=system_id)],
            [2, 1],
        )

    def test_risk_assessment_scoped_per_system(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        gov_repo.publish_risk_assessment(
            db, org_id=org_id, system_id=ObjectId(), payload={}, actor_user_id=ObjectId()
        )
        self.assertIsNone(
            gov_repo.latest_risk_assessment(db, org_id=org_id, system_id=ObjectId())
        )

    def _checklist(self, **overrides) -> list[dict]:
        item = {
            "bloco": "A",
            "item_id": "A1",
            "texto": "Base legal identificada",
            "critico": True,
            "status": "pendente",
            "evidencia": {"descricao": "", "link_ou_artifact_id": ""},
            "origem": {"tipo": "template", "swot_item_id": None, "rule": None},
        }
        item.update(overrides)
        return [item]

    def test_create_gate_starts_as_undecided_draft(self) -> None:
        db = _FakeDb()
        org_id, system_id = ObjectId(), ObjectId()

        gate = gov_repo.create_gate(
            db, org_id=org_id, system_id=system_id, checklist=self._checklist(),
            template_version="1", rules_applied=[], actor_user_id=ObjectId(),
        )

        self.assertEqual(gate["revision"], 1)
        self.assertIsNone(gate["decisao"])
        self.assertEqual(gov_repo.latest_gate(db, org_id=org_id, system_id=system_id)["_id"], gate["_id"])

    def test_update_checklist_item_mutates_same_revision(self) -> None:
        db = _FakeDb()
        org_id, system_id = ObjectId(), ObjectId()
        gate = gov_repo.create_gate(
            db, org_id=org_id, system_id=system_id, checklist=self._checklist(),
            template_version="1", rules_applied=[], actor_user_id=ObjectId(),
        )

        updated = gov_repo.update_gate_checklist_item(
            db, org_id=org_id, gate_id=str(gate["_id"]), item_id="A1",
            status="aprovado", evidencia={"descricao": "ok", "link_ou_artifact_id": ""},
        )

        self.assertEqual(updated["_id"], gate["_id"], "mesma revisao, so mutou o item")
        self.assertEqual(updated["revision"], 1)
        self.assertEqual(updated["checklist"][0]["status"], "aprovado")

    def test_update_unknown_item_raises(self) -> None:
        db = _FakeDb()
        org_id, system_id = ObjectId(), ObjectId()
        gate = gov_repo.create_gate(
            db, org_id=org_id, system_id=system_id, checklist=self._checklist(),
            template_version="1", rules_applied=[], actor_user_id=ObjectId(),
        )
        with self.assertRaises(gov_repo.GovernanceError) as ctx:
            gov_repo.update_gate_checklist_item(
                db, org_id=org_id, gate_id=str(gate["_id"]), item_id="Z9", status="aprovado"
            )
        self.assertEqual(ctx.exception.code, "ITEM_NOT_FOUND")

    def test_critico_nao_aplicavel_sem_justificativa_raises(self) -> None:
        db = _FakeDb()
        org_id, system_id = ObjectId(), ObjectId()
        gate = gov_repo.create_gate(
            db, org_id=org_id, system_id=system_id, checklist=self._checklist(),
            template_version="1", rules_applied=[], actor_user_id=ObjectId(),
        )
        with self.assertRaises(gov_repo.GovernanceError) as ctx:
            gov_repo.update_gate_checklist_item(
                db, org_id=org_id, gate_id=str(gate["_id"]), item_id="A1", status="nao_aplicavel"
            )
        self.assertEqual(ctx.exception.code, "ITEM_JUSTIFICATION_REQUIRED")

    def test_critico_nao_aplicavel_com_justificativa_ok(self) -> None:
        db = _FakeDb()
        org_id, system_id = ObjectId(), ObjectId()
        gate = gov_repo.create_gate(
            db, org_id=org_id, system_id=system_id, checklist=self._checklist(),
            template_version="1", rules_applied=[], actor_user_id=ObjectId(),
        )
        updated = gov_repo.update_gate_checklist_item(
            db, org_id=org_id, gate_id=str(gate["_id"]), item_id="A1", status="nao_aplicavel",
            evidencia={"descricao": "Nao se aplica pois...", "link_ou_artifact_id": ""},
        )
        self.assertEqual(updated["checklist"][0]["status"], "nao_aplicavel")

    def test_decide_gate_blocks_go_with_open_critical_item(self) -> None:
        db = _FakeDb()
        org_id, system_id = ObjectId(), ObjectId()
        gate = gov_repo.create_gate(
            db, org_id=org_id, system_id=system_id, checklist=self._checklist(),
            template_version="1", rules_applied=[], actor_user_id=ObjectId(),
        )
        with self.assertRaises(gov_repo.GovernanceError) as ctx:
            gov_repo.decide_gate(
                db, org_id=org_id, gate_id=str(gate["_id"]),
                decisao={"resultado": "go", "aprovador_user_id": str(ObjectId())},
                actor_user_id=ObjectId(),
            )
        self.assertEqual(ctx.exception.code, "GATE_CRITICAL_ITEM_OPEN")

    def test_decide_gate_go_condicional_requires_condicoes(self) -> None:
        db = _FakeDb()
        org_id, system_id = ObjectId(), ObjectId()
        gate = gov_repo.create_gate(
            db, org_id=org_id, system_id=system_id, checklist=self._checklist(status="aprovado"),
            template_version="1", rules_applied=[], actor_user_id=ObjectId(),
        )
        with self.assertRaises(gov_repo.GovernanceError) as ctx:
            gov_repo.decide_gate(
                db, org_id=org_id, gate_id=str(gate["_id"]),
                decisao={"resultado": "go_condicional", "condicoes": [], "aprovador_user_id": str(ObjectId())},
                actor_user_id=ObjectId(),
            )
        self.assertEqual(ctx.exception.code, "CONDITION_REQUIRED")

    def test_decide_gate_success_locks_document(self) -> None:
        db = _FakeDb()
        org_id, system_id = ObjectId(), ObjectId()
        gate = gov_repo.create_gate(
            db, org_id=org_id, system_id=system_id, checklist=self._checklist(status="aprovado"),
            template_version="1", rules_applied=[], actor_user_id=ObjectId(),
        )
        actor = ObjectId()

        decided = gov_repo.decide_gate(
            db, org_id=org_id, gate_id=str(gate["_id"]),
            decisao={"resultado": "go", "aprovador_user_id": str(ObjectId())},
            actor_user_id=actor,
        )
        self.assertEqual(decided["decisao"]["resultado"], "go")
        self.assertEqual(decided["decided_by_user_id"], actor)

        with self.assertRaises(gov_repo.GovernanceError) as ctx:
            gov_repo.update_gate_checklist_item(
                db, org_id=org_id, gate_id=str(gate["_id"]), item_id="A1", status="reprovado"
            )
        self.assertEqual(ctx.exception.code, "GATE_ALREADY_DECIDED")

        with self.assertRaises(gov_repo.GovernanceError) as ctx2:
            gov_repo.decide_gate(
                db, org_id=org_id, gate_id=str(gate["_id"]),
                decisao={"resultado": "no_go", "aprovador_user_id": str(ObjectId())},
                actor_user_id=actor,
            )
        self.assertEqual(ctx2.exception.code, "GATE_ALREADY_DECIDED")

    def test_new_cycle_after_decision_increments_revision(self) -> None:
        db = _FakeDb()
        org_id, system_id = ObjectId(), ObjectId()
        first = gov_repo.create_gate(
            db, org_id=org_id, system_id=system_id, checklist=self._checklist(status="aprovado"),
            template_version="1", rules_applied=[], actor_user_id=ObjectId(),
        )
        gov_repo.decide_gate(
            db, org_id=org_id, gate_id=str(first["_id"]),
            decisao={"resultado": "no_go", "aprovador_user_id": str(ObjectId())},
            actor_user_id=ObjectId(),
        )

        second = gov_repo.create_gate(
            db, org_id=org_id, system_id=system_id, checklist=self._checklist(),
            template_version="1", rules_applied=[], actor_user_id=ObjectId(),
        )

        self.assertEqual(second["revision"], 2)
        self.assertIsNone(second["decisao"])
        latest = gov_repo.latest_gate(db, org_id=org_id, system_id=system_id)
        self.assertEqual(latest["_id"], second["_id"])
        self.assertEqual(
            [d["revision"] for d in gov_repo.list_gates(db, org_id=org_id, system_id=system_id)], [2, 1]
        )

    def test_evidence_snapshot_scoped_by_organization(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        other_org_id = ObjectId()
        gov_repo.publish_evidence_snapshot(
            db, org_id=org_id, payload={"pct_sistemas_inventariados": 0.5}, actor_user_id=ObjectId()
        )

        self.assertIsNotNone(gov_repo.latest_evidence_snapshot(db, org_id=org_id))
        self.assertIsNone(gov_repo.latest_evidence_snapshot(db, org_id=other_org_id))


class GovernanceProfundidadeTests(unittest.TestCase):
    def test_defaults_to_fundacao_without_maturidade(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        db.organizations.insert_one({"_id": org_id, "name": "Empresa"})

        settings = gov_repo.get_governance_profundidade(db, org_id=org_id)

        self.assertEqual(settings["value"], "fundacao")
        self.assertIsNone(settings["suggested_value"])

    def test_returns_stored_value(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        db.organizations.insert_one(
            {"_id": org_id, "name": "Empresa", "governance_profundidade": {"value": "completo"}}
        )

        settings = gov_repo.get_governance_profundidade(db, org_id=org_id)

        self.assertEqual(settings["value"], "completo")


class NivelFinalDaReguaTests(unittest.TestCase):
    def test_worst_criterion_wins(self) -> None:
        regua = AvaliacaoRegua(dados="baixo", impacto_erro="alto", autonomia="baixo", exposicao_juridica="medio")
        self.assertEqual(nivel_final_da_regua(regua), "alto")

    def test_all_baixo_is_baixo(self) -> None:
        regua = AvaliacaoRegua(dados="baixo", impacto_erro="baixo", autonomia="baixo", exposicao_juridica="baixo")
        self.assertEqual(nivel_final_da_regua(regua), "baixo")

    def test_any_critico_wins(self) -> None:
        regua = AvaliacaoRegua(dados="alto", impacto_erro="alto", autonomia="critico", exposicao_juridica="alto")
        self.assertEqual(nivel_final_da_regua(regua), "critico")


if __name__ == "__main__":
    unittest.main()
