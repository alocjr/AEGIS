from datetime import datetime, timezone
from pathlib import Path
import json

from pymongo import MongoClient
from pymongo.database import Database
from bson import ObjectId

from app.config import settings

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_MATURITY_SEED_FILE = _DATA_DIR / "ai_maturity_model.json"


# tlsCAFile com certifi evita SSL: CERTIFICATE_VERIFY_FAILED no macOS
client = MongoClient(settings.mongodb_uri)
db: Database = client[settings.mongodb_db_name]


def get_db() -> Database:
    return db


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


def init_indexes() -> None:
    db.users.create_index("email", unique=True)
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
    # Múltiplas respostas por aluno: remover índice único antigo (1 resposta por user) se existir
    try:
        db.maturity_responses.drop_index("user_id_1_model_version_1")
    except Exception:
        pass  # índice já não existe ou nome diferente
    db.maturity_responses.create_index([("user_id", 1), ("submitted_at", -1)])
    db.maturity_responses.create_index([("user_id", 1), ("model_id", 1), ("submitted_at", -1)])
    db.quiz.create_index("encontro", unique=True)
    db.quiz_responses.create_index([("user_id", 1), ("encontro", 1)], unique=True)
    db.leads.create_index("created_at")
    db.landing_materials.create_index([("active", 1), ("order", 1)])
    db.landing_materials.create_index("created_at")
    db.landing_prompts.create_index([("active", 1), ("order", 1)])
    db.landing_prompts.create_index("created_at")
    _seed_landing_prompts_if_empty()
    db.canvas_projects.create_index([("user_id", 1), ("updated_at", -1)])
    db.swot_analyses.create_index("user_id", unique=True)
    db.auth_rate_limits.create_index("at", expireAfterSeconds=3600)
    db.auth_rate_limits.create_index([("email", 1), ("scope", 1), ("at", -1)])
