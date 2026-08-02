"""R2 — swot_para_checklist.

Seleciona itens de `fraquezas`/`ameacas` da SWOT ligados a governança — por `pilar` explícito
ou por referenciarem uma pergunta `GR*` (ver adaptação do R1) — e gera itens de checklist do
bloco F do gate. `item_id` é determinístico a partir do id do item SWOT, então repetir a regra
sobre a mesma SWOT produz a mesma lista (dedupe na re-execução via upsert por `item_id`, feito
pela camada de endpoints).

Adaptação: `prioridade` do item SWOT é a posição na lista (não um rótulo alta/média/baixa) —
"crítico" usa `impacto >= 4`, o mesmo limiar já usado em outras partes do repo (ex.: quadrante
do canvas de oportunidades).
"""

from __future__ import annotations

RULE_ID = "swot_para_checklist"
RULE_VERSION = "1"

_QUADRANTES_ELEGIVEIS = ("fraquezas", "ameacas")
_GOV_RISK_PREFIX = "GR"
_IMPACTO_CRITICO_MIN = 4


def _e_item_de_governanca(item: dict) -> bool:
    pilar = str(item.get("pilar") or "").strip().lower()
    if pilar == "governanca":
        return True
    question_id = str(item.get("question_id") or "").strip().upper()
    return question_id.startswith(_GOV_RISK_PREFIX)


def swot_para_checklist(swot: dict) -> dict:
    """Input: documento SWOT (`aegis.swot-ia`) já serializado (`forcas`/`fraquezas`/...)."""
    itens: list[dict] = []
    for quadrante in _QUADRANTES_ELEGIVEIS:
        for item in swot.get(quadrante) or []:
            if not _e_item_de_governanca(item):
                continue
            swot_item_id = str(item.get("id") or "")
            impacto = item.get("impacto")
            critico = isinstance(impacto, (int, float)) and impacto >= _IMPACTO_CRITICO_MIN
            itens.append(
                {
                    "bloco": "F",
                    "item_id": f"F_{swot_item_id}",
                    "texto": f"Mitigação verificada: {item.get('texto') or ''}",
                    "critico": critico,
                    "status": "pendente",
                    "evidencia": {"descricao": "", "link_ou_artifact_id": ""},
                    "origem": {
                        "tipo": "swot",
                        "swot_item_id": swot_item_id,
                        "rule": RULE_ID,
                    },
                }
            )

    return {"itens": itens, "rule_id": RULE_ID, "rule_version": RULE_VERSION}
