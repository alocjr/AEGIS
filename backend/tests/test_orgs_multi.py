"""Memberships multi-organização e visibilidade de artefatos."""

from __future__ import annotations

import unittest

from bson import ObjectId
from fastapi import HTTPException

from app.orgs import (
    VISIBILITY_PRIVATE,
    VISIBILITY_SHARED,
    can_view_artifact,
    is_member_of,
    members_of_org_query,
    membership_set,
    org_admin_ids_of,
    org_ids_of,
    visible_query,
)
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
                out = dict(d)
                if projection:
                    keep = {k for k, v in projection.items() if v}
                    out = {k: out[k] for k in keep if k in out}
                    if "_id" in d and (not projection or projection.get("_id", 1)):
                        out["_id"] = d["_id"]
                return out
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


class OrgIdsOfTests(unittest.TestCase):
    def test_falls_back_to_legacy_organization_id(self) -> None:
        oid = ObjectId()
        self.assertEqual(org_ids_of({"organization_id": oid}), [oid])

    def test_prefers_organization_ids(self) -> None:
        a, b = ObjectId(), ObjectId()
        self.assertEqual(
            org_ids_of({"organization_id": a, "organization_ids": [b, a]}),
            [b, a],
        )


class OrgAdminIdsOfTests(unittest.TestCase):
    def test_legacy_flag_on_active_org(self) -> None:
        oid = ObjectId()
        self.assertEqual(org_admin_ids_of({"organization_id": oid, "is_org_admin": True}), [oid])

    def test_empty_when_not_admin(self) -> None:
        self.assertEqual(org_admin_ids_of({"organization_id": ObjectId()}), [])


class MembersOfOrgQueryTests(unittest.TestCase):
    def test_matches_membership_even_when_active_org_differs(self) -> None:
        org_a, org_b = ObjectId(), ObjectId()
        member = {
            "organization_id": org_b,
            "organization_ids": [org_a, org_b],
        }
        outsider = {"organization_id": org_b, "organization_ids": [org_b]}
        q = members_of_org_query(org_a)
        self.assertTrue(matches(member, q))
        self.assertFalse(matches(outsider, q))


class MembershipSetTests(unittest.TestCase):
    def test_active_must_belong_and_admin_flag_follows_active(self) -> None:
        a, b = ObjectId(), ObjectId()
        fields = membership_set([a, b], [b], a)
        self.assertEqual(fields["organization_ids"], [a, b])
        self.assertEqual(fields["org_admin_ids"], [b])
        self.assertEqual(fields["organization_id"], a)
        self.assertFalse(fields["is_org_admin"])

        fields = membership_set([a, b], [b], b)
        self.assertTrue(fields["is_org_admin"])

    def test_drops_admin_ids_outside_membership(self) -> None:
        a, b = ObjectId(), ObjectId()
        fields = membership_set([a], [b], a)
        self.assertEqual(fields["org_admin_ids"], [])


class VisibilityTests(unittest.TestCase):
    def test_missing_visibility_is_shared(self) -> None:
        author = ObjectId()
        other = ObjectId()
        doc = {"organization_id": ObjectId(), "created_by_user_id": author}
        self.assertTrue(can_view_artifact(doc, other))

    def test_private_only_author(self) -> None:
        author = ObjectId()
        other = ObjectId()
        doc = {
            "organization_id": ObjectId(),
            "created_by_user_id": author,
            "visibility": VISIBILITY_PRIVATE,
        }
        self.assertTrue(can_view_artifact(doc, author))
        self.assertFalse(can_view_artifact(doc, other))

    def test_visible_query_hides_others_private(self) -> None:
        org = ObjectId()
        author = ObjectId()
        viewer = ObjectId()
        shared = {"organization_id": org, "created_by_user_id": author}
        mine = {
            "organization_id": org,
            "created_by_user_id": viewer,
            "visibility": VISIBILITY_PRIVATE,
        }
        hidden = {
            "organization_id": org,
            "created_by_user_id": author,
            "visibility": VISIBILITY_PRIVATE,
        }
        other_org = {"organization_id": ObjectId(), "created_by_user_id": viewer}
        q = visible_query(org, viewer)
        self.assertTrue(matches(shared, q))
        self.assertTrue(matches(mine, q))
        self.assertFalse(matches(hidden, q))
        self.assertFalse(matches(other_org, q))


class SwitchOrganizationTests(unittest.TestCase):
    def test_switches_active_org_and_admin_flag(self) -> None:
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
        db.users.insert_one(user)

        result = switch_organization(
            SwitchOrganizationRequest(organization_id=str(b)),
            user=user,
            db=db,
        )
        stored = db.users.find_one({"_id": user["_id"]})
        self.assertEqual(stored["organization_id"], b)
        self.assertTrue(stored["is_org_admin"])
        self.assertEqual(result["organization_id"], str(b))
        self.assertEqual({o["id"] for o in result["organizations"]}, {str(a), str(b)})

    def test_rejects_org_user_does_not_belong_to(self) -> None:
        db = _FakeDb()
        a, other = ObjectId(), ObjectId()
        user = {"_id": ObjectId(), "name": "Ana", "email": "ana@ex.com", **membership_set([a], [], a)}
        self.assertTrue(is_member_of(user, a))
        with self.assertRaises(HTTPException) as ctx:
            switch_organization(
                SwitchOrganizationRequest(organization_id=str(other)),
                user=user,
                db=db,
            )
        self.assertEqual(ctx.exception.status_code, 403)
