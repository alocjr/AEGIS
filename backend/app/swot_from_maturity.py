"""Gera payload SWOT (v3) a partir de uma resposta do Modelo de Maturidade."""

from __future__ import annotations

import secrets
from typing import Any


_DIM_TO_PILLAR = {
    "strategy": "portfolio",
    "data_infra": "dados",
    "people_culture": "talento",
    "gov_risk": "governanca",
}

_TIER_LABEL = {
    "basico": "Básico",
    "completo": "Completo",
    "complementar": "Complementar",
}

_DEFAULT_PILARES = {
    "forcas": [
        {"id": "portfolio", "nome": "Estratégia e Visão"},
        {"id": "dados", "nome": "Dados e Infraestrutura"},
        {"id": "talento", "nome": "Pessoas e Cultura"},
        {"id": "governanca", "nome": "Governança e Risco"},
    ],
    "fraquezas": [
        {"id": "portfolio", "nome": "Estratégia e Visão"},
        {"id": "dados", "nome": "Dados e Infraestrutura"},
        {"id": "talento", "nome": "Pessoas e Cultura"},
        {"id": "governanca", "nome": "Governança e Risco"},
    ],
    "oportunidades": [
        {"id": "ecossistema", "nome": "Tecnologia e ecossistema"},
        {"id": "portfolio", "nome": "Mercado e clientes"},
        {"id": "governanca", "nome": "Ambiente regulatório"},
        {"id": "talento", "nome": "Talento e incentivos"},
    ],
    "ameacas": [
        {"id": "portfolio", "nome": "Concorrência"},
        {"id": "governanca", "nome": "Regulação e risco"},
        {"id": "ecossistema", "nome": "Fornecedores e modelos"},
        {"id": "talento", "nome": "Talento e ritmo"},
    ],
}

_FIELD_PREFIX = {
    "forcas": "f",
    "fraquezas": "fx",
    "oportunidades": "o",
    "ameacas": "a",
}


def _nid(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(3)}"


def _visible(question_tier: str, selected_tier: str, order: dict[str, int]) -> bool:
    return order.get(question_tier, 99) <= order.get(selected_tier, 0)


def build_swot_fields_from_maturity(
    *,
    model: dict[str, Any],
    answers: dict[str, int],
    tier: str,
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Devolve campos editáveis da SWOT preenchidos a partir do diagnóstico."""
    order = {"basico": 0, "completo": 1, "complementar": 2}
    buckets: dict[str, list[dict]] = {
        "forcas": [],
        "fraquezas": [],
        "oportunidades": [],
        "ameacas": [],
    }

    for dimension in model.get("dimensions") or []:
        dim_id = str(dimension.get("id") or "")
        dim_name = str(dimension.get("name") or dim_id)
        pilar = _DIM_TO_PILLAR.get(dim_id, "")
        for q in dimension.get("questions") or []:
            qid = str(q.get("id") or "")
            if not qid or qid not in answers:
                continue
            q_tier = str(q.get("tier") or "basico")
            if not _visible(q_tier, tier, order):
                continue
            lvl = int(answers[qid])
            if lvl < 1 or lvl > 5:
                continue
            levels = q.get("levels") or {}
            evidence = str(levels.get(str(lvl)) or levels.get(lvl) or "")[:1000]
            csf = q.get("csfId") or q.get("csf_id")
            is_external = bool(csf and str(csf).startswith("R"))
            if is_external:
                field = "oportunidades" if lvl >= 4 else "ameacas"
            else:
                field = "forcas" if lvl >= 4 else "fraquezas"
            prefix = _FIELD_PREFIX[field]
            buckets[field].append(
                {
                    "id": f"{prefix}_{qid.lower()}",
                    "texto": str(q.get("text") or qid)[:500],
                    "pilar": pilar,
                    "impacto": lvl,
                    "viabilidade": lvl if field in ("forcas", "fraquezas") else None,
                    "probabilidade": lvl if field in ("oportunidades", "ameacas") else None,
                    "evidencia": evidence,
                    "prioridade": None,
                    "_dim": dim_name,
                    "_code": qid,
                }
            )

    for field, items in buckets.items():
        items.sort(key=lambda it: it.get("_code") or "")
        for i, it in enumerate(items, start=1):
            it["prioridade"] = i
            it.pop("_dim", None)
            it.pop("_code", None)

    def pair(
        internos: list[dict],
        externos: list[dict],
        template: str,
        capacity: int,
        prefix: str,
    ) -> list[dict]:
        if not internos or not externos:
            return []
        n = min(capacity, max(len(internos), len(externos)))
        out: list[dict] = []
        seen: set[str] = set()
        for i in range(n):
            a = internos[i % len(internos)]
            b = externos[i % len(externos)]
            acao = template.format(a=a["texto"], b=b["texto"], ai=a["id"], bi=b["id"])
            if acao in seen:
                continue
            seen.add(acao)
            out.append(
                {
                    "id": _nid(prefix),
                    "acao": acao[:1000],
                    "dono": "",
                    "horizonte": "",
                    "itens_internos": [a["id"]],
                    "itens_externos": [b["id"]],
                }
            )
        return out

    tows_fo = pair(
        buckets["forcas"],
        buckets["oportunidades"],
        "Usar «{a}» ({ai}) para aproveitar «{b}» ({bi}).",
        4,
        "fo",
    )
    tows_fa = pair(
        buckets["forcas"],
        buckets["ameacas"],
        "Usar «{a}» ({ai}) para conter o risco de «{b}» ({bi}).",
        4,
        "fa",
    )
    tows_fxo = pair(
        buckets["fraquezas"],
        buckets["oportunidades"],
        "Aproveitar «{b}» ({bi}) como janela para corrigir «{a}» ({ai}).",
        4,
        "fxo",
    )
    tows_fxa = pair(
        buckets["fraquezas"],
        buckets["ameacas"],
        "Plano defensivo: tratar «{a}» ({ai}) antes que «{b}» ({bi}) vire problema real.",
        4,
        "fxa",
    )

    result = result or {}
    level = result.get("level") or {}
    band_label = str(level.get("label") or "—")
    band_desc = str(level.get("description") or "")
    pct = float(result.get("percent_score") or 0)
    if pct >= 70:
        veredito_tipo = "executavel"
    elif pct >= 40:
        veredito_tipo = "fundacao"
    else:
        veredito_tipo = "repensar"

    total = int(result.get("total_score") or 0)
    max_score = int(result.get("max_score") or 0)
    tier_label = _TIER_LABEL.get(tier, tier)
    optica = (
        f"Estratégia de IA sustentada pelo diagnóstico de maturidade "
        f"(abrangência {tier_label}) — nível «{band_label}»."
    )[:2000]

    veredito_titulo = f"{band_label} · {total}/{max_score} pts"[:300]
    counts = (
        f"{len(buckets['forcas'])} força(s), {len(buckets['fraquezas'])} fraqueza(s), "
        f"{len(buckets['oportunidades'])} oportunidade(s) e {len(buckets['ameacas'])} ameaça(s)."
    )
    veredito_texto = (
        f"{band_desc} Gerado a partir do Modelo de Maturidade em IA. No total: {counts}"
    ).strip()[:8000]

    return {
        "optica": optica,
        "pilares": {k: [dict(s) for s in v] for k, v in _DEFAULT_PILARES.items()},
        "forcas": buckets["forcas"],
        "fraquezas": buckets["fraquezas"],
        "oportunidades": buckets["oportunidades"],
        "ameacas": buckets["ameacas"],
        "tows_fo": tows_fo,
        "tows_fa": tows_fa,
        "tows_fxo": tows_fxo,
        "tows_fxa": tows_fxa,
        "veredito_tipo": veredito_tipo,
        "veredito_titulo": veredito_titulo,
        "veredito_texto": veredito_texto,
    }
