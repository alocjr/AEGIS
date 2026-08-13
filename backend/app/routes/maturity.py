from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.database import get_db
from app.deps import get_current_organization_id, get_verified_user, require_tool
from app.schemas import MaturityAnswersRequest
from app.tools import TOOL_MATURITY


router = APIRouter(
    prefix="/api/maturity",
    tags=["maturity"],
    dependencies=[Depends(require_tool(TOOL_MATURITY))],
)

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


def _owned_response(db: Database, org_id, user_id, response_id: str) -> dict:
    """Resposta completa: visível para toda a organização. Rascunho: só o autor."""
    if not ObjectId.is_valid(response_id):
        raise HTTPException(status_code=404, detail="Resposta nao encontrada")
    doc = db.maturity_responses.find_one({"_id": ObjectId(response_id), "organization_id": org_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Resposta nao encontrada")
    if not doc.get("complete") and doc.get("created_by_user_id") != user_id:
        raise HTTPException(status_code=404, detail="Resposta nao encontrada")
    return doc


def _model_of_response(db: Database, doc: dict) -> dict:
    """Modelo usado na autoavaliação — cai no ativo se o original não existir mais."""
    model_id = doc.get("model_id")
    if model_id:
        found = db.ai_maturity_model.find_one({"_id": model_id})
        if found:
            return _serialize_model(found)
    return _load_model(db)


def _answers_of(doc: dict) -> dict[str, int]:
    answers: dict[str, int] = {}
    for qid, raw in (doc.get("answers") or {}).items():
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if 1 <= value <= 5:
            answers[str(qid)] = value
    return answers


def _export_question(question: dict, answers: dict[str, int]) -> dict:
    qid = str(question.get("id") or "")
    value = answers.get(qid)
    levels = question.get("levels") or {}
    exported = {
        "id": qid,
        "tier": question.get("tier") or "basico",
        "texto": question.get("text") or "",
        "peso": int(question.get("weight", 1) or 1),
        "resposta": value,
        "resposta_descricao": str(levels.get(str(value)) or "") if value else "",
    }
    csf_id = str(question.get("csfId") or "")
    csf_name = str(question.get("csfName") or "")
    if csf_id or csf_name:
        exported["referencia"] = {"csf_id": csf_id, "csf_nome": csf_name}
    return exported


@router.get("/model")
def get_model(user=Depends(get_verified_user), db: Database = Depends(get_db)):
    return _load_model(db)


@router.get("/my-responses")
def list_my_responses(
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Lista autoavaliações da organização para o modelo ativo (mais recentes primeiro).

    Rascunhos (complete=False) só aparecem para quem os criou.
    """
    model = _load_model(db)
    model_oid = ObjectId(model["id"])
    cursor = db.maturity_responses.find(
        {
            "organization_id": org_id,
            "model_id": model_oid,
            "$or": [{"complete": True}, {"created_by_user_id": user["_id"]}],
        }
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
            "complete": bool(doc.get("complete")),
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
    response_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Retorna uma resposta específica (para visualizar detalhes)."""
    doc = _owned_response(db, org_id, user["_id"], response_id)
    submitted_at = doc.get("submitted_at")
    return {
        "id": str(doc["_id"]),
        "model_id": str(doc["model_id"]) if doc.get("model_id") else None,
        "answers": doc.get("answers", {}),
        "tier": doc.get("tier"),
        "complete": bool(doc.get("complete")),
        "submitted_at": submitted_at.isoformat() if submitted_at else None,
        "result": doc.get("result"),
    }


@router.get("/my-responses/{response_id}/export")
def export_my_response(
    response_id: str,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
    """Autoavaliação em JSON (envelope `aegis.maturidade-ia`): respostas com o texto das perguntas."""
    doc = _owned_response(db, org_id, user["_id"], response_id)
    model = _model_of_response(db, doc)
    tier = _normalize_tier(doc.get("tier"))
    answers = _answers_of(doc)
    result = doc.get("result") or _score_submission(model, answers, tier)
    dimension_scores = result.get("dimension_scores") or {}
    level = result.get("level") or {}
    tier_cfg = (model.get("levels") or {}).get(tier) or {}

    dimensoes = []
    total_questions = 0
    answered_questions = 0
    for dimension in model.get("dimensions", []):
        questions = [
            q
            for q in dimension.get("questions", [])
            if _is_visible_tier(q.get("tier", "basico"), tier)
        ]
        if not questions:
            continue
        total_questions += len(questions)
        answered_questions += sum(1 for q in questions if answers.get(str(q.get("id"))))
        dim_id = dimension["id"]
        scores = dimension_scores.get(dim_id) or {}
        score = scores.get("score")
        maximo = scores.get("max")
        dimensoes.append(
            {
                "id": dim_id,
                "nome": dimension.get("name") or scores.get("name") or "",
                "pontuacao": score,
                "pontuacao_maxima": maximo,
                "media": scores.get("avg"),
                "percentual": (
                    round(score / maximo * 100, 2)
                    if isinstance(score, (int, float)) and maximo
                    else None
                ),
                "perguntas": [_export_question(q, answers) for q in questions],
            }
        )

    submitted_at = doc.get("submitted_at")
    return {
        "format": "aegis.maturidade-ia",
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "titulo": doc.get("assessment_title")
            or model.get("assessment_title")
            or model.get("title")
            or "",
            "modelo_versao": doc.get("model_version") or model.get("version") or "",
            "abrangencia": {
                "tier": tier,
                "label": tier_cfg.get("label") or tier,
                "descricao": tier_cfg.get("description") or "",
                "perguntas_respondidas": answered_questions,
                "perguntas_total": total_questions,
            },
            "completo": bool(doc.get("complete")),
            "respondido_em": submitted_at.isoformat() if submitted_at else None,
            "resultado": {
                "pontuacao": result.get("total_score", 0),
                "pontuacao_maxima": result.get("max_score", 0),
                "percentual": result.get("percent_score", 0),
                "nivel": {
                    "label": level.get("label") or "",
                    "descricao": level.get("description") or "",
                },
            },
            "dimensoes": dimensoes,
        },
    }


@router.post("/my-response")
def save_my_response(
    payload: MaturityAnswersRequest,
    user=Depends(get_verified_user),
    org_id=Depends(get_current_organization_id),
    db: Database = Depends(get_db),
):
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
    existing = None
    if response_id:
        if not ObjectId.is_valid(response_id):
            raise HTTPException(status_code=404, detail="Resposta nao encontrada")
        existing = db.maturity_responses.find_one(
            {"_id": ObjectId(response_id), "organization_id": org_id}
        )
        if not existing or (
            not existing.get("complete") and existing.get("created_by_user_id") != user["_id"]
        ):
            raise HTTPException(status_code=404, detail="Resposta nao encontrada")
    else:
        # Autosave sem id: reutiliza o rascunho incompleto mais recente do mesmo autor/modelo
        # (evita duplicar registros quando o cliente ainda não recebeu o response_id, e evita
        # que dois membros da mesma organização colidam no mesmo rascunho em edição).
        existing = db.maturity_responses.find_one(
            {
                "organization_id": org_id,
                "model_id": model_oid,
                "created_by_user_id": user["_id"],
                "complete": {"$ne": True},
            },
            sort=[("updated_at", -1), ("submitted_at", -1)],
        )

    if existing:
        oid = existing["_id"]
        db.maturity_responses.update_one(
            {"_id": oid},
            {
                "$set": {
                    **common_fields,
                    "submitted_at": now if complete else existing.get("submitted_at") or now,
                }
            },
        )
        doc_id = str(oid)
        submitted_at = now if complete else (existing.get("submitted_at") or now)
    else:
        doc = {
            "organization_id": org_id,
            "created_by_user_id": user["_id"],
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
