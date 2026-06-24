import certifi
from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings


# tlsCAFile com certifi evita SSL: CERTIFICATE_VERIFY_FAILED no macOS
client = MongoClient(settings.mongodb_uri)
db: Database = client[settings.mongodb_db_name]


def get_db() -> Database:
    return db


def init_indexes() -> None:
    db.users.create_index("email", unique=True)
    db.password_resets.create_index("token_hash", unique=True)
    db.password_resets.create_index("expires_at", expireAfterSeconds=0)
    db.password_resets.create_index([("user_id", 1), ("created_at", -1)])
    db.progress.create_index([("user_id", 1), ("course_slug", 1)], unique=True)
    db.courses.create_index("slug", unique=True)
    db.ai_maturity_model.create_index("version")
    # Múltiplas respostas por aluno: remover índice único antigo (1 resposta por user) se existir
    try:
        db.maturity_responses.drop_index("user_id_1_model_version_1")
    except Exception:
        pass  # índice já não existe ou nome diferente
    db.maturity_responses.create_index([("user_id", 1), ("submitted_at", -1)])
    db.quiz.create_index("encontro", unique=True)
    db.quiz_responses.create_index([("user_id", 1), ("encontro", 1)], unique=True)
    db.leads.create_index("created_at")
    db.auth_rate_limits.create_index("at", expireAfterSeconds=3600)
    db.auth_rate_limits.create_index([("email", 1), ("scope", 1), ("at", -1)])
