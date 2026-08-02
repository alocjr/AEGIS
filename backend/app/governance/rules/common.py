"""Constantes e helpers puros compartilhados pelas regras R1–R4."""

from __future__ import annotations

NIVEL_ORDER: tuple[str, ...] = ("baixo", "medio", "alto", "critico")
SENSIBILIDADE_ORDER: tuple[str, ...] = ("publico", "interno", "pessoal", "sensivel")


def pior_nivel(niveis: list[str]) -> str:
    """Elo mais fraco entre níveis de risco (baixo < medio < alto < critico)."""
    return max(niveis, key=NIVEL_ORDER.index)
