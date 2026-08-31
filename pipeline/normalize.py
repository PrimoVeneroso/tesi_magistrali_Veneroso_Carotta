"""Normalizzazione di una singola entità WHO (MMS o Foundation)."""

from __future__ import annotations

from typing import Any, FrozenSet, Iterable

from pipeline.fields import (
    FOUNDATION_KEEP,
    MMS_KEEP,
    REFERENCE_LIST_FIELDS,
    VALUE_FIELDS,
)
from pipeline.uris import extract_entity_id, is_foundation_uri, is_url


def unwrap_value(value: Any) -> Any:
    if isinstance(value, dict) and "@value" in value:
        return value.get("@value", "")
    return value


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def empty_ref(title: str = "") -> dict[str, str]:
    return {
        "title": title or "",
        "foundationReference": "",
        "linearizationReference": "",
    }


def assign_url_to_ref(ref: dict[str, str], url: str) -> dict[str, str]:
    if not url:
        return ref
    if is_foundation_uri(url):
        if not ref.get("foundationReference"):
            ref["foundationReference"] = url
    else:
        if not ref.get("linearizationReference"):
            ref["linearizationReference"] = url
    return ref


def ref_from_url(url: str, title_lookup: dict[str, str] | None = None) -> dict[str, str]:
    lookup = title_lookup or {}
    title = lookup.get(url, "")
    if not title:
        entity_id = extract_entity_id(url)
        if entity_id == "root":
            title = "ICD-11 root"
    ref = empty_ref(title)
    return assign_url_to_ref(ref, url)


def ref_from_object(item: dict, title_lookup: dict[str, str] | None = None) -> dict[str, str]:
    lookup = title_lookup or {}
    label = item.get("label", item.get("title", ""))
    title = unwrap_value(label) if not isinstance(label, str) else label
    title = title or ""

    foundation = item.get("foundationReference", "") or ""
    linearization = item.get("linearizationReference", "") or ""
    extra_url = item.get("link", "") or item.get("@id", "") or ""

    ref = empty_ref(str(title))
    assign_url_to_ref(ref, foundation)
    assign_url_to_ref(ref, linearization)
    if extra_url and extra_url != foundation and extra_url != linearization:
        assign_url_to_ref(ref, extra_url)

    if not ref["title"]:
        for url in (ref["foundationReference"], ref["linearizationReference"]):
            if url and url in lookup:
                ref["title"] = lookup[url]
                break
    return ref


def normalize_reference_list(
    values: Any, title_lookup: dict[str, str] | None = None
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in as_list(values):
        if isinstance(item, str):
            if is_url(item):
                out.append(ref_from_url(item, title_lookup))
            elif item.strip():
                out.append(empty_ref(item.strip()))
        elif isinstance(item, dict):
            out.append(ref_from_object(item, title_lookup))
    return out


def normalize_postcoordination(
    scales: Any, title_lookup: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for scale in as_list(scales):
        if not isinstance(scale, dict):
            continue
        entities = [
            ref_from_url(url, title_lookup) if is_url(url) else empty_ref(str(url))
            for url in as_list(scale.get("scaleEntity", []))
        ]
        out.append(
            {
                "@id": scale.get("@id", ""),
                "axisName": unwrap_value(scale.get("axisName", "")),
                "requiredPostcoordination": scale.get("requiredPostcoordination", ""),
                "allowMultipleValues": scale.get("allowMultipleValues", ""),
                "scaleEntity": entities,
            }
        )
    return out


def build_title_lookup(mms_data: Iterable[dict], foundation_data: Iterable[dict]) -> dict[str, str]:
    """URI → titolo. I titoli MMS sovrascrivono quelli Foundation sullo stesso URI."""
    lookup: dict[str, str] = {}
    for entity in foundation_data:
        uri = entity.get("@id", "")
        title = unwrap_value(entity.get("title", ""))
        if uri and title:
            lookup[uri] = str(title)
    for entity in mms_data:
        title = unwrap_value(entity.get("title", ""))
        if not title:
            continue
        title_s = str(title)
        mms_uri = entity.get("@id", "")
        source = entity.get("source", "")
        if mms_uri:
            lookup[mms_uri] = title_s
        if source:
            lookup[source] = title_s
    return lookup


def _select(entity: dict, keep: FrozenSet[str] | set[str]) -> dict:
    return {key: entity[key] for key in keep if key in entity}


def normalize_entity(
    entity: dict,
    *,
    source_kind: str,
    title_lookup: dict[str, str] | None = None,
) -> dict[str, Any]:
    keep = MMS_KEEP if source_kind == "mms" else FOUNDATION_KEEP
    selected = _select(entity, keep)
    processed: dict[str, Any] = {}

    for key, value in selected.items():
        if key in VALUE_FIELDS:
            processed[key] = unwrap_value(value) or ""
        elif key in REFERENCE_LIST_FIELDS:
            processed[key] = normalize_reference_list(value, title_lookup)
        elif key == "postcoordinationScale":
            processed[key] = normalize_postcoordination(value, title_lookup)
        else:
            processed[key] = value
    return processed
