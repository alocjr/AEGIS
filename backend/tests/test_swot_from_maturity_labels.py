"""Garante que itens SWOT/TOWS usam swotLabels / towsLabels do modelo."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.swot_from_maturity import (
    _rule_for_answer,
    _swot_label,
    _tows_label,
    build_swot_fields_from_maturity,
    build_tows_from_swot,
)

_SEED = Path(__file__).resolve().parents[1] / "data" / "ai_maturity_model.json"


def _load_seed() -> dict:
    return json.loads(_SEED.read_text(encoding="utf-8"))


def _qid_from_item_id(item_id: str) -> str:
    return item_id.split("_", 1)[1]


class SwotTowsLabelMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = _load_seed()
        cls.framework = cls.model["swotFramework"]
        cls.questions = {
            q["id"]: q
            for dim in cls.model["dimensions"]
            for q in dim["questions"]
        }

    def test_seed_has_labels_for_every_question(self) -> None:
        for qid, q in self.questions.items():
            self.assertTrue(q.get("swotLabels"), f"{qid} sem swotLabels")
            self.assertTrue(q.get("towsLabels"), f"{qid} sem towsLabels")

    def test_dual_quadrant_uses_distinct_swot_labels(self) -> None:
        q = self.questions["EV1"]
        answers = {qid: 3 for qid in self.questions}
        answers["EV1"] = 5
        # Garante ao menos uma ameaça para não interferir neste assert
        answers["DI3"] = 1
        fields = build_swot_fields_from_maturity(
            model=self.model,
            answers=answers,
            tier="basico",
            result={
                "percent_score": 50,
                "total_score": 30,
                "max_score": 60,
                "level": {"label": "T", "description": "d"},
            },
        )
        force = next(i for i in fields["forcas"] if i["id"] == "f_ev1")
        opp = next(i for i in fields["oportunidades"] if i["id"] == "o_ev1")
        self.assertEqual(force["texto"], q["swotLabels"]["strength"])
        self.assertEqual(opp["texto"], q["swotLabels"]["opportunity"])
        self.assertNotEqual(force["texto"], opp["texto"])
        self.assertNotEqual(force["texto"], q["text"])

    def test_every_generated_item_matches_swot_labels(self) -> None:
        answers = {qid: (i % 5) + 1 for i, qid in enumerate(self.questions)}
        fields = build_swot_fields_from_maturity(
            model=self.model,
            answers=answers,
            tier="complementar",
            result={
                "percent_score": 55,
                "total_score": 120,
                "max_score": 240,
                "level": {"label": "T", "description": "d"},
            },
        )
        for field, quad in (
            ("forcas", "strength"),
            ("fraquezas", "weakness"),
            ("oportunidades", "opportunity"),
            ("ameacas", "threat"),
        ):
            for item in fields[field]:
                qid = _qid_from_item_id(item["id"]).upper()
                q = self.questions[qid]
                expected = _swot_label(q, quad, "FALLBACK")
                self.assertEqual(item["texto"], expected, f"{qid} → {field}")
                rule = _rule_for_answer(self.framework, q["swotCategory"], answers[qid])
                self.assertIn(quad, rule["quadrants"])

        for item in fields["watchlist"]:
            q = self.questions[item["id"]]
            self.assertEqual(answers[item["id"]], 3)
            self.assertEqual(item["texto"], _swot_label(q, "watchlist", "FALLBACK"))

    def test_tows_respects_item_checkbox(self) -> None:
        answers = {qid: 4 for qid in self.questions}
        answers["EV1"] = 5
        answers["DI3"] = 1
        fields = build_swot_fields_from_maturity(
            model=self.model,
            answers=answers,
            tier="basico",
            result={
                "percent_score": 70,
                "total_score": 45,
                "max_score": 60,
                "level": {"label": "T", "description": "d"},
            },
        )
        # Desmarca a força EV1 e a ameaça DI3
        forcas = [{**i, "tows": i["id"] != "f_ev1"} for i in fields["forcas"]]
        ameacas = [{**i, "tows": i["id"] != "a_di3"} for i in fields["ameacas"]]
        tows = build_tows_from_swot(
            forcas=forcas,
            fraquezas=fields["fraquezas"],
            oportunidades=fields["oportunidades"],
            ameacas=ameacas,
            model=self.model,
        )
        for init in tows["tows_fo"] + tows["tows_fa"]:
            self.assertNotIn("f_ev1", init.get("itens_internos") or [])
        for init in tows["tows_fa"] + tows["tows_fxa"]:
            self.assertNotIn("a_di3", init.get("itens_externos") or [])
        # Sem oportunidades marcadas → SO/WO vazios
        tows_no_opp = build_tows_from_swot(
            forcas=fields["forcas"],
            fraquezas=fields["fraquezas"],
            oportunidades=[{**i, "tows": False} for i in fields["oportunidades"]],
            ameacas=fields["ameacas"],
            model=self.model,
        )
        self.assertEqual(tows_no_opp["tows_fo"], [])
        self.assertEqual(tows_no_opp["tows_fxo"], [])
        self.assertTrue(tows_no_opp["tows_fa"] or tows_no_opp["tows_fxa"])

    def test_tows_uses_tows_labels_of_internal_question(self) -> None:
        answers = {qid: 4 for qid in self.questions}
        answers["EV1"] = 5  # market → força + oportunidade
        answers["DI3"] = 1  # risk → fraqueza + ameaça
        fields = build_swot_fields_from_maturity(
            model=self.model,
            answers=answers,
            tier="basico",
            result={
                "percent_score": 70,
                "total_score": 45,
                "max_score": 60,
                "level": {"label": "T", "description": "d"},
            },
        )
        tows_map = {
            "tows_fo": "SO",
            "tows_fa": "ST",
            "tows_fxo": "WO",
            "tows_fxa": "WT",
        }
        for field, key in tows_map.items():
            for init in fields[field]:
                internal = (init.get("itens_internos") or [""])[0]
                qid = _qid_from_item_id(internal).upper()
                expected = _tows_label(self.questions[qid], key)
                self.assertEqual(init["acao"], expected, f"{qid} {field}")
                self.assertTrue(expected, f"{qid} sem towsLabels.{key}")


if __name__ == "__main__":
    unittest.main()
