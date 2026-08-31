"""Estrazione BFS dall'ICD-API locale (Docker OMS) o remota."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

import requests

from pipeline.config import Settings


def fetch_json(session: requests.Session, uri: str, settings: Settings) -> dict[str, Any]:
    response = session.get(settings.to_local(uri), headers=settings.headers(), timeout=30)
    response.raise_for_status()
    return response.json()


def list_releases(settings: Settings | None = None) -> list[str]:
    """Chiede all'API le release disponibili per la linearizzazione (senza id di release)."""
    settings = settings or Settings.from_env()
    session = requests.Session()
    data = fetch_json(session, settings.linearization_root_unversioned, settings)
    releases = data.get("release") or data.get("availableReleases") or data.get("child") or []
    if isinstance(releases, list):
        return [str(item) for item in releases]
    return []


def crawl(root_uri: str, settings: Settings, output: Path | None = None) -> list[dict[str, Any]]:
    session = requests.Session()
    seen: set[str] = set()
    queue: deque[str] = deque([root_uri])
    entities: list[dict[str, Any]] = []

    handle = None
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        handle = output.open("w", encoding="utf-8")
        handle.write("[\n")

    first = True
    try:
        while queue:
            uri = queue.popleft()
            if uri in seen:
                continue
            seen.add(uri)
            try:
                data = fetch_json(session, uri, settings)
            except Exception as exc:
                print(f"Errore su {uri}: {exc}")
                continue

            entities.append(data)
            if handle is not None:
                if not first:
                    handle.write(",\n")
                json.dump(data, handle, ensure_ascii=False, indent=2)
                first = False

            for child in data.get("child", []) or []:
                if child not in seen:
                    queue.append(child)

            if len(entities) % 200 == 0:
                print(f"Scaricate {len(entities)} entità...")
    finally:
        if handle is not None:
            handle.write("\n]\n")
            handle.close()

    print(f"Totale entità scaricate: {len(entities)}")
    return entities
