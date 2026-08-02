"""Acesso a dados do módulo de Governança de IA.

`ai_systems` é estado operacional mutável — toda mutação grava uma entrada em
`ai_governance_audit_log` (quem, quando, diff). As 3 coleções restantes
(`ai_risk_assessments`, `ai_governance_gates`, `ai_governance_evidence`) são imutáveis por
versão: publicar sempre insere um novo documento, nunca edita um payload já publicado.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.database import Database


class GovernanceError(Exception):
    """Erro de negócio com `code` estável — a camada de rotas traduz para HTTP 422/404."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


# ---- ai_systems ----

_AI_SYSTEM_FIELDS = (
    "nome",
    "area_negocio",
    "finalidade",
    "descricao_dados",
    "sensibilidade_dados",
    "fornecedor",
    "modelo",
    "versao_pinned",
    "origem_ia",
    "responsavel_negocio_user_id",
    "responsavel_tecnico_user_id",
    "hitl_obrigatorio",
    "hitl_descricao",
    "status",
)


def _diff_fields(before: dict, after: dict, fields: tuple[str, ...]) -> dict:
    changes: dict[str, dict[str, Any]] = {}
    for field in fields:
        b, a = before.get(field), after.get(field)
        if b != a:
            changes[field] = {"before": b, "after": a}
    return changes


def _write_audit_log(
    db: Database,
    *,
    org_id: ObjectId,
    entity_type: str,
    entity_id: ObjectId,
    action: str,
    actor_user_id: ObjectId,
    diff: dict,
) -> None:
    db.ai_governance_audit_log.insert_one(
        {
            "organization_id": org_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "actor_user_id": actor_user_id,
            "at": datetime.now(timezone.utc),
            "diff": diff,
        }
    )


_USER_REF_FIELDS = ("responsavel_negocio_user_id", "responsavel_tecnico_user_id")


def _as_object_id(value: str | ObjectId | None) -> ObjectId | None:
    if not value:
        return None
    return value if isinstance(value, ObjectId) else ObjectId(value)


def _normalize_user_refs(data: dict) -> dict:
    out = dict(data)
    for field in _USER_REF_FIELDS:
        if field in out:
            out[field] = _as_object_id(out[field])
    return out


def create_ai_system(
    db: Database, *, org_id: ObjectId, actor_user_id: ObjectId, data: dict
) -> dict:
    now = datetime.now(timezone.utc)
    data = _normalize_user_refs(data)
    canvas_project_id = data.get("canvas_project_id")
    doc = {
        "organization_id": org_id,
        "canvas_project_id": ObjectId(canvas_project_id) if canvas_project_id else None,
        **{k: data.get(k) for k in _AI_SYSTEM_FIELDS if k != "status"},
        "status": data.get("status") or "rascunho",
        "classificacao_risco": {"nivel": None, "fonte": None, "avaliacao_id": None},
        "created_by_user_id": actor_user_id,
        "created_at": now,
        "updated_at": now,
    }
    result = db.ai_systems.insert_one(doc)
    doc["_id"] = result.inserted_id
    _write_audit_log(
        db,
        org_id=org_id,
        entity_type="ai_system",
        entity_id=doc["_id"],
        action="create",
        actor_user_id=actor_user_id,
        diff={k: {"before": None, "after": v} for k, v in doc.items() if k not in ("_id",)},
    )
    return doc


def get_ai_system(db: Database, *, org_id: ObjectId, system_id: str) -> dict:
    if not ObjectId.is_valid(system_id):
        raise GovernanceError("INVALID_ID", "ID de sistema inválido")
    doc = db.ai_systems.find_one({"_id": ObjectId(system_id), "organization_id": org_id})
    if not doc:
        raise GovernanceError("SYSTEM_NOT_FOUND", "Sistema de IA não encontrado")
    return doc


def find_ai_system_by_canvas_project(
    db: Database, *, org_id: ObjectId, canvas_project_id: ObjectId
) -> dict | None:
    return db.ai_systems.find_one(
        {"organization_id": org_id, "canvas_project_id": canvas_project_id}
    )


def list_ai_systems(db: Database, *, org_id: ObjectId) -> list[dict]:
    return list(db.ai_systems.find({"organization_id": org_id}).sort("updated_at", -1))


_REAVALIACAO_TRIGGER_FIELDS = ("modelo", "fornecedor", "versao_pinned", "descricao_dados")


def update_ai_system(
    db: Database, *, org_id: ObjectId, actor_user_id: ObjectId, system_id: str, updates: dict
) -> dict:
    before = get_ai_system(db, org_id=org_id, system_id=system_id)
    clean = _normalize_user_refs({k: v for k, v in updates.items() if k in _AI_SYSTEM_FIELDS})
    if not clean:
        return before

    # Gatilho de reavaliação (Seção 5, hook 4): mudar modelo/fornecedor/dados de um sistema em
    # produção volta o status para reavaliacao_pendente — a menos que esta própria chamada já
    # esteja fazendo uma transição de status intencional (ex.: decisão do gate).
    if "status" not in clean and before.get("status") == "producao":
        trigger_changed = any(
            field in clean and clean[field] != before.get(field)
            for field in _REAVALIACAO_TRIGGER_FIELDS
        )
        if trigger_changed:
            clean["status"] = "reavaliacao_pendente"

    clean["updated_at"] = datetime.now(timezone.utc)
    db.ai_systems.update_one({"_id": before["_id"]}, {"$set": clean})
    after = db.ai_systems.find_one({"_id": before["_id"]})
    diff = _diff_fields(before, after, _AI_SYSTEM_FIELDS)
    if diff:
        _write_audit_log(
            db,
            org_id=org_id,
            entity_type="ai_system",
            entity_id=before["_id"],
            action="update",
            actor_user_id=actor_user_id,
            diff=diff,
        )
    return after


def set_ai_system_risk(
    db: Database,
    *,
    org_id: ObjectId,
    system_id: ObjectId,
    nivel: str,
    fonte: str,
    avaliacao_id: ObjectId | None = None,
) -> None:
    """Atualiza `classificacao_risco` sem passar pelo fluxo de audit log de campos livres.

    Usado pelas regras determinísticas (R3: preliminar) e pela publicação de avaliação
    (fonte="avaliacao") — a origem da mudança já fica registrada no artefato publicado.
    """
    db.ai_systems.update_one(
        {"_id": system_id, "organization_id": org_id},
        {
            "$set": {
                "classificacao_risco": {
                    "nivel": nivel,
                    "fonte": fonte,
                    "avaliacao_id": avaliacao_id,
                },
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )


# ---- coleções imutáveis por versão ----


def _publish_version(
    db: Database,
    collection_name: str,
    *,
    org_id: ObjectId,
    system_id: ObjectId,
    artifact_type: str,
    artifact_version: int,
    payload: dict,
    actor_user_id: ObjectId,
) -> dict:
    now = datetime.now(timezone.utc)
    revision = db[collection_name].count_documents(
        {"organization_id": org_id, "system_id": system_id}
    ) + 1
    doc = {
        "organization_id": org_id,
        "system_id": system_id,
        "type": artifact_type,
        "version": artifact_version,
        "revision": revision,
        "payload": payload,
        "published_by_user_id": actor_user_id,
        "published_at": now,
    }
    result = db[collection_name].insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def _latest_version(
    db: Database, collection_name: str, *, org_id: ObjectId, system_id: ObjectId
) -> dict | None:
    return db[collection_name].find_one(
        {"organization_id": org_id, "system_id": system_id},
        sort=[("revision", -1)],
    )


def _list_versions(
    db: Database, collection_name: str, *, org_id: ObjectId, system_id: ObjectId
) -> list[dict]:
    return list(
        db[collection_name]
        .find({"organization_id": org_id, "system_id": system_id})
        .sort("revision", -1)
    )


def publish_risk_assessment(
    db: Database, *, org_id: ObjectId, system_id: ObjectId, payload: dict, actor_user_id: ObjectId
) -> dict:
    from app.governance.schemas import (
        ARTIFACT_TYPE_AVALIACAO_RISCO,
        ARTIFACT_VERSION_AVALIACAO_RISCO,
    )

    return _publish_version(
        db,
        "ai_risk_assessments",
        org_id=org_id,
        system_id=system_id,
        artifact_type=ARTIFACT_TYPE_AVALIACAO_RISCO,
        artifact_version=ARTIFACT_VERSION_AVALIACAO_RISCO,
        payload=payload,
        actor_user_id=actor_user_id,
    )


def latest_risk_assessment(db: Database, *, org_id: ObjectId, system_id: ObjectId) -> dict | None:
    return _latest_version(db, "ai_risk_assessments", org_id=org_id, system_id=system_id)


def list_risk_assessments(db: Database, *, org_id: ObjectId, system_id: ObjectId) -> list[dict]:
    return _list_versions(db, "ai_risk_assessments", org_id=org_id, system_id=system_id)


def create_gate(
    db: Database,
    *,
    org_id: ObjectId,
    system_id: ObjectId,
    checklist: list[dict],
    template_version: str,
    rules_applied: list[dict],
    actor_user_id: ObjectId,
) -> dict:
    """Abre um novo ciclo de gate (revision + 1) com o checklist montado (template + R2).

    Diferente das outras duas coleções versionadas: um gate nasce como rascunho mutável
    (`decisao: None`) — os itens vão sendo preenchidos um a um via `update_gate_checklist_item`
    até `decide_gate` fechar o ciclo. Depois de decidido, o documento fica imutável; qualquer
    correção exige abrir um novo ciclo (nova chamada a `create_gate`), não editar este.
    """
    from app.governance.schemas import ARTIFACT_TYPE_GATE_GOVERNANCA, ARTIFACT_VERSION_GATE_GOVERNANCA

    now = datetime.now(timezone.utc)
    revision = (
        db.ai_governance_gates.count_documents({"organization_id": org_id, "system_id": system_id})
        + 1
    )
    doc = {
        "organization_id": org_id,
        "system_id": system_id,
        "type": ARTIFACT_TYPE_GATE_GOVERNANCA,
        "version": ARTIFACT_VERSION_GATE_GOVERNANCA,
        "revision": revision,
        "template_version": template_version,
        "rules_applied": rules_applied,
        "checklist": checklist,
        "decisao": None,
        "created_by_user_id": actor_user_id,
        "created_at": now,
        "updated_at": now,
        "decided_by_user_id": None,
        "decided_at": None,
    }
    result = db.ai_governance_gates.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def get_gate(db: Database, *, org_id: ObjectId, gate_id: str) -> dict:
    if not ObjectId.is_valid(gate_id):
        raise GovernanceError("INVALID_ID", "ID de gate inválido")
    doc = db.ai_governance_gates.find_one({"_id": ObjectId(gate_id), "organization_id": org_id})
    if not doc:
        raise GovernanceError("GATE_NOT_FOUND", "Gate não encontrado")
    return doc


def update_gate_checklist_item(
    db: Database,
    *,
    org_id: ObjectId,
    gate_id: str,
    item_id: str,
    status: str | None = None,
    evidencia: dict | None = None,
) -> dict:
    gate = get_gate(db, org_id=org_id, gate_id=gate_id)
    if gate.get("decisao"):
        raise GovernanceError("GATE_ALREADY_DECIDED", "Gate já foi decidido — abra um novo ciclo")

    checklist = [dict(item) for item in (gate.get("checklist") or [])]
    alvo = next((item for item in checklist if item.get("item_id") == item_id), None)
    if alvo is None:
        raise GovernanceError("ITEM_NOT_FOUND", "Item de checklist não encontrado")

    if status is not None:
        alvo["status"] = status
    if evidencia is not None:
        alvo["evidencia"] = evidencia
    if alvo.get("critico") and alvo.get("status") == "nao_aplicavel":
        if not (alvo.get("evidencia") or {}).get("descricao"):
            raise GovernanceError(
                "ITEM_JUSTIFICATION_REQUIRED",
                "Item crítico marcado como não aplicável exige justificativa na evidência",
            )

    db.ai_governance_gates.update_one(
        {"_id": gate["_id"]},
        {"$set": {"checklist": checklist, "updated_at": datetime.now(timezone.utc)}},
    )
    return get_gate(db, org_id=org_id, gate_id=gate_id)


def decide_gate(
    db: Database, *, org_id: ObjectId, gate_id: str, decisao: dict, actor_user_id: ObjectId
) -> dict:
    """Fecha o ciclo — a partir daqui o gate é imutável. Valida só os invariantes que dependem
    apenas do próprio documento; validação de RACI (aprovador é admin da mesma org etc.) é
    responsabilidade da rota, que tem acesso a `users`.
    """
    gate = get_gate(db, org_id=org_id, gate_id=gate_id)
    if gate.get("decisao"):
        raise GovernanceError("GATE_ALREADY_DECIDED", "Gate já foi decidido")

    resultado = decisao.get("resultado")
    if resultado == "go":
        for item in gate.get("checklist") or []:
            if item.get("critico") and item.get("status") not in ("aprovado", "nao_aplicavel"):
                raise GovernanceError(
                    "GATE_CRITICAL_ITEM_OPEN",
                    f"Item crítico {item.get('item_id')} ainda não foi aprovado/marcado como não aplicável",
                )
    if resultado == "go_condicional" and not decisao.get("condicoes"):
        raise GovernanceError("CONDITION_REQUIRED", "go_condicional exige ao menos uma condição")

    now = datetime.now(timezone.utc)
    db.ai_governance_gates.update_one(
        {"_id": gate["_id"]},
        {
            "$set": {
                "decisao": decisao,
                "decided_by_user_id": actor_user_id,
                "decided_at": now,
                "updated_at": now,
            }
        },
    )
    return get_gate(db, org_id=org_id, gate_id=gate_id)


def latest_gate(db: Database, *, org_id: ObjectId, system_id: ObjectId) -> dict | None:
    return _latest_version(db, "ai_governance_gates", org_id=org_id, system_id=system_id)


def list_gates(db: Database, *, org_id: ObjectId, system_id: ObjectId) -> list[dict]:
    return _list_versions(db, "ai_governance_gates", org_id=org_id, system_id=system_id)


def publish_evidence_snapshot(
    db: Database, *, org_id: ObjectId, payload: dict, actor_user_id: ObjectId
) -> dict:
    """Snapshot é por organização, não por sistema — usa `org_id` como chave de versão."""
    from app.governance.schemas import (
        ARTIFACT_TYPE_EVIDENCIA_GOVERNANCA,
        ARTIFACT_VERSION_EVIDENCIA_GOVERNANCA,
    )

    return _publish_version(
        db,
        "ai_governance_evidence",
        org_id=org_id,
        system_id=org_id,
        artifact_type=ARTIFACT_TYPE_EVIDENCIA_GOVERNANCA,
        artifact_version=ARTIFACT_VERSION_EVIDENCIA_GOVERNANCA,
        payload=payload,
        actor_user_id=actor_user_id,
    )


def latest_evidence_snapshot(db: Database, *, org_id: ObjectId) -> dict | None:
    return _latest_version(db, "ai_governance_evidence", org_id=org_id, system_id=org_id)


# ---- profundidade de implantação (R1) ----

_DEFAULT_PROFUNDIDADE = {
    "value": "fundacao",
    "suggested_value": None,
    "suggested_at": None,
    "confirmed_by_user_id": None,
    "confirmed_at": None,
}


def get_governance_profundidade(db: Database, *, org_id: ObjectId) -> dict:
    """Sem `aegis.maturidade` publicado, a organização opera em `fundacao` por default."""
    org = db.organizations.find_one({"_id": org_id}, {"governance_profundidade": 1})
    settings = (org or {}).get("governance_profundidade")
    return {**_DEFAULT_PROFUNDIDADE, **settings} if settings else dict(_DEFAULT_PROFUNDIDADE)
