"""T028 — fluxo forgot-password / reset-password (002-reset-senha-ui).

Valida mensagem genérica, persistência do token via e-mail (não na resposta HTTP)
e troca de senha com token válido.
"""

from __future__ import annotations

import inspect
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from bson import ObjectId
from fastapi import HTTPException

from app.routes import auth as auth_routes
from app.schemas import ForgotPasswordRequest, ResetPasswordRequest
from app.security import hash_password, hash_password_reset_token

_forgot_password = inspect.unwrap(auth_routes.forgot_password)


def _matches(doc: dict, flt: dict | None) -> bool:
    for key, expected in (flt or {}).items():
        if key == "$or":
            if not any(_matches(doc, sub) for sub in expected):
                return False
            continue
        if isinstance(expected, dict):
            if "$gt" in expected and not (doc.get(key) and doc.get(key) > expected["$gt"]):
                return False
            continue
        if doc.get(key) != expected:
            return False
    return True


class _Collection:
    def __init__(self) -> None:
        self.docs: list[dict] = []

    def insert_one(self, doc: dict):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.docs.append(doc)
        return type("Result", (), {"inserted_id": doc["_id"]})()

    def find_one(self, flt: dict | None = None, projection=None, sort=None) -> dict | None:
        candidates = [d for d in self.docs if _matches(d, flt)]
        return dict(candidates[0]) if candidates else None

    def update_one(self, flt: dict, update: dict) -> None:
        for d in self.docs:
            if _matches(d, flt):
                d.update(update.get("$set", {}))
                break

    def update_many(self, flt: dict, update: dict) -> None:
        for d in self.docs:
            if _matches(d, flt):
                d.update(update.get("$set", {}))


class _FakeDb:
    def __init__(self) -> None:
        self._collections: dict[str, _Collection] = {}

    def __getattr__(self, name: str) -> _Collection:
        return self._collections.setdefault(name, _Collection())


class PasswordResetFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = _FakeDb()
        self.user_id = ObjectId()
        self.db.users.insert_one(
            {
                "_id": self.user_id,
                "name": "Test User",
                "email": "user@example.com",
                "password_hash": hash_password("old-secret"),
                "is_admin": False,
                "email_verified": True,
            }
        )
        self.sent_tokens: list[str] = []

    def _capture_email(self, _email: str, token: str) -> bool:
        self.sent_tokens.append(token)
        return True

    @patch("app.routes.auth.send_password_reset_email")
    @patch("app.routes.auth.enforce_email_rate_limit")
    def test_forgot_password_generic_response_no_token_leak(
        self, _rate_limit, mock_send_email
    ) -> None:
        mock_send_email.side_effect = self._capture_email

        resp = _forgot_password(
            request=unittest.mock.Mock(),
            payload=ForgotPasswordRequest(email="user@example.com"),
            db=self.db,
        )
        self.assertEqual(
            resp["message"],
            "Se o email existir, enviaremos instruções para reset de senha.",
        )
        self.assertNotIn("reset_token", resp)
        self.assertEqual(len(self.sent_tokens), 1)

        unknown = _forgot_password(
            request=unittest.mock.Mock(),
            payload=ForgotPasswordRequest(email="unknown@example.com"),
            db=self.db,
        )
        self.assertEqual(unknown["message"], resp["message"])
        self.assertEqual(len(self.sent_tokens), 1)

    @patch("app.routes.auth.send_password_reset_email")
    @patch("app.routes.auth.enforce_email_rate_limit")
    def test_reset_password_with_valid_token(self, _rate_limit, mock_send_email) -> None:
        mock_send_email.side_effect = self._capture_email
        _forgot_password(
            request=unittest.mock.Mock(),
            payload=ForgotPasswordRequest(email="user@example.com"),
            db=self.db,
        )
        token = self.sent_tokens[0]

        result = auth_routes.reset_password(
            ResetPasswordRequest(token=token, new_password="new-secret-123"),
            db=self.db,
        )
        self.assertEqual(result["message"], "Senha atualizada com sucesso.")

        user = self.db.users.find_one({"_id": self.user_id})
        self.assertTrue(user)
        self.assertNotEqual(user["password_hash"], hash_password("old-secret"))

    def test_reset_password_rejects_invalid_token(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            auth_routes.reset_password(
                ResetPasswordRequest(
                    token="invalid-token-xxxxxxxxxxxx",
                    new_password="new-secret-123",
                ),
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("app.routes.auth.send_password_reset_email")
    @patch("app.routes.auth.enforce_email_rate_limit")
    def test_reset_password_rejects_expired_token(self, _rate_limit, mock_send_email) -> None:
        mock_send_email.side_effect = self._capture_email
        _forgot_password(
            request=unittest.mock.Mock(),
            payload=ForgotPasswordRequest(email="user@example.com"),
            db=self.db,
        )
        token = self.sent_tokens[0]
        token_hash = hash_password_reset_token(token)
        for doc in self.db.password_resets.docs:
            if doc.get("token_hash") == token_hash:
                doc["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)

        with self.assertRaises(HTTPException) as ctx:
            auth_routes.reset_password(
                ResetPasswordRequest(token=token, new_password="new-secret-123"),
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
