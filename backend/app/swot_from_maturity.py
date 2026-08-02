"""Gera payload SWOT (v3) a partir do Modelo de Maturidade via swotFramework."""

from __future__ import annotations

import secrets
from typing import Any


_DIM_TO_PILLAR = {
    "strategy": "portfolio",
    "data_infra": "dados",
    "people_culture": "talento",
    "gov_risk": "governanca",
}

_DIM_ORDER = ("strategy", "data_infra", "people_culture", "gov_risk")

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
        {"id": "portfolio", "nome": "Mercado e clientes"},
        {"id": "dados", "nome": "Dados e Infraestrutura"},
        {"id": "talento", "nome": "Pessoas e Cultura"},
        {"id": "governanca", "nome": "Ambiente regulatório"},
    ],
    "ameacas": [
        {"id": "portfolio", "nome": "Concorrência"},
        {"id": "governanca", "nome": "Regulação e risco"},
        {"id": "dados", "nome": "Dados e Infraestrutura"},
        {"id": "talento", "nome": "Talento e ritmo"},
    ],
}

_QUADRANT_TO_FIELD = {
    "strength": "forcas",
    "weakness": "fraquezas",
    "opportunity": "oportunidades",
    "threat": "ameacas",
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


def _dim_sort_key(dim_id: str, qid: str) -> tuple[int, str]:
    try:
        idx = _DIM_ORDER.index(dim_id)
    except ValueError:
        idx = 99
    return (idx, qid)


def _fallback_rules(lvl: int) -> dict[str, Any]:
    """Fallback se o modelo não tiver swotFramework (legado)."""
    if lvl == 3:
        return {"quadrants": ["watchlist"]}
    if lvl >= 4:
        return {"quadrants": ["strength"]}
    return {"quadrants": ["weakness"]}


def _rule_for_answer(
    framework: dict[str, Any] | None,
    category: str | None,
    lvl: int,
) -> dict[str, Any]:
    cats = (framework or {}).get("categories") or {}
    cat_cfg = cats.get(category or "") if category else None
    if not isinstance(cat_cfg, dict):
        return _fallback_rules(lvl)
    rules = cat_cfg.get("score_rules") or {}
    rule = rules.get(str(lvl)) or rules.get(lvl)
    if isinstance(rule, dict) and rule.get("quadrants"):
        return rule
    return _fallback_rules(lvl)


def build_swot_fields_from_maturity(
    *,
    model: dict[str, Any],
    answers: dict[str, int],
    tier: str,
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Agrega respostas pelo swotFramework → Forças / Fraquezas / Oportunidades / Ameaças."""
    order = {"basico": 0, "completo": 1, "complementar": 2}
    framework = model.get("swotFramework") if isinstance(model.get("swotFramework"), dict) else None

    buckets: dict[str, list[dict]] = {
        "forcas": [],
        "fraquezas": [],
        "oportunidades": [],
        "ameacas": [],
    }
    watchlist: list[dict[str, Any]] = []

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
            category = q.get("swotCategory") or q.get("swot_category")
            category = str(category) if category else None
            rule = _rule_for_answer(framework, category, lvl)
            quadrants = [str(x) for x in (rule.get("quadrants") or [])]

            base_meta = {
                "_dim_id": dim_id,
                "_dim": dim_name,
                "_code": qid,
                "_category": category or "",
            }

            if "watchlist" in quadrants or (quadrants == ["watchlist"]):
                watchlist.append(
                    {
                        "id": qid,
                        "texto": str(q.get("text") or qid)[:500],
                        "pilar": pilar,
                        "dimensao": dim_name,
                        "nota": lvl,
                        "evidencia": evidence,
                        "swotCategory": category,
                    }
                )
                # Nota 3 não entra nos quadrantes SWOT
                continue

            for quad in quadrants:
                field = _QUADRANT_TO_FIELD.get(quad)
                if not field:
                    continue
                prefix = _FIELD_PREFIX[field]
                if field == "oportunidades":
                    label = str(rule.get("opportunity_label") or "").strip()
                    texto = (label or str(q.get("text") or qid))[:500]
                    evid = (
                        f"{qid} · N{lvl} · {str(q.get('text') or '')}. {evidence}"
                    ).strip()[:1000]
                elif field == "ameacas":
                    label = str(rule.get("threat_label") or "").strip()
                    texto = (label or str(q.get("text") or qid))[:500]
                    evid = (
                        f"{qid} · N{lvl} · {str(q.get('text') or '')}. {evidence}"
                    ).strip()[:1000]
                else:
                    texto = str(q.get("text") or qid)[:500]
                    evid = evidence
                    if rule.get("threat_mitigated") and field == "forcas":
                        evid = (
                            f"{evidence} · Ameaça regulatória/reputacional mitigada "
                            f"(risk_compliance N{lvl})."
                        ).strip()[:1000]

                buckets[field].append(
                    {
                        "id": f"{prefix}_{qid.lower()}",
                        "texto": texto,
                        "pilar": pilar,
                        "impacto": lvl,
                        "viabilidade": lvl if field in ("forcas", "fraquezas") else None,
                        "probabilidade": lvl if field in ("oportunidades", "ameacas") else None,
                        "evidencia": evid,
                        "prioridade": None,
                        **base_meta,
                    }
                )

    for field, items in buckets.items():
        items.sort(key=lambda it: _dim_sort_key(str(it.get("_dim_id") or ""), str(it.get("_code") or "")))
        for i, it in enumerate(items, start=1):
            it["prioridade"] = i
            for k in ("_dim_id", "_dim", "_code", "_category"):
                it.pop(k, None)

    watchlist.sort(key=lambda it: _dim_sort_key(
        next((d for d, p in _DIM_TO_PILLAR.items() if p == it.get("pilar")), ""),
        str(it.get("id") or ""),
    ))

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
    watch_note = ""
    if watchlist:
        codes = ", ".join(w["id"] for w in watchlist[:12])
        extra = f" (+{len(watchlist) - 12})" if len(watchlist) > 12 else ""
        watch_note = (
            f" Pontos de Atenção (nota 3, fora do SWOT): {len(watchlist)} — {codes}{extra}."
        )
    veredito_texto = (
        f"{band_desc} Gerado via swotFramework do Modelo de Maturidade em IA. "
        f"No total: {counts}{watch_note}"
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
