"""
Sincroniza quiz_id (ObjectId) em cada encontro de cada trilha na base de dados.

Executar a partir da raiz do backend (com o ambiente virtual ativado):
  cd backend
  source .venv/bin/activate   # ou: .venv\\Scripts\\activate no Windows
  python -m app.scripts.sync_quiz_ids

Alternativa (usa apenas variáveis de ambiente MONGODB_URI e MONGODB_DB_NAME):
  cd backend && python -m app.scripts.sync_quiz_ids --standalone
  (requer: pip install pymongo)
"""
import copy
import os
import sys


def _fill_quiz_ids_in_payload(db, payload: dict) -> dict:
    """Preenche quiz_id em cada encontro do payload com o ObjectId do quiz correspondente."""
    payload = copy.deepcopy(payload)
    for semana in (payload.get("jornada_aprendizagem") or []):
        for enc in (semana.get("encontros") or []):
            eid = enc.get("id")
            if eid is None:
                continue
            eid_int = int(eid)
            quiz = db.quiz.find_one({"encontro": eid_int}, {"_id": 1})
            if quiz:
                enc["quiz_id"] = quiz["_id"]
            else:
                enc.pop("quiz_id", None)
    return payload


def run_with_app_db():
    from app.database import db
    return _run(db)


def run_standalone():
    from pymongo import MongoClient
    # Carrega .env do backend se existir (para rodar: cd backend && python -m app.scripts.sync_quiz_ids --standalone)
    for env_path in (".env", os.path.join(os.path.dirname(__file__), "..", "..", ".env")):
        if os.path.isfile(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGODB_URI_CONNECTION")
    db_name = os.environ.get("MONGODB_DB_NAME", "valorian4future")
    if not uri:
        raise SystemExit("Defina MONGODB_URI (ou MONGODB_URI_CONNECTION) no ambiente ou .env")
    client = MongoClient(uri)
    db = client[db_name]
    return _run(db)


def _run(db):
    updated = 0
    for course in db.courses.find({}, {"slug": 1, "programa_formacao_executiva": 1}):
        pfe = course.get("programa_formacao_executiva") or {}
        payload = _fill_quiz_ids_in_payload(db, pfe)
        db.courses.update_one(
            {"slug": course["slug"]},
            {"$set": {"programa_formacao_executiva": payload}},
        )
        updated += 1
        print(f"  Trilha atualizada: {course['slug']}")
    return updated


if __name__ == "__main__":
    print("Sincronizando quiz_id nos encontros das trilhas...")
    standalone = "--standalone" in sys.argv
    try:
        if standalone:
            n = run_standalone()
        else:
            n = run_with_app_db()
        print(f"Sincronização concluída. {n} trilha(s) atualizada(s).")
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
