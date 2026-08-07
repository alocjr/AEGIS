"""Contagem de acessos aos recursos da plataforma.

Fonte única de verdade de **o que** pode ser contado (`RESOURCES`) e de como os eventos são
gravados e agregados (`resource_access_events`). O frontend só envia uma chave; quem decide se
ela existe é este módulo — assim o endpoint público de ingestão não vira porta de entrada para
gravar documento arbitrário.

Duas famílias de chave:

- **Estáticas** (`RESOURCES`): telas de ferramenta, mentoria, plataforma e a calculadora. A chave
  é `dominio.funcionalidade` e o rótulo vive aqui.
- **Dinâmicas** (`material:<id>` / `prompt:<id>`): um card de material gratuito ou um prompt da
  landing, que o admin cria e apaga. O rótulo é resolvido no relatório, lendo as coleções
  `landing_materials` / `landing_prompts`.

Privacidade: nenhum IP é gravado. Para contar visitante único sem identificar quem é, guardamos
`visitor_hash` — digest do IP + user agent + dia + segredo da aplicação. Ele muda todo dia, então
não dá para correlacionar a mesma pessoa entre dias nem reverter para o IP de origem.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo.database import Database

from app.config import settings
from app.tools import (
    TOOL_CANVAS,
    TOOL_GOVERNANCE,
    TOOL_MATURITY,
    TOOL_OKR,
    TOOL_STRATEGIC_MAP,
    TOOL_SWOT,
)

COLLECTION = "resource_access_events"

CATEGORY_TOOL = "ferramenta"
CATEGORY_MENTORIA = "mentoria"
CATEGORY_PLATAFORMA = "plataforma"
CATEGORY_UTILITARIO = "utilitario"
CATEGORY_MATERIAL = "material"
CATEGORY_PROMPT = "prompt"

# Ordem em que o dashboard apresenta os blocos.
CATEGORY_LABELS: tuple[tuple[str, str], ...] = (
    (CATEGORY_TOOL, "Ferramentas"),
    (CATEGORY_MENTORIA, "Mentoria"),
    (CATEGORY_UTILITARIO, "Utilitários"),
    (CATEGORY_PROMPT, "Prompts gratuitos"),
    (CATEGORY_MATERIAL, "Materiais gratuitos"),
    (CATEGORY_PLATAFORMA, "Plataforma"),
)


@dataclass(frozen=True)
class TrackedResource:
    """`group` junta as funcionalidades de uma mesma ferramenta na hora de exibir."""

    key: str
    label: str
    category: str
    group: str


RESOURCES: tuple[TrackedResource, ...] = (
    # — Ferramentas do AI Hub (uma linha por funcionalidade da ferramenta) —
    TrackedResource(f"{TOOL_MATURITY}.lista", "Lista de autoavaliações", CATEGORY_TOOL, "Modelo de Maturidade"),
    TrackedResource(f"{TOOL_MATURITY}.nova", "Nova autoavaliação", CATEGORY_TOOL, "Modelo de Maturidade"),
    TrackedResource(f"{TOOL_MATURITY}.edicao", "Edição de autoavaliação", CATEGORY_TOOL, "Modelo de Maturidade"),
    TrackedResource(f"{TOOL_MATURITY}.resultado", "Resultado da maturidade", CATEGORY_TOOL, "Modelo de Maturidade"),
    TrackedResource(f"{TOOL_SWOT}.editor", "Matriz SWOT e TOWS", CATEGORY_TOOL, "SWOT de IA"),
    TrackedResource(f"{TOOL_CANVAS}.lista", "Portfólio de projetos", CATEGORY_TOOL, "AI Canvas"),
    TrackedResource(f"{TOOL_CANVAS}.projeto", "Canvas do projeto", CATEGORY_TOOL, "AI Canvas"),
    TrackedResource(f"{TOOL_OKR}.ciclos", "Lista de ciclos", CATEGORY_TOOL, "OKR"),
    TrackedResource(f"{TOOL_OKR}.editor", "Editor do ciclo", CATEGORY_TOOL, "OKR"),
    TrackedResource(f"{TOOL_STRATEGIC_MAP}.painel", "Mapa estratégico", CATEGORY_TOOL, "Mapa Estratégico"),
    TrackedResource(f"{TOOL_GOVERNANCE}.dashboard", "Dashboard de governança", CATEGORY_TOOL, "Governança de IA"),
    TrackedResource(f"{TOOL_GOVERNANCE}.inventario", "Inventário de sistemas", CATEGORY_TOOL, "Governança de IA"),
    TrackedResource(f"{TOOL_GOVERNANCE}.sistema", "Ficha do sistema", CATEGORY_TOOL, "Governança de IA"),
    TrackedResource(f"{TOOL_GOVERNANCE}.gate", "Gate de aprovação", CATEGORY_TOOL, "Governança de IA"),
    # — Mentoria (governada por trilha, não por `users.tools`) —
    TrackedResource("mentoria.programa", "Programa", CATEGORY_MENTORIA, "Mentoria"),
    TrackedResource("mentoria.materiais", "Materiais da trilha", CATEGORY_MENTORIA, "Mentoria"),
    TrackedResource("mentoria.agenda", "Agenda", CATEGORY_MENTORIA, "Mentoria"),
    TrackedResource("mentoria.quiz", "Quiz", CATEGORY_MENTORIA, "Mentoria"),
    TrackedResource("mentoria.quiz_respostas", "Respostas do quiz", CATEGORY_MENTORIA, "Mentoria"),
    TrackedResource("mentoria.trilhas", "Vitrine de trilhas", CATEGORY_MENTORIA, "Mentoria"),
    TrackedResource("mentoria.trilha", "Detalhe da trilha", CATEGORY_MENTORIA, "Mentoria"),
    # — Utilitários públicos —
    TrackedResource("utilitario.calculadora_tokens", "Calculadora de tokens", CATEGORY_UTILITARIO, "Calculadora de tokens"),
    # — Plataforma —
    TrackedResource("plataforma.landing", "Landing page", CATEGORY_PLATAFORMA, "Plataforma"),
    TrackedResource("plataforma.login", "Tela de login", CATEGORY_PLATAFORMA, "Plataforma"),
    TrackedResource("plataforma.organizacao", "Minha organização", CATEGORY_PLATAFORMA, "Plataforma"),
)

RESOURCES_BY_KEY: dict[str, TrackedResource] = {r.key: r for r in RESOURCES}

_DYNAMIC_KEY_RE = re.compile(r"^(material|prompt):([0-9a-fA-F]{24})$")

_DYNAMIC_COLLECTIONS = {
    CATEGORY_MATERIAL: "landing_materials",
    CATEGORY_PROMPT: "landing_prompts",
}

# Teto por visitante/minuto. Alto o bastante para navegação normal (a SPA emite um evento por
# troca de rota) e baixo o bastante para um script não inflar a contagem sozinho.
MAX_EVENTS_PER_MINUTE = 60

RETENTION_DAYS = 400


def _now() -> datetime:
    return datetime.now(timezone.utc)


def visitor_hash(ip: str, user_agent: str, day: str) -> str:
    """Identificador de visitante que expira em 24h e não permite voltar ao IP."""
    raw = f"{day}|{ip}|{user_agent}|{settings.jwt_secret_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def material_key(material_id) -> str:
    """Chave de um card de material gratuito da landing."""
    return f"material:{material_id}"


def prompt_key(prompt_id) -> str:
    """Chave de um prompt da landing."""
    return f"prompt:{prompt_id}"


def access_counts_for_keys(db: Database, keys: list[str]) -> dict[str, dict]:
    """Acessos acumulados por chave, sem recorte de período.

    Usado nas telas em que o admin gerencia o item (materiais e prompts da landing): ali o número
    que importa é "quanto esse card rendeu desde que existe", não a janela do dashboard. O teto
    natural é a retenção de `RETENTION_DAYS`.
    """
    if not keys:
        return {}
    rows = db[COLLECTION].aggregate(
        [
            {"$match": {"resource_key": {"$in": keys}}},
            {
                "$group": {
                    "_id": "$resource_key",
                    "events": {"$sum": 1},
                    "visitors": {"$addToSet": "$visitor_hash"},
                    "last_at": {"$max": "$at"},
                }
            },
        ]
    )
    return {
        row["_id"]: {
            "events": int(row["events"]),
            "unique_visitors": len(row["visitors"]),
            "last_at": row["last_at"],
        }
        for row in rows
    }


def resolve_category(db: Database, resource_key: str) -> str | None:
    """Categoria da chave, ou `None` se ela não corresponde a nenhum recurso existente.

    Para as chaves dinâmicas a checagem vai ao banco de propósito: sem isso, qualquer ObjectId
    inventado viraria uma linha no relatório.
    """
    static = RESOURCES_BY_KEY.get(resource_key)
    if static is not None:
        return static.category

    match = _DYNAMIC_KEY_RE.match(resource_key)
    if match is None:
        return None
    category = CATEGORY_MATERIAL if match.group(1) == "material" else CATEGORY_PROMPT
    collection = _DYNAMIC_COLLECTIONS[category]
    if db[collection].find_one({"_id": ObjectId(match.group(2))}, {"_id": 1}) is None:
        return None
    return category


def record_access(
    db: Database,
    *,
    resource_key: str,
    category: str,
    user: dict | None,
    ip: str,
    user_agent: str,
) -> bool:
    """Grava um acesso. Devolve `False` quando o visitante estourou o teto do minuto."""
    at = _now()
    day = at.strftime("%Y-%m-%d")
    vhash = visitor_hash(ip, user_agent, day)

    recent = db[COLLECTION].count_documents(
        {"visitor_hash": vhash, "at": {"$gte": at - timedelta(minutes=1)}},
        limit=MAX_EVENTS_PER_MINUTE + 1,
    )
    if recent > MAX_EVENTS_PER_MINUTE:
        return False

    db[COLLECTION].insert_one(
        {
            "resource_key": resource_key,
            "category": category,
            "user_id": (user or {}).get("_id"),
            "organization_id": (user or {}).get("organization_id"),
            "visitor_hash": vhash,
            "at": at,
            "day": day,
        }
    )
    return True


def _dynamic_labels(db: Database, keys: list[str]) -> dict[str, str]:
    """Títulos atuais dos materiais/prompts citados nos eventos do período."""
    by_collection: dict[str, list[ObjectId]] = {}
    for key in keys:
        match = _DYNAMIC_KEY_RE.match(key)
        if match is None:
            continue
        category = CATEGORY_MATERIAL if match.group(1) == "material" else CATEGORY_PROMPT
        by_collection.setdefault(_DYNAMIC_COLLECTIONS[category], []).append(ObjectId(match.group(2)))

    labels: dict[str, str] = {}
    for collection, ids in by_collection.items():
        prefix = "material" if collection == "landing_materials" else "prompt"
        for doc in db[collection].find({"_id": {"$in": ids}}, {"title": 1}):
            labels[f"{prefix}:{doc['_id']}"] = doc.get("title") or "(sem título)"
    return labels


def resource_access_report(db: Database, days: int) -> dict:
    """Contagem por recurso no período, mais a série diária e os totais do topo.

    Recursos estáticos sem nenhum acesso aparecem zerados — "ninguém abriu" é justamente uma das
    respostas que o admin procura no dashboard.
    """
    since = _now() - timedelta(days=days)

    grouped = list(
        db[COLLECTION].aggregate(
            [
                {"$match": {"at": {"$gte": since}}},
                {
                    "$group": {
                        "_id": "$resource_key",
                        "events": {"$sum": 1},
                        "users": {"$addToSet": "$user_id"},
                        "visitors": {"$addToSet": "$visitor_hash"},
                        "last_at": {"$max": "$at"},
                    }
                },
            ]
        )
    )
    stats = {
        row["_id"]: {
            "events": int(row["events"]),
            "unique_users": len([u for u in row["users"] if u is not None]),
            "unique_visitors": len(row["visitors"]),
            "last_at": row["last_at"],
        }
        for row in grouped
        if row.get("_id")
    }

    dynamic_keys = [k for k in stats if k not in RESOURCES_BY_KEY]
    labels = _dynamic_labels(db, dynamic_keys)

    entries: list[dict] = []
    for resource in RESOURCES:
        entries.append(_entry(resource.key, resource.label, resource.category, resource.group, stats))
    for key in dynamic_keys:
        label = labels.get(key)
        if label is None:
            continue  # material/prompt apagado pelo admin: some do relatório junto com o card
        category = CATEGORY_MATERIAL if key.startswith("material:") else CATEGORY_PROMPT
        group = "Materiais gratuitos" if category == CATEGORY_MATERIAL else "Prompts gratuitos"
        entries.append(_entry(key, label, category, group, stats))

    categories = []
    for category, label in CATEGORY_LABELS:
        items = [e for e in entries if e["category"] == category]
        if not items:
            continue
        items.sort(key=lambda e: (-e["events"], e["group"], e["label"]))
        categories.append(
            {
                "key": category,
                "label": label,
                "events": sum(e["events"] for e in items),
                "resources": items,
            }
        )

    daily = [
        {"day": row["_id"], "events": int(row["events"])}
        for row in db[COLLECTION].aggregate(
            [
                {"$match": {"at": {"$gte": since}}},
                {"$group": {"_id": "$day", "events": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
            ]
        )
    ]

    totals_rows = list(
        db[COLLECTION].aggregate(
            [
                {"$match": {"at": {"$gte": since}}},
                {
                    "$group": {
                        "_id": None,
                        "events": {"$sum": 1},
                        "users": {"$addToSet": "$user_id"},
                        "visitors": {"$addToSet": "$visitor_hash"},
                    }
                },
            ]
        )
    )
    totals_row = totals_rows[0] if totals_rows else {}

    return {
        "range_days": days,
        "since": since.isoformat(),
        "generated_at": _now().isoformat(),
        "totals": {
            "events": int(totals_row.get("events", 0)),
            "unique_users": len([u for u in totals_row.get("users", []) if u is not None]),
            "unique_visitors": len(totals_row.get("visitors", [])),
            "tracked_resources": len(entries),
        },
        "daily": daily,
        "categories": categories,
    }


def _entry(key: str, label: str, category: str, group: str, stats: dict) -> dict:
    stat = stats.get(key)
    last_at = stat["last_at"] if stat else None
    return {
        "key": key,
        "label": label,
        "category": category,
        "group": group,
        "events": stat["events"] if stat else 0,
        "unique_users": stat["unique_users"] if stat else 0,
        "unique_visitors": stat["unique_visitors"] if stat else 0,
        "last_at": last_at.isoformat() if isinstance(last_at, datetime) else None,
    }
