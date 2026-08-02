"""E2E do módulo de Governança (Seção 9 do prompt original, critério de aceite de integração):

canvas publicado → sistema criado com risco preliminar → avaliação publicada → gate montado
(template + bloco F) → decisão `go` bloqueada com item crítico aberto → aprovação dos críticos
→ `go` → sistema em produção → mutação de `modelo` ⇒ `reavaliacao_pendente`.

Exercita a cadeia completa pela camada de rotas (canvas_projects.aprovar_portfolio +
app.routes.governance), no mesmo padrão fake-Mongo/chamada direta dos demais testes do repo.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException

from app.governance.schemas import (
    AiSystemUpdateRequest,
    AvaliacaoAIA,
    AvaliacaoRegua,
    GateChecklistUpdateRequest,
    GateDecisao,
    GateDecisionRequest,
    RiskAssessmentCreateRequest,
)
from app.routes import governance as gov_routes
from app.routes.canvas_projects import aprovar_portfolio


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


class GovernanceEndToEndTests(unittest.TestCase):
    def test_full_lifecycle_canvas_to_reavaliacao(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        member = {"_id": ObjectId(), "organization_id": org_id, "is_admin": False, "name": "Mentee"}
        admin = {"_id": ObjectId(), "organization_id": org_id, "is_admin": True, "name": "Admin"}
        db.users.insert_one(member)
        db.users.insert_one(admin)

        # ---- 1. canvas publicado: oportunidade de agente autônomo, dados sensíveis, sem HITL,
        # com exposição regulatória — a R3 deve classificar como risco preliminar crítico. ----
        now = datetime.now(timezone.utc)
        canvas_project = {
            "_id": ObjectId(),
            "organization_id": org_id,
            "created_by_user_id": member["_id"],
            "title": "Triagem automática de pacientes",
            "area_negocio": "Pronto-socorro",
            "objetivo_estrategico": "Reduzir tempo de espera",
            "oportunidade": ["Triagem automática por IA"],
            "oportunidade_tipos": ["Agente autônomo"],
            "dados_estruturado": {"descricao": "Prontuários", "sensibilidade": "sensivel"},
            "riscos_estruturado": {
                "descricao": "",
                "regulatorio": ["LGPD art.11"],
                "human_in_the_loop": "nenhum",
            },
            "status": "rascunho",
            "ai_system_id": None,
            "created_at": now,
            "updated_at": now,
        }
        db.canvas_projects.insert_one(canvas_project)

        # ---- 2. hook Canvas -> Inventário ----
        approved = aprovar_portfolio(str(canvas_project["_id"]), user=member, org_id=org_id, db=db)
        self.assertTrue(approved["created"])
        self.assertEqual(approved["risco_preliminar"], "critico")
        system_id = approved["ai_system_id"]

        system = gov_routes.get_system(system_id, user=member, org_id=org_id, db=db)
        self.assertEqual(system["status"], "aguardando_avaliacao")
        self.assertEqual(system["classificacao_risco"]["fonte"], "preliminar_r3")

        # ---- 3. gate bloqueado sem avaliação publicada (risco preliminar já é crítico) ----
        with self.assertRaises(HTTPException) as ctx:
            gov_routes.create_gate(system_id, user=member, org_id=org_id, db=db)
        self.assertEqual(ctx.exception.detail["code"], "ASSESSMENT_REQUIRED")

        # ---- 4. avaliação de risco publicada (AIA obrigatória p/ nível alto/crítico) ----
        assessment_body = RiskAssessmentCreateRequest(
            regua=AvaliacaoRegua(dados="critico", impacto_erro="alto", autonomia="critico", exposicao_juridica="alto"),
            aia=AvaliacaoAIA(
                finalidade_base_legal="Tutela da saúde (LGPD art. 11)",
                titulares_afetados="Pacientes do pronto-socorro",
                analise_vieses="Sem viés relevante identificado",
                medidas_mitigadoras=["Auditoria mensal"],
                plano_incidentes="Escalonar para o comitê de governança",
            ),
        )
        assessment = gov_routes.create_assessment(system_id, assessment_body, user=member, org_id=org_id, db=db)
        self.assertEqual(assessment["payload"]["nivel_final"], "critico")

        system = gov_routes.get_system(system_id, user=member, org_id=org_id, db=db)
        self.assertEqual(system["status"], "avaliado")
        self.assertEqual(system["classificacao_risco"]["fonte"], "avaliacao")

        # ---- 5. SWOT da organização com item de governança de alto impacto (-> bloco F) ----
        db.swot_analyses.insert_one(
            {
                "_id": ObjectId(),
                "organization_id": org_id,
                "fraquezas": [
                    {
                        "id": "fx_gov",
                        "texto": "Sem processo de auditoria de decisões automatizadas",
                        "pilar": "governanca",
                        "question_id": "GR4",
                        "impacto": 5,
                    }
                ],
                "ameacas": [],
                "forcas": [],
                "oportunidades": [],
                "updated_at": now,
            }
        )

        # ---- 6. gate montado (template A/C/D/E + bloco F da R2) ----
        gate = gov_routes.create_gate(system_id, user=member, org_id=org_id, db=db)
        blocos = {item["bloco"] for item in gate["checklist"]}
        self.assertEqual(blocos, {"A", "C", "D", "E", "F"})
        bloco_f_item = next(i for i in gate["checklist"] if i["bloco"] == "F")
        self.assertEqual(bloco_f_item["origem"]["swot_item_id"], "fx_gov")
        self.assertTrue(bloco_f_item["critico"], "impacto 5 >= 4 deve virar item critico")

        system = gov_routes.get_system(system_id, user=member, org_id=org_id, db=db)
        self.assertEqual(system["status"], "em_gate")

        # ---- 7. decisão `go` bloqueada com item crítico aberto ----
        decision_body = GateDecisionRequest(
            decisao=GateDecisao(resultado="go", aprovador_user_id=str(admin["_id"]))
        )
        with self.assertRaises(HTTPException) as ctx2:
            gov_routes.decide_gate(gate["id"], decision_body, user=member, org_id=org_id, db=db)
        self.assertEqual(ctx2.exception.detail["code"], "GATE_CRITICAL_ITEM_OPEN")

        # ---- 8. aprovação de todos os itens críticos ----
        for item in gate["checklist"]:
            if item["critico"]:
                gov_routes.update_gate_item(
                    gate["id"], item["item_id"],
                    GateChecklistUpdateRequest(status="aprovado"),
                    user=member, org_id=org_id, db=db,
                )

        # ---- 9. `go` ----
        decided = gov_routes.decide_gate(gate["id"], decision_body, user=member, org_id=org_id, db=db)
        self.assertEqual(decided["decisao"]["resultado"], "go")

        system = gov_routes.get_system(system_id, user=member, org_id=org_id, db=db)
        self.assertEqual(system["status"], "producao")

        # ---- 10. mutação de modelo/fornecedor com sistema em produção -> reavaliação pendente ----
        gov_routes.update_system(
            system_id, AiSystemUpdateRequest(modelo="novo-modelo-v2"), user=member, org_id=org_id, db=db
        )
        system = gov_routes.get_system(system_id, user=member, org_id=org_id, db=db)
        self.assertEqual(system["status"], "reavaliacao_pendente")


if __name__ == "__main__":
    unittest.main()
