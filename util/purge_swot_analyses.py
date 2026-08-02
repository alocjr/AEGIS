"""Remove documentos de SWOT antigos (pré-alinhamento ao Modelo de Maturidade).

Uso (a partir da raiz do repo):
  python util/purge_swot_analyses.py
  python util/purge_swot_analyses.py --dry-run
  python util/purge_swot_analyses.py --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permite importar "app.*" a partir de backend/
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.database import db, purge_legacy_swot_analyses  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Limpa SWOTs antigos da coleção swot_analyses.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas conta documentos; não apaga.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Apaga todos os documentos de swot_analyses (não só os com rótulos legados).",
    )
    args = parser.parse_args()

    total = db.swot_analyses.count_documents({})
    print(f"swot_analyses: {total} documento(s)")

    if args.dry_run:
        if args.all:
            print(f"dry-run: apagaria todos ({total}).")
        else:
            # Conta legados sem apagar
            from app.database import _LEGACY_SWOT_PILLAR_NAMES

            legacy = 0
            for doc in db.swot_analyses.find({}, {"pilares": 1}):
                pilares = doc.get("pilares") or {}
                if not isinstance(pilares, dict):
                    legacy += 1
                    continue
                names: list[str] = []
                for field in ("forcas", "fraquezas", "oportunidades", "ameacas"):
                    for slot in pilares.get(field) or []:
                        if isinstance(slot, dict) and slot.get("nome"):
                            names.append(str(slot["nome"]).strip())
                if names and any(n in _LEGACY_SWOT_PILLAR_NAMES for n in names):
                    legacy += 1
            print(f"dry-run: apagaria {legacy} SWOT(s) com rótulos legados.")
        return

    if args.all:
        deleted = int(db.swot_analyses.delete_many({}).deleted_count)
        print(f"apagados (todos): {deleted}")
    else:
        deleted = purge_legacy_swot_analyses()
        print(f"apagados (legados): {deleted}")

    print(f"swot_analyses após limpeza: {db.swot_analyses.count_documents({})}")


if __name__ == "__main__":
    main()
