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
