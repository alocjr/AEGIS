"""Promove um usuário existente a administrador (bootstrap único via CLI)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Permite executar: python -m app.scripts.promote_admin --email admin@exemplo.com
_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.database import db  # noqa: E402


def promote_admin(email: str) -> None:
    normalized = email.strip().lower()
    if not normalized:
        print("Informe um email válido.", file=sys.stderr)
        sys.exit(1)

    result = db.users.update_one(
        {"email": normalized},
        {
            "$set": {
                "is_admin": True,
                "email_verified": True,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    if result.matched_count == 0:
        print(f"Nenhum usuário encontrado com email: {normalized}", file=sys.stderr)
        sys.exit(1)
    print(f"Admin promovido: {normalized}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Promove usuário a administrador no MongoDB")
    parser.add_argument("--email", required=True, help="Email do usuário a promover")
    args = parser.parse_args()
    promote_admin(args.email)


if __name__ == "__main__":
    main()
