"""Ciclos OKR: CRUD, invariante de "um ciclo ativo por vez", fórmula de progresso do KR."""

from __future__ import annotations

import unittest

from bson import ObjectId
from fastapi import HTTPException

from app.routes import okrs as okrs_routes
from app.schemas import KeyResult, Objective, OkrCycleCreateRequest, OkrCycleUpdateRequest


def _matches(doc: dict, flt: dict | None) -> bool:
    for key, expected in (flt or {}).items():
        if key == "$or":
            if not any(_matches(doc, sub) for sub in expected):
                return False
            continue
        if isinstance(expected, dict):
            if "$ne" in expected:
                if doc.get(key) == expected["$ne"]:
                    return False
                continue
            if "$exists" in expected:
                if (key in doc) != expected["$exists"]:
                    return False
                continue
            if "$in" in expected:
                if doc.get(key) not in expected["$in"]:
                    return False
                continue
        if doc.get(key) != expected:
            return False
    return True


class _Cursor:
    def __init__(self, docs: list[dict]) -> None:
        self._docs = docs

    def sort(self, *args, **kwargs) -> "_Cursor":
        keys = args[0] if args and isinstance(args[0], list) else [(args[0], kwargs.get("direction", 1))]
        docs = list(self._docs)
        # Sort ascending by field priority (stable sort applied last-key-first so the
        # first key in `keys` ends up as the primary sort key).
        for field, direction in reversed(keys):
            docs = sorted(docs, key=lambda d: (d.get(field) is None, d.get(field) or 0), reverse=direction < 0)
        self._docs = docs
        return self

    def __iter__(self):
        return iter(self._docs)


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

    def find(self, flt: dict | None = None, projection=None) -> _Cursor:
        return _Cursor([dict(d) for d in self.docs if _matches(d, flt)])

    def update_one(self, flt: dict, update: dict) -> None:
        for d in self.docs:
            if _matches(d, flt):
                d.update(update.get("$set", {}))
                break

    def delete_one(self, flt: dict) -> None:
        for d in list(self.docs):
            if _matches(d, flt):
                self.docs.remove(d)
                break

    def count_documents(self, flt: dict | None = None) -> int:
        return len([d for d in self.docs if _matches(d, flt)])


class _FakeDb:
    def __init__(self) -> None:
        self._collections: dict[str, _Collection] = {}

    def _col(self, name: str) -> _Collection:
        return self._collections.setdefault(name, _Collection())

    def __getattr__(self, name: str) -> _Collection:
        return self._col(name)

    def __getitem__(self, name: str) -> _Collection:
        return self._col(name)


def _user(**overrides) -> dict:
    doc = {"_id": ObjectId(), "name": "U", "email": "u@x.com"}
    doc.update(overrides)
    return doc


class KrProgressTests(unittest.TestCase):
    def test_baseline_equals_target_is_100(self) -> None:
        pct, raw = okrs_routes._kr_progress(50, 10, 50)
        self.assertEqual(pct, 100.0)
        self.assertEqual(raw, 100.0)

    def test_increase_direction_midpoint(self) -> None:
        pct, _ = okrs_routes._kr_progress(baseline=0, current=50, target=100)
        self.assertEqual(pct, 50.0)

    def test_decrease_direction_midpoint(self) -> None:
        pct, _ = okrs_routes._kr_progress(baseline=100, current=60, target=20)
        self.assertEqual(pct, 50.0)

    def test_decrease_direction_full_progress(self) -> None:
        pct, _ = okrs_routes._kr_progress(baseline=100, current=20, target=20)
        self.assertEqual(pct, 100.0)

    def test_decrease_direction_no_progress(self) -> None:
        pct, _ = okrs_routes._kr_progress(baseline=100, current=100, target=20)
        self.assertEqual(pct, 0.0)

    def test_overshoot_clamped_but_raw_preserved(self) -> None:
        pct, raw = okrs_routes._kr_progress(baseline=0, current=150, target=100)
        self.assertEqual(pct, 100.0)
        self.assertEqual(raw, 150.0)

    def test_undershoot_clamped_to_zero(self) -> None:
        pct, raw = okrs_routes._kr_progress(baseline=50, current=0, target=100)
        self.assertEqual(pct, 0.0)
        self.assertEqual(raw, -100.0)


class CreateCycleTests(unittest.TestCase):
    def test_creates_empty_cycle_in_planejamento(self) -> None:
        db = _FakeDb()
        user = _user()
        org_id = ObjectId()

        result = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="trimestre", ano=2026, trimestre=1),
            user=user, org_id=org_id, db=db,
        )

        self.assertEqual(result["status"], "planejamento")
        self.assertEqual(result["label"], "Q1 2026")
        self.assertEqual(result["objectives_count"], 0)

    def test_trimestre_type_requires_trimestre_field(self) -> None:
        db = _FakeDb()
        with self.assertRaises(HTTPException) as ctx:
            okrs_routes.create_cycle(
                OkrCycleCreateRequest(tipo="trimestre", ano=2026),
                user=_user(), org_id=ObjectId(), db=db,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_ano_type_does_not_require_trimestre(self) -> None:
        db = _FakeDb()
        result = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026),
            user=_user(), org_id=ObjectId(), db=db,
        )
        self.assertEqual(result["label"], "2026")


class UpdateCycleTests(unittest.TestCase):
    def test_full_replace_objectives_generates_ids_and_computes_progress(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db
        )

        updated = okrs_routes.update_cycle(
            cycle["id"],
            OkrCycleUpdateRequest(objectives=[
                Objective(titulo="Reduzir custo operacional", key_results=[
                    KeyResult(titulo="Custo/ticket", baseline=100, current=60, target=20, direction="decrease"),
                ]),
            ]),
            user=_user(), org_id=org_id, db=db,
        )

        self.assertEqual(len(updated["objectives"]), 1)
        obj = updated["objectives"][0]
        self.assertTrue(obj["id"].startswith("obj_"))
        kr = obj["key_results"][0]
        self.assertTrue(kr["id"].startswith("kr_"))
        self.assertEqual(kr["progress_pct"], 50.0)
        self.assertEqual(obj["progress_pct"], 50.0)
        self.assertEqual(updated["progress_pct"], 50.0)

    def test_client_supplied_ids_survive_successive_saves(self) -> None:
        """O editor grava a cada pausa de digitação e reaproveita os ids devolvidos; se um save
        regerasse os ids, os vínculos do Canvas (kr_ids) apontariam para KRs inexistentes."""
        db = _FakeDb()
        org_id = ObjectId()
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db
        )

        first = okrs_routes.update_cycle(
            cycle["id"],
            OkrCycleUpdateRequest(objectives=[
                Objective(titulo="Objetivo", key_results=[KeyResult(titulo="KR", target=10)]),
            ]),
            user=_user(), org_id=org_id, db=db,
        )
        obj_id = first["objectives"][0]["id"]
        kr_id = first["objectives"][0]["key_results"][0]["id"]

        second = okrs_routes.update_cycle(
            cycle["id"],
            OkrCycleUpdateRequest(objectives=[
                Objective(id=obj_id, titulo="Objetivo revisado", key_results=[
                    KeyResult(id=kr_id, titulo="KR revisado", target=10, current=5),
                ]),
            ]),
            user=_user(), org_id=org_id, db=db,
        )

        self.assertEqual(second["objectives"][0]["id"], obj_id)
        self.assertEqual(second["objectives"][0]["key_results"][0]["id"], kr_id)

    def test_untitled_objectives_and_key_results_are_dropped(self) -> None:
        """Item sem título não é persistido — o editor mantém a linha na tela como rascunho e
        avisa o usuário, em vez de perder o preenchimento silenciosamente."""
        db = _FakeDb()
        org_id = ObjectId()
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db
        )

        updated = okrs_routes.update_cycle(
            cycle["id"],
            OkrCycleUpdateRequest(objectives=[
                Objective(titulo="", descricao="rascunho ainda sem título"),
                Objective(titulo="Objetivo válido", key_results=[
                    KeyResult(titulo="", baseline=1, target=2),
                    KeyResult(titulo="KR válido", target=10),
                ]),
            ]),
            user=_user(), org_id=org_id, db=db,
        )

        self.assertEqual([o["titulo"] for o in updated["objectives"]], ["Objetivo válido"])
        self.assertEqual(
            [kr["titulo"] for kr in updated["objectives"][0]["key_results"]], ["KR válido"]
        )

    def test_invalid_swot_id_reference_is_nulled_not_rejected(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db
        )

        updated = okrs_routes.update_cycle(
            cycle["id"],
            OkrCycleUpdateRequest(objectives=[
                Objective(titulo="Objetivo sem SWOT válida", swot_id=str(ObjectId())),
            ]),
            user=_user(), org_id=org_id, db=db,
        )

        self.assertIsNone(updated["objectives"][0]["swot_id"])

    def test_valid_swot_id_reference_is_kept(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        swot_id = ObjectId()
        db.swot_analyses.insert_one({"_id": swot_id, "organization_id": org_id})
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db
        )

        updated = okrs_routes.update_cycle(
            cycle["id"],
            OkrCycleUpdateRequest(objectives=[
                Objective(titulo="Objetivo com SWOT válida", swot_id=str(swot_id)),
            ]),
            user=_user(), org_id=org_id, db=db,
        )

        self.assertEqual(updated["objectives"][0]["swot_id"], str(swot_id))

    def test_wrong_org_raises_404(self) -> None:
        db = _FakeDb()
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=ObjectId(), db=db
        )
        with self.assertRaises(HTTPException) as ctx:
            okrs_routes.update_cycle(
                cycle["id"], OkrCycleUpdateRequest(nome="X"), user=_user(), org_id=ObjectId(), db=db
            )
        self.assertEqual(ctx.exception.status_code, 404)


class ActivateCycleTests(unittest.TestCase):
    def test_activating_demotes_previous_active_cycle(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        cycle_a = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2025), user=_user(), org_id=org_id, db=db
        )
        cycle_b = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db
        )
        okrs_routes.activate_cycle(cycle_a["id"], user=_user(), org_id=org_id, db=db)

        result = okrs_routes.activate_cycle(cycle_b["id"], user=_user(), org_id=org_id, db=db)

        self.assertEqual(result["status"], "ativo")
        reloaded_a = okrs_routes.get_cycle(cycle_a["id"], user=_user(), org_id=org_id, db=db)
        self.assertEqual(reloaded_a["status"], "encerrado")

    def test_reactivating_same_cycle_is_idempotent(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db
        )
        okrs_routes.activate_cycle(cycle["id"], user=_user(), org_id=org_id, db=db)
        result = okrs_routes.activate_cycle(cycle["id"], user=_user(), org_id=org_id, db=db)
        self.assertEqual(result["status"], "ativo")

    def test_active_cycles_from_different_orgs_do_not_interfere(self) -> None:
        db = _FakeDb()
        org_a, org_b = ObjectId(), ObjectId()
        cycle_a = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_a, db=db
        )
        cycle_b = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_b, db=db
        )
        okrs_routes.activate_cycle(cycle_a["id"], user=_user(), org_id=org_a, db=db)
        okrs_routes.activate_cycle(cycle_b["id"], user=_user(), org_id=org_b, db=db)

        self.assertEqual(okrs_routes._get_active(db, org_a)["_id"], ObjectId(cycle_a["id"]))
        self.assertEqual(okrs_routes._get_active(db, org_b)["_id"], ObjectId(cycle_b["id"]))


class GetActiveCycleTests(unittest.TestCase):
    def test_404_when_no_active_cycle(self) -> None:
        db = _FakeDb()
        with self.assertRaises(HTTPException) as ctx:
            okrs_routes.get_active_cycle(user=_user(), org_id=ObjectId(), db=db)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_returns_active_cycle(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db
        )
        okrs_routes.activate_cycle(cycle["id"], user=_user(), org_id=org_id, db=db)

        result = okrs_routes.get_active_cycle(user=_user(), org_id=org_id, db=db)
        self.assertEqual(result["id"], cycle["id"])


class ArchiveAndDeleteCycleTests(unittest.TestCase):
    def test_archive_sets_status_encerrado(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db
        )
        result = okrs_routes.archive_cycle(cycle["id"], user=_user(), org_id=org_id, db=db)
        self.assertEqual(result["status"], "encerrado")

    def test_delete_removes_cycle(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db
        )
        okrs_routes.delete_cycle(cycle["id"], user=_user(), org_id=org_id, db=db)
        self.assertIsNone(db.okr_cycles.find_one({"_id": ObjectId(cycle["id"])}))

    def test_delete_wrong_org_raises_404(self) -> None:
        db = _FakeDb()
        cycle = okrs_routes.create_cycle(
            OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=ObjectId(), db=db
        )
        with self.assertRaises(HTTPException) as ctx:
            okrs_routes.delete_cycle(cycle["id"], user=_user(), org_id=ObjectId(), db=db)
        self.assertEqual(ctx.exception.status_code, 404)


class ListCyclesTests(unittest.TestCase):
    def test_lists_only_own_organization_sorted_desc(self) -> None:
        db = _FakeDb()
        org_id = ObjectId()
        okrs_routes.create_cycle(OkrCycleCreateRequest(tipo="ano", ano=2024), user=_user(), org_id=org_id, db=db)
        okrs_routes.create_cycle(OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=org_id, db=db)
        okrs_routes.create_cycle(OkrCycleCreateRequest(tipo="ano", ano=2026), user=_user(), org_id=ObjectId(), db=db)

        result = okrs_routes.list_cycles(user=_user(), org_id=org_id, db=db)

        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["items"][0]["ano"], 2026)


if __name__ == "__main__":
    unittest.main()
