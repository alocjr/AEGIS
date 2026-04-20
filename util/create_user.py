import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# pyright: reportMissingImports=false

# Permite importar "app.*" a partir de backend/
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.database import db  # noqa: E402
from app.security import hash_password  # noqa: E402


def create_or_update_admin() -> None:
    admin_name = os.environ.get("ADMIN_NAME", "admin")
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
    if not admin_email or not admin_password:
        print("Defina ADMIN_EMAIL e ADMIN_PASSWORD no ambiente. Ex.: ADMIN_EMAIL=admin@exemplo.com ADMIN_PASSWORD=sua_senha_segura python -m util.create_user")
        sys.exit(1)
    password_hash = hash_password(admin_password)

    now = datetime.now(timezone.utc)

    result = db.users.update_one(
        {"email": admin_email},
        {
            "$set": {
                "name": admin_name,
                "email": admin_email,
                "password_hash": password_hash,
                "is_admin": True,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    if result.upserted_id:
        print(f"Admin criado com sucesso: {admin_email}")
    else:
        print(f"Admin atualizado com sucesso: {admin_email}")


if __name__ == "__main__":
    create_or_update_admin()