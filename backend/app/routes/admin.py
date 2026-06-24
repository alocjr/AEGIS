import copy
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.database import get_db
from app.deps import get_current_admin
from app.routes.course import COURSE_SLUG, _progress_with_quiz_effect
from app.utils.course_payload import payload_for_json
from app.utils.progress_liberados import ordered_encontro_ids
from app.schemas import (
    AdminCreateCourseRequest,
    AdminCreateUserRequest,
    AdminQuizCreateUpdateRequest,
    AdminUpdateCourseRequest,
    AdminUpdateProgressRequest,
    AdminUpdateUserRequest,
    LiberarEncontroRequest,
)
from app.security import hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _course_to_list_item(course: dict) -> dict:
    cab = (course.get("programa_formacao_executiva") or {}).get("cabecalho") or {}
    return {
        "slug": course.get("slug"),
        "titulo": cab.get("titulo", course.get("slug", "")),
        "tema": cab.get("tema", ""),
    }


@router.get("/courses")
def list_courses(admin=Depends(get_current_admin), db: Database = Depends(get_db)):
    """Lista todas as trilhas (cursos). Apenas admin."""
    courses = list(db.courses.find({}, {"slug": 1, "programa_formacao_executiva.cabecalho": 1}))
    return [_course_to_list_item(c) for c in courses]


@router.get("/courses/{slug}")
def get_course(slug: str, admin=Depends(get_current_admin), db: Database = Depends(get_db)):
    """Retorna uma trilha pelo slug. Apenas admin."""
    course = db.courses.find_one({"slug": slug})
    if not course:
        raise HTTPException(status_code=404, detail="Trilha nao encontrada")
    payload = course.get("programa_formacao_executiva") or {}
    return {"slug": course["slug"], "programa_formacao_executiva": payload_for_json(payload)}


@router.post("/courses")
def create_course(
    body: AdminCreateCourseRequest,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Cria uma nova trilha. Apenas admin."""
    slug = body.slug.strip()
    if not slug:
        raise HTTPException(status_code=400, detail="slug e obrigatorio")
    if db.courses.find_one({"slug": slug}):
        raise HTTPException(status_code=400, detail="Ja existe uma trilha com este slug")
    payload = body.programa_formacao_executiva or {}
    db.courses.insert_one({"slug": slug, "programa_formacao_executiva": payload})
    return {"slug": slug, "message": "Trilha criada"}


def _fill_quiz_ids_in_payload(db: Database, payload: dict) -> dict:
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


@router.put("/courses/{slug}")
def update_course(
    slug: str,
    body: AdminUpdateCourseRequest,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Atualiza uma trilha existente. Apenas admin. Preserva/preenche quiz_id em cada encontro."""
    course = db.courses.find_one({"slug": slug})
    if not course:
        raise HTTPException(status_code=404, detail="Trilha nao encontrada")
    payload = _fill_quiz_ids_in_payload(db, body.programa_formacao_executiva)
    db.courses.update_one(
        {"slug": slug},
        {"$set": {"programa_formacao_executiva": payload}},
    )
    return {"slug": slug, "message": "Trilha atualizada"}


@router.delete("/courses/{slug}")
def delete_course(slug: str, admin=Depends(get_current_admin), db: Database = Depends(get_db)):
    """Remove uma trilha. Apenas admin."""
    result = db.courses.delete_one({"slug": slug})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Trilha nao encontrada")
    return {"slug": slug, "message": "Trilha removida"}


def _get_total_encontros(course_payload: dict) -> int:
    total = 0
    for semana in course_payload.get("jornada_aprendizagem", []):
        total += len(semana.get("encontros", []))
    return total


def _get_total_materiais(course_payload: dict) -> int:
    total = 0
    for semana in course_payload.get("jornada_aprendizagem", []):
        for enc in semana.get("encontros", []):
            total += len(enc.get("material_suporte", []))
    return total


@router.get("/dashboard")
def get_dashboard(admin=Depends(get_current_admin), db: Database = Depends(get_db)):
    """Lista alunos com progresso (encontros, material, quiz) e data do próximo encontro. Ordenado pela data do próximo encontro (mais próximo primeiro). Apenas admin."""
    users = list(
        db.users.find(
            {"$or": [{"is_admin": {"$ne": True}}, {"is_admin": {"$exists": False}}]},
            {"_id": 1, "name": 1, "email": 1, "course_slug": 1, "course_slugs": 1, "phone": 1},
        )
    )
    progress_by_user_slug = {(p["user_id"], p["course_slug"]): p for p in db.progress.find({})}
    quiz_count = db.quiz.count_documents({})
    quiz_responses_by_user: dict = {}
    for r in db.quiz_responses.aggregate([{"$group": {"_id": "$user_id", "count": {"$sum": 1}}}]):
        quiz_responses_by_user[r["_id"]] = r["count"]

    maturity_responded_user_ids = set()
    for doc in db.maturity_responses.find({}, {"user_id": 1}):
        maturity_responded_user_ids.add(doc["user_id"])

    courses_cache: dict = {}  # slug -> (pfe, titulo)
    rows = []
    for u in users:
        uid = u["_id"]
        primary_slug = (u.get("course_slugs") or [u.get("course_slug")])[0] if (u.get("course_slugs") or u.get("course_slug")) else u.get("course_slug") or ""
        progress = progress_by_user_slug.get((uid, primary_slug)) or {}
        course_slug = progress.get("course_slug") or primary_slug
        concluidos = progress.get("concluidos") or []
        ativo = progress.get("ativo") or 1
        total_enc = progress.get("total") or 0
        material_checks = progress.get("material_checks") or {}
        encontro_agendas = progress.get("encontro_agendas") or {}

        if course_slug not in courses_cache:
            course = db.courses.find_one({"slug": course_slug})
            pfe = (course or {}).get("programa_formacao_executiva") or {}
            cab = (pfe or {}).get("cabecalho") or {}
            titulo = cab.get("titulo", course_slug or "—")
            courses_cache[course_slug] = (pfe, titulo)
        pfe, course_titulo = courses_cache[course_slug]
        total_materiais = _get_total_materiais(pfe) if pfe else 0
        material_checked = sum(len(v) if isinstance(v, dict) else 0 for v in material_checks.values())

        quiz_done = quiz_responses_by_user.get(uid, 0)
        maturity_done = 1 if uid in maturity_responded_user_ids else 0
        maturity_total = 1

        next_iso = encontro_agendas.get(str(ativo)) if ativo else None
        next_ts = None
        if next_iso:
            try:
                s = next_iso.replace("Z", "+00:00")
                next_ts = datetime.fromisoformat(s).timestamp()
            except Exception:
                pass

        rows.append({
            "id": str(uid),
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "phone": u.get("phone") or "",
            "course_slug": course_slug,
            "course_titulo": course_titulo,
            "encontros_done": len(concluidos),
            "encontros_total": total_enc,
            "material_checked": material_checked,
            "material_total": total_materiais,
            "quiz_done": quiz_done,
            "quiz_total": quiz_count,
            "maturity_done": maturity_done,
            "maturity_total": maturity_total,
            "next_meeting_iso": next_iso,
            "_next_ts": next_ts,
        })

    rows.sort(key=lambda x: (x["_next_ts"] is None, x["_next_ts"] or 0))
    for r in rows:
        del r["_next_ts"]

    return rows


@router.post("/users")
def create_user(
    payload: AdminCreateUserRequest,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Cria um novo usuário com uma ou mais trilhas e opcionalmente datas por encontro. Apenas admin."""
    email = payload.email.strip().lower()
    if db.users.find_one({"email": email}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")

    course_slugs = [s.strip() for s in payload.course_slugs if s and s.strip()]
    if not course_slugs:
        raise HTTPException(status_code=400, detail="Informe ao menos uma trilha")
    for slug in course_slugs:
        if not db.courses.find_one({"slug": slug}):
            raise HTTPException(status_code=404, detail=f"Trilha nao encontrada: {slug}")

    now = datetime.now(timezone.utc)
    user_doc = {
        "name": payload.name.strip(),
        "email": email,
        "password_hash": hash_password(payload.password),
        "course_slug": course_slugs[0],
        "course_slugs": course_slugs,
        "created_at": now,
        "updated_at": now,
        "email_verified": True,
    }
    if payload.phone is not None and payload.phone.strip():
        user_doc["phone"] = payload.phone.strip()
    result = db.users.insert_one(user_doc)
    user_id = result.inserted_id

    encontro_agendas = payload.encontro_agendas or {}
    for i, course_slug in enumerate(course_slugs):
        course = db.courses.find_one({"slug": course_slug})
        payload_pfe = (course or {}).get("programa_formacao_executiva") or {}
        total = _get_total_encontros(payload_pfe)
        progress_doc = {
            "user_id": user_id,
            "course_slug": course_slug,
            "concluidos": [],
            "ativo": 1,
            "total": total,
            "encontros_liberados": [1],
            "material_checks": {},
            "encontro_conclusoes": {},
            "encontro_agendas": encontro_agendas if i == 0 else {},
            "updated_at": now,
        }
        db.progress.insert_one(progress_doc)

    return {
        "message": "Usuario criado",
        "user_id": str(user_id),
        "email": email,
        "course_slugs": course_slugs,
    }


def _serialize_created_at(doc: dict) -> str | None:
    """Serializa created_at para JSON (datetime -> isoformat ou None)."""
    val = doc.get("created_at")
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None


@router.get("/users")
def list_users(admin=Depends(get_current_admin), db: Database = Depends(get_db)):
    """Lista todos os usuários (alunos). Apenas admin."""
    users = list(
        db.users.find(
            {},
            {"_id": 1, "name": 1, "email": 1, "course_slug": 1, "course_slugs": 1, "is_admin": 1, "created_at": 1, "phone": 1},
        )
    )
    out = []
    for u in users:
        slugs = u.get("course_slugs") or ([u.get("course_slug")] if u.get("course_slug") else [])
        out.append({
            "id": str(u["_id"]),
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "phone": u.get("phone") or "",
            "course_slug": slugs[0] if slugs else u.get("course_slug", ""),
            "course_slugs": slugs,
            "is_admin": u.get("is_admin", False),
            "created_at": _serialize_created_at(u),
        })
    return out


@router.get("/users/{user_id}")
def get_user(user_id: str, admin=Depends(get_current_admin), db: Database = Depends(get_db)):
    """Retorna um usuário para edição (sem senha). Apenas admin."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    user = db.users.find_one({"_id": ObjectId(user_id)}, {"password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    slugs = user.get("course_slugs") or ([user.get("course_slug")] if user.get("course_slug") else [])
    progress = db.progress.find_one(
        {"user_id": ObjectId(user_id)},
        {"course_slug": 1, "encontro_agendas": 1},
    )
    return {
        "id": str(user["_id"]),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone") or "",
        "course_slug": slugs[0] if slugs else user.get("course_slug", ""),
        "course_slugs": slugs,
        "is_admin": user.get("is_admin", False),
        "created_at": _serialize_created_at(user),
        "encontro_agendas": progress.get("encontro_agendas", {}) if progress else {},
    }


@router.put("/users/{user_id}")
def update_user(
    user_id: str,
    payload: AdminUpdateUserRequest,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Atualiza um usuário. Apenas admin."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    uid = ObjectId(user_id)
    user = db.users.find_one({"_id": uid})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    updates = {"updated_at": datetime.now(timezone.utc)}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.email is not None:
        email = payload.email.strip().lower()
        other = db.users.find_one({"email": email, "_id": {"$ne": uid}})
        if other:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja em uso")
        updates["email"] = email
    if payload.password is not None and payload.password.strip():
        updates["password_hash"] = hash_password(payload.password)
    if payload.course_slugs is not None:
        course_slugs = [s.strip() for s in payload.course_slugs if s and s.strip()]
        if not course_slugs:
            raise HTTPException(status_code=400, detail="Informe ao menos uma trilha")
        for slug in course_slugs:
            if not db.courses.find_one({"slug": slug}):
                raise HTTPException(status_code=404, detail=f"Trilha nao encontrada: {slug}")
        updates["course_slug"] = course_slugs[0]
        updates["course_slugs"] = course_slugs
    if payload.phone is not None:
        updates["phone"] = payload.phone.strip() if payload.phone.strip() else ""
    if payload.is_admin is not None:
        updates["is_admin"] = payload.is_admin

    if updates:
        db.users.update_one({"_id": uid}, {"$set": updates})

    if payload.course_slugs is not None:
        now = datetime.now(timezone.utc)
        for course_slug in course_slugs:
            existing = db.progress.find_one({"user_id": uid, "course_slug": course_slug})
            if not existing:
                course = db.courses.find_one({"slug": course_slug})
                payload_pfe = (course or {}).get("programa_formacao_executiva") or {}
                total = _get_total_encontros(payload_pfe)
                db.progress.insert_one({
                    "user_id": uid,
                    "course_slug": course_slug,
                    "concluidos": [],
                    "ativo": 1,
                    "total": total,
                    "encontros_liberados": [1],
                    "material_checks": {},
                    "encontro_conclusoes": {},
                    "encontro_agendas": {},
                    "updated_at": now,
                })

    if payload.encontro_agendas is not None:
        first_slug = None
        if payload.course_slugs is not None and course_slugs:
            first_slug = course_slugs[0]
        else:
            u = db.users.find_one({"_id": uid}, {"course_slugs": 1, "course_slug": 1})
            slugs = (u or {}).get("course_slugs") or ([u.get("course_slug")] if (u or {}).get("course_slug") else [])
            first_slug = slugs[0] if slugs else None
        if first_slug:
            db.progress.update_one(
                {"user_id": uid, "course_slug": first_slug},
                {"$set": {"encontro_agendas": payload.encontro_agendas, "updated_at": datetime.now(timezone.utc)}},
            )

    return {"message": "Usuario atualizado", "id": user_id}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Remove um usuário e seu progresso. O admin não pode excluir a si mesmo. Apenas admin."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    uid = ObjectId(user_id)
    if uid == admin["_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao e possivel excluir seu proprio usuario",
        )
    user = db.users.find_one({"_id": uid})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    db.users.delete_one({"_id": uid})
    db.progress.delete_many({"user_id": uid})
    db.quiz_responses.delete_many({"user_id": uid})
    db.maturity_responses.delete_many({"user_id": uid})
    return {"message": "Usuario excluido", "id": user_id}


@router.get("/users/{user_id}/course-and-progress")
def get_user_course_and_progress(
    user_id: str,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
    course_slug: str | None = None,
):
    """Retorna curso e progresso do aluno para visualização pelo admin. Apenas admin. Opcional: ?course_slug= para uma trilha específica."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    uid = ObjectId(user_id)
    user = db.users.find_one({"_id": uid}, {"course_slug": 1, "course_slugs": 1, "name": 1, "email": 1})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    slugs = user.get("course_slugs") or ([user.get("course_slug")] if user.get("course_slug") else [])
    if course_slug:
        if course_slug not in slugs and not db.progress.find_one({"user_id": uid, "course_slug": course_slug}):
            raise HTTPException(status_code=404, detail="Trilha nao encontrada para este usuario")
    else:
        course_slug = slugs[0] if slugs else user.get("course_slug") or COURSE_SLUG
    course = db.courses.find_one({"slug": course_slug})
    if not course:
        raise HTTPException(status_code=404, detail="Trilha do aluno nao encontrada")
    payload = course.get("programa_formacao_executiva") or {}
    total = _get_total_encontros(payload)
    progress = db.progress.find_one({"user_id": uid, "course_slug": course_slug})
    if not progress:
        progress = {
            "user_id": uid,
            "course_slug": course_slug,
            "concluidos": [],
            "ativo": 1,
            "total": total,
            "encontros_liberados": [1],
            "material_checks": {},
            "encontro_conclusoes": {},
            "encontro_agendas": {},
        }
    concluidos_efetivos, ativo_efetivo = _progress_with_quiz_effect(db, uid, payload, progress)

    materiais_por_encontro = {}
    for semana in (payload.get("jornada_aprendizagem") or []):
        for enc in (semana.get("encontros") or []):
            eid = enc.get("id")
            if eid is not None:
                materiais_por_encontro[str(eid)] = len(enc.get("material_suporte", []))

    encontros_com_quiz = {q["encontro"] for q in db.quiz.find({}, {"encontro": 1})}
    quiz_responses_data = {
        r["encontro"]: {"score": r.get("score"), "total": r.get("total")}
        for r in db.quiz_responses.find(
            {"user_id": uid},
            {"encontro": 1, "score": 1, "total": 1},
        )
    }
    quiz_por_encontro = {}
    for eid in set(materiais_por_encontro.keys()) | encontros_com_quiz:
        eid_int = int(eid) if isinstance(eid, str) and eid.isdigit() else eid
        resp = quiz_responses_data.get(eid_int, {})
        quiz_por_encontro[str(eid)] = {
            "tem_quiz": eid_int in encontros_com_quiz,
            "respondido": eid_int in quiz_responses_data,
            "score": resp.get("score"),
            "total": resp.get("total"),
        }

    return {
        "user": {"id": user_id, "name": user.get("name", ""), "email": user.get("email", "")},
        "course_slug": course_slug,
        "programa_formacao_executiva": payload_for_json(payload),
        "materiais_por_encontro": materiais_por_encontro,
        "quiz_por_encontro": quiz_por_encontro,
        "progress": {
            "concluidos": progress.get("concluidos", []),
            "ativo": progress.get("ativo", 1),
            "total": progress.get("total", total),
            "concluidos_efetivos": concluidos_efetivos,
            "ativo_efetivo": ativo_efetivo,
            "encontros_liberados": progress.get("encontros_liberados", [1]),
            "material_checks": progress.get("material_checks", {}),
            "encontro_conclusoes": progress.get("encontro_conclusoes", {}),
            "encontro_agendas": progress.get("encontro_agendas", {}),
        },
    }


@router.post("/users/{user_id}/liberar-encontro")
def liberar_encontro(
    user_id: str,
    body: LiberarEncontroRequest,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Libera um encontro para o aluno. Apenas admin."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    uid = ObjectId(user_id)
    user = db.users.find_one({"_id": uid}, {"course_slug": 1})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    encontro_id = body.encontro_id
    course_slug = user.get("course_slug") or COURSE_SLUG
    course = db.courses.find_one({"slug": course_slug})
    if not course:
        raise HTTPException(status_code=404, detail="Trilha do aluno nao encontrada")
    payload = course.get("programa_formacao_executiva") or {}
    max_id = 0
    for semana in (payload.get("jornada_aprendizagem") or []):
        for enc in (semana.get("encontros") or []):
            max_id = max(max_id, int(enc.get("id", 0)))
    if encontro_id < 1 or encontro_id > max_id:
        raise HTTPException(status_code=400, detail="Encontro invalido")
    progress = db.progress.find_one({"user_id": uid, "course_slug": course_slug})
    if not progress:
        progress = {
            "user_id": uid,
            "course_slug": course_slug,
            "concluidos": [],
            "ativo": 1,
            "total": max_id,
            "encontros_liberados": [1],
            "material_checks": {},
            "encontro_conclusoes": {},
            "encontro_agendas": {},
            "updated_at": datetime.now(timezone.utc),
        }
        db.progress.insert_one(progress)
    # Admin pode liberar qualquer encontro sem obedecer regra de materiais
    liberados = list(progress.get("encontros_liberados") or [1])
    if encontro_id not in liberados:
        liberados.append(encontro_id)
        liberados.sort()
        db.progress.update_one(
            {"user_id": uid, "course_slug": course_slug},
            {"$set": {"encontros_liberados": liberados, "updated_at": datetime.now(timezone.utc)}},
        )
    return {"message": "Encontro liberado", "user_id": user_id, "encontro_id": encontro_id}


@router.patch("/users/{user_id}/progress")
def update_user_progress(
    user_id: str,
    payload: AdminUpdateProgressRequest,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Atualiza o progresso do aluno para uma trilha (ex.: datas dos encontros). Apenas admin."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    uid = ObjectId(user_id)
    if not db.users.find_one({"_id": uid}):
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    course_slug = payload.course_slug.strip()
    if not db.courses.find_one({"slug": course_slug}):
        raise HTTPException(status_code=404, detail="Trilha nao encontrada")
    progress = db.progress.find_one({"user_id": uid, "course_slug": course_slug})
    if not progress:
        raise HTTPException(status_code=404, detail="Progresso nao encontrado para esta trilha")
    # Normalize keys to string and validate ISO-like values
    agendas = {}
    for k, v in (payload.encontro_agendas or {}).items():
        if v and str(v).strip():
            agendas[str(k).strip()] = str(v).strip()
    db.progress.update_one(
        {"user_id": uid, "course_slug": course_slug},
        {"$set": {"encontro_agendas": agendas, "updated_at": datetime.now(timezone.utc)}},
    )
    return {"message": "Progresso atualizado", "encontro_agendas": agendas}


# --- Quiz (admin) ---


def _quiz_to_list_item(q: dict) -> dict:
    return {
        "encontro": q["encontro"],
        "titulo": q.get("titulo", f"Quiz Encontro {q['encontro']}"),
        "total": len(q.get("questoes", [])),
    }


def _set_quiz_id_in_payload(payload: dict, encontro_id: int, quiz_oid: ObjectId | None) -> None:
    """Atualiza in-place cada encontro com id == encontro_id, definindo ou removendo quiz_id."""
    for semana in (payload.get("jornada_aprendizagem") or []):
        for enc in (semana.get("encontros") or []):
            if int(enc.get("id", 0)) == encontro_id:
                if quiz_oid is not None:
                    enc["quiz_id"] = quiz_oid
                else:
                    enc.pop("quiz_id", None)


def _sync_quiz_id_in_courses(db: Database, encontro_id: int, quiz_oid: ObjectId | None) -> None:
    """Atualiza em todos os cursos o encontro com id == encontro_id, definindo quiz_id (ou removendo)."""
    for course in db.courses.find({}, {"slug": 1, "programa_formacao_executiva": 1}):
        pfe = (course.get("programa_formacao_executiva") or {})
        if encontro_id not in ordered_encontro_ids(pfe):
            continue
        payload = copy.deepcopy(pfe)
        _set_quiz_id_in_payload(payload, encontro_id, quiz_oid)
        db.courses.update_one(
            {"slug": course["slug"]},
            {"$set": {"programa_formacao_executiva": payload}},
        )


@router.get("/quiz")
def list_quizzes_admin(
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Lista todos os quizzes agrupados por trilha (course). Apenas admin."""
    quizzes = list(db.quiz.find({}, {"encontro": 1, "titulo": 1, "questoes": 1}))
    quiz_items = [_quiz_to_list_item(q) for q in sorted(quizzes, key=lambda x: x["encontro"])]
    encontro_to_quiz = {q["encontro"]: q for q in quiz_items}

    courses = list(db.courses.find({}, {"slug": 1, "programa_formacao_executiva": 1}))
    grouped = []
    encontros_assigned = set()

    for course in sorted(courses, key=lambda c: _course_to_list_item(c).get("titulo", c.get("slug", ""))):
        slug = course.get("slug")
        pfe = course.get("programa_formacao_executiva") or {}
        enc_ids = ordered_encontro_ids(pfe)
        trilha_quizzes = [encontro_to_quiz[eid] for eid in enc_ids if eid in encontro_to_quiz]
        for item in trilha_quizzes:
            encontros_assigned.add(item["encontro"])
        if trilha_quizzes:
            titulo = _course_to_list_item(course).get("titulo", slug or "")
            grouped.append({"course_slug": slug, "titulo": titulo, "quizzes": trilha_quizzes})

    orphan = [q for q in quiz_items if q["encontro"] not in encontros_assigned]
    if orphan:
        grouped.append({"course_slug": None, "titulo": "Sem trilha", "quizzes": orphan})

    return {"grouped": grouped}


@router.get("/quiz/{encontro_id}")
def get_quiz_admin(
    encontro_id: int,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Retorna o quiz do encontro para edição. Apenas admin."""
    quiz = db.quiz.find_one({"encontro": encontro_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz nao encontrado para este encontro")
    return {
        "encontro": quiz["encontro"],
        "titulo": quiz.get("titulo", ""),
        "questoes": quiz.get("questoes", []),
    }


@router.post("/quiz")
def create_or_update_quiz(
    body: AdminQuizCreateUpdateRequest,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Cria ou atualiza um quiz. Apenas admin. Atualiza quiz_id em cada encontro das trilhas."""
    encontro = body.encontro
    titulo = (body.titulo or "").strip() or f"Quiz Encontro {encontro}"
    doc = {
        "encontro": encontro,
        "titulo": titulo,
        "questoes": body.questoes,
    }
    db.quiz.update_one(
        {"encontro": encontro},
        {"$set": doc},
        upsert=True,
    )
    quiz = db.quiz.find_one({"encontro": encontro}, {"_id": 1})
    if quiz:
        _sync_quiz_id_in_courses(db, encontro, quiz["_id"])
    return {"message": "Quiz salvo", "encontro": encontro}


@router.delete("/quiz/{encontro_id}")
def delete_quiz(
    encontro_id: int,
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Remove o quiz do encontro. Apenas admin. Remove quiz_id dos encontros das trilhas."""
    _sync_quiz_id_in_courses(db, encontro_id, None)
    result = db.quiz.delete_one({"encontro": encontro_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Quiz nao encontrado para este encontro")
    return {"message": "Quiz removido", "encontro": encontro_id}


@router.post("/sync-quiz-ids")
def sync_quiz_ids(
    admin=Depends(get_current_admin),
    db: Database = Depends(get_db),
):
    """Sincroniza quiz_id em todos os encontros de todas as trilhas. Apenas admin."""
    updated = 0
    for course in db.courses.find({}, {"slug": 1, "programa_formacao_executiva": 1}):
        pfe = course.get("programa_formacao_executiva") or {}
        payload = _fill_quiz_ids_in_payload(db, pfe)
        db.courses.update_one(
            {"slug": course["slug"]},
            {"$set": {"programa_formacao_executiva": payload}},
        )
        updated += 1
    return {"message": "Sincronização concluída", "courses_updated": updated}
