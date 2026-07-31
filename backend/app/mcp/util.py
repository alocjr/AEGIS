"""Helpers para tools MCP."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError

from app.mcp.auth import raise_http_as_tool

try:
    from fastmcp.exceptions import ToolError
except ImportError:  # pragma: no cover
    class ToolError(Exception):
        pass


def call_route(fn, **kwargs):
    """Invoca handler de rota FastAPI e converte HTTPException em ToolError."""
    try:
        return fn(**kwargs)
    except HTTPException as exc:
        raise_http_as_tool(exc)
    except ToolError:
        raise
    except ValidationError as exc:
        raise ToolError(f"Payload invalido: {exc.errors()}") from exc
    except Exception as exc:  # pragma: no cover
        raise ToolError(f"Erro interno: {exc}") from exc


def parse_json_object(value: Any, *, label: str = "document") -> dict:
    """Aceita dict ou string JSON; exige objeto."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ToolError(f"{label} nao e JSON valido: {exc}") from exc
    if not isinstance(value, dict):
        raise ToolError(f"{label} deve ser um objeto JSON.")
    return value


def validate_model(model_cls, data: dict):
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise ToolError(f"Payload invalido: {exc.errors()}") from exc
