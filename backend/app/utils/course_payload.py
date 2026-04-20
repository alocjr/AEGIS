"""Utilitários para o payload do programa (programa_formacao_executiva)."""
import copy

from bson import ObjectId


def payload_for_json(payload: dict) -> dict:
    """Cópia do payload com ObjectId (ex.: quiz_id nos encontros) convertidos para string (JSON)."""
    out = copy.deepcopy(payload)
    for semana in (out.get("jornada_aprendizagem") or []):
        for enc in (semana.get("encontros") or []):
            qid = enc.get("quiz_id")
            if isinstance(qid, ObjectId):
                enc["quiz_id"] = str(qid)
    return out
