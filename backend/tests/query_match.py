"""Matcher mínimo de filtros Mongo usado pelos fakes dos testes."""

from __future__ import annotations


def matches(doc: dict, flt: dict | None) -> bool:
    if not flt:
        return True
    for key, expected in flt.items():
        if key == "$or":
            if not any(matches(doc, sub) for sub in expected):
                return False
            continue
        if key == "$and":
            if not all(matches(doc, sub) for sub in expected):
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
                val = doc.get(key)
                allowed = expected["$in"]
                if isinstance(val, list):
                    if not any(item in allowed for item in val):
                        return False
                elif val not in allowed:
                    return False
                continue
        val = doc.get(key)
        if val == expected:
            continue
        # Mongo: igualdade em campo array = "contém o valor"
        if isinstance(val, list) and expected in val:
            continue
        return False
    return True
