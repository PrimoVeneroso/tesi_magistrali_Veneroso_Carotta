"""Fusione MMS + Foundation.

Join ufficiale: MMS.source == Foundation.@id.
Le entità Foundation non linearizzate restano come EF (non vengono scartate).
inclusion, indexTerm e synonym restano campi distinti.
"""

from __future__ import annotations

from typing import Any, Iterable

from pipeline.normalize import build_title_lookup, normalize_entity, unwrap_value
from pipeline.uris import extract_entity_id, extract_release, is_residual_id, normalize_title


def _texts_differ(left: str, right: str) -> bool:
    return normalize_title(left) != normalize_title(right) and bool(left) and bool(right)


def _id_from_ref(ref: dict) -> str:
    return extract_entity_id(
        ref.get("foundationReference") or ref.get("linearizationReference") or ""
    )


def extra_parents(mms_parents: list[dict], foundation_parents: list[dict]) -> list[dict]:
    mms_ids = { _id_from_ref(ref) for ref in mms_parents if _id_from_ref(ref) }
    extra = []
    for ref in foundation_parents:
        fid = _id_from_ref(ref)
        if fid and fid not in mms_ids:
            extra.append(ref)
    return extra


def _dedupe_refs(items: Iterable[dict]) -> list[dict]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict] = []
    for item in items:
        title = str(item.get("title", "")).strip()
        foundation = item.get("foundationReference", "") or ""
        linearization = item.get("linearizationReference", "") or ""
        key = (normalize_title(title), foundation, linearization)
        if key in seen or (not title and not foundation and not linearization):
            continue
        seen.add(key)
        out.append(
            {
                "title": title,
                "foundationReference": foundation,
                "linearizationReference": linearization,
            }
        )
    return out


def merge_datasets(
    mms_data: list[dict],
    foundation_data: list[dict],
    *,
    release: str = "",
) -> dict[str, Any]:
    title_lookup = build_title_lookup(mms_data, foundation_data)

    foundation_by_uri: dict[str, dict] = {}
    foundation_norm_by_uri: dict[str, dict] = {}
    for raw in foundation_data:
        uri = raw.get("@id", "")
        if not uri:
            continue
        foundation_by_uri[uri] = raw
        foundation_norm_by_uri[uri] = normalize_entity(
            raw, source_kind="foundation", title_lookup=title_lookup
        )

    detected_release = release
    em_records: list[dict] = []
    used_foundation: set[str] = set()

    for raw_mms in mms_data:
        if not isinstance(raw_mms, dict):
            continue
        mms = normalize_entity(raw_mms, source_kind="mms", title_lookup=title_lookup)
        mms_uri = mms.get("@id", "") or ""
        source = mms.get("source", "") or ""
        if not detected_release:
            detected_release = extract_release(mms_uri)

        found = foundation_norm_by_uri.get(source, {})
        if source:
            used_foundation.add(source)

        definition_mms = mms.get("definition", "") or ""
        definition_f = found.get("definition", "") or ""
        long_mms = mms.get("longDefinition", "") or ""
        long_f = found.get("longDefinition", "") or ""

        entity_id = extract_entity_id(mms_uri) or extract_entity_id(source) or ""
        record = {
            "entity_kind": "EM",
            "entity_id": entity_id,
            "is_residual": is_residual_id(entity_id),
            "has_foundation": bool(found),
            "release": detected_release,
            "code": mms.get("code", "") or "",
            "title": mms.get("title", "") or unwrap_value(raw_mms.get("title", "")),
            "mms_uri": mms_uri,
            "foundation_uri": source,
            "browser_url_mms": mms.get("browserUrl", "") or "",
            "browser_url_foundation": found.get("browserUrl", "") or "",
            "class_kind": mms.get("classKind", "") or "",
            "fully_specified_name": mms.get("fullySpecifiedName", "")
            or found.get("fullySpecifiedName", "")
            or "",
            "definition": definition_mms or definition_f,
            "definition_alt": [definition_f] if _texts_differ(definition_mms, definition_f) else [],
            "long_definition": long_mms or long_f,
            "long_definition_alt": [long_f] if _texts_differ(long_mms, long_f) else [],
            "coding_note": mms.get("codingNote", "") or "",
            "parents": mms.get("parent", []),
            "other_parents": extra_parents(mms.get("parent", []), found.get("parent", [])),
            "children": mms.get("child", []),
            "inclusions": _dedupe_refs(
                list(mms.get("inclusion", [])) + list(found.get("inclusion", []))
            ),
            "exclusions": _dedupe_refs(
                list(mms.get("exclusion", [])) + list(found.get("exclusion", []))
            ),
            "index_terms": _dedupe_refs(mms.get("indexTerm", [])),
            "synonyms": _dedupe_refs(found.get("synonym", [])),
            "foundation_child_elsewhere": mms.get("foundationChildElsewhere", []),
            "related_maternal": mms.get("relatedEntitiesInMaternalChapter", []),
            "related_perinatal": mms.get("relatedEntitiesInPerinatalChapter", []),
            "postcoordination_scale": mms.get("postcoordinationScale", []),
        }
        em_records.append(record)

    ef_records: list[dict] = []
    for uri, found in foundation_norm_by_uri.items():
        if uri in used_foundation:
            continue
        entity_id = extract_entity_id(uri)
        ef_records.append(
            {
                "entity_kind": "EF",
                "entity_id": entity_id,
                "is_residual": False,
                "has_foundation": True,
                "release": detected_release,
                "code": "",
                "title": found.get("title", ""),
                "mms_uri": "",
                "foundation_uri": uri,
                "browser_url_mms": "",
                "browser_url_foundation": found.get("browserUrl", "") or "",
                "class_kind": "",
                "fully_specified_name": found.get("fullySpecifiedName", "") or "",
                "definition": found.get("definition", "") or "",
                "definition_alt": [],
                "long_definition": found.get("longDefinition", "") or "",
                "long_definition_alt": [],
                "coding_note": "",
                "parents": found.get("parent", []),
                "other_parents": [],
                "children": found.get("child", []),
                "inclusions": _dedupe_refs(found.get("inclusion", [])),
                "exclusions": _dedupe_refs(found.get("exclusion", [])),
                "index_terms": [],
                "synonyms": _dedupe_refs(found.get("synonym", [])),
                "foundation_child_elsewhere": [],
                "related_maternal": [],
                "related_perinatal": [],
                "postcoordination_scale": [],
            }
        )

    return {
        "release": detected_release,
        "counts": {
            "mms_input": len(mms_data),
            "foundation_input": len(foundation_data),
            "EM": len(em_records),
            "EF": len(ef_records),
            "EM_with_foundation": sum(1 for rec in em_records if rec["has_foundation"]),
            "EM_mms_only": sum(1 for rec in em_records if not rec["has_foundation"]),
            "EM_residual": sum(1 for rec in em_records if rec["is_residual"]),
        },
        "entities": em_records + ef_records,
    }
