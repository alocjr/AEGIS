"""GET /api/maturity/my-responses/{id}/export: envelope aegis.maturidade-ia."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from fastapi import HTTPException

from app.routes.maturity import _score_submission, export_my_response

_SEED = Path(__file__).resolve().parents[1] / "data" / "ai_maturity_model.json"


class _Collection:
    def __init__(self, docs: list[dict]) -> None:
        self.docs = docs

    def find_one(self, flt: dict | None = None, projection=None, sort=None) -> dict | None:
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in (flt or {}).items()):
                return doc
        return None


class _FakeDb:
    def __init__(self, model: dict, responses: list[dict]) -> None:
        self.ai_maturity_model = _Collection([model])
        self.maturity_responses = _Collection(responses)


class MaturityExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(_SEED.read_text(encoding="utf-8"))
        cls.model["_id"] = ObjectId()
        cls.basic_questions = [
            {**q, "dim_id": dim["id"]}
            for dim in cls.model["dimensions"]
            for q in dim["questions"]
            if q.get("tier") == "basico"
        ]

    def _fixture(self, *, skip_first_answer: bool = False) -> tuple[_FakeDb, dict, str]:
        user_id = ObjectId()
        response_id = ObjectId()
        answers = {q["id"]: 4 for q in self.basic_questions}
        if skip_first_answer:
            answers.pop(self.basic_questions[0]["id"])
        model = {k: v for k, v in self.model.items()}
        serialized = {**{k: v for k, v in model.items() if k != "_id"}, "id": str(model["_id"])}
        result = _score_submission(serialized, answers, "basico")
        result["complete"] = not skip_first_answer
        doc = {
            "_id": response_id,
            "user_id": user_id,
            "model_id": model["_id"],
            "model_version": model.get("version"),
            "assessment_title": model.get("assessment_title"),
            "tier": "basico",
            "answers": answers,
            "result": result,
            "complete": not skip_first_answer,
            "submitted_at": datetime(2026, 8, 1, 15, 30, tzinfo=timezone.utc),
        }
        return _FakeDb(model, [doc]), {"_id": user_id}, str(response_id)

    def test_envelope_carries_questions_and_answers(self) -> None:
        db, user, response_id = self._fixture()

        doc = export_my_response(response_id, user=user, db=db)

        self.assertEqual(doc["format"], "aegis.maturidade-ia")
        self.assertEqual(doc["version"], 1)
        payload = doc["payload"]
        self.assertTrue(payload["completo"])
        self.assertEqual(payload["respondido_em"], "2026-08-01T15:30:00+00:00")
        self.assertEqual(payload["abrangencia"]["tier"], "basico")
        self.assertEqual(payload["abrangencia"]["perguntas_total"], len(self.basic_questions))
        self.assertEqual(
            payload["abrangencia"]["perguntas_respondidas"], len(self.basic_questions)
        )
        self.assertEqual(len(payload["dimensoes"]), len(self.model["dimensions"]))

        exported = [q for dim in payload["dimensoes"] for q in dim["perguntas"]]
        self.assertEqual(len(exported), len(self.basic_questions))
        first = self.basic_questions[0]
        match = next(q for q in exported if q["id"] == first["id"])
        self.assertEqual(match["texto"], first["text"])
        self.assertEqual(match["resposta"], 4)
        self.assertEqual(match["resposta_descricao"], first["levels"]["4"])

    def test_scores_mirror_stored_result(self) -> None:
        db, user, response_id = self._fixture()

        payload = export_my_response(response_id, user=user, db=db)["payload"]

        stored = db.maturity_responses.docs[0]["result"]
        self.assertEqual(payload["resultado"]["pontuacao"], stored["total_score"])
        self.assertEqual(payload["resultado"]["pontuacao_maxima"], stored["max_score"])
        self.assertEqual(payload["resultado"]["nivel"]["label"], stored["level"]["label"])
        for dim in payload["dimensoes"]:
            self.assertEqual(dim["pontuacao"], stored["dimension_scores"][dim["id"]]["score"])

    def test_unanswered_question_exports_as_null(self) -> None:
        db, user, response_id = self._fixture(skip_first_answer=True)

        payload = export_my_response(response_id, user=user, db=db)["payload"]

        self.assertFalse(payload["completo"])
        self.assertEqual(
            payload["abrangencia"]["perguntas_respondidas"], len(self.basic_questions) - 1
        )
        exported = [q for dim in payload["dimensoes"] for q in dim["perguntas"]]
        missing = next(q for q in exported if q["id"] == self.basic_questions[0]["id"])
        self.assertIsNone(missing["resposta"])
        self.assertEqual(missing["resposta_descricao"], "")

    def test_other_users_response_is_not_exported(self) -> None:
        db, _user, response_id = self._fixture()

        with self.assertRaises(HTTPException) as ctx:
            export_my_response(response_id, user={"_id": ObjectId()}, db=db)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
