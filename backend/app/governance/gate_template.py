"""Template v1 do checklist de gate — seed versionado em código (Seção 11: sem UI de admin
para templates). Blocos A–E são estáticos; o bloco F vem da regra R2 (swot_para_checklist).

Bloco B (due diligence de fornecedor) só entra quando o sistema é `origem_ia == api_terceiros`.
"""

from __future__ import annotations

TEMPLATE_VERSION = "1"

_BLOCOS_BASE: tuple[dict, ...] = (
    {
        "bloco": "A",
        "item_id": "A1",
        "texto": "Base legal para o tratamento dos dados usados pelo sistema está identificada e documentada.",
        "critico": True,
    },
    {
        "bloco": "A",
        "item_id": "A2",
        "texto": "Dados pessoais/sensíveis usados pelo sistema estão mapeados (o quê, origem, retenção).",
        "critico": True,
    },
    {
        "bloco": "A",
        "item_id": "A3",
        "texto": "Existe processo para atender solicitações de titulares de dados (acesso, correção, exclusão).",
        "critico": False,
    },
    {
        "bloco": "C",
        "item_id": "C1",
        "texto": "O escopo de ações do sistema é limitado ao necessário (least privilege).",
        "critico": True,
    },
    {
        "bloco": "C",
        "item_id": "C2",
        "texto": "Existe monitoramento/log das ações executadas pelo sistema.",
        "critico": True,
    },
    {
        "bloco": "C",
        "item_id": "C3",
        "texto": "Existe plano de rollback/desligamento rápido em caso de comportamento indevido.",
        "critico": False,
    },
    {
        "bloco": "D",
        "item_id": "D1",
        "texto": "Análise de vieses foi realizada e documentada (obrigatória quando a AIA se aplica).",
        "critico": True,
    },
    {
        "bloco": "D",
        "item_id": "D2",
        "texto": "Medidas de mitigação para os vieses identificados estão definidas.",
        "critico": False,
    },
    {
        "bloco": "E",
        "item_id": "E1",
        "texto": "Métrica de valor/sucesso do sistema está definida e será monitorada em produção.",
        "critico": False,
    },
    {
        "bloco": "E",
        "item_id": "E2",
        "texto": "Responsável de negócio e responsável técnico pelo sistema em produção estão definidos.",
        "critico": True,
    },
)

_BLOCO_B_API_TERCEIROS: tuple[dict, ...] = (
    {
        "bloco": "B",
        "item_id": "B1",
        "texto": "Contrato com o fornecedor inclui DPA (Data Processing Agreement) assinado.",
        "critico": True,
    },
    {
        "bloco": "B",
        "item_id": "B2",
        "texto": "Cláusula contratual garante que o fornecedor não usa os dados enviados para treinar outros modelos.",
        "critico": True,
    },
    {
        "bloco": "B",
        "item_id": "B3",
        "texto": "Certificações de segurança do fornecedor (ex.: SOC2, ISO27001) foram verificadas.",
        "critico": False,
    },
)


def montar_checklist_base(origem_ia: str) -> list[dict]:
    """Itens dos blocos A–E do template, prontos para virar `ChecklistItem` (status=pendente,
    evidencia vazia, origem.tipo=template). Bloco F é responsabilidade do chamador (regra R2)."""
    itens = list(_BLOCOS_BASE)
    if origem_ia == "api_terceiros":
        itens = itens + list(_BLOCO_B_API_TERCEIROS)
    return [
        {
            "bloco": item["bloco"],
            "item_id": item["item_id"],
            "texto": item["texto"],
            "critico": item["critico"],
            "status": "pendente",
            "evidencia": {"descricao": "", "link_ou_artifact_id": ""},
            "origem": {"tipo": "template", "swot_item_id": None, "rule": None},
        }
        for item in itens
    ]
