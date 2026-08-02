"""Endpoints do módulo de Governança de IA — inventário, avaliação de risco, gate go/no-go,
rastreabilidade e evidências. RBAC adaptado ao repo (sem personas): qualquer membro
verificado da organização pode operar o inventário/checklist; a decisão do gate exige que o
aprovador seja administrador da mesma organização (ver plano salvo da feature)."""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.database import get_db
from app.deps import get_current_organization_id, get_verified_user
from app.governance import repository as gov_repo
from app.governance.gate_template import TEMPLATE_VERSION, montar_checklist_base
from app.governance.rules.r1_maturidade import (
    gov_risk_answers_from_maturity,
    maturidade_para_profundidade,
)
from app.governance.rules.r2_swot import swot_para_checklist
from app.governance.schemas import (
    AiSystemCreateRequest,
    AiSystemUpdateRequest,
    EvidenceSnapshotCreateRequest,
    GateChecklistUpdateRequest,
    GateDecisionRequest,
    RiskAssessmentCreateRequest,
    nivel_final_da_regua,
)
from app.routes.swot_analysis import _to_item as _swot_to_item

router = APIRouter(prefix="/api/governance", tags=["governance"])

_PROFUNDIDADE_ORDER = ("fundacao", "intermediario", "completo")


# ---- helpers ----


def _raise(exc: gov_repo.GovernanceError) -> None:
    if exc.code == "INVALID_ID":
        status_code = 400
    elif exc.code.endswith("_NOT_FOUND"):
        status_code = 404
    else:
        status_code = 422
    raise HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})


def _iso(value) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None


def _require_org_member(db: Database, org_id: ObjectId, user_id: str) -> dict:
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=422, detail={"code": "USER_NOT_IN_ORGANIZATION", "message": "Usuário inválido."}
        )
    member = db.users.find_one({"_id": ObjectId(user_id), "organization_id": org_id})
    if not member:
        raise HTTPException(
            status_code=422,
            detail={"code": "USER_NOT_IN_ORGANIZATION", "message": "Usuário não pertence à organização."},
        )
    return member


def _get_system_or_404(db: Database, org_id: ObjectId, system_id: str) -> dict:
    try:
        return gov_repo.get_ai_system(db, org_id=org_id, system_id=system_id)
    except gov_repo.GovernanceError as exc:
        _raise(exc)


def _get_gate_or_404(db: Database, org_id: ObjectId, gate_id: str) -> dict:
    try:
        return gov_repo.get_gate(db, org_id=org_id, gate_id=gate_id)
    except gov_repo.GovernanceError as exc:
        _raise(exc)


# ---- serialização ----


def _serialize_system(doc: dict) -> dict:
    risco = doc.get("classificacao_risco") or {}
    return {
        "id": str(doc["_id"]),
        "nome": doc.get("nome") or "",
        "area_negocio": doc.get("area_negocio") or "",
        "finalidade": doc.get("finalidade") or "",
        "descricao_dados": doc.get("descricao_dados") or "",
        "sensibilidade_dados": doc.get("sensibilidade_dados"),
        "fornecedor": doc.get("fornecedor") or "",
        "modelo": doc.get("modelo") or "",
        "versao_pinned": doc.get("versao_pinned") or "",
        "origem_ia": doc.get("origem_ia"),
        "responsavel_negocio_user_id": str(doc["responsavel_negocio_user_id"])
        if doc.get("responsavel_negocio_user_id")
        else None,
        "responsavel_tecnico_user_id": str(doc["responsavel_tecnico_user_id"])
        if doc.get("responsavel_tecnico_user_id")
        else None,
        "hitl_obrigatorio": bool(doc.get("hitl_obrigatorio")),
        "hitl_descricao": doc.get("hitl_descricao") or "",
        "status": doc.get("status"),
        "canvas_project_id": str(doc["canvas_project_id"]) if doc.get("canvas_project_id") else None,
        "classificacao_risco": {
            "nivel": risco.get("nivel"),
            "fonte": risco.get("fonte"),
            "avaliacao_id": str(risco["avaliacao_id"]) if risco.get("avaliacao_id") else None,
        },
        "created_by_user_id": str(doc["created_by_user_id"]) if doc.get("created_by_user_id") else None,
        "created_at": _iso(doc.get("created_at")),
        "updated_at": _iso(doc.get("updated_at")),
    }


def _serialize_assessment(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "system_id": str(doc["system_id"]),
        "type": doc.get("type"),
        "version": doc.get("version"),
        "revision": doc.get("revision"),
        "payload": doc.get("payload"),
        "published_by_user_id": str(doc["published_by_user_id"]) if doc.get("published_by_user_id") else None,
        "published_at": _iso(doc.get("published_at")),
    }


def _serialize_gate(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "system_id": str(doc["system_id"]),
        "type": doc.get("type"),
        "version": doc.get("version"),
        "revision": doc.get("revision"),
        "template_version": doc.get("template_version"),
        "rules_applied": doc.get("rules_applied") or [],
        "checklist": doc.get("checklist") or [],
        "decisao": doc.get("decisao"),
        "created_by_user_id": str(doc["created_by_user_id"]) if doc.get("created_by_user_id") else None,
        "created_at": _iso(doc.get("created_at")),
        "updated_at": _iso(doc.get("updated_at")),
        "decided_by_user_id": str(doc["decided_by_user_id"]) if doc.get("decided_by_user_id") else None,
        "decided_at": _iso(doc.get("decided_at")),
    }


def _serialize_evidence(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "type": doc.get("type"),
        "version": doc.get("version"),
        "revision": doc.get("revision"),
        "payload": doc.get("payload"),
        "published_by_user_id": str(doc["published_by_user_id"]) if doc.get("published_by_user_id") else None,
        "published_at": _iso(doc.get("published_at")),
    }


# ---- membros da organização (para o seletor de RACI na decisão do gate) ----


@router.get("/organization-members")
def list_organization_members(
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    members = db.users.find({"organization_id": org_id}, {"name": 1, "email": 1, "is_admin": 1})
    return {
        "items": [
            {
                "id": str(m["_id"]),
                "name": m.get("name") or m.get("email") or "",
                "is_admin": bool(m.get("is_admin")),
            }
            for m in members
        ]
    }


# ---- ai_systems ----


@router.get("/systems")
def list_systems(
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    return {"items": [_serialize_system(d) for d in gov_repo.list_ai_systems(db, org_id=org_id)]}


@router.post("/systems")
def create_system(
    body: AiSystemCreateRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    system = gov_repo.create_ai_system(
        db, org_id=org_id, actor_user_id=user["_id"], data=body.model_dump(exclude_unset=True)
    )
    return _serialize_system(system)


@router.get("/systems/{system_id}")
def get_system(
    system_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    return _serialize_system(_get_system_or_404(db, org_id, system_id))


@router.patch("/systems/{system_id}")
def update_system(
    system_id: str,
    body: AiSystemUpdateRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    try:
        system = gov_repo.update_ai_system(
            db,
            org_id=org_id,
            actor_user_id=user["_id"],
            system_id=system_id,
            updates=body.model_dump(exclude_unset=True),
        )
    except gov_repo.GovernanceError as exc:
        _raise(exc)
    return _serialize_system(system)


# ---- avaliação de risco (aegis.avaliacao-risco) ----


@router.post("/systems/{system_id}/assessments")
def create_assessment(
    system_id: str,
    body: RiskAssessmentCreateRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    system = _get_system_or_404(db, org_id, system_id)

    nivel_final = nivel_final_da_regua(body.regua)
    if nivel_final in ("alto", "critico") and body.aia is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "AIA_REQUIRED", "message": "AIA é obrigatória para nível de risco alto/crítico."},
        )
    if system.get("origem_ia") == "api_terceiros" and body.due_diligence_fornecedor is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "DUE_DILIGENCE_REQUIRED",
                "message": "Due diligence do fornecedor é obrigatória quando origem_ia=api_terceiros.",
            },
        )

    payload = {
        "regua": body.regua.model_dump(),
        "nivel_final": nivel_final,
        "aia": body.aia.model_dump() if body.aia else None,
        "due_diligence_fornecedor": body.due_diligence_fornecedor.model_dump()
        if body.due_diligence_fornecedor
        else None,
        "gatilhos_reavaliacao": body.gatilhos_reavaliacao,
        "avaliador_user_id": str(user["_id"]),
    }
    assessment = gov_repo.publish_risk_assessment(
        db, org_id=org_id, system_id=system["_id"], payload=payload, actor_user_id=user["_id"]
    )
    gov_repo.set_ai_system_risk(
        db,
        org_id=org_id,
        system_id=system["_id"],
        nivel=nivel_final,
        fonte="avaliacao",
        avaliacao_id=assessment["_id"],
    )
    gov_repo.update_ai_system(
        db, org_id=org_id, actor_user_id=user["_id"], system_id=system_id, updates={"status": "avaliado"}
    )
    return _serialize_assessment(assessment)


@router.get("/systems/{system_id}/assessments")
def list_assessments(
    system_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    system = _get_system_or_404(db, org_id, system_id)
    items = gov_repo.list_risk_assessments(db, org_id=org_id, system_id=system["_id"])
    return {"items": [_serialize_assessment(d) for d in items]}


# ---- gate go/no-go (aegis.gate-governanca) ----


@router.post("/systems/{system_id}/gates")
def create_gate(
    system_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    system = _get_system_or_404(db, org_id, system_id)

    nivel_atual = (system.get("classificacao_risco") or {}).get("nivel")
    tem_avaliacao = gov_repo.latest_risk_assessment(db, org_id=org_id, system_id=system["_id"]) is not None
    if nivel_atual in ("alto", "critico") and not tem_avaliacao:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ASSESSMENT_REQUIRED",
                "message": "Sistemas com risco alto/crítico exigem avaliação publicada antes do gate.",
            },
        )

    checklist = montar_checklist_base(system.get("origem_ia") or "interno")
    rules_applied = [{"rule_id": "gate_template", "rule_version": TEMPLATE_VERSION}]

    swot_doc = db.swot_analyses.find_one({"organization_id": org_id}, sort=[("updated_at", -1)])
    if swot_doc:
        r2 = swot_para_checklist(_swot_to_item(swot_doc))
        checklist = checklist + r2["itens"]
        rules_applied.append({"rule_id": r2["rule_id"], "rule_version": r2["rule_version"]})

    gate = gov_repo.create_gate(
        db,
        org_id=org_id,
        system_id=system["_id"],
        checklist=checklist,
        template_version=TEMPLATE_VERSION,
        rules_applied=rules_applied,
        actor_user_id=user["_id"],
    )
    gov_repo.update_ai_system(
        db, org_id=org_id, actor_user_id=user["_id"], system_id=system_id, updates={"status": "em_gate"}
    )
    return _serialize_gate(gate)


@router.get("/systems/{system_id}/gates")
def list_gates(
    system_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    system = _get_system_or_404(db, org_id, system_id)
    items = gov_repo.list_gates(db, org_id=org_id, system_id=system["_id"])
    return {"items": [_serialize_gate(d) for d in items]}


@router.get("/gates/{gate_id}")
def get_gate(
    gate_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    return _serialize_gate(_get_gate_or_404(db, org_id, gate_id))


@router.patch("/gates/{gate_id}/items/{item_id}")
def update_gate_item(
    gate_id: str,
    item_id: str,
    body: GateChecklistUpdateRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    try:
        gate = gov_repo.update_gate_checklist_item(
            db,
            org_id=org_id,
            gate_id=gate_id,
            item_id=item_id,
            status=body.status,
            evidencia=body.evidencia.model_dump() if body.evidencia else None,
        )
    except gov_repo.GovernanceError as exc:
        _raise(exc)
    return _serialize_gate(gate)


@router.post("/gates/{gate_id}/decision")
def decide_gate(
    gate_id: str,
    body: GateDecisionRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    gate = _get_gate_or_404(db, org_id, gate_id)
    decisao = body.decisao

    aprovador = _require_org_member(db, org_id, decisao.aprovador_user_id)
    if not aprovador.get("is_admin"):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "SINGLE_APPROVER_VIOLATION",
                "message": "O aprovador precisa ser administrador da organização.",
            },
        )
    for consultado_id in decisao.consultados_user_ids:
        _require_org_member(db, org_id, consultado_id)
    for condicao in decisao.condicoes:
        _require_org_member(db, org_id, condicao.dono_user_id)

    try:
        decided = gov_repo.decide_gate(
            db,
            org_id=org_id,
            gate_id=gate_id,
            decisao=decisao.model_dump(),
            actor_user_id=user["_id"],
        )
    except gov_repo.GovernanceError as exc:
        _raise(exc)

    novo_status = {"go": "producao", "no_go": "avaliado", "go_condicional": "em_gate"}[decisao.resultado]
    gov_repo.update_ai_system(
        db,
        org_id=org_id,
        actor_user_id=user["_id"],
        system_id=str(gate["system_id"]),
        updates={"status": novo_status},
    )
    return _serialize_gate(decided)


# ---- rastreabilidade ----


@router.get("/systems/{system_id}/traceability")
def get_traceability(
    system_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    system = _get_system_or_404(db, org_id, system_id)

    canvas = None
    swot_items: list[dict] = []
    csf_ids: list[str] = []
    maturity_response_id: str | None = None
    canvas_project_id = system.get("canvas_project_id")
    if canvas_project_id:
        canvas_doc = db.canvas_projects.find_one(
            {"_id": canvas_project_id, "organization_id": org_id}
        )
        if canvas_doc:
            swot_id = canvas_doc.get("swot_id")
            canvas = {
                "canvas_project_id": str(canvas_doc["_id"]),
                "title": canvas_doc.get("title") or "",
                "area_negocio": canvas_doc.get("area_negocio") or "",
                "swot_id": swot_id,
            }
            linked_item_ids = set(canvas_doc.get("swot_item_ids") or [])
            if swot_id and ObjectId.is_valid(swot_id):
                swot_doc = db.swot_analyses.find_one(
                    {"_id": ObjectId(swot_id), "organization_id": org_id}
                )
                if swot_doc:
                    mid = swot_doc.get("maturity_response_id")
                    maturity_response_id = str(mid) if mid else None
                    for quadrante in ("forcas", "fraquezas", "oportunidades", "ameacas"):
                        for item in swot_doc.get(quadrante) or []:
                            if item.get("id") not in linked_item_ids:
                                continue
                            swot_items.append(
                                {
                                    "id": item.get("id"),
                                    "texto": item.get("texto") or "",
                                    "quadrante": quadrante,
                                    "question_id": item.get("question_id") or "",
                                }
                            )
                            if item.get("question_id"):
                                csf_ids.append(item["question_id"])

    assessments = gov_repo.list_risk_assessments(db, org_id=org_id, system_id=system["_id"])
    gates = gov_repo.list_gates(db, org_id=org_id, system_id=system["_id"])

    return {
        "system_id": str(system["_id"]),
        "csf_ids": csf_ids,
        "maturity_response_id": maturity_response_id,
        "swot_items": swot_items,
        "canvas": canvas,
        "assessments": [_serialize_assessment(d) for d in assessments],
        "gates": [_serialize_gate(d) for d in gates],
    }


# ---- evidências e métricas ----


@router.get("/metrics")
def get_metrics(
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    snapshot = gov_repo.latest_evidence_snapshot(db, org_id=org_id)
    if not snapshot:
        return {"published": False, "metrics": None, "published_at": None}
    return {"published": True, "metrics": snapshot.get("payload"), "published_at": _iso(snapshot.get("published_at"))}


@router.post("/evidence-snapshots")
def create_evidence_snapshot(
    body: EvidenceSnapshotCreateRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    doc = gov_repo.publish_evidence_snapshot(
        db, org_id=org_id, payload=body.model_dump(), actor_user_id=user["_id"]
    )
    return _serialize_evidence(doc)


# ---- profundidade de implantação (R1) ----


@router.get("/settings/profundidade")
def get_profundidade(
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    return gov_repo.get_governance_profundidade(db, org_id=org_id)


@router.post("/settings/profundidade/recalcular")
def recalcular_profundidade(
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Roda a R1 sobre a última resposta completa de maturidade. Upgrades aplicam direto;
    rebaixamentos só ficam como sugestão até confirmação humana (`.../confirmar`)."""
    maturity_doc = db.maturity_responses.find_one(
        {"organization_id": org_id, "complete": True}, sort=[("submitted_at", -1)]
    )
    if not maturity_doc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "MATURITY_NOT_PUBLISHED",
                "message": "Nenhuma autoavaliação de maturidade completa encontrada para a organização.",
            },
        )
    gr_answers = gov_risk_answers_from_maturity(maturity_doc.get("answers") or {})
    try:
        resultado_r1 = maturidade_para_profundidade(gr_answers)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail={"code": "MATURITY_MISSING_GOV_RISK_ANSWERS", "message": str(exc)}
        ) from exc

    atual = gov_repo.get_governance_profundidade(db, org_id=org_id)
    sugerido = resultado_r1["profundidade"]
    now = datetime.now(timezone.utc)
    novo = {**atual, "suggested_value": sugerido, "suggested_at": now}
    if _PROFUNDIDADE_ORDER.index(sugerido) >= _PROFUNDIDADE_ORDER.index(atual["value"]):
        novo["value"] = sugerido  # upgrade (ou igual) aplica direto

    db.organizations.update_one({"_id": org_id}, {"$set": {"governance_profundidade": novo}})
    return gov_repo.get_governance_profundidade(db, org_id=org_id)


@router.post("/settings/profundidade/confirmar")
def confirmar_profundidade(
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Confirma manualmente um rebaixamento sugerido (Seção 8, regra 9)."""
    atual = gov_repo.get_governance_profundidade(db, org_id=org_id)
    if not atual.get("suggested_value"):
        raise HTTPException(
            status_code=422,
            detail={"code": "NO_PENDING_SUGGESTION", "message": "Não há sugestão de profundidade pendente."},
        )
    now = datetime.now(timezone.utc)
    novo = {
        **atual,
        "value": atual["suggested_value"],
        "confirmed_by_user_id": user["_id"],
        "confirmed_at": now,
    }
    db.organizations.update_one({"_id": org_id}, {"$set": {"governance_profundidade": novo}})
    return gov_repo.get_governance_profundidade(db, org_id=org_id)
