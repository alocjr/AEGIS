"""MCP multi-organização: org_list/org_switch, org ativa nas tools, visibilidade."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from bson import ObjectId
from fastapi import HTTPException

from app.mcp.tools_learner import _org_id, _with_org, build_org_context
from app.orgs import membership_set
from app.routes.auth import switch_organization
from app.schemas import SwitchOrganizationRequest
from tests.query_match import matches


class _Collection:
    def __init__(self) -> None:
        self.docs: list[dict] = []

    def insert_one(self, doc: dict):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.docs.append(doc)
        return type("Result", (), {"inserted_id": doc["_id"]})()

    def find_one(self, flt: dict | None = None, projection=None, sort=None) -> dict | None:
        for d in self.docs:
            if matches(d, flt):
                if projection:
                    keep = {k for k, v in projection.items() if v}
                    out = {k: d[k] for k in keep if k in d}
                    if "_id" in d and projection.get("_id", 1):
                        out["_id"] = d["_id"]
                    return out
                return dict(d)
        return None

    def find(self, flt: dict | None = None, projection=None):
        return [d for d in self.docs if matches(d, flt)]

    def update_one(self, flt: dict, update: dict) -> None:
        for d in self.docs:
            if matches(d, flt):
                d.update(update.get("$set", {}))
                break


class _FakeDb:
    def __init__(self) -> None:
        self.users = _Collection()
        self.organizations = _Collection()


class BuildOrgContextTests(unittest.TestCase):
    def test_marks_active_and_lists_all_memberships(self) -> None:
        db = _FakeDb()
        a, b = ObjectId(), ObjectId()
        db.organizations.insert_one({"_id": a, "name": "Alpha"})
        db.organizations.insert_one({"_id": b, "name": "Beta"})
        user = {
            "_id": ObjectId(),
            "name": "Ana",
            "email": "ana@ex.com",
            **membership_set([a, b], [b], a),
        }
        ctx = build_org_context(user, db)
        self.assertEqual(ctx["organization_id"], str(a))
        self.assertEqual(ctx["organization_name"], "Alpha")
        by_id = {o["id"]: o for o in ctx["organizations"]}
        self.assertTrue(by_id[str(a)]["active"])
        self.assertFalse(by_id[str(b)]["active"])
        self.assertTrue(by_id[str(b)]["is_org_admin"])
        self.assertIn("org_switch", ctx["hint"])


class OrgIdReloadTests(unittest.TestCase):
    def test_reads_active_org_from_db_not_stale_dict(self) -> None:
        db = _FakeDb()
        a, b = ObjectId(), ObjectId()
        user = {"_id": ObjectId(), **membership_set([a, b], [], a)}
        db.users.insert_one({**user, **membership_set([a, b], [], b)})
        stale = {**user}  # still thinks A is active
        with patch("app.mcp.tools_learner.get_db", return_value=db):
            self.assertEqual(_org_id(stale), b)

    def test_falls_back_to_organization_ids_when_active_missing(self) -> None:
        db = _FakeDb()
        a = ObjectId()
        user = {"_id": ObjectId(), "organization_ids": [a], "organization_id": None}
        db.users.insert_one(dict(user))
        with patch("app.mcp.tools_learner.get_db", return_value=db):
            self.assertEqual(_org_id(user), a)


class OrgSwitchThenOrgIdTests(unittest.TestCase):
    def test_switch_then_tools_see_new_org(self) -> None:
        db = _FakeDb()
        a, b = ObjectId(), ObjectId()
        db.organizations.insert_one({"_id": a, "name": "Alpha"})
        db.organizations.insert_one({"_id": b, "name": "Beta"})
        user = {
            "_id": ObjectId(),
            "name": "Ana",
            "email": "ana@ex.com",
            **membership_set([a, b], [], a),
        }
        db.users.insert_one(dict(user))

        switch_organization(SwitchOrganizationRequest(organization_id=str(b)), user=user, db=db)
        stored = db.users.find_one({"_id": user["_id"]})
        self.assertEqual(stored["organization_id"], b)
        ctx = build_org_context(stored, db)
        self.assertEqual(ctx["organization_id"], str(b))
        self.assertEqual(ctx["organization_name"], "Beta")

        stale = {**user}  # snapshot from before the switch
        with patch("app.mcp.tools_learner.get_db", return_value=db):
            self.assertEqual(_org_id(stale), b)
            fresh, org_id = _with_org(stale)
            self.assertEqual(org_id, b)
            self.assertEqual(fresh["organization_id"], b)
            self.assertFalse(fresh["is_org_admin"])

    def test_switch_rejects_non_member(self) -> None:
        db = _FakeDb()
        a, other = ObjectId(), ObjectId()
        user = {"_id": ObjectId(), "name": "Ana", "email": "ana@ex.com", **membership_set([a], [], a)}
        with self.assertRaises(HTTPException) as ctx:
            switch_organization(
                SwitchOrganizationRequest(organization_id=str(other)), user=user, db=db
            )
        self.assertEqual(ctx.exception.status_code, 403)
