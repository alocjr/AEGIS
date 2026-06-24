from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from app.database import get_db
from app.deps import get_verified_user
from app.routes.progress import _resolve_course_slug
from app.schemas import QuizSubmitRequest


router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.get("")
def list_my_quiz_responses(
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
    course_slug: str | None = Query(None, description="Trilha (slug). Se omitido, usa a trilha principal."),
):
    """Lista todos os encontros que têm quiz e a resposta do usuário (se houver). Inclui ativo (progresso) para saber quais encontros estão liberados."""
    slug = _resolve_course_slug(user, db, course_slug)
    quizzes = list(db.quiz.find({}, {"_id": 1, "encontro": 1, "titulo": 1, "questoes": 1}))
    responses = {
        r["encontro"]: r
        for r in db.quiz_responses.find(
            {"user_id": user["_id"]},
            {"encontro": 1, "score": 1, "total": 1, "answers": 1, "submitted_at": 1},
        )
    }
    progress = db.progress.find_one({"user_id": user["_id"], "course_slug": slug}, {"ativo": 1, "encontros_liberados": 1})
    ativo = (progress or {}).get("ativo", 1)
    liberados = (progress or {}).get("encontros_liberados") or [1]
    out = []
    for q in sorted(quizzes, key=lambda x: x["encontro"]):
        total = len(q.get("questoes", []))
        r = responses.get(q["encontro"]) or {}
        answers = r.get("answers") or {}
        total_answered = len(answers)
        item = {
            "encontro": q["encontro"],
            "titulo": q.get("titulo", f"Quiz Encontro {q['encontro']}"),
            "total": total,
            "total_answered": total_answered,
            "score": r.get("score"),
            "submitted_at": r.get("submitted_at").isoformat() if r.get("submitted_at") else None,
        }
        if q.get("_id"):
            item["quiz_id"] = str(q["_id"])
        out.append(item)
    return {"items": out, "ativo": ativo, "encontros_liberados": liberados}


def _sanitize_quiz_doc(doc: dict, include_rationales: bool = False) -> dict:
    def _opcoes(questao: dict):
        for idx, op in enumerate(questao.get("opcoes", [])):
            out = {"index": idx, "text": op["text"]}
            if include_rationales:
                out["rationale"] = op.get("rationale", "")
                out["isCorrect"] = op.get("isCorrect") is True
            yield out

    return {
        "encontro": doc["encontro"],
        "titulo": doc.get("titulo", f"Quiz Encontro {doc['encontro']}"),
        "questoes": [
            {
                "id": q["id"],
                "pergunta": q["pergunta"],
                "hint": q.get("hint", ""),
                "opcoes": list(_opcoes(q)),
            }
            for q in doc.get("questoes", [])
        ],
    }


def _get_quiz_impl(
    encontro_id: int,
    user: dict,
    db: Database,
    batch: int | None,
    review: bool,
    rationales_for: str | None,
    course_slug: str | None = None,
):
    """Lógica compartilhada para obter quiz por encontro_id (usada por get_quiz e get_quiz_by_id)."""
    quiz = db.quiz.find_one({"encontro": encontro_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz nao encontrado para este encontro")
    slug = _resolve_course_slug(user, db, course_slug)
    progress = db.progress.find_one({"user_id": user["_id"], "course_slug": slug}, {"ativo": 1, "encontros_liberados": 1})
    ativo = (progress or {}).get("ativo", 1)
    liberados = (progress or {}).get("encontros_liberados") or [1]
    if encontro_id > ativo or encontro_id not in liberados:
        raise HTTPException(
            status_code=403,
            detail="Conclua o encontro " + str(encontro_id) + " no programa e aguarde a liberacao para acessar este quiz",
        )
    response = db.quiz_responses.find_one({"user_id": user["_id"], "encontro": encontro_id})
    existing_answers = (response or {}).get("answers", {})
    all_questoes = quiz.get("questoes", [])
    total_questoes = len(all_questoes)
    if rationales_for is not None:
        ids_str = [s.strip() for s in rationales_for.split(",") if s.strip()]
        ids_set = set(int(x) for x in ids_str if x.isdigit())
        take = [q for q in all_questoes if q.get("id") in ids_set]
        return _sanitize_quiz_doc({**quiz, "questoes": take}, include_rationales=True)
    if review:
        if not response or not existing_answers:
            raise HTTPException(status_code=403, detail="Responda ao menos uma questao para visualizar os racionais")
        if len(existing_answers) >= total_questoes:
            return _sanitize_quiz_doc(quiz, include_rationales=True)
        take = [q for q in all_questoes if str(q["id"]) in existing_answers]
        return _sanitize_quiz_doc({**quiz, "questoes": take}, include_rationales=True)
    if batch is not None and batch > 0:
        unanswered = [q for q in all_questoes if str(q["id"]) not in existing_answers]
        take = unanswered[:batch]
        if not take:
            return {
                "encontro": quiz["encontro"],
                "titulo": quiz.get("titulo", f"Quiz Encontro {quiz['encontro']}"),
                "questoes": [],
                "all_answered": True,
            }
        return _sanitize_quiz_doc({**quiz, "questoes": take}, include_rationales=False)
    return _sanitize_quiz_doc(quiz, include_rationales=False)


@router.get("/by-id/{quiz_id}")
def get_quiz_by_id(
    quiz_id: str,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
    batch: int | None = Query(None),
    review: bool = Query(False),
    rationales_for: str | None = Query(None),
    course_slug: str | None = Query(None),
):
    """Retorna o quiz pelo ObjectId (quiz_id do encontro). Mesma resposta e regras de acesso que GET /{encontro_id}."""
    if not ObjectId.is_valid(quiz_id):
        raise HTTPException(status_code=404, detail="Quiz nao encontrado")
    quiz = db.quiz.find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz nao encontrado")
    return _get_quiz_impl(
        quiz["encontro"], user, db, batch, review, rationales_for, course_slug
    )


@router.get("/{encontro_id}")
def get_quiz(
    encontro_id: int,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
    batch: int | None = Query(None, description="Devolver apenas as N primeiras perguntas ainda nao respondidas"),
    review: bool = Query(False, description="Devolver quiz com racionais (todas ou só as já respondidas)"),
    rationales_for: str | None = Query(None, description="IDs das questões para devolver com racionais (ex: 1,2,3)"),
    course_slug: str | None = Query(None),
):
    return _get_quiz_impl(encontro_id, user, db, batch, review, rationales_for, course_slug)


@router.get("/{encontro_id}/my-response")
def get_my_quiz_response(
    encontro_id: int,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
    course_slug: str | None = Query(None),
):
    slug = _resolve_course_slug(user, db, course_slug)
    progress = db.progress.find_one({"user_id": user["_id"], "course_slug": slug}, {"ativo": 1, "encontros_liberados": 1})
    ativo = (progress or {}).get("ativo", 1)
    liberados = (progress or {}).get("encontros_liberados") or [1]
    if encontro_id > ativo or encontro_id not in liberados:
        raise HTTPException(status_code=403, detail="Encontro ainda nao liberado")
    response = db.quiz_responses.find_one({"user_id": user["_id"], "encontro": encontro_id})
    if not response:
        return {"answers": {}, "score": None, "total": None, "feedback": {}, "submitted_at": None}
    submitted_at = response.get("submitted_at")
    return {
        "answers": response.get("answers", {}),
        "score": response.get("score"),
        "total": response.get("total"),
        "feedback": response.get("feedback", {}),
        "submitted_at": submitted_at.isoformat() if submitted_at else None,
    }


def _compute_feedback_for_answers(quiz: dict, answers: dict[str, int]) -> tuple[dict, dict, int, int]:
    feedback: dict[str, dict] = {}
    correct = 0
    total = len(quiz.get("questoes", []))
    for q in quiz.get("questoes", []):
        qid = str(q["id"])
        options = q.get("opcoes", [])
        selected = answers.get(qid)
        if selected is None or selected < 0 or selected >= len(options):
            continue
        selected_option = options[selected]
        is_correct = selected_option.get("isCorrect") is True
        correct_index = next((i for i, op in enumerate(options) if op.get("isCorrect") is True), None)
        feedback[qid] = {
            "is_correct": is_correct,
            "rationale": selected_option.get("rationale", ""),
            "selected_index": selected,
            "correct_index": correct_index,
        }
        if is_correct:
            correct += 1
    return feedback, feedback, correct, total


@router.post("/{encontro_id}/submit")
def submit_quiz(
    encontro_id: int,
    payload: QuizSubmitRequest,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
    course_slug: str | None = Query(None),
):
    slug = _resolve_course_slug(user, db, course_slug)
    quiz = db.quiz.find_one({"encontro": encontro_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz nao encontrado para este encontro")
    progress = db.progress.find_one({"user_id": user["_id"], "course_slug": slug}, {"ativo": 1, "encontros_liberados": 1})
    ativo = (progress or {}).get("ativo", 1)
    liberados = (progress or {}).get("encontros_liberados") or [1]
    if encontro_id > ativo or encontro_id not in liberados:
        raise HTTPException(status_code=403, detail="Encontro ainda nao liberado")

    all_questoes = quiz.get("questoes", [])
    total_questoes = len(all_questoes)
    existing = db.quiz_responses.find_one({"user_id": user["_id"], "encontro": encontro_id})
    existing_answers = dict((existing or {}).get("answers", {}))

    for qid, selected in (payload.answers or {}).items():
        q = next((x for x in all_questoes if str(x["id"]) == qid), None)
        if q is None:
            continue
        options = q.get("opcoes", [])
        if selected < 0 or selected >= len(options):
            raise HTTPException(status_code=400, detail=f"Resposta invalida na questao {qid}")
        existing_answers[qid] = selected

    new_feedback, _, correct, _ = _compute_feedback_for_answers(quiz, existing_answers)
    existing_feedback = (existing or {}).get("feedback", {})
    feedback = {**existing_feedback, **new_feedback}
    total = total_questoes
    submitted_at = None
    if len(existing_answers) >= total_questoes:
        submitted_at = datetime.now(timezone.utc)
    elif existing and existing.get("submitted_at") is not None:
        submitted_at = existing["submitted_at"]

    # Relatório da sessão: acertos apenas nas respostas enviadas neste request (ex.: batch de 3)
    session_answers = payload.answers or {}
    _, _, session_correct, session_total = _compute_feedback_for_answers(quiz, session_answers)
    total_answered = len(existing_answers)

    set_payload = {
        "user_id": user["_id"],
        "encontro": encontro_id,
        "answers": existing_answers,
        "score": correct,
        "total": total,
        "feedback": feedback,
    }
    if submitted_at is not None:
        set_payload["submitted_at"] = submitted_at

    db.quiz_responses.update_one(
        {"user_id": user["_id"], "encontro": encontro_id},
        {"$set": set_payload},
        upsert=True,
    )

    return {
        "answers": existing_answers,
        "score": correct,
        "total": total,
        "total_answered": total_answered,
        "feedback": feedback,
        "submitted_at": submitted_at.isoformat() if submitted_at else None,
        "session_correct": session_correct,
        "session_total": session_total,
    }
