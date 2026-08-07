"""Contagem de acesso aos recursos: validação de chave, gravação e montagem do relatório.

Mesmo padrão fake-Mongo/chamada direta dos demais testes do repo.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app import analytics


class FakeCollection:
    def __init__(self, docs: list[dict] | None = None, aggregate_rows: dict | None = None) -> None:
        self.docs = docs or []
        self.inserted: list[dict] = []
        # Respostas por tipo de pipeline, para não reimplementar o motor de agregação.
        self.aggregate_rows = aggregate_rows or {}
        self.recent_count = 0

    def insert_one(self, doc: dict) -> None:
        self.inserted.append(doc)

    def count_documents(self, flt: dict, limit: int | None = None) -> int:
        return self.recent_count

    def find_one(self, flt: dict, projection: dict | None = None) -> dict | None:
        for doc in self.docs:
            if doc["_id"] == flt.get("_id"):
                return doc
        return None

    def find(self, flt: dict, projection: dict | None = None):
        wanted = set(flt.get("_id", {}).get("$in", []))
        return [doc for doc in self.docs if doc["_id"] in wanted]

    def aggregate(self, pipeline: list[dict]):
        group_id = pipeline[-1]["$group"]["_id"] if "$group" in pipeline[-1] else pipeline[1]["$group"]["_id"]
        if group_id == "$resource_key":
            return list(self.aggregate_rows.get("by_resource", []))
        if group_id == "$day":
            return list(self.aggregate_rows.get("by_day", []))
        return list(self.aggregate_rows.get("totals", []))


class FakeDb:
    def __init__(self, collections: dict[str, FakeCollection]) -> None:
        self._collections = collections

    def __getitem__(self, name: str) -> FakeCollection:
        return self._collections.setdefault(name, FakeCollection())


class ResolveCategoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.material_id = ObjectId()
        self.db = FakeDb(
            {
                "landing_materials": FakeCollection([{"_id": self.material_id, "title": "Guia de IA"}]),
                "landing_prompts": FakeCollection([]),
            }
        )

    def test_static_key_resolves_without_touching_the_database(self) -> None:
        self.assertEqual(analytics.resolve_category(self.db, "swot.editor"), analytics.CATEGORY_TOOL)
        self.assertEqual(
            analytics.resolve_category(self.db, "utilitario.calculadora_tokens"),
            analytics.CATEGORY_UTILITARIO,
        )

    def test_unknown_key_is_rejected(self) -> None:
        self.assertIsNone(analytics.resolve_category(self.db, "inexistente.qualquer"))
        self.assertIsNone(analytics.resolve_category(self.db, ""))
        self.assertIsNone(analytics.resolve_category(self.db, "material:nao-e-objectid"))

    def test_dynamic_key_requires_the_document_to_exist(self) -> None:
        self.assertEqual(
            analytics.resolve_category(self.db, f"material:{self.material_id}"),
            analytics.CATEGORY_MATERIAL,
        )
        self.assertIsNone(analytics.resolve_category(self.db, f"material:{ObjectId()}"))
        self.assertIsNone(analytics.resolve_category(self.db, f"prompt:{self.material_id}"))


class RecordAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = FakeCollection()
        self.db = FakeDb({analytics.COLLECTION: self.events})

    def test_logged_user_is_recorded_with_identity(self) -> None:
        user_id, org_id = ObjectId(), ObjectId()
        ok = analytics.record_access(
            self.db,
            resource_key="okr.editor",
            category=analytics.CATEGORY_TOOL,
            user={"_id": user_id, "organization_id": org_id},
            ip="10.0.0.1",
            user_agent="Mozilla/5.0",
        )
        self.assertTrue(ok)
        doc = self.events.inserted[0]
        self.assertEqual(doc["resource_key"], "okr.editor")
        self.assertEqual(doc["user_id"], user_id)
        self.assertEqual(doc["organization_id"], org_id)
        self.assertEqual(doc["day"], doc["at"].strftime("%Y-%m-%d"))

    def test_anonymous_visitor_is_recorded_without_identity_or_ip(self) -> None:
        analytics.record_access(
            self.db,
            resource_key="utilitario.calculadora_tokens",
            category=analytics.CATEGORY_UTILITARIO,
            user=None,
            ip="10.0.0.1",
            user_agent="Mozilla/5.0",
        )
        doc = self.events.inserted[0]
        self.assertIsNone(doc["user_id"])
        self.assertNotIn("10.0.0.1", repr(doc))
        self.assertEqual(len(doc["visitor_hash"]), 32)

    def test_visitor_hash_changes_with_the_day(self) -> None:
        today = analytics.visitor_hash("10.0.0.1", "ua", "2026-08-06")
        tomorrow = analytics.visitor_hash("10.0.0.1", "ua", "2026-08-07")
        self.assertNotEqual(today, tomorrow)

    def test_burst_above_the_limit_is_dropped(self) -> None:
        self.events.recent_count = analytics.MAX_EVENTS_PER_MINUTE + 1
        ok = analytics.record_access(
            self.db,
            resource_key="swot.editor",
            category=analytics.CATEGORY_TOOL,
            user=None,
            ip="10.0.0.1",
            user_agent="ua",
        )
        self.assertFalse(ok)
        self.assertEqual(self.events.inserted, [])


class AccessCountsForKeysTests(unittest.TestCase):
    """Números que as telas de gestão de materiais/prompts da landing mostram por item."""

    def setUp(self) -> None:
        self.material_id = ObjectId()
        self.last_at = datetime.now(timezone.utc)
        self.db = FakeDb(
            {
                analytics.COLLECTION: FakeCollection(
                    aggregate_rows={
                        "by_resource": [
                            {
                                "_id": analytics.material_key(self.material_id),
                                "events": 9,
                                # $addToSet já devolve sem repetição — 9 cliques, 2 pessoas.
                                "visitors": ["a", "b"],
                                "last_at": self.last_at,
                            }
                        ]
                    }
                )
            }
        )

    def test_keys_follow_the_dynamic_format_accepted_on_ingestion(self) -> None:
        self.assertEqual(analytics.material_key(self.material_id), f"material:{self.material_id}")
        self.assertEqual(analytics.prompt_key(self.material_id), f"prompt:{self.material_id}")

    def test_counts_are_returned_per_key(self) -> None:
        counts = analytics.access_counts_for_keys(self.db, [analytics.material_key(self.material_id)])
        stat = counts[analytics.material_key(self.material_id)]
        self.assertEqual(stat["events"], 9)
        self.assertEqual(stat["unique_visitors"], 2)
        self.assertEqual(stat["last_at"], self.last_at)

    def test_key_without_access_is_simply_absent(self) -> None:
        counts = analytics.access_counts_for_keys(self.db, [analytics.prompt_key(ObjectId())])
        self.assertNotIn(analytics.prompt_key(ObjectId()), counts)

    def test_empty_input_does_not_query_the_database(self) -> None:
        self.assertEqual(analytics.access_counts_for_keys(self.db, []), {})


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prompt_id = ObjectId()
        self.deleted_prompt_id = ObjectId()
        self.user_id = ObjectId()
        last_at = datetime.now(timezone.utc) - timedelta(hours=2)
        events = FakeCollection(
            aggregate_rows={
                "by_resource": [
                    {
                        "_id": "swot.editor",
                        "events": 12,
                        "users": [self.user_id, None],
                        "visitors": ["a", "b"],
                        "last_at": last_at,
                    },
                    {
                        "_id": f"prompt:{self.prompt_id}",
                        "events": 5,
                        "users": [None],
                        "visitors": ["c"],
                        "last_at": last_at,
                    },
                    {
                        "_id": f"prompt:{self.deleted_prompt_id}",
                        "events": 3,
                        "users": [None],
                        "visitors": ["d"],
                        "last_at": last_at,
                    },
                ],
                "by_day": [{"_id": "2026-08-05", "events": 8}],
                "totals": [
                    {"_id": None, "events": 20, "users": [self.user_id, None], "visitors": ["a", "b", "c", "d"]}
                ],
            }
        )
        self.db = FakeDb(
            {
                analytics.COLLECTION: events,
                "landing_prompts": FakeCollection([{"_id": self.prompt_id, "title": "Prompt SWOT"}]),
                "landing_materials": FakeCollection([]),
            }
        )
        self.report = analytics.resource_access_report(self.db, 30)

    def _find(self, key: str) -> dict | None:
        for category in self.report["categories"]:
            for resource in category["resources"]:
                if resource["key"] == key:
                    return resource
        return None

    def test_null_user_ids_do_not_count_as_identified_users(self) -> None:
        self.assertEqual(self.report["totals"]["unique_users"], 1)
        self.assertEqual(self.report["totals"]["unique_visitors"], 4)
        self.assertEqual(self._find("swot.editor")["unique_users"], 1)

    def test_resource_without_access_appears_zeroed(self) -> None:
        entry = self._find("governance.gate")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["events"], 0)
        self.assertIsNone(entry["last_at"])

    def test_dynamic_resource_gets_the_current_title(self) -> None:
        entry = self._find(f"prompt:{self.prompt_id}")
        self.assertEqual(entry["label"], "Prompt SWOT")
        self.assertEqual(entry["category"], analytics.CATEGORY_PROMPT)

    def test_deleted_dynamic_resource_is_dropped(self) -> None:
        self.assertIsNone(self._find(f"prompt:{self.deleted_prompt_id}"))

    def test_resources_are_sorted_by_access_within_the_category(self) -> None:
        tools = next(c for c in self.report["categories"] if c["key"] == analytics.CATEGORY_TOOL)
        self.assertEqual(tools["resources"][0]["key"], "swot.editor")
        self.assertEqual(tools["events"], 12)


if __name__ == "__main__":
    unittest.main()
