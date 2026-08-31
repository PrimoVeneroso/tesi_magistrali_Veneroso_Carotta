"""Classificazione EM / EF / EE e recupero dei link mancanti.

Risposta al secondo problema del README:

- EM = ogni nodo della linearizzazione MMS (anche residui other/unspecified)
- EF = nodo Foundation il cui @id non è `source` di nessuna entità MMS
- EE = termine lessicale (indexTerm, synonym, inclusion, exclusion, ...)
  senza URI e senza match univoco di titolo verso EM/EF

Il titolo non è una chiave. Un match per titolo è ammesso solo se è univoco,
abbastanza lungo e non appartiene alla blocklist dei residui.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, Iterable

from pipeline.fields import TITLE_MATCH_BLOCKLIST, TITLE_MATCH_MIN_LENGTH
from pipeline.uris import extract_entity_id, normalize_title

TERM_FIELDS = (
    "inclusions",
    "exclusions",
    "index_terms",
    "synonyms",
    "parents",
    "other_parents",
    "children",
    "foundation_child_elsewhere",
    "related_maternal",
    "related_perinatal",
)


def _entity_index(entities: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for entity in entities:
        for uri in (entity.get("mms_uri"), entity.get("foundation_uri")):
            if uri:
                index[uri] = entity
        entity_id = entity.get("entity_id") or ""
        if entity_id and entity_id not in index:
            index[entity_id] = entity
    return index


def _title_index(entities: list[dict]) -> dict[str, set[str]]:
    titles: dict[str, set[str]] = defaultdict(set)
    for entity in entities:
        title = normalize_title(entity.get("title", ""))
        entity_id = entity.get("entity_id") or ""
        if title and entity_id:
            titles[title].add(entity_id)
    return titles


def _eligible_for_title_match(title: str) -> bool:
    normalized = normalize_title(title)
    if not normalized or len(normalized) < TITLE_MATCH_MIN_LENGTH:
        return False
    if normalized in TITLE_MATCH_BLOCKLIST:
        return False
    return True


def _surrogate_ee_id(title: str) -> str:
    digest = hashlib.sha1(normalize_title(title).encode("utf-8")).hexdigest()[:12]
    return f"ee:{digest}"


def _iter_term_dicts(entity: dict) -> Iterable[tuple[str, dict]]:
    for field in TERM_FIELDS:
        for item in entity.get(field, []) or []:
            if isinstance(item, dict):
                yield field, item
    for scale in entity.get("postcoordination_scale", []) or []:
        if not isinstance(scale, dict):
            continue
        for item in scale.get("scaleEntity", []) or []:
            if isinstance(item, dict):
                yield "postcoordination_scale", item


def classify_terms(merged: dict[str, Any]) -> dict[str, Any]:
    entities = merged.get("entities", [])
    by_key = _entity_index(entities)
    titles = _title_index(entities)

    stats = {
        "terms_total": 0,
        "terms_with_uri": 0,
        "terms_uri_resolves_EM": 0,
        "terms_uri_resolves_EF": 0,
        "terms_uri_dangling": 0,
        "terms_no_uri": 0,
        "recovered_unique_title": 0,
        "ambiguous_title": 0,
        "blocked_title": 0,
        "true_EE": 0,
    }
    dangling: list[dict[str, str]] = []
    ambiguous: list[dict[str, str]] = []
    true_ee: dict[str, dict[str, Any]] = {}

    for entity in entities:
        for field, term in _iter_term_dicts(entity):
            stats["terms_total"] += 1
            title = str(term.get("title", "") or "")
            foundation = term.get("foundationReference", "") or ""
            linearization = term.get("linearizationReference", "") or ""
            uri = foundation or linearization
            term["resolution"] = "unresolved"

            if uri:
                stats["terms_with_uri"] += 1
                target = by_key.get(uri) or by_key.get(extract_entity_id(uri))
                if target:
                    kind = target.get("entity_kind", "")
                    stats[f"terms_uri_resolves_{kind}"] = stats.get(
                        f"terms_uri_resolves_{kind}", 0
                    ) + 1
                    term["resolution"] = f"uri:{kind}"
                    term["resolved_entity_id"] = target.get("entity_id", "")
                    if not foundation and target.get("foundation_uri"):
                        term["foundationReference"] = target["foundation_uri"]
                    if not linearization and target.get("mms_uri"):
                        term["linearizationReference"] = target["mms_uri"]
                else:
                    stats["terms_uri_dangling"] += 1
                    term["resolution"] = "uri:dangling"
                    dangling.append(
                        {
                            "title": title,
                            "uri": uri,
                            "field": field,
                            "owner_id": entity.get("entity_id", ""),
                        }
                    )
                continue

            stats["terms_no_uri"] += 1
            if not _eligible_for_title_match(title):
                stats["blocked_title"] += 1
                term["resolution"] = "ee:blocked_title"
                _add_ee(true_ee, title, field, entity)
                continue

            matches = titles.get(normalize_title(title), set())
            if len(matches) == 1:
                matched_id = next(iter(matches))
                target = by_key.get(matched_id)
                if target:
                    stats["recovered_unique_title"] += 1
                    term["resolution"] = f"title:{target.get('entity_kind')}"
                    term["resolved_entity_id"] = matched_id
                    if target.get("foundation_uri"):
                        term["foundationReference"] = target["foundation_uri"]
                    if target.get("mms_uri"):
                        term["linearizationReference"] = target["mms_uri"]
                    continue
            if len(matches) > 1:
                stats["ambiguous_title"] += 1
                term["resolution"] = "title:ambiguous"
                ambiguous.append(
                    {
                        "title": title,
                        "matches": sorted(matches),
                        "field": field,
                        "owner_id": entity.get("entity_id", ""),
                    }
                )
                continue

            term["resolution"] = "ee:true"
            _add_ee(true_ee, title, field, entity)

    stats["true_EE"] = len(true_ee)
    ee_records = list(true_ee.values())
    for record in ee_records:
        record["entity_kind"] = "EE"

    merged = dict(merged)
    counts = dict(merged.get("counts", {}))
    counts["EE"] = len(ee_records)
    merged["counts"] = counts
    merged["external_terms"] = ee_records
    merged["audit"] = {
        "term_stats": stats,
        "dangling_uris": dangling,
        "ambiguous_titles": ambiguous,
    }
    return merged


def _add_ee(bucket: dict[str, dict[str, Any]], title: str, field: str, owner: dict) -> None:
    if not title.strip():
        return
    key = normalize_title(title)
    if key not in bucket:
        bucket[key] = {
            "entity_id": _surrogate_ee_id(title),
            "title": title.strip(),
            "fields": [],
            "owners": [],
        }
    if field not in bucket[key]["fields"]:
        bucket[key]["fields"].append(field)
    owner_id = owner.get("entity_id", "")
    if owner_id and owner_id not in bucket[key]["owners"]:
        bucket[key]["owners"].append(owner_id)
