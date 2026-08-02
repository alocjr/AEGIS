"""GET /api/swot-analysis/list: resumo das SWOTs sem criar documento vazio."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bson import ObjectId

from app.routes.swot_analysis import list_swots


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs

    def sort(self, *_args, **_kwargs) -> "_Cursor":
        return self

    def __iter__(self):
        return iter(self._docs)


class _Collection:
    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs

    def find(self, flt: dict | None = None, projection=None) -> _Cursor:
        return _Cursor(
            [d for d in self.docs if all(d.get(k) == v for k, v in (flt or {}).items())]
        )


class _FakeDb:
    def __init__(self, docs: list[dict]) -> None:
        self.swot_analyses = _Collection(docs)


class SwotListTests(unittest.TestCase):
    def test_summarizes_own_swots_only(self) -> None:
        user_id = ObjectId()
        other_id = ObjectId()
        maturity_id = ObjectId()
        now = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        db = _FakeDb(
            [
                {
                    "_id": ObjectId(),
                    "user_id": user_id,
                    "maturity_response_id": maturity_id,
                    "optica": "Organização",
                    "veredito_titulo": "Fundação primeiro",
                    "forcas": [{"id": "f_ev1", "texto": "Patrocínio"}],
                    "fraquezas": [{"id": "w_di3", "texto": "Dados soltos"}],
                    "oportunidades": [],
                    "ameacas": [],
                    "tows_fo": [{"id": "t1", "acao": "Escalar copiloto"}],
                    "tows_fxa": [{"id": "t2", "acao": "Blindar dados"}],
                    "created_at": now,
                    "updated_at": now,
                },
                {"_id": ObjectId(), "user_id": other_id, "veredito_titulo": "De outro"},
            ]
        )

        items = list_swots(user={"_id": user_id}, db=db)["items"]

        self.assertEqual(len(items), 1)
        summary = items[0]
        self.assertEqual(summary["maturity_response_id"], str(maturity_id))
        self.assertEqual(summary["veredito_titulo"], "Fundação primeiro")
        self.assertEqual(summary["items_count"], 2)
        self.assertEqual(summary["tows_count"], 2)
        self.assertEqual(summary["updated_at"], now.isoformat())

    def test_empty_when_user_has_no_swot(self) -> None:
        db = _FakeDb([])
        self.assertEqual(list_swots(user={"_id": ObjectId()}, db=db)["items"], [])


if __name__ == "__main__":
    unittest.main()
