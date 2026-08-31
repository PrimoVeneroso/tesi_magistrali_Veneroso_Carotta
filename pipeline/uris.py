"""Parsing URI ICD-11 indipendente dalla release.

Le URI MMS contengono la release (`/release/11/2026-01/mms/...`).
L'identità ontologica è l'ID numerico (eventualmente `/other` o `/unspecified`).
Il join ufficiale MMS→Foundation è il campo `source`, non il titolo.
"""

from __future__ import annotations

import re
from typing import Any

RELEASE_IN_PATH = re.compile(r"/release/11/([^/]+)/")
ID_FROM_ENTITY = re.compile(r"/entity/(\d+(?:/[A-Za-z0-9_-]+)*)/?$")
ID_FROM_LINEARIZATION = re.compile(r"/(?:mms|icf)/(\d+(?:/[A-Za-z0-9_-]+)*)/?$")
ID_FROM_FRAGMENT = re.compile(r"#(\d+(?:/[A-Za-z0-9_-]+)*)")
RESIDUAL_SUFFIXES = ("other", "unspecified")


def is_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def extract_release(url: str) -> str:
    if not isinstance(url, str):
        return ""
    match = RELEASE_IN_PATH.search(url)
    return match.group(1) if match else ""


def extract_entity_id(url: str) -> str:
    """Estrae l'ID ontologico da URI Foundation, MMS, browserUrl o fragment."""
    if not isinstance(url, str) or not url.strip():
        return ""

    cleaned = url.strip()
    if "#" in cleaned:
        match = ID_FROM_FRAGMENT.search(cleaned)
        if match:
            return match.group(1)

    stripped = cleaned.rstrip("/")
    if stripped.endswith(("/mms", "/entity", "/icf")):
        return "root"

    match = ID_FROM_ENTITY.search(stripped)
    if match:
        return match.group(1)

    match = ID_FROM_LINEARIZATION.search(stripped)
    if match:
        return match.group(1)

    return ""


def is_residual_id(entity_id: str) -> bool:
    if not entity_id or "/" not in entity_id:
        return False
    return entity_id.rsplit("/", 1)[-1].lower() in RESIDUAL_SUFFIXES


def is_foundation_uri(url: str) -> bool:
    return isinstance(url, str) and "/entity/" in url


def is_linearization_uri(url: str) -> bool:
    if not isinstance(url, str):
        return False
    return "/mms/" in url or url.endswith("/mms") or "/icf/" in url or url.endswith("/icf")


def normalize_title(title: str) -> str:
    if not isinstance(title, str):
        return ""
    return " ".join(title.strip().lower().split())
