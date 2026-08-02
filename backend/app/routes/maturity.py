from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.database import get_db
from app.deps import get_verified_user
from app.schemas import MaturityAnswersRequest


router = APIRouter(prefix="/api/maturity", tags=["maturity"])

TIER_ORDER = {"basico": 0, "completo": 1, "complementar": 2}
TIER_KEYS = ("basico", "completo", "complementar")


def _serialize_model(doc: dict) -> dict:
    model = {k: v for k, v in doc.items() if k != "_id"}
    model["id"] = str(doc["_id"])
    return model


def _load_model(db: Database) -> dict:
    """Carrega o modelo ativo da coleção MongoDB `ai_maturity_model`."""
    doc = db.ai_maturity_model.find_one(sort=[("_id", -1)])
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo de maturidade nao configurado",
        )
    model = _serialize_model(doc)
    if not model.get("dimensions"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo de maturidade invalido",
        )
    return model


def _normalize_tier(tier: str | None) -> str:
    key = (tier or "basico").strip().lower()
    if key not in TIER_ORDER:
        raise HTTPException(status_code=400, detail="Tier invalido")
    return key


def _is_visible_tier(question_tier: str, selected_tier: str) -> bool:
    return TIER_ORDER.get(question_tier, 99) <= TIER_ORDER[selected_tier]


def _questions_for_tier(model: dict, tier: str) -> list[dict]:
    out: list[dict] = []
    for dimension in model.get("dimensions", []):
        for q in dimension.get("questions", []):
            if _is_visible_tier(q.get("tier", "basico"), tier):
                out.append({**q, "dim_id": dimension["id"], "dim_name": dimension["name"]})
    return out


def _score_submission(model: dict, answers: dict[str, int], tier: str) -> dict:
    questions = _questions_for_tier(model, tier)
    levels_cfg = (model.get("levels") or {}).get(tier) or {}
    max_score = int(levels_cfg.get("max_score") or (len(questions) * 5))

    total_score = 0
    dimension_scores: dict[str, dict] = {}

    for dimension in model.get("dimensions", []):
        dim_id = dimension["id"]
        dim_name = dimension["name"]
        dim_qs = [
            q
            for q in dimension.get("questions", [])
            if _is_visible_tier(q.get("tier", "basico"), tier)
        ]
        dim_score = 0
        dim_max = 0
        for q in dim_qs:
            qid = q["id"]
            weight = int(q.get("weight", 1))
            value = int(answers.get(qid, 0))
            if value < 1 or value > 5:
                value = 0
            dim_score += value * weight
            dim_max += 5 * weight
        question_count = len(dim_qs)
        avg = (dim_score / question_count) if question_count else 0
        dimension_scores[dim_id] = {
            "name": dim_name,
            "score": dim_score,
            "max": dim_max,
            "avg": round(avg, 2),
        }
        total_score += dim_score

    scoring = ((model.get("scoring") or {}).get(tier)) or {}
    level = None
    for key in ("level_1", "level_2", "level_3", "level_4", "level_5"):
        cfg = scoring.get(key)
        if not cfg:
            continue
        if cfg.get("min", 0) <= total_score <= cfg.get("max", 0):
            level = cfg
            break
    if level is None and scoring:
        first = scoring.get("level_1")
        last = scoring.get("level_5")
        if first and total_score < first.get("min", 0):
            level = first
        elif last:
            level = last

    return {
        "total_score": total_score,
        "max_score": max_score,
        "percent_score": round((total_score / max_score) * 100, 2) if max_score else 0,
        "dimension_scores": dimension_scores,
        "level": level,
        "tier": tier,
    }


@router.get("/model")
def get_model(user=Depends(get_verified_user), db: Database = Depends(get_db)):
    return _load_model(db)


@router.get("/my-responses")
def list_my_responses(user=Depends(get_verified_user), db: Database = Depends(get_db)):
    """Lista autoavaliações do aluno para o modelo ativo (mais recentes primeiro)."""
    model = _load_model(db)
    model_oid = ObjectId(model["id"])
    cursor = db.maturity_responses.find(
        {"user_id": user["_id"], "model_id": model_oid}
    ).sort("submitted_at", -1)
    items = []
    for doc in cursor:
        submitted_at = doc.get("submitted_at")
        result = doc.get("result") or {}
        dim_scores = result.get("dimension_scores") or {}
        items.append({
            "id": str(doc["_id"]),
            "model_id": str(doc["model_id"]) if doc.get("model_id") else model["id"],
            "submitted_at": submitted_at.isoformat() if submitted_at else None,
            "tier": doc.get("tier") or result.get("tier"),
            "result": {
                "total_score": result.get("total_score", 0),
                "max_score": result.get("max_score", 0),
                "percent_score": result.get("percent_score", 0),
                "level": result.get("level"),
                "dimension_scores": dim_scores,
                "tier": result.get("tier") or doc.get("tier"),
            },
        })
    return {"items": items}


@router.get("/my-responses/{response_id}")
def get_my_response_by_id(
    response_id: str, user=Depends(get_verified_user), db: Database = Depends(get_db)
):
    """Retorna uma resposta específica (para visualizar detalhes)."""
    if not ObjectId.is_valid(response_id):
        raise HTTPException(status_code=404, detail="Resposta nao encontrada")
    oid = ObjectId(response_id)
    doc = db.maturity_responses.find_one({"_id": oid, "user_id": user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Resposta nao encontrada")
    submitted_at = doc.get("submitted_at")
    return {
        "id": str(doc["_id"]),
        "model_id": str(doc["model_id"]) if doc.get("model_id") else None,
        "answers": doc.get("answers", {}),
        "tier": doc.get("tier"),
        "submitted_at": submitted_at.isoformat() if submitted_at else None,
        "result": doc.get("result"),
    }


@router.post("/my-response")
def save_my_response(payload: MaturityAnswersRequest, user=Depends(get_verified_user), db: Database = Depends(get_db)):
    """Cria ou atualiza uma autoavaliação vinculada ao modelo ativo no banco."""
    model = _load_model(db)
    model_oid = ObjectId(model["id"])
    tier = _normalize_tier(payload.tier)
    known = {q["id"] for d in model.get("dimensions", []) for q in d.get("questions", [])}
    if not known:
        raise HTTPException(status_code=500, detail="Modelo de maturidade invalido")

    answers: dict[str, int] = {}
    for qid, raw in (payload.answers or {}).items():
        if qid not in known:
            continue
        value = int(raw)
        if value < 1 or value > 5:
            raise HTTPException(status_code=400, detail=f"Resposta invalida para {qid}")
        answers[qid] = value

    required = {q["id"] for q in _questions_for_tier(model, tier)}
    complete = bool(required) and required.issubset(answers.keys())
    result = _score_submission(model, answers, tier)
    result["complete"] = complete
    now = datetime.now(timezone.utc)

    common_fields = {
        "model_id": model_oid,
        "model_version": model.get("version", "1.0"),
        "assessment_title": model.get("assessment_title") or model.get("title"),
        "tier": tier,
        "answers": answers,
        "result": result,
        "complete": complete,
        "updated_at": now,
    }

    response_id = (payload.response_id or "").strip() or None
    if response_id:
        if not ObjectId.is_valid(response_id):
            raise HTTPException(status_code=404, detail="Resposta nao encontrada")
        oid = ObjectId(response_id)
        existing = db.maturity_responses.find_one({"_id": oid, "user_id": user["_id"]})
        if not existing:
            raise HTTPException(status_code=404, detail="Resposta nao encontrada")
        db.maturity_responses.update_one(
            {"_id": oid},
            {
                "$set": {
                    **common_fields,
                    "submitted_at": now if complete else existing.get("submitted_at") or now,
                }
            },
        )
        doc_id = response_id
        submitted_at = now if complete else (existing.get("submitted_at") or now)
    else:
        doc = {
            "user_id": user["_id"],
            **common_fields,
            "submitted_at": now,
        }
        ins = db.maturity_responses.insert_one(doc)
        doc_id = str(ins.inserted_id)
        submitted_at = now

    return {
        "id": doc_id,
        "model_id": model["id"],
        "answers": answers,
        "tier": tier,
        "complete": complete,
        "submitted_at": submitted_at.isoformat() if hasattr(submitted_at, "isoformat") else submitted_at,
        "result": result,
    }
