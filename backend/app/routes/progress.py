from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from app.database import get_db
from app.deps import get_verified_user
from app.routes.course import COURSE_SLUG, _user_has_course
from app.schemas import CompleteProgressResponse, MaterialCheckRequest
from app.utils.progress_liberados import find_encontro, recompute_liberados


def _resolve_course_slug(user: dict, db: Database, slug_param: str | None) -> str:
    if slug_param:
        if not _user_has_course(user, slug_param, db):
            raise HTTPException(status_code=403, detail="Voce nao tem acesso a esta trilha")
        return slug_param
    return user.get("course_slug") or ((user.get("course_slugs") or [])[0] if (user.get("course_slugs")) else None) or COURSE_SLUG


router = APIRouter(prefix="/api/progress", tags=["progress"])


def _max_encontro_id(course_payload: dict) -> int:
    max_id = 0
    for semana in course_payload.get("jornada_aprendizagem", []):
        for encontro in semana.get("encontros", []):
            max_id = max(max_id, int(encontro["id"]))
    return max_id


def _ensure_progress(progress: dict | None, user_id, max_id: int, course_slug: str = COURSE_SLUG):
    now = datetime.now(timezone.utc)
    if progress:
        progress["material_checks"] = progress.get("material_checks", {})
        progress["encontro_conclusoes"] = progress.get("encontro_conclusoes", {})
        if "encontros_liberados" not in progress:
            progress["encontros_liberados"] = progress.get("encontros_liberados") or [1]
        return progress
    return {
        "user_id": user_id,
        "course_slug": course_slug,
        "concluidos": [],
        "ativo": 1,
        "total": max_id,
        "encontros_liberados": [1],
        "material_checks": {},
        "encontro_conclusoes": {},
        "updated_at": now,
    }


def _serialize_progress(progress: dict):
    material_checks = {}
    for enc_id, marks in (progress.get("material_checks") or {}).items():
        material_checks[str(enc_id)] = {}
        for mat_idx, dt in (marks or {}).items():
            material_checks[str(enc_id)][str(mat_idx)] = dt.isoformat() if isinstance(dt, datetime) else str(dt)

    encontro_conclusoes = {}
    for enc_id, dt in (progress.get("encontro_conclusoes") or {}).items():
        encontro_conclusoes[str(enc_id)] = dt.isoformat() if isinstance(dt, datetime) else str(dt)

    return {
        "concluidos": progress["concluidos"],
        "ativo": progress["ativo"],
        "total": progress["total"],
        "encontros_liberados": progress.get("encontros_liberados", [1]),
        "material_checks": material_checks,
        "encontro_conclusoes": encontro_conclusoes,
    }


@router.post("/material")
def update_material_check(payload: MaterialCheckRequest, user=Depends(get_verified_user), db: Database = Depends(get_db)):
    course_slug = _resolve_course_slug(user, db, payload.course_slug)
    course = db.courses.find_one({"slug": course_slug})
    if not course:
        raise HTTPException(status_code=404, detail="Curso nao encontrado")

    course_payload = course["programa_formacao_executiva"]
    encontro = find_encontro(course_payload, payload.encontro_id)
    if not encontro:
        raise HTTPException(status_code=400, detail="Encontro invalido")

    materials = encontro.get("material_suporte", [])
    if payload.material_index < 0 or payload.material_index >= len(materials):
        raise HTTPException(status_code=400, detail="Material invalido")

    progress = db.progress.find_one({"user_id": user["_id"], "course_slug": course_slug})
    progress = _ensure_progress(progress, user["_id"], _max_encontro_id(course_payload), course_slug)

    enc_key = str(payload.encontro_id)
    mat_key = str(payload.material_index)
    checks = progress.get("material_checks", {})
    checks.setdefault(enc_key, {})

    if payload.checked:
        checks[enc_key][mat_key] = datetime.now(timezone.utc)
    else:
        checks[enc_key].pop(mat_key, None)
        if not checks[enc_key]:
            checks.pop(enc_key, None)

    progress["material_checks"] = checks
    # União: regra automática (materiais) + encontros já liberados (ex.: pelo admin)
    liberados_regra = set(recompute_liberados(course_payload, progress))
    liberados_existentes = set(progress.get("encontros_liberados") or [1])
    progress["encontros_liberados"] = sorted(liberados_regra | liberados_existentes)
    progress["updated_at"] = datetime.now(timezone.utc)

    db.progress.update_one(
        {"user_id": user["_id"], "course_slug": course_slug},
        {
            "$set": {
                "concluidos": progress["concluidos"],
                "ativo": progress["ativo"],
                "total": progress["total"],
                "material_checks": progress["material_checks"],
                "encontros_liberados": progress["encontros_liberados"],
                "encontro_conclusoes": progress["encontro_conclusoes"],
                "updated_at": progress["updated_at"],
            }
        },
        upsert=True,
    )

    return _serialize_progress(progress)


@router.post("/complete/{encontro_id}", response_model=CompleteProgressResponse)
def complete_encontro(
    encontro_id: int,
    user=Depends(get_verified_user),
    db: Database = Depends(get_db),
    course_slug: str | None = Query(None, description="Trilha (slug). Se omitido, usa a trilha principal do usuário."),
):
    course_slug = _resolve_course_slug(user, db, course_slug)
    course = db.courses.find_one({"slug": course_slug})
    if not course:
        raise HTTPException(status_code=404, detail="Curso nao encontrado")

    payload = course["programa_formacao_executiva"]
    max_id = _max_encontro_id(payload)
    if encontro_id < 1 or encontro_id > max_id:
        raise HTTPException(status_code=400, detail="Encontro invalido")

    progress = db.progress.find_one({"user_id": user["_id"], "course_slug": course_slug})
    progress = _ensure_progress(progress, user["_id"], max_id, course_slug)

    if encontro_id in progress["concluidos"]:
        return _serialize_progress(progress)

    if encontro_id != progress["ativo"]:
        raise HTTPException(status_code=400, detail="Conclua o encontro ativo primeiro")

    liberados = progress.get("encontros_liberados") or [1]
    if encontro_id not in liberados:
        raise HTTPException(
            status_code=403,
            detail="Este encontro ainda nao foi liberado para voce. Aguarde a liberacao pelo administrador.",
        )

    encontro = find_encontro(payload, encontro_id)
    if not encontro:
        raise HTTPException(status_code=400, detail="Encontro invalido")

    material_total = len(encontro.get("material_suporte", []))
    checked_count = len((progress.get("material_checks", {}).get(str(encontro_id), {})))
    if checked_count < material_total:
        raise HTTPException(status_code=400, detail="Marque todos os materiais antes de concluir")

    concluidos = sorted(progress["concluidos"] + [encontro_id])
    novo_ativo = min(encontro_id + 1, progress["total"])
    now = datetime.now(timezone.utc)
    encontro_conclusoes = progress.get("encontro_conclusoes", {})
    encontro_conclusoes[str(encontro_id)] = now

    # Liberar o próximo encontro na sequência (disponível apenas após concluir o atual)
    liberados = list(progress.get("encontros_liberados") or [1])
    proximo_id = encontro_id + 1
    if proximo_id <= progress["total"] and proximo_id not in liberados:
        liberados.append(proximo_id)
        liberados.sort()

    progress["concluidos"] = concluidos
    progress["ativo"] = novo_ativo
    progress["encontros_liberados"] = liberados
    progress["encontro_conclusoes"] = encontro_conclusoes
    progress["updated_at"] = now

    db.progress.update_one(
        {"user_id": user["_id"], "course_slug": course_slug},
        {
            "$set": {
                "concluidos": progress["concluidos"],
                "ativo": progress["ativo"],
                "encontros_liberados": progress["encontros_liberados"],
                "total": progress["total"],
                "material_checks": progress["material_checks"],
                "encontro_conclusoes": progress["encontro_conclusoes"],
                "updated_at": progress["updated_at"],
            }
        },
        upsert=True,
    )

    return _serialize_progress(progress)
