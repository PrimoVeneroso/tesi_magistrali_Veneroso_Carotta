"""Configurazione della pipeline ICD-11, indipendente dalla release."""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_RELEASE = "2026-01"
DEFAULT_LINEARIZATION = "mms"
DEFAULT_LANGUAGE = "en"
CANONICAL_HOST = "http://id.who.int"
DEFAULT_API_BASE = "http://localhost"


@dataclass(frozen=True)
class Settings:
    """Parametri di una estrazione/fusione ICD-11.

    La release non va mai scritta negli script: si passa da CLI, env o questo oggetto.
    URI canonici WHO restano su id.who.int; l'API locale (Docker) si usa solo in fetch.
    """

    release: str = DEFAULT_RELEASE
    linearization: str = DEFAULT_LINEARIZATION
    language: str = DEFAULT_LANGUAGE
    api_base: str = DEFAULT_API_BASE
    canonical_host: str = CANONICAL_HOST
    api_version: str = "v2"

    @classmethod
    def from_env(cls, **overrides: str) -> "Settings":
        values = {
            "release": os.environ.get("ICD11_RELEASE", DEFAULT_RELEASE),
            "linearization": os.environ.get("ICD11_LINEARIZATION", DEFAULT_LINEARIZATION),
            "language": os.environ.get("ICD11_LANGUAGE", DEFAULT_LANGUAGE),
            "api_base": os.environ.get("ICD11_API_BASE", DEFAULT_API_BASE),
            "canonical_host": os.environ.get("ICD11_CANONICAL_HOST", CANONICAL_HOST),
            "api_version": os.environ.get("ICD11_API_VERSION", "v2"),
        }
        values.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**values)

    @property
    def linearization_root(self) -> str:
        return (
            f"{self.canonical_host}/icd/release/11/"
            f"{self.release}/{self.linearization}"
        )

    @property
    def linearization_root_unversioned(self) -> str:
        """Senza release: l'API restituisce l'elenco delle release disponibili."""
        return f"{self.canonical_host}/icd/release/11/{self.linearization}"

    @property
    def foundation_root(self) -> str:
        return f"{self.canonical_host}/icd/entity"

    def headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "API-Version": self.api_version,
            "Accept-Language": self.language,
        }

    def to_local(self, uri: str) -> str:
        return uri.replace(self.canonical_host, self.api_base)
