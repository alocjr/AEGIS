"""Gera payload SWOT/TOWS a partir do Modelo de Maturidade (swotFramework + towsFramework)."""

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


# Chaves canônicas do swotFramework → aliases aceitos em swotLabels
_SWOT_LABEL_KEYS: dict[str, tuple[str, ...]] = {
    "strength": ("strength", "forca", "força", "forcas", "forças"),
    "weakness": ("weakness", "fraqueza", "fraquezas"),
    "opportunity": ("opportunity", "oportunidade", "oportunidades"),
    "threat": ("threat", "ameaca", "ameaça", "ameacas", "ameaças"),
    "watchlist": ("watchlist", "pontos_de_atencao", "pontos_de_atenção"),
}

# Cruzamentos canônicos do towsFramework → aliases aceitos em towsLabels
_TOWS_LABEL_KEYS: dict[str, tuple[str, ...]] = {
    "SO": ("SO", "so", "FO", "fo"),
    "ST": ("ST", "st", "FA", "fa"),
    "WO": ("WO", "wo", "FxO", "fxo", "f×O"),
    "WT": ("WT", "wt", "FxA", "fxa", "f×A"),
}


def _label_from_map(labels: Any, keys: tuple[str, ...]) -> str:
    if not isinstance(labels, dict):
        return ""
    for key in keys:
        text = str(labels.get(key) or "").strip()
        if text:
            return text
    return ""


def _swot_label(
    q: dict[str, Any],
    quadrant: str,
    fallback: str,
    rule: dict[str, Any] | None = None,
) -> str:
    """Texto do item: swotLabels[quadrante] (canônico), senão rótulo da regra, senão fallback."""
    labels = q.get("swotLabels") or q.get("swot_labels") or {}
    keys = _SWOT_LABEL_KEYS.get(quadrant, (quadrant,))
    text = _label_from_map(labels, keys)
    if text:
        return text[:500]
    if isinstance(rule, dict):
        if quadrant == "opportunity":
            text = str(rule.get("opportunity_label") or "").strip()
        elif quadrant == "threat":
            text = str(rule.get("threat_label") or "").strip()
        if text:
            return text[:500]
    return fallback[:500]


def _tows_label(q: dict[str, Any], key: str) -> str:
    """Estratégia TOWS: towsLabels.SO|ST|WO|WT (canônico do towsFramework)."""
    labels = q.get("towsLabels") or q.get("tows_labels") or {}
    keys = _TOWS_LABEL_KEYS.get(key, (key, key.lower(), key.upper()))
    return _label_from_map(labels, keys)[:1000]


def _tows_selected(items: list[dict] | None) -> list[dict]:
    """Itens do SWOT marcados para entrar no cruzamento TOWS (`tows=True`; default True)."""
    out: list[dict] = []
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        if raw.get("tows") is False:
            continue
        if not str(raw.get("texto") or "").strip():
            continue
        if not str(raw.get("id") or "").strip():
            continue
        out.append(raw)
    return out


def _question_map(model: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    qmap: dict[str, dict[str, Any]] = {}
    if not isinstance(model, dict):
        return qmap
    for dimension in model.get("dimensions") or []:
        for q in dimension.get("questions") or []:
            qid = str(q.get("id") or "").strip().lower()
            if qid:
                qmap[qid] = q
    return qmap


def _qid_from_swot_item_id(item_id: str) -> str:
    """f_ev1 / fx_ev2 / o_ev1 / a_di3 → ev1 / ev2 / …"""
    parts = str(item_id or "").strip().lower().split("_", 1)
    return parts[1] if len(parts) == 2 else ""


def build_tows_from_swot(
    *,
    forcas: list[dict] | None,
    fraquezas: list[dict] | None,
    oportunidades: list[dict] | None,
    ameacas: list[dict] | None,
    model: dict[str, Any] | None = None,
) -> dict[str, list[dict]]:
    """
    Monta TOWS só com itens SWOT marcados (`tows=True`).

    Regras (towsFramework):
    - Força marcada × Oportunidade(s) marcada(s) → SO (towsLabels.SO)
    - Força marcada × Ameaça(s) marcada(s) → ST
    - Fraqueza marcada × Oportunidade(s) → WO
    - Fraqueza marcada × Ameaça(s) → WT
    """
    forces = _tows_selected(forcas)
    weaknesses = _tows_selected(fraquezas)
    opps = _tows_selected(oportunidades)
    threats = _tows_selected(ameacas)

    opp_ids = [str(i["id"]) for i in opps][:10]
    threat_ids = [str(i["id"]) for i in threats][:10]
    has_opp = bool(opp_ids)
    has_threat = bool(threat_ids)
    qmap = _question_map(model)

    tows_out: dict[str, list[dict]] = {
        "tows_fo": [],
        "tows_fa": [],
        "tows_fxo": [],
        "tows_fxa": [],
    }

    def append_init(field: str, prefix: str, acao: str, internal_id: str, external_ids: list[str]) -> None:
        if not acao or not external_ids:
            return
        tows_out[field].append(
            {
                "id": _nid(prefix),
                "acao": acao[:1000],
                "dono": "",
                "horizonte": "",
                "itens_internos": [internal_id],
                "itens_externos": list(external_ids),
            }
        )

    for item in forces:
        item_id = str(item["id"])
        q = qmap.get(_qid_from_swot_item_id(item_id))
        if has_opp:
            acao = _tows_label(q, "SO") if q else ""
            append_init("tows_fo", "fo", acao, item_id, opp_ids)
        if has_threat:
            acao = _tows_label(q, "ST") if q else ""
            append_init("tows_fa", "fa", acao, item_id, threat_ids)

    for item in weaknesses:
        item_id = str(item["id"])
        q = qmap.get(_qid_from_swot_item_id(item_id))
        if has_opp:
            acao = _tows_label(q, "WO") if q else ""
            append_init("tows_fxo", "fxo", acao, item_id, opp_ids)
        if has_threat:
            acao = _tows_label(q, "WT") if q else ""
            append_init("tows_fxa", "fxa", acao, item_id, threat_ids)

    for key in tows_out:
        tows_out[key] = tows_out[key][:20]

    # Fallback legado se nenhum towsLabels casou, mas há lados marcados
    if not any(tows_out.values()) and (forces or weaknesses) and (opps or threats):
        tows_out = _legacy_pair_tows(
            {
                "forcas": forces,
                "fraquezas": weaknesses,
                "oportunidades": opps,
                "ameacas": threats,
            }
        )

    return tows_out


def build_swot_fields_from_maturity(
    *,
    model: dict[str, Any],
    answers: dict[str, int],
    tier: str,
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Agrega respostas com swotLabels / towsLabels do modelo v3."""
    order = {"basico": 0, "completo": 1, "complementar": 2}
    framework = model.get("swotFramework") if isinstance(model.get("swotFramework"), dict) else None
    tows_fw = model.get("towsFramework") if isinstance(model.get("towsFramework"), dict) else None

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
            # Texto da alternativa escolhida na resposta (levels[nota]) — evidência / fallback
            evidence = str(levels.get(str(lvl)) or levels.get(lvl) or "").strip()[:1000]
            category = q.get("swotCategory") or q.get("swot_category")
            category = str(category) if category else None
            rule = _rule_for_answer(framework, category, lvl)
            quadrants = [str(x) for x in (rule.get("quadrants") or [])]
            # Fallback de rótulo: alternativa respondida, senão enunciado da pergunta
            label_fallback = evidence or str(q.get("text") or qid)

            base_meta = {
                "_dim_id": dim_id,
                "_dim": dim_name,
                "_code": qid,
            }

            if "watchlist" in quadrants:
                watchlist.append(
                    {
                        "id": qid,
                        "texto": _swot_label(q, "watchlist", label_fallback, rule),
                        "pilar": pilar,
                        "dimensao": dim_name,
                        "nota": lvl,
                        "evidencia": evidence,
                        "swotCategory": category,
                    }
                )
                continue

            for quad in quadrants:
                field = _QUADRANT_TO_FIELD.get(quad)
                if not field:
                    continue
                prefix = _FIELD_PREFIX[field]
                item_id = f"{prefix}_{qid.lower()}"
                # Item do quadrante: sempre swotLabels[quad] (strength/weakness/opportunity/threat)
                texto = _swot_label(q, quad, label_fallback, rule)
                evid = evidence
                if rule.get("threat_mitigated") and quad == "strength":
                    evid = (
                        f"{evidence} · Ameaça regulatória/reputacional mitigada "
                        f"(risk_compliance N{lvl})."
                    ).strip()[:1000]
                elif quad in ("opportunity", "threat"):
                    # Mantém a pergunta original como âncora da evidência
                    evid = f"{qid} · N{lvl} · {str(q.get('text') or '')}. {evidence}".strip()[:1000]

                buckets[field].append(
                    {
                        "id": item_id,
                        "texto": texto,
                        "pilar": pilar,
                        "question_id": qid,
                        "impacto": lvl,
                        "viabilidade": lvl if field in ("forcas", "fraquezas") else None,
                        "probabilidade": lvl if field in ("oportunidades", "ameacas") else None,
                        "evidencia": evid,
                        "prioridade": None,
                        "tows": True,
                        **base_meta,
                    }
                )

    for field, items in buckets.items():
        items.sort(key=lambda it: _dim_sort_key(str(it.get("_dim_id") or ""), str(it.get("_code") or "")))
        for i, it in enumerate(items, start=1):
            it["prioridade"] = i
            for k in ("_dim_id", "_dim", "_code"):
                it.pop(k, None)

    watchlist.sort(
        key=lambda it: _dim_sort_key(
            next((d for d, p in _DIM_TO_PILLAR.items() if p == it.get("pilar")), ""),
            str(it.get("id") or ""),
        )
    )

    tows_out = build_tows_from_swot(
        forcas=buckets["forcas"],
        fraquezas=buckets["fraquezas"],
        oportunidades=buckets["oportunidades"],
        ameacas=buckets["ameacas"],
        model=model,
    )
    has_opp = bool(_tows_selected(buckets["oportunidades"]))

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
            f" Pontos de Atenção (nota 3, fora do SWOT/TOWS): {len(watchlist)} — {codes}{extra}."
        )
    empty_opp_note = ""
    if tows_fw and not has_opp and (
        _tows_selected(buckets["forcas"]) or _tows_selected(buckets["fraquezas"])
    ):
        empty_opp_note = (
            " Sem oportunidades marcadas para o TOWS, as estratégias ofensivas (SO/WO) ficam vazias — "
            "sinal de posicionamento de mercado insuficiente para ofensiva."
        )
    veredito_texto = (
        f"{band_desc} Gerado via swotFramework/towsFramework do Modelo de Maturidade em IA. "
        f"No total: {counts}{watch_note}{empty_opp_note}"
    ).strip()[:8000]

    return {
        "optica": optica,
        "pilares": {k: [dict(s) for s in v] for k, v in _DEFAULT_PILARES.items()},
        "forcas": buckets["forcas"],
        "fraquezas": buckets["fraquezas"],
        "oportunidades": buckets["oportunidades"],
        "ameacas": buckets["ameacas"],
        "watchlist": [
            {
                "id": w.get("id") or "",
                "texto": w.get("texto") or "",
                "pilar": w.get("pilar") or "",
                "dimensao": w.get("dimensao") or "",
                "nota": w.get("nota"),
                "evidencia": w.get("evidencia") or "",
                "swotCategory": w.get("swotCategory"),
            }
            for w in watchlist
        ],
        "tows_fo": tows_out["tows_fo"],
        "tows_fa": tows_out["tows_fa"],
        "tows_fxo": tows_out["tows_fxo"],
        "tows_fxa": tows_out["tows_fxa"],
        "veredito_tipo": veredito_tipo,
        "veredito_titulo": veredito_titulo,
        "veredito_texto": veredito_texto,
    }


def _legacy_pair_tows(buckets: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Pareamento antigo por template, se o modelo não tiver towsLabels."""

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

    return {
        "tows_fo": pair(
            buckets["forcas"],
            buckets["oportunidades"],
            "Usar «{a}» ({ai}) para aproveitar «{b}» ({bi}).",
            4,
            "fo",
        ),
        "tows_fa": pair(
            buckets["forcas"],
            buckets["ameacas"],
            "Usar «{a}» ({ai}) para conter o risco de «{b}» ({bi}).",
            4,
            "fa",
        ),
        "tows_fxo": pair(
            buckets["fraquezas"],
            buckets["oportunidades"],
            "Aproveitar «{b}» ({bi}) como janela para corrigir «{a}» ({ai}).",
            4,
            "fxo",
        ),
        "tows_fxa": pair(
            buckets["fraquezas"],
            buckets["ameacas"],
            "Plano defensivo: tratar «{a}» ({ai}) antes que «{b}» ({bi}) vire problema real.",
            4,
            "fxa",
        ),
    }
