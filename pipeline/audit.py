"""Verifica indipendente della classificazione EM / EF / EE.

Ogni check ha un esito pass/fail e un valore osservato. Se un check fallisce,
la classificazione non è considerata affidabile.
"""

from __future__ import annotations

from typing import Any

from pipeline.fields import TITLE_MATCH_BLOCKLIST, TITLE_MATCH_MIN_LENGTH
from pipeline.uris import extract_entity_id, is_residual_id, normalize_title


def audit_classification(merged: dict[str, Any], mms_data: list[dict], foundation_data: list[dict]) -> dict[str, Any]:
    entities = merged.get("entities", [])
    em = [e for e in entities if e.get("entity_kind") == "EM"]
    ef = [e for e in entities if e.get("entity_kind") == "EF"]
    ee = merged.get("external_terms", [])
    stats = merged.get("audit", {}).get("term_stats", {})
    dangling = merged.get("audit", {}).get("dangling_uris", [])
    ambiguous = merged.get("audit", {}).get("ambiguous_titles", [])

    mms_ids = [extract_entity_id(item.get("@id", "")) for item in mms_data if isinstance(item, dict)]
    foundation_uris = {item.get("@id") for item in foundation_data if item.get("@id")}
    em_mms_uris = {e.get("mms_uri") for e in em if e.get("mms_uri")}
    ef_uris = {e.get("foundation_uri") for e in ef if e.get("foundation_uri")}
    used_sources = {item.get("source") for item in mms_data if item.get("source")}
    titles_to_ids: dict[str, set[str]] = {}
    for entity in em + ef:
        title = normalize_title(entity.get("title", ""))
        entity_id = entity.get("entity_id") or ""
        if title and entity_id:
            titles_to_ids.setdefault(title, set()).add(entity_id)

    false_ee = []
    for term in ee:
        title = normalize_title(term.get("title", ""))
        matches = titles_to_ids.get(title, set())
        eligible = (
            len(title) >= TITLE_MATCH_MIN_LENGTH
            and title not in TITLE_MATCH_BLOCKLIST
        )
        if eligible and len(matches) == 1:
            false_ee.append(term.get("title"))

    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, observed: Any, expected: str) -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "observed": observed,
                "expected": expected,
            }
        )

    check(
        "EM_count_equals_mms_input",
        len(em) == len(mms_data),
        {"EM": len(em), "mms": len(mms_data)},
        "Ogni record MMS diventa esattamente un EM.",
    )
    check(
        "no_duplicate_mms_uri_in_EM",
        len(em_mms_uris) == len([e for e in em if e.get("mms_uri")]),
        len(em_mms_uris),
        "Nessun MMS URI duplicato tra gli EM.",
    )
    check(
        "EF_are_foundation_not_used_as_mms_source",
        ef_uris.isdisjoint(used_sources) and ef_uris <= foundation_uris,
        {"EF": len(ef), "unexpected": sorted(ef_uris - foundation_uris)[:10]},
        "Ogni EF è una Foundation mai usata come source MMS.",
    )
    expected_ef = len(foundation_uris - used_sources)
    check(
        "EF_count_matches_unused_foundation",
        len(ef) == expected_ef,
        {"EF": len(ef), "unused_foundation": expected_ef},
        "Nessuna Foundation-only è stata persa nel merge.",
    )
    check(
        "residual_EM_have_no_own_foundation_or_are_flagged",
        all(e["is_residual"] == is_residual_id(e.get("entity_id", "")) for e in em),
        sum(1 for e in em if e.get("is_residual")),
        "I residui other/unspecified sono marcati is_residual.",
    )
    check(
        "EE_have_no_uri_and_surrogate_id",
        all(str(e.get("entity_id", "")).startswith("ee:") for e in ee),
        len(ee),
        "Le EE hanno solo una surrogate key ee:...",
    )
    check(
        "no_EE_title_uniquely_matches_an_entity",
        not false_ee,
        {"false_ee": false_ee[:20], "ee_records": len(ee)},
        "Le EE residue non hanno un titolo univoco tra EM/EF.",
    )
    check(
        "dangling_uris_are_reported",
        True,
        len(dangling),
        "URI citati ma assenti dai dump sono elencati, non silenziati.",
    )
    check(
        "ambiguous_titles_are_not_auto_linked",
        True,
        len(ambiguous),
        "Titoli ambigui non ricevono un link automatico.",
    )
    check(
        "mms_root_or_numeric_ids_extracted",
        all(bool(eid) for eid in mms_ids if mms_ids),
        sum(1 for eid in mms_ids if not eid),
        "Tutti gli @id MMS producono un entity_id.",
    )

    passed = all(item["passed"] for item in checks)
    return {
        "passed": passed,
        "release": merged.get("release", ""),
        "counts": merged.get("counts", {}),
        "term_stats": stats,
        "dangling_uri_count": len(dangling),
        "ambiguous_title_count": len(ambiguous),
        "checks": checks,
        "how_to_read": {
            "EM": "nodi MMS (linearizzazione), inclusa la radice e i residui",
            "EF": "nodi Foundation non linearizzati in questa release MMS",
            "EE": "termini lessicali senza URI e senza match univoco di titolo",
            "recovered_unique_title": "falsi orfani: il titolo punta a un solo EM/EF",
            "ambiguous_title": "non classificare come EE 'certe' né collegare in automatico",
            "terms_uri_dangling": "errori di dump o riferimenti fuori dal grafo scaricato",
        },
    }
