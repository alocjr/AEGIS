"""MCP Roadmap: recorte do Gantt e validação de duração."""

from __future__ import annotations

import unittest

from fastmcp.exceptions import ToolError

from app.mcp.tools_learner import (
    _roadmap_pack_item,
    _roadmap_semanas_of,
    _validate_roadmap_semanas,
)


class RoadmapPackTests(unittest.TestCase):
    def test_packs_list_item_with_top_level_semanas(self) -> None:
        packed = _roadmap_pack_item(
            {
                "id": "abc",
                "title": "Copiloto de sinistros",
                "area_negocio": "Operações",
                "prioridade": "P1",
                "data_inicio_real": "2026-09-10",
                "mes_inicio": "set",
                "semanas": 12,
                "periodicidade": "mensal",
                "projeto_aprovado": True,
            }
        )
        self.assertEqual(packed["id"], "abc")
        self.assertEqual(packed["semanas"], 12)
        self.assertEqual(packed["data_inicio_real"], "2026-09-10")
        self.assertTrue(packed["projeto_aprovado"])

    def test_reads_semanas_from_cronograma(self) -> None:
        self.assertEqual(
            _roadmap_semanas_of({"cronograma": {"semanas": 16, "atividades": [], "marcos": []}}),
            16,
        )

    def test_defaults_semanas_to_eight(self) -> None:
        packed = _roadmap_pack_item({"id": "x", "title": "Novo"})
        self.assertEqual(packed["semanas"], 8)
        self.assertEqual(packed["prioridade"], "P4")
        self.assertFalse(packed["projeto_aprovado"])


class RoadmapSemanasTests(unittest.TestCase):
    def test_accepts_horizon(self) -> None:
        self.assertEqual(_validate_roadmap_semanas(4), 4)
        self.assertEqual(_validate_roadmap_semanas(52), 52)
        self.assertEqual(_validate_roadmap_semanas("8"), 8)

    def test_rejects_out_of_range(self) -> None:
        with self.assertRaises(ToolError):
            _validate_roadmap_semanas(3)
        with self.assertRaises(ToolError):
            _validate_roadmap_semanas(53)


if __name__ == "__main__":
    unittest.main()
