from datetime import datetime, timezone
from pathlib import Path
import json

from pymongo import MongoClient
from pymongo.database import Database
from bson import ObjectId

from app import analytics
from app.config import settings
from app.tools import default_tools

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_MATURITY_SEED_FILE = _DATA_DIR / "ai_maturity_model.json"


# tlsCAFile com certifi evita SSL: CERTIFICATE_VERIFY_FAILED no macOS
client = MongoClient(settings.mongodb_uri)
db: Database = client[settings.mongodb_db_name]


def get_db() -> Database:
    return db


def migrate_users_to_organizations() -> int:
    """Garante que todo usuario tenha organization_id.

    Cria uma organizacao solo para cada usuario que ainda nao tem uma,
    preservando o comportamento atual (cada um continua vendo so o seu)
    ate que um admin agrupe usuarios na mesma organizacao manualmente.
    Idempotente: usuarios que ja tem organization_id sao ignorados.
    """
    now = datetime.now(timezone.utc)
    migrated = 0
    for user in db.users.find({"organization_id": {"$exists": False}}, {"name": 1, "email": 1}):
        label = (user.get("name") or user.get("email") or "Mentorado").strip()
        org = db.organizations.insert_one(
            {
                "name": f"{label} — Organização",
                "created_at": now,
                "updated_at": now,
            }
        )
        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"organization_id": org.inserted_id}},
        )
        migrated += 1
    return migrated


def backfill_user_tools() -> int:
    """Preenche `users.tools` em quem foi criado antes do controle de ferramentas.

    Todos ganham o catálogo completo: o controle nasce sem tirar acesso de ninguém, e o admin
    passa a desabilitar caso a caso. Idempotente — só toca documentos sem o campo.
    """
    result = db.users.update_many(
        {"tools": {"$exists": False}},
        {"$set": {"tools": default_tools()}},
    )
    return int(result.modified_count)


def provision_solo_organization(name_hint: str) -> ObjectId:
    """Cria uma organizacao solo para um usuario novo (sem convite/self-service)."""
    now = datetime.now(timezone.utc)
    label = (name_hint or "Mentorado").strip() or "Mentorado"
    org = db.organizations.insert_one(
        {
            "name": f"{label} — Organização",
            "created_at": now,
            "updated_at": now,
        }
    )
    return org.inserted_id


def _seed_landing_prompts_if_empty() -> None:
    """Garante os dois prompts padrão da landing na primeira subida."""
    if db.landing_prompts.count_documents({}) > 0:
        return
    now = datetime.now(timezone.utc)
    db.landing_prompts.insert_many(
        [
            {
                "title": "Gerar uma SWOT de IA em JSON",
                "description": "Produza a análise no formato importável pela plataforma Valorian.",
                "meta_label": "Prompt · SWOT de IA",
                "prompt_url": "/material_gratuito/prompt-swot-ia-json.md",
                "order": 0,
                "active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "title": "Preencher o Canvas de Oportunidades em JSON",
                "description": (
                    "Gere um rascunho inicial por área de negócio, "
                    "pronto para importar na plataforma Valorian."
                ),
                "meta_label": "Prompt · Canvas de Oportunidades",
                "prompt_url": "/material_gratuito/prompt-canvas-oportunidades-json.md",
                "order": 1,
                "active": True,
                "created_at": now,
                "updated_at": now,
            },
        ]
    )


def seed_maturity_model_from_file() -> ObjectId | None:
    """Insere o JSON de bootstrap em `ai_maturity_model` se a coleção estiver vazia."""
    existing = db.ai_maturity_model.find_one(sort=[("_id", -1)])
    if existing:
        return existing["_id"]
    if not _MATURITY_SEED_FILE.is_file():
        return None
    try:
        payload = json.loads(_MATURITY_SEED_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not payload.get("dimensions"):
        return None
    now = datetime.now(timezone.utc)
    payload.pop("_id", None)
    payload["created_at"] = now
    payload["updated_at"] = now
    ins = db.ai_maturity_model.insert_one(payload)
    return ins.inserted_id


# Rótulos do banco de itens anterior ao alinhamento com o Modelo de Maturidade.
_LEGACY_SWOT_PILLAR_NAMES = frozenset(
    {
        "Talento & cultura",
        "Infra & governança",
        "Portfólio & recursos",
        "Tecnologia & ecossistema",
        "Mercado & clientes",
        "Talento & incentivos",
        "Fornecedores & modelo",
        "Cultura & Liderança",
        "Governança & Regulação",
        "Portfólio de casos",
        "Ecossistema & Fornecedores",
    }
)


def purge_legacy_swot_analyses() -> int:
    """Remove SWOTs cujo banco de itens ainda usa rótulos pré-maturidade.

    Documentos vazios (sem pilares persistidos) são mantidos — a UI aplica os
    novos defaults. Retorna a quantidade apagada.
    """
    legacy_ids: list = []
    for doc in db.swot_analyses.find({}, {"pilares": 1}):
        pilares = doc.get("pilares") or {}
        if not isinstance(pilares, dict):
            legacy_ids.append(doc["_id"])
            continue
        names: list[str] = []
        for field in ("forcas", "fraquezas", "oportunidades", "ameacas"):
            slots = pilares.get(field) or []
            if not isinstance(slots, list):
                continue
            for slot in slots:
                if isinstance(slot, dict) and slot.get("nome"):
                    names.append(str(slot["nome"]).strip())
        if names and any(n in _LEGACY_SWOT_PILLAR_NAMES for n in names):
            legacy_ids.append(doc["_id"])
    if not legacy_ids:
        return 0
    result = db.swot_analyses.delete_many({"_id": {"$in": legacy_ids}})
    return int(result.deleted_count)


def init_indexes() -> None:
    db.users.create_index("email", unique=True)
    db.users.create_index("organization_id")
    migrate_users_to_organizations()
    backfill_user_tools()
    db.password_resets.create_index("token_hash", unique=True)
    db.password_resets.create_index("expires_at", expireAfterSeconds=0)
    db.password_resets.create_index([("user_id", 1), ("created_at", -1)])
    db.email_verifications.create_index("token_hash", unique=True)
    db.email_verifications.create_index("expires_at", expireAfterSeconds=0)
    db.email_verifications.create_index([("user_id", 1), ("created_at", -1)])
    db.progress.create_index([("user_id", 1), ("course_slug", 1)], unique=True)
    db.courses.create_index("slug", unique=True)
    # Questionário ativo em ai_maturity_model; seed a partir do JSON se a coleção estiver vazia
    db.ai_maturity_model.create_index("version")
    seed_maturity_model_from_file()
    # Múltiplas respostas por organização: remover índices antigos por user_id se existirem
    # (cada drop_index no seu próprio try — um nome que não existe não pode impedir os outros)
    for _old_index in (
        "user_id_1_model_version_1",
        "user_id_1_submitted_at_-1",
        "user_id_1_model_id_1_submitted_at_-1",
    ):
        try:
            db.maturity_responses.drop_index(_old_index)
        except Exception:
            pass  # índice já não existe ou nome diferente
    # Respostas completas são visíveis para toda a organização
    db.maturity_responses.create_index([("organization_id", 1), ("submitted_at", -1)])
    db.maturity_responses.create_index([("organization_id", 1), ("model_id", 1), ("submitted_at", -1)])
    # Rascunhos (complete=False) ficam isolados por autor até serem completados
    db.maturity_responses.create_index(
        [("organization_id", 1), ("model_id", 1), ("created_by_user_id", 1), ("complete", 1)]
    )
    db.quiz.create_index("encontro", unique=True)
    db.quiz_responses.create_index([("user_id", 1), ("encontro", 1)], unique=True)
    db.leads.create_index("created_at")
    db.landing_materials.create_index([("active", 1), ("order", 1)])
    db.landing_materials.create_index("created_at")
    db.landing_prompts.create_index([("active", 1), ("order", 1)])
    db.landing_prompts.create_index("created_at")
    _seed_landing_prompts_if_empty()
    try:
        db.canvas_projects.drop_index("user_id_1_updated_at_-1")
    except Exception:
        pass
    db.canvas_projects.create_index([("organization_id", 1), ("updated_at", -1)])
    # SWOT: vários docs por organização (um por resposta de maturidade + manuais)
    for _old_index in ("user_id_1", "user_id_1_updated_at_-1", "user_id_1_maturity_response_id_1"):
        try:
            db.swot_analyses.drop_index(_old_index)
        except Exception:
            pass
    db.swot_analyses.create_index([("organization_id", 1), ("updated_at", -1)])
    db.swot_analyses.create_index(
        [("organization_id", 1), ("maturity_response_id", 1)],
        unique=True,
        partialFilterExpression={"maturity_response_id": {"$exists": True}},
    )
    purge_legacy_swot_analyses()

    # OKR: vários ciclos por organização (trimestre/ano); no máximo um "ativo" por vez.
    db.okr_cycles.create_index([("organization_id", 1), ("updated_at", -1)])
    db.okr_cycles.create_index(
        [("organization_id", 1)],
        unique=True,
        partialFilterExpression={"status": "ativo"},
    )

    db.auth_rate_limits.create_index("at", expireAfterSeconds=3600)
    db.auth_rate_limits.create_index([("email", 1), ("scope", 1), ("at", -1)])

    # Módulo de Governança de IA
    db.ai_systems.create_index([("organization_id", 1), ("updated_at", -1)])
    # Índices parciais do Mongo não suportam $ne (compila para $not, proibido aqui) —
    # $type exclui null e "ausente" ao mesmo tempo, já que canvas_project_id só é
    # ObjectId quando presente (None nos sistemas cadastrados manualmente).
    db.ai_systems.create_index(
        [("organization_id", 1), ("canvas_project_id", 1)],
        unique=True,
        partialFilterExpression={"canvas_project_id": {"$type": "objectId"}},
    )
    db.ai_governance_audit_log.create_index(
        [("organization_id", 1), ("entity_type", 1), ("entity_id", 1), ("at", -1)]
    )
    # ai_risk_assessments / ai_governance_gates / ai_governance_evidence: imutáveis por
    # versão — "revision" cresce a cada publicação para o mesmo system_id (nunca editado).
    db.ai_risk_assessments.create_index(
        [("organization_id", 1), ("system_id", 1), ("revision", -1)]
    )
    db.ai_governance_gates.create_index(
        [("organization_id", 1), ("system_id", 1), ("revision", -1)]
    )
    db.ai_governance_evidence.create_index(
        [("organization_id", 1), ("system_id", 1), ("revision", -1)]
    )

    # Contagem de acessos aos recursos (dashboard do admin). O TTL em "at" também é o índice
    # que atende os recortes por período do relatório.
    db[analytics.COLLECTION].create_index("at", expireAfterSeconds=analytics.RETENTION_DAYS * 86400)
    db[analytics.COLLECTION].create_index([("resource_key", 1), ("at", -1)])
    db[analytics.COLLECTION].create_index([("visitor_hash", 1), ("at", -1)])
    db[analytics.COLLECTION].create_index([("day", 1)])
