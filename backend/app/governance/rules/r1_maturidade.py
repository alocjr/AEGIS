"""R1 — maturidade_para_profundidade.

Adaptação ao modelo real: o prompt original usa CSFs `R1..R5` e `D4` de um modelo de 6
dimensões que não existe neste repo. O modelo de maturidade ativo (`ai_maturity_model.json`)
tem 4 dimensões — a de Governança & Risco (`gov_risk`, perguntas `GR1..GR11`) é o equivalente
mais direto ao pilar de governança do prompt original, e é a única usada aqui (decisão
registrada no plano da feature).

Elo mais fraco entre as respostas GR* → profundidade de implantação do módulo de Governança:
n ≤ 2 ⇒ fundação · n == 3 ⇒ intermediário · n ≥ 4 ⇒ completo.
"""

from __future__ import annotations

RULE_ID = "maturidade_para_profundidade"
RULE_VERSION = "1"

_GOV_RISK_PREFIX = "GR"


def gov_risk_answers_from_maturity(answers: dict[str, int]) -> dict[str, int]:
    """Filtra um dict de respostas (`{question_id: nota}`) só para as perguntas GR*."""
    return {
        qid: nota
        for qid, nota in answers.items()
        if str(qid).upper().startswith(_GOV_RISK_PREFIX)
    }


def maturidade_para_profundidade(gov_risk_answers: dict[str, int]) -> dict:
    """Input: respostas GR1..GR11 do último `aegis.maturidade` completo publicado pela org.

    Não decide sozinha se a profundidade deve ser aplicada — nunca rebaixa automaticamente
    (Seção 8, regra 9); quem chama esta função decide se o resultado é aceito ou pede
    confirmação humana quando representar um rebaixamento frente ao valor vigente.
    """
    if not gov_risk_answers:
        raise ValueError(
            "gov_risk_answers vazio — nao ha respostas GR* para calcular a profundidade"
        )

    elo_id, elo_valor = min(gov_risk_answers.items(), key=lambda kv: kv[1])
    if elo_valor <= 2:
        profundidade = "fundacao"
    elif elo_valor == 3:
        profundidade = "intermediario"
    else:
        profundidade = "completo"

    return {
        "profundidade": profundidade,
        "elo_mais_fraco": {"question_id": elo_id, "valor": elo_valor},
        "rule_id": RULE_ID,
        "rule_version": RULE_VERSION,
    }
