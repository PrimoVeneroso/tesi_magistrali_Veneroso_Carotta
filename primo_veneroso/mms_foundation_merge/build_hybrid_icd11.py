#!/usr/bin/env python3
"""
ETL per fondere ICD-11 MMS e Foundation in un unico dataset "ibrido"
ottimizzato per il chunking e l'indicizzazione in un Vector DB (RAG).

Progettato per file di diversi GB senza saturare la RAM:
  - la Foundation viene letta a flusso (ijson) e indicizzata su disco
    (SQLite), salvando solo i campi realmente necessari per ogni nodo
    (non l'oggetto raw completo)
  - l'MMS viene letto anch'esso a flusso; per ogni nodo si fa una
    lookup SQLite sul foundationReference
  - l'output viene scritto in streaming (JSON Lines), senza mai tenere
    l'intero dataset fuso in memoria

Dipendenze:
    pip install ijson

Uso:
    python build_hybrid_icd11.py \
        --mms mms_completo.json \
        --foundation foundation_completo.json \
        --output mms_ibrido_vettoriale.jsonl
"""

import argparse
import ijson
import sqlite3
import json
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("icd11_etl")


# ---------------------------------------------------------------------------
# Utility di estrazione testo, robuste a strutture malformate
# ---------------------------------------------------------------------------
def extract_text(items_list):
    """Estrae le stringhe da liste di oggetti {'label': {'@value': ...}}.
    Tollera elementi mancanti, malformati o con tipi inattesi, senza
    interrompere la pipeline."""
    results = []
    if not items_list:
        return results
    if not isinstance(items_list, list):
        items_list = [items_list]  # a volte l'API restituisce un oggetto singolo

    for item in items_list:
        try:
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            if isinstance(label, dict):
                value = label.get("@value")
                if isinstance(value, str) and value.strip():
                    results.append(value.strip())
            elif isinstance(label, str) and label.strip():
                # fallback difensivo per schemi non standard
                results.append(label.strip())
        except Exception as e:
            log.debug("Elemento malformato ignorato in extract_text: %r (%s)", item, e)
    return results


def extract_single_value(field, default=""):
    """Estrae un singolo campo testuale tipo {'@value': ...}, con fallback."""
    try:
        if isinstance(field, dict):
            value = field.get("@value")
            return value if isinstance(value, str) else default
        if isinstance(field, str):
            return field
    except Exception:
        pass
    return default


def dedup_preserve_order(*lists):
    """Deduplica preservando l'ordine di prima apparizione.
    Più leggibile e deterministico di list(set(...)); stesso costo O(n)."""
    merged = []
    for lst in lists:
        merged.extend(lst)
    return list(dict.fromkeys(merged))


# ---------------------------------------------------------------------------
# Fase 1: indicizzazione della Foundation su SQLite (streaming, non in RAM)
# ---------------------------------------------------------------------------
def build_foundation_index(foundation_filepath, db_path, batch_size=5000):
    if os.path.exists(db_path):
        os.remove(db_path)  # indice rigenerabile, si riparte pulito ad ogni run

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA synchronous = OFF")   # ok: l'indice è rigenerabile da zero
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute(
        "CREATE TABLE foundation (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
    )

    count = 0
    errors = 0
    batch = []

    with open(foundation_filepath, "rb") as f:
        for item in ijson.items(f, "item"):
            try:
                fid = item.get("@id")
                if not fid:
                    errors += 1
                    continue

                # Salvo SOLO i campi che serviranno nella fusione: questo è
                # il punto chiave che evita di ricreare il problema di RAM
                # spostandolo semplicemente dal file JSON al dizionario Python.
                compact = {
                    "inclusion": extract_text(item.get("inclusion", [])),
                    "exclusion": extract_text(item.get("exclusion", [])),
                    "synonym": extract_text(item.get("synonym", [])),
                    "definition": extract_single_value(item.get("definition")),
                }
                batch.append((fid, json.dumps(compact, ensure_ascii=False)))
                count += 1

                if len(batch) >= batch_size:
                    conn.executemany(
                        "INSERT OR REPLACE INTO foundation (id, payload) VALUES (?, ?)",
                        batch,
                    )
                    conn.commit()
                    batch.clear()
                    log.info("Foundation indicizzata: %d nodi...", count)

            except Exception as e:
                errors += 1
                log.warning("Nodo Foundation scartato per errore: %s", e)

    if batch:
        conn.executemany(
            "INSERT OR REPLACE INTO foundation (id, payload) VALUES (?, ?)", batch
        )
        conn.commit()

    conn.execute("CREATE INDEX IF NOT EXISTS idx_foundation_id ON foundation(id)")
    conn.commit()
    conn.close()

    log.info(
        "Indicizzazione Foundation completata: %d nodi, %d errori/scarti.",
        count, errors,
    )


# ---------------------------------------------------------------------------
# Fase 2: fusione MMS + Foundation, output in streaming (JSON Lines)
# ---------------------------------------------------------------------------
def build_hybrid_database(mms_filepath, db_path, output_filepath, output_format="jsonl"):
    """
    output_format="jsonl": un oggetto JSON per riga. Comodo per pipeline RAG
        a valle: puoi rileggere e fare chunking riga per riga senza dover
        ri-parsare un array enorme con ijson.
    output_format="json": un unico array JSON valido (es. [ {...}, {...} ]),
        scritto comunque in streaming, senza mai tenere l'intero dataset
        in memoria contemporaneamente.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    count = 0
    errors = 0
    is_json_array = output_format == "json"

    with open(mms_filepath, "rb") as fin, \
         open(output_filepath, "w", encoding="utf-8") as fout:

        if is_json_array:
            fout.write("[\n")
        first = True

        for mms_node in ijson.items(fin, "item"):
            try:
                hybrid_node = {
                    "code": mms_node.get("code", "N/A"),
                    "title": extract_single_value(mms_node.get("title")),
                    "mms_exclusions": extract_text(mms_node.get("exclusion", [])),
                    "mms_inclusions": extract_text(mms_node.get("inclusion", [])),
                    "index_terms": extract_text(mms_node.get("indexTerm", [])),
                    "all_inclusions": [],
                    "all_search_terms": [],
                    "foundation_exclusions": [],
                    "definition": "",
                }

                foundation_ref = mms_node.get("foundationReference")
                found_payload = None

                if foundation_ref:
                    cur.execute(
                        "SELECT payload FROM foundation WHERE id = ?", (foundation_ref,)
                    )
                    row = cur.fetchone()
                    if row:
                        found_payload = json.loads(row[0])

                if found_payload:
                    hybrid_node["all_inclusions"] = dedup_preserve_order(
                        hybrid_node["mms_inclusions"], found_payload["inclusion"]
                    )
                    hybrid_node["all_search_terms"] = dedup_preserve_order(
                        hybrid_node["index_terms"], found_payload["synonym"]
                    )
                    hybrid_node["foundation_exclusions"] = found_payload["exclusion"]
                    hybrid_node["definition"] = found_payload["definition"]
                else:
                    hybrid_node["all_inclusions"] = hybrid_node["mms_inclusions"]
                    hybrid_node["all_search_terms"] = hybrid_node["index_terms"]
                    if foundation_ref:
                        log.warning(
                            "foundationReference non trovato: %s (code=%s)",
                            foundation_ref, hybrid_node["code"],
                        )

                if is_json_array:
                    if not first:
                        fout.write(",\n")
                    first = False
                    fout.write(json.dumps(hybrid_node, ensure_ascii=False, indent=2))
                else:
                    fout.write(json.dumps(hybrid_node, ensure_ascii=False))
                    fout.write("\n")

                count += 1
                if count % 2000 == 0:
                    log.info("MMS fusi: %d nodi...", count)

            except Exception as e:
                errors += 1
                log.warning("Nodo MMS scartato per errore: %s", e)

        if is_json_array:
            fout.write("\n]\n")

    conn.close()
    log.info("Fusione completata: %d nodi scritti, %d errori/scarti.", count, errors)


def main():
    parser = argparse.ArgumentParser(description="Fusione ICD-11 MMS + Foundation (streaming)")
    parser.add_argument("--mms", default="mms_completo.json")
    parser.add_argument("--foundation", default="foundation_completo.json")
    parser.add_argument("--output", default="mms_ibrido_vettoriale.json")
    parser.add_argument("--index-db", default="foundation_index.sqlite")
    parser.add_argument(
        "--format", choices=["json", "jsonl"], default="json",
        help="json = un unico array JSON valido; jsonl = un oggetto per riga",
    )
    args = parser.parse_args()

    log.info("1/2 - Indicizzazione Foundation su disco (SQLite)...")
    build_foundation_index(args.foundation, args.index_db)

    log.info("2/2 - Fusione MMS + Foundation con output in streaming (%s)...", args.format)
    build_hybrid_database(args.mms, args.index_db, args.output, output_format=args.format)

    log.info("Fatto. Output: %s", args.output)
    log.info("Indice SQLite mantenuto in: %s (puoi rimuoverlo se non ti serve più)", args.index_db)


if __name__ == "__main__":
    main()
