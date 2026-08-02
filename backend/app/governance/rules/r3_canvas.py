"""R3 — canvas_para_risco_preliminar.

Deriva um nível de risco preliminar a partir de uma oportunidade do canvas de portfólio,
usando os campos estruturados aditivos `dados_estruturado`/`riscos_estruturado`
(`backend/app/routes/canvas_projects.py`) que preservam a estrutura de origem do
aegis.canvas-oportunidades — perdida no texto livre usado pela UI atual.

Adaptação de taxonomia: o `human_in_the_loop` do canvas real não é booleano — é
`nenhum|sugerir|aprovar|supervisionar`. Tratamos como "humano no loop" qualquer valor
diferente de `nenhum`/vazio, preservando a intenção do critério original do prompt.
"""

from __future__ import annotations

from app.governance.rules.common import SENSIBILIDADE_ORDER, pior_nivel

RULE_ID = "canvas_para_risco_preliminar"
RULE_VERSION = "1"

_SENSIVEL_KEYWORDS = ("lgpd art. 11", "lgpd art.11", "dados sensíveis", "dados sensiveis", "dado sensível")
_PESSOAL_KEYWORDS = ("lgpd",)


def opportunity_input_from_canvas_project(doc: dict) -> dict:
    """Adapta um documento `canvas_projects` para o input puro da R3."""
    dados = doc.get("dados_estruturado") or {}
    riscos = doc.get("riscos_estruturado") or {}
    tipos = set(doc.get("oportunidade_tipos") or [])
    tipo_execucao = "agente_executa" if "Agente autônomo" in tipos else "assiste_sugere"
    return {
        "sensibilidade": dados.get("sensibilidade"),
        "regulatorio": list(riscos.get("regulatorio") or []),
        "human_in_the_loop": riscos.get("human_in_the_loop"),
        "tipo_execucao": tipo_execucao,
    }


def _derivar_sensibilidade_de_regulatorio(regulatorio: list[str]) -> str:
    """Fallback quando `dados.sensibilidade` não foi informado (canvas ainda sem o campo)."""
    texto = " ".join(regulatorio).lower()
    if any(k in texto for k in _SENSIVEL_KEYWORDS):
        return "sensivel"
    if any(k in texto for k in _PESSOAL_KEYWORDS):
        return "pessoal"
    return "interno"


def canvas_para_risco_preliminar(opportunity: dict) -> dict:
    """Input: shape de `opportunity_input_from_canvas_project` (ou equivalente manual)."""
    regulatorio = [str(r) for r in (opportunity.get("regulatorio") or [])]

    sensibilidade = str(opportunity.get("sensibilidade") or "").strip().lower() or None
    derivado_de_regulatorio = False
    if not sensibilidade:
        sensibilidade = _derivar_sensibilidade_de_regulatorio(regulatorio)
        derivado_de_regulatorio = True
    if sensibilidade not in SENSIBILIDADE_ORDER:
        sensibilidade = "interno"

    if sensibilidade == "sensivel":
        dados_nivel = "alto"
    elif sensibilidade == "pessoal":
        dados_nivel = "medio"
    else:
        dados_nivel = "baixo"

    tipo_execucao = opportunity.get("tipo_execucao") or "assiste_sugere"
    hitl_raw = str(opportunity.get("human_in_the_loop") or "").strip().lower()
    humano_no_loop = hitl_raw not in ("", "nenhum")

    if tipo_execucao == "agente_executa":
        autonomia_nivel = "alto" if humano_no_loop else "critico"
    else:
        sensibilidade_rank = SENSIBILIDADE_ORDER.index(sensibilidade)
        pessoal_rank = SENSIBILIDADE_ORDER.index("pessoal")
        autonomia_nivel = "medio" if sensibilidade_rank >= pessoal_rank else "baixo"

    exposicao_nivel = "alto" if regulatorio else "baixo"

    nivel_preliminar = pior_nivel([dados_nivel, autonomia_nivel, exposicao_nivel])

    return {
        "nivel_preliminar": nivel_preliminar,
        "criterios": {
            "dados": dados_nivel,
            "autonomia": autonomia_nivel,
            "exposicao": exposicao_nivel,
        },
        "sensibilidade_usada": sensibilidade,
        "derivado_de_regulatorio": derivado_de_regulatorio,
        "rule_id": RULE_ID,
        "rule_version": RULE_VERSION,
    }
