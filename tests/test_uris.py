from __future__ import annotations

from pipeline.uris import extract_entity_id, extract_release, is_residual_id, normalize_title


def test_extract_id_from_mms_and_foundation_same_entity():
    mms = "http://id.who.int/icd/release/11/2026-01/mms/622600769"
    found = "http://id.who.int/icd/entity/622600769"
    older = "http://id.who.int/icd/release/11/2024-01/mms/622600769"
    assert extract_entity_id(mms) == "622600769"
    assert extract_entity_id(found) == "622600769"
    assert extract_entity_id(older) == "622600769"


def test_residual_and_root():
    residual = "http://id.who.int/icd/release/11/2026-01/mms/622600769/other"
    root = "http://id.who.int/icd/release/11/2026-01/mms"
    browser = "https://icd.who.int/browse/2026-01/mms/en#622600769"
    assert extract_entity_id(residual) == "622600769/other"
    assert is_residual_id(extract_entity_id(residual))
    assert extract_entity_id(root) == "root"
    assert extract_entity_id(browser) == "622600769"


def test_release_is_not_part_of_identity():
    url = "http://id.who.int/icd/release/11/2025-01/mms/111"
    assert extract_release(url) == "2025-01"
    assert extract_entity_id(url) == "111"


def test_normalize_title_collapses_whitespace():
    assert normalize_title("  Blood   Poisoning ") == "blood poisoning"
