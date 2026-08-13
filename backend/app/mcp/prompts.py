"""Prompts MCP nomeados para fluxos SWOT e Canvas."""

from __future__ import annotations

from app.utils.material_gratuito import material_gratuito_dir


def _prompt_body(filename: str) -> str:
    path = material_gratuito_dir() / filename
    if not path.is_file():
        return f"(prompt nao encontrado: {filename})"
    return path.read_text(encoding="utf-8")


def register_prompts(mcp) -> None:
    @mcp.prompt
    def swot_gerar_json() -> str:
        """Gera uma SWOT de IA em JSON e importa na conta do mentorado."""
        body = _prompt_body("prompt-swot-ia-json.md")
        return (
            f"{body}\n\n"
            "---\n"
            "## Integração AEGIS (MCP)\n"
            "Ao concluir o JSON no formato `aegis.swot-ia` (versão 3), chame a tool "
            "`swot_import` passando o documento completo no argumento `document`. "
            "Para ajustes incrementais (quadrantes, veredito ou iniciativas TOWS) use "
            "`swot_update`; para só recalcular TOWS a partir dos itens marcados, use "
            "`tows_rebuild`. "
            "Antes, você pode consultar o resource `aegis://schema/swot-ia` ou "
            "`aegis://data/swot-pillars` se precisar validar a estrutura.\n"
        )

    @mcp.prompt
    def canvas_gerar_json() -> str:
        """Gera Canvas de Oportunidades em JSON e importa na conta do mentorado."""
        body = _prompt_body("prompt-canvas-oportunidades-json.md")
        return (
            f"{body}\n\n"
            "---\n"
            "## Integração AEGIS (MCP)\n"
            "Ao concluir o JSON no formato `aegis.canvas-oportunidades`, chame a tool "
            "`canvas_import` com o documento em `document` (cria um projeto por "
            "oportunidade). Se o usuário já tiver um projeto aberto, use "
            "`canvas_import_into` com `project_id` e o mesmo documento "
            "(aplica a 1ª oportunidade). Para um canvas vazio use `canvas_create`; "
            "para editar campos, `canvas_update`. `canvas_approve_portfolio` envia "
            "o projeto ao inventário de Governança.\n"
        )

    @mcp.prompt
    def maturity_responder() -> str:
        """Conduz o Diagnóstico de Maturidade em IA com o mentorado e grava as respostas."""
        return (
            "Você é o mentor Valorian conduzindo o Diagnóstico de Maturidade em IA pela plataforma AEGIS.\n\n"
            "## Como proceder\n"
            "1. Chame `maturity_questionnaire` (tier `basico` por padrão; `completo` ou `complementar` se o usuário pedir).\n"
            "2. Apresente as perguntas **uma a uma** (ou no máximo um bloco da mesma dimensão). "
            "Mostre o texto e as 5 âncoras (`levels` 1–5). Peça ao usuário que escolha um número de 1 a 5, "
            "com uma frase de contexto se quiser.\n"
            "3. Grave com `maturity_answer`: `question_id` + `score`, e o `response_id` devolvido. "
            "Várias respostas de uma vez: `answers` `{ \"EV1\": 4, \"EV2\": 3 }`.\n"
            "4. Use `next` e `unanswered_ids` para seguir. Não pule perguntas sem o usuário responder.\n"
            "5. Quando `complete` for true, mostre o `result` (nível e pontuação) e ofereça gerar a SWOT "
            "com `swot_from_maturity` passando o `id` da autoavaliação.\n\n"
            "## Regras\n"
            "- Não invente notas. Só grave o que o usuário escolheu.\n"
            "- `maturity_answer` faz merge: não apaga respostas anteriores.\n"
            "- Não use `maturity_save` neste fluxo (ele substitui o mapa inteiro).\n"
            "- Não despeje o `maturity_model` completo no chat — use o questionário enxuto.\n"
        )
