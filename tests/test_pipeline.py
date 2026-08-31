from __future__ import annotations

import json
from pathlib import Path

from pipeline.audit import audit_classification
from pipeline.classify import classify_terms
from pipeline.merge import merge_datasets
from pipeline.normalize import unwrap_value

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str):
    with (FIXTURES / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def test_unwrap_value():
    assert unwrap_value({"@language": "en", "@value": "Sepsis"}) == "Sepsis"
    assert unwrap_value("already text") == "already text"


def test_merge_keeps_inclusions_and_synonyms_apart_and_retains_ef():
    merged = merge_datasets(_load("mini_mms.json"), _load("mini_foundation.json"))
    by_id = {item["entity_id"]: item for item in merged["entities"]}

    sepsis = by_id["111"]
    assert sepsis["entity_kind"] == "EM"
    assert sepsis["definition"] == "Sepsis is organ dysfunction."
    assert sepsis["definition_alt"] == ["Foundation sepsis definition"]
    assert [item["title"] for item in sepsis["inclusions"]] == ["Septic shock without isolation"]
    assert {item["title"] for item in sepsis["synonyms"]} == {"blood poisoning", "septic condition"}
    assert any(
        item.get("foundationReference", "").endswith("/entity/444")
        for item in sepsis["other_parents"]
    )

    assert by_id["111/other"]["entity_kind"] == "EM"
    assert by_id["111/other"]["is_residual"] is True
    assert by_id["111/other"]["has_foundation"] is False

    assert by_id["222"]["entity_kind"] == "EF"
    assert by_id["444"]["entity_kind"] == "EF"
    assert merged["counts"]["EM"] == 5
    assert merged["counts"]["EF"] == 2


def test_classify_recovers_unique_titles_and_isolates_true_ee():
    merged = classify_terms(
        merge_datasets(_load("mini_mms.json"), _load("mini_foundation.json"))
    )
    sepsis = next(item for item in merged["entities"] if item["entity_id"] == "111")
    index_by_title = {item["title"]: item for item in sepsis["index_terms"]}

    assert index_by_title["Sepsis"]["resolution"].startswith("title:")
    assert index_by_title["Sepsis"]["foundationReference"].endswith("/entity/111")
    assert index_by_title["Hidden foundation child"]["resolution"] == "uri:EF"
    assert index_by_title["Truly external diagnostic phrase"]["resolution"] == "ee:true"

    ee_titles = {item["title"] for item in merged["external_terms"]}
    assert "Truly external diagnostic phrase" in ee_titles
    assert "Sepsis" not in ee_titles
    assert "Hidden foundation child" not in ee_titles
    assert "Other" in ee_titles

    stats = merged["audit"]["term_stats"]
    assert stats["recovered_unique_title"] >= 1
    assert stats["true_EE"] >= 2


def test_audit_passes_on_fixture():
    mms = _load("mini_mms.json")
    foundation = _load("mini_foundation.json")
    merged = classify_terms(merge_datasets(mms, foundation))
    report = audit_classification(merged, mms, foundation)
    failed = [item["name"] for item in report["checks"] if not item["passed"]]
    assert report["passed"], failed
