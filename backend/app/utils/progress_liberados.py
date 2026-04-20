"""Regras de liberação de encontros: primeiro sempre liberado; próximo só quando todos os materiais do anterior estiverem marcados."""


def ordered_encontro_ids(course_payload: dict) -> list:
    ids = []
    for semana in (course_payload.get("jornada_aprendizagem") or []):
        for enc in (semana.get("encontros") or []):
            ids.append(int(enc["id"]))
    return sorted(ids)


def find_encontro(course_payload: dict, encontro_id: int) -> dict | None:
    for semana in course_payload.get("jornada_aprendizagem", []):
        for encontro in semana.get("encontros", []):
            if int(encontro["id"]) == encontro_id:
                return encontro
    return None


def recompute_liberados(course_payload: dict, progress: dict) -> list:
    """Primeiro encontro sempre liberado; próximo só quando todos os materiais do anterior estiverem marcados."""
    ordered = ordered_encontro_ids(course_payload)
    if not ordered:
        return [1]
    liberados = [ordered[0]]
    for i in range(1, len(ordered)):
        prev_id = ordered[i - 1]
        enc = find_encontro(course_payload, prev_id)
        if not enc:
            continue
        total_mat = len(enc.get("material_suporte", []))
        checks = (progress.get("material_checks") or {}).get(str(prev_id), {})
        if total_mat > 0 and len(checks) < total_mat:
            break
        liberados.append(ordered[i])
    return sorted(liberados)
