from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.database import get_db
from app.deps import get_current_user
from app.schemas import MaturityAnswersRequest


router = APIRouter(prefix="/api/maturity", tags=["maturity"])


def _load_model(db: Database) -> dict:
    doc = db.ai_maturity_model.find_one(sort=[("_id", -1)])
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo de maturidade nao configurado",
        )
    model = {k: v for k, v in doc.items() if k != "_id"}
    if not model.get("dimensions"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo de maturidade invalido",
        )
    return model


def _score_submission(model: dict, answers: dict[str, int]) -> dict:
    dimensions = model.get("dimensions", [])
    total_score = 0
    total_max = 0
    dimension_scores: dict[str, dict] = {}

    for dimension in dimensions:
        dim_id = dimension["id"]
        dim_name = dimension["name"]
        dim_score = 0
        dim_max = 0
        question_count = 0

        for q in dimension.get("questions", []):
            qid = q["id"]
            weight = int(q.get("weight", 1))
            value = int(answers.get(qid, 0))
            if value < 1 or value > 5:
                value = 0
            dim_score += value * weight
            dim_max += 5 * weight
            question_count += 1

        total_score += dim_score
        total_max += dim_max
        avg = (dim_score / question_count) if question_count else 0
        dimension_scores[dim_id] = {"name": dim_name, "score": dim_score, "max": dim_max, "avg": round(avg, 2)}

    level = None
    for _, cfg in model.get("scoring_logic", {}).items():
        if cfg.get("min", 0) <= total_score <= cfg.get("max", 0):
            level = cfg
            break

    return {
        "total_score": total_score,
        "max_score": total_max,
        "percent_score": round((total_score / total_max) * 100, 2) if total_max else 0,
        "dimension_scores": dimension_scores,
        "level": level,
    }


@router.get("/model")
def get_model(user=Depends(get_current_user), db: Database = Depends(get_db)):
    return _load_model(db)


@router.get("/my-responses")
def list_my_responses(user=Depends(get_current_user), db: Database = Depends(get_db)):
    """Lista todas as autoavaliações do aluno (mais recentes primeiro)."""
    model = _load_model(db)
    version = model.get("version", "1.0")
    cursor = db.maturity_responses.find(
        {"user_id": user["_id"], "model_version": version}
    ).sort("submitted_at", -1)
    items = []
    for doc in cursor:
        submitted_at = doc.get("submitted_at")
        result = doc.get("result") or {}
        dim_scores = result.get("dimension_scores") or {}
        items.append({
            "id": str(doc["_id"]),
            "submitted_at": submitted_at.isoformat() if submitted_at else None,
            "result": {
                "total_score": result.get("total_score", 0),
                "max_score": result.get("max_score", 0),
                "percent_score": result.get("percent_score", 0),
                "level": result.get("level"),
                "dimension_scores": dim_scores,
            },
        })
    return {"items": items}


@router.get("/my-responses/{response_id}")
def get_my_response_by_id(
    response_id: str, user=Depends(get_current_user), db: Database = Depends(get_db)
):
    """Retorna uma resposta específica (para visualizar detalhes)."""
    from bson import ObjectId
    if not ObjectId.is_valid(response_id):
        raise HTTPException(status_code=404, detail="Resposta nao encontrada")
    oid = ObjectId(response_id)
    doc = db.maturity_responses.find_one({"_id": oid, "user_id": user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Resposta nao encontrada")
    submitted_at = doc.get("submitted_at")
    return {
        "id": str(doc["_id"]),
        "answers": doc.get("answers", {}),
        "submitted_at": submitted_at.isoformat() if submitted_at else None,
        "result": doc.get("result"),
    }


@router.post("/my-response")
def save_my_response(payload: MaturityAnswersRequest, user=Depends(get_current_user), db: Database = Depends(get_db)):
    """Cria uma nova autoavaliação (múltiplas respostas por aluno)."""
    from bson import ObjectId
    model = _load_model(db)
    all_questions = {q["id"] for d in model.get("dimensions", []) for q in d.get("questions", [])}
    if not all_questions:
        raise HTTPException(status_code=500, detail="Modelo de maturidade invalido")

    answers = {}
    for qid in all_questions:
        value = int(payload.answers.get(qid, 0))
        if value < 1 or value > 5:
            raise HTTPException(status_code=400, detail=f"Resposta invalida para {qid}")
        answers[qid] = value

    result = _score_submission(model, answers)
    submitted_at = datetime.now(timezone.utc)

    doc = {
        "user_id": user["_id"],
        "model_version": model.get("version", "1.0"),
        "assessment_title": model.get("assessment_title"),
        "answers": answers,
        "result": result,
        "submitted_at": submitted_at,
    }
    ins = db.maturity_responses.insert_one(doc)
    doc["_id"] = ins.inserted_id

    return {
        "id": str(ins.inserted_id),
        "answers": answers,
        "submitted_at": submitted_at.isoformat(),
        "result": result,
    }
