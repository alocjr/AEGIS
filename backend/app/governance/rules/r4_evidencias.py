"""R4 — evidencias_para_sugestao_maturidade.

Sugere notas (nunca grava — Seção 8, regra 8) para perguntas GR* da próxima rodada de
maturidade, a partir de um snapshot `aegis.evidencia-governanca`. O mapeamento
métrica → pergunta vive em `config/r4_map.yaml` (não hardcoded, editável sem deploy de
código) — carregar o arquivo é a única fronteira de I/O; a função de decisão em si
(`evidencias_para_sugestao_maturidade`) é pura e recebe o mapeamento já carregado.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

RULE_ID = "evidencias_para_sugestao_maturidade"
RULE_VERSION = "1"

_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "r4_map.yaml"

_OPERATORS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
}


def load_r4_map(path: Path | None = None) -> list[dict[str, Any]]:
    """Fronteira de I/O — lê e faz parse do YAML. Chamar uma vez e reusar o resultado."""
    with (path or _CONFIG_PATH).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("rules") or []


def _condicao_satisfeita(condicao: dict, metricas: dict) -> bool:
    metric = condicao.get("metric")
    op = condicao.get("op")
    valor_esperado = condicao.get("value")
    valor_real = metricas.get(metric)
    if valor_real is None or op not in _OPERATORS:
        return False
    return _OPERATORS[op](valor_real, valor_esperado)


def evidencias_para_sugestao_maturidade(
    evidencia_payload: dict, config: list[dict[str, Any]]
) -> dict:
    """Pura: `config` é o retorno de `load_r4_map()`, passado explicitamente pelo chamador."""
    sugestoes: list[dict] = []
    for regra in config:
        question_id = regra.get("question_id")
        for tier in regra.get("tiers") or []:
            condicoes = tier.get("conditions") or []
            if condicoes and all(_condicao_satisfeita(c, evidencia_payload) for c in condicoes):
                sugestoes.append(
                    {
                        "question_id": question_id,
                        "nota_sugerida": tier.get("nota"),
                        "evidencia": {
                            c.get("metric"): evidencia_payload.get(c.get("metric"))
                            for c in condicoes
                        },
                    }
                )
                break  # tiers em ordem decrescente de exigência — primeiro match vence

    return {"sugestoes": sugestoes, "rule_id": RULE_ID, "rule_version": RULE_VERSION}
