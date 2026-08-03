"""Catálogo das ferramentas do AI Hub e resolução de quais o usuário pode abrir.

A liberação é **por usuário** (`users.tools`), definida pelo admin da plataforma. Este módulo é
a fonte única de verdade de quais ferramentas existem: as rotas, o `/api/auth/me`, o admin e o
frontend consomem daqui, sem repetir ids nem rótulos.

Fora deste controle:
- Mentoria (Programa, Materiais, Agenda, Quiz) — continua governada por `users.course_slugs`.
- `/api/admin/*` e `/api/org-admin/*` — governados por `is_admin` / `is_org_admin`.

Documento sem o campo `tools` (legado ou criado antes da migração) vale como "tudo liberado",
para nenhuma conta perder acesso que já tinha. `backfill_user_tools` em `database.py` preenche
o campo no startup.
"""

from __future__ import annotations

TOOL_MATURITY = "maturity"
TOOL_SWOT = "swot"
TOOL_OKR = "okr"
TOOL_CANVAS = "canvas"
TOOL_STRATEGIC_MAP = "strategic_map"
TOOL_GOVERNANCE = "governance"

TOOLS: tuple[dict[str, str], ...] = (
    {
        "id": TOOL_MATURITY,
        "label": "Modelo de Maturidade",
        "path": "/ai-maturity",
        "descricao": "Autoavaliação de maturidade em IA da organização.",
    },
    {
        "id": TOOL_SWOT,
        "label": "SWOT de IA",
        "path": "/swot",
        "descricao": "Diagnóstico SWOT e cruzamentos TOWS a partir da maturidade.",
    },
    {
        "id": TOOL_CANVAS,
        "label": "AI Canvas",
        "path": "/projetos",
        "descricao": "Canvas de oportunidades de IA e portfólio de projetos.",
    },
    {
        "id": TOOL_OKR,
        "label": "OKR",
        "path": "/okrs",
        "descricao": "Ciclos de OKR ligados às estratégias da SWOT.",
    },
    {
        "id": TOOL_STRATEGIC_MAP,
        "label": "Mapa Estratégico",
        "path": "/mapa-estrategico",
        "descricao": "Visão encadeada de maturidade, SWOT, projetos e OKR.",
    },
    {
        "id": TOOL_GOVERNANCE,
        "label": "Governança de IA",
        "path": "/governanca/inventario",
        "descricao": "Inventário de sistemas de IA, riscos e gates de aprovação.",
    },
)

TOOL_IDS: frozenset[str] = frozenset(t["id"] for t in TOOLS)


def all_tool_ids() -> list[str]:
    """Ids na ordem do catálogo (é a ordem em que a UI apresenta as ferramentas)."""
    return [t["id"] for t in TOOLS]


def default_tools() -> list[str]:
    """Estado inicial de uma conta nova: tudo liberado; o admin desabilita o que não vendeu."""
    return all_tool_ids()


def sanitize_tools(value) -> list[str]:
    """Descarta ids desconhecidos e duplicados, devolvendo na ordem do catálogo.

    Normalizar pela ordem do catálogo deixa a comparação entre dois conjuntos (ex.: "este
    usuário tem o mesmo acesso da organização?") ser uma igualdade de listas.
    """
    if not isinstance(value, (list, tuple, set, frozenset)):
        return []
    chosen = {str(item or "").strip() for item in value}
    return [tid for tid in all_tool_ids() if tid in chosen]


def user_tools(user: dict) -> list[str]:
    """Ferramentas liberadas para o usuário. Sem o campo = tudo (ver docstring do módulo)."""
    raw = (user or {}).get("tools")
    if raw is None:
        return default_tools()
    return sanitize_tools(raw)


def user_has_tool(user: dict, tool_id: str) -> bool:
    """`is_admin` não é atalho aqui de propósito: o que está marcado na tela do admin é o que
    vale para todo mundo, inclusive para ele — assim o admin vê a plataforma como o cliente vê.
    O acesso ao painel `/api/admin/*` não depende disso."""
    return tool_id in user_tools(user)
