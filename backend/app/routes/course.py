from datetime import datetime, timezone
from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from app.database import get_db
from app.deps import get_current_user
from app.utils.course_payload import payload_for_json
from app.utils.progress_liberados import recompute_liberados


COURSE_SLUG = "trilha-ia-executiva"

router = APIRouter(prefix="/api/course", tags=["course"])


def _get_total_encontros(course_payload: dict) -> int:
    total = 0
    for semana in course_payload.get("jornada_aprendizagem", []):
        total += len(semana.get("encontros", []))
    return total


def _ordered_encontro_ids(payload: dict) -> list:
    ids = []
    for semana in (payload.get("jornada_aprendizagem") or []):
        for enc in (semana.get("encontros") or []):
            ids.append(enc["id"])
    return ids


def _progress_with_quiz_effect(db: Database, user_id, payload: dict, progress: dict) -> Tuple[list, int]:
    """Concluídos efetivos = concluídos (conclusão não exige quiz). ativo_efetivo = primeiro não concluído."""
    ordered_ids = _ordered_encontro_ids(payload)
    if not ordered_ids:
        return [], 1
    concluidos = set(progress.get("concluidos") or [])
    concluidos_efetivos = [eid for eid in ordered_ids if eid in concluidos]
    ativo_efetivo = None
    for eid in ordered_ids:
        if eid not in concluidos:
            ativo_efetivo = eid
            break
    if ativo_efetivo is None:
        ativo_efetivo = max(ordered_ids) + 1
    return concluidos_efetivos, ativo_efetivo


def _get_or_create_progress(db: Database, user_id, course_slug: str, total: int):
    progress = db.progress.find_one({"user_id": user_id, "course_slug": course_slug})
    if progress:
        needs_patch = "material_checks" not in progress or "encontro_conclusoes" not in progress
        if needs_patch:
            db.progress.update_one(
                {"_id": progress["_id"]},
                {"$set": {"material_checks": progress.get("material_checks", {}), "encontro_conclusoes": progress.get("encontro_conclusoes", {})}},
            )
            progress["material_checks"] = progress.get("material_checks", {})
            progress["encontro_conclusoes"] = progress.get("encontro_conclusoes", {})
        return progress

    progress = {
        "user_id": user_id,
        "course_slug": course_slug,
        "concluidos": [],
        "ativo": 1,
        "total": total,
        "encontros_liberados": [1],
        "material_checks": {},
        "encontro_conclusoes": {},
        "updated_at": datetime.now(timezone.utc),
    }
    db.progress.insert_one(progress)
    return progress


def _user_has_course(user: dict, slug: str, db: Database) -> bool:
    if slug == user.get("course_slug"):
        return True
    if slug in (user.get("course_slugs") or []):
        return True
    return db.progress.find_one({"user_id": user["_id"], "course_slug": slug}) is not None


@router.get("/current")
def get_current_course(
    user=Depends(get_current_user),
    db: Database = Depends(get_db),
    course_slug: str | None = Query(None, description="Trilha a exibir (slug). Se omitido, usa a trilha principal do usuário."),
):
    chosen = course_slug
    if not chosen:
        chosen = user.get("course_slug") or ((user.get("course_slugs") or [])[0] if (user.get("course_slugs")) else None) or COURSE_SLUG
    elif not _user_has_course(user, chosen, db):
        raise HTTPException(status_code=403, detail="Voce nao tem acesso a esta trilha")
    course_slug = chosen
    course = db.courses.find_one({"slug": course_slug})
    if not course:
        raise HTTPException(status_code=404, detail="Curso nao encontrado")

    payload = course["programa_formacao_executiva"]
    total = _get_total_encontros(payload)
    progress = _get_or_create_progress(db, user["_id"], course_slug, total)
    concluidos_efetivos, ativo_efetivo = _progress_with_quiz_effect(
        db, user["_id"], payload, progress
    )
    # Ao listar: incluir encontros liberados pela regra (materiais) além dos liberados pelo admin
    liberados_stored = list(progress.get("encontros_liberados") or [1])
    liberados_regra = recompute_liberados(payload, progress)
    liberados_final = sorted(set(liberados_stored) | set(liberados_regra))
    if liberados_final != liberados_stored:
        db.progress.update_one(
            {"user_id": user["_id"], "course_slug": course_slug},
            {"$set": {"encontros_liberados": liberados_final, "updated_at": datetime.now(timezone.utc)}},
        )

    encontros_com_quiz = {q["encontro"] for q in db.quiz.find({}, {"encontro": 1})}
    quiz_respondidos = {
        r["encontro"] for r in db.quiz_responses.find({"user_id": user["_id"]}, {"encontro": 1})
    }
    ordered_ids = _ordered_encontro_ids(payload)
    quiz_por_encontro = {}
    for eid in ordered_ids:
        quiz_por_encontro[str(eid)] = {
            "tem_quiz": eid in encontros_com_quiz,
            "respondido": eid in quiz_respondidos,
        }

    return {
        "course_slug": course_slug,
        "programa_formacao_executiva": payload_for_json(payload),
        "progress": {
            "concluidos": progress["concluidos"],
            "ativo": progress["ativo"],
            "total": progress["total"],
            "concluidos_efetivos": concluidos_efetivos,
            "ativo_efetivo": ativo_efetivo,
            "encontros_liberados": liberados_final,
            "material_checks": progress.get("material_checks", {}),
            "encontro_conclusoes": progress.get("encontro_conclusoes", {}),
            "encontro_agendas": progress.get("encontro_agendas", {}),
            "quiz_por_encontro": quiz_por_encontro,
        },
    }
