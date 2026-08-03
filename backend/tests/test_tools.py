"""Controle de ferramentas do AI Hub: catálogo, sanitize, require_tool e lote por organização."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from bson import ObjectId
from fastapi import HTTPException

from app.deps import require_tool
from app.routes import admin as admin_routes
from app.schemas import AdminUpdateUserRequest, OrganizationToolsRequest
from app.tools import (
    TOOL_CANVAS,
    TOOL_MATURITY,
    TOOL_OKR,
    TOOL_SWOT,
    all_tool_ids,
    default_tools,
    sanitize_tools,
    user_has_tool,
    user_tools,
)


class CatalogTests(unittest.TestCase):
    def test_default_is_full_catalog(self) -> None:
        self.assertEqual(default_tools(), all_tool_ids())
        self.assertIn(TOOL_SWOT, default_tools())
        self.assertIn(TOOL_OKR, default_tools())

    def test_sanitize_drops_unknown_and_keeps_catalog_order(self) -> None:
        self.assertEqual(
            sanitize_tools([TOOL_OKR, "inexistente", TOOL_SWOT, TOOL_SWOT]),
            [TOOL_SWOT, TOOL_OKR],
        )

    def test_missing_field_means_everything_enabled(self) -> None:
        self.assertEqual(user_tools({}), default_tools())
        self.assertTrue(user_has_tool({}, TOOL_CANVAS))

    def test_empty_list_means_nothing_enabled(self) -> None:
        self.assertEqual(user_tools({"tools": []}), [])
        self.assertFalse(user_has_tool({"tools": []}, TOOL_MATURITY))


class RequireToolTests(unittest.TestCase):
    def test_blocks_when_tool_not_in_list(self) -> None:
        dep = require_tool(TOOL_SWOT)
        with self.assertRaises(HTTPException) as ctx:
            dep(user={"tools": [TOOL_MATURITY], "email_verified": True})
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], "TOOL_NOT_ENABLED")

    def test_allows_when_tool_enabled(self) -> None:
        dep = require_tool(TOOL_SWOT)
        user = {"tools": [TOOL_SWOT], "email_verified": True}
        self.assertIs(dep(user=user), user)


class _UsersColl:
    def __init__(self) -> None:
        self.docs: list[dict] = []

    def find_one(self, flt, *args, **kwargs):
        for d in self.docs:
            if all(d.get(k) == v for k, v in flt.items()):
                return d
        return None

    def update_one(self, flt, update):
        doc = self.find_one(flt)
        if doc and "$set" in update:
            doc.update(update["$set"])
        return MagicMock(modified_count=1 if doc else 0)

    def update_many(self, flt, update):
        n = 0
        for d in self.docs:
            if all(d.get(k) == v for k, v in flt.items()):
                if "$set" in update:
                    d.update(update["$set"])
                n += 1
        return MagicMock(modified_count=n)

    def find(self, flt=None, *args, **kwargs):
        flt = flt or {}
        return [d for d in self.docs if all(d.get(k) == v for k, v in flt.items())]


class _OrgsColl:
    def __init__(self) -> None:
        self.docs: list[dict] = []

    def find_one(self, flt, *args, **kwargs):
        for d in self.docs:
            if all(d.get(k) == v for k, v in flt.items()):
                return d
        return None


class _FakeDb:
    def __init__(self) -> None:
        self.users = _UsersColl()
        self.organizations = _OrgsColl()
        self.progress = MagicMock()
        self.courses = MagicMock()
        self.courses.find_one.return_value = None


class AdminToolsTests(unittest.TestCase):
    def test_update_user_tools_and_apply_to_organization(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        db.organizations.docs.append({"_id": org_id, "name": "Acme"})
        u1 = ObjectId()
        u2 = ObjectId()
        db.users.docs.append(
            {"_id": u1, "organization_id": org_id, "tools": default_tools(), "email": "a@x.com"}
        )
        db.users.docs.append(
            {"_id": u2, "organization_id": org_id, "tools": default_tools(), "email": "b@x.com"}
        )
        admin = {"_id": ObjectId(), "is_admin": True}

        result = admin_routes.update_user(
            str(u1),
            AdminUpdateUserRequest(tools=[TOOL_SWOT, TOOL_MATURITY], apply_tools_to_organization=True),
            admin=admin,
            db=db,
        )

        self.assertEqual(result["members_updated"], 2)
        expected = sanitize_tools([TOOL_SWOT, TOOL_MATURITY])
        self.assertEqual(db.users.docs[0]["tools"], expected)
        self.assertEqual(db.users.docs[1]["tools"], expected)

    def test_set_organization_tools_endpoint(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        db.organizations.docs.append({"_id": org_id, "name": "Acme"})
        db.users.docs.append({"_id": ObjectId(), "organization_id": org_id, "tools": default_tools()})
        db.users.docs.append({"_id": ObjectId(), "organization_id": org_id, "tools": default_tools()})

        result = admin_routes.set_organization_tools(
            str(org_id),
            OrganizationToolsRequest(tools=[TOOL_CANVAS]),
            admin={"_id": ObjectId(), "is_admin": True},
            db=db,
        )
        self.assertEqual(result["members_updated"], 2)
        self.assertEqual(result["tools"], [TOOL_CANVAS])
        self.assertEqual(db.users.docs[0]["tools"], [TOOL_CANVAS])


if __name__ == "__main__":
    unittest.main()
