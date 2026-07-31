"""Resources MCP: prompts MD, schemas e pilares."""

from __future__ import annotations

from pathlib import Path

from app.utils.material_gratuito import material_gratuito_dir

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
DATA_DIR = BASE_DIR / "data"
SCHEMAS_DIR = DATA_DIR / "schemas"


def _read_text(path: Path) -> str:
    if not path.is_file():
        return f"(arquivo nao encontrado: {path.name})"
    return path.read_text(encoding="utf-8")


def register_resources(mcp) -> None:
    @mcp.resource("aegis://prompt/swot-ia")
    def prompt_swot_ia() -> str:
        """Prompt para gerar SWOT de IA no formato aegis.swot-ia."""
        return _read_text(material_gratuito_dir() / "prompt-swot-ia-json.md")

    @mcp.resource("aegis://prompt/canvas-oportunidades")
    def prompt_canvas() -> str:
        """Prompt para gerar Canvas de Oportunidades no formato aegis.canvas-oportunidades."""
        return _read_text(material_gratuito_dir() / "prompt-canvas-oportunidades-json.md")

    @mcp.resource("aegis://schema/swot-ia")
    def schema_swot() -> str:
        """JSON Schema da exportação SWOT de IA."""
        return _read_text(SCHEMAS_DIR / "swot-ia-export-v2.schema.json")

    @mcp.resource("aegis://schema/canvas-oportunidades")
    def schema_canvas() -> str:
        """JSON Schema do Canvas de Oportunidades."""
        return _read_text(SCHEMAS_DIR / "canvas-oportunidades-v1.schema.json")

    @mcp.resource("aegis://data/swot-pillars")
    def swot_pillars() -> str:
        """Catálogo de pilares canônicos da SWOT de IA."""
        return _read_text(DATA_DIR / "swot-ia-pillars.json")
