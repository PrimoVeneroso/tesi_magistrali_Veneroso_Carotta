"""Policy di pulizia: quali campi tenere, quali scartare, quali link usare.

Questa è la risposta operativa al primo problema del README.
Le decisioni sono eseguite da `normalize.py`; qui restano esplicite e testabili.
"""

from __future__ import annotations

from typing import FrozenSet

# Metadati API / JSON-LD inutili per RAG e per lo schema relazionale.
DROP_ALWAYS: FrozenSet[str] = frozenset(
    {
        "@context",
        "language",
        "@language",
    }
)

# Wrapper linguistici WHO: si tiene solo `@value`.
VALUE_FIELDS: FrozenSet[str] = frozenset(
    {
        "title",
        "definition",
        "longDefinition",
        "codingNote",
        "fullySpecifiedName",
    }
)

# Liste di URI o di oggetti {label, foundationReference, linearizationReference}.
# Dopo la normalizzazione ogni elemento diventa
# {title, foundationReference, linearizationReference}.
REFERENCE_LIST_FIELDS: FrozenSet[str] = frozenset(
    {
        "parent",
        "child",
        "exclusion",
        "inclusion",
        "indexTerm",
        "synonym",
        "foundationChildElsewhere",
        "relatedEntitiesInMaternalChapter",
        "relatedEntitiesInPerinatalChapter",
    }
)

# Campi MMS da conservare nel record fuso.
MMS_KEEP: FrozenSet[str] = frozenset(
    {
        "code",
        "@id",
        "source",
        "title",
        "definition",
        "longDefinition",
        "codingNote",
        "fullySpecifiedName",
        "classKind",
        "browserUrl",
        "parent",
        "child",
        "exclusion",
        "inclusion",
        "indexTerm",
        "foundationChildElsewhere",
        "relatedEntitiesInMaternalChapter",
        "relatedEntitiesInPerinatalChapter",
        "postcoordinationScale",
    }
)

# Campi Foundation da conservare (oltre a quelli già coperti da MMS_KEEP).
FOUNDATION_KEEP: FrozenSet[str] = frozenset(
    {
        "@id",
        "title",
        "definition",
        "longDefinition",
        "fullySpecifiedName",
        "browserUrl",
        "parent",
        "child",
        "inclusion",
        "exclusion",
        "synonym",
    }
)

# inclusion ≠ synonym ≠ indexTerm: non vanno collassati in un unico campo.
# - indexTerm (MMS): termini di indicizzazione per la codifica
# - synonym (Foundation): varianti lessicali dell'entità ontologica
# - inclusion: diagnosi/condizioni comprese in quella categoria
KEEP_SEPARATE_TERM_FIELDS = True

# Quale URI è l'identità.
# 1) Foundation URI (`source` in MMS, `@id` in Foundation) = identità ontologica
# 2) MMS URI (`@id` della linearizzazione) = identità statistica, dipende dalla release
# 3) Il titolo NON è una chiave: in ICD-11 è ambiguo (residui "Other"/"Unspecified")
PRIMARY_JOIN = "mms.source == foundation.@id"
TITLE_MATCH_MIN_LENGTH = 4
TITLE_MATCH_BLOCKLIST: FrozenSet[str] = frozenset(
    {
        "other",
        "unspecified",
        "nos",
        "not otherwise specified",
        "not elsewhere classified",
        "other specified",
        "unspecified residual",
    }
)
