#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
  ICD-11 Hybrid ETL — MMS + Foundation → Vector DB Base
═══════════════════════════════════════════════════════════════════════════

Fonde mms_completo.json (array JSON, ~70 MB) e foundation_full.json
(dizionario JSON con chiavi localhost, ~53 MB) in un unico dataset JSONL
pronto per il chunking e l'indicizzazione vettoriale (RAG).

Architettura in 3 fasi:
  1) Indicizzazione Foundation su SQLite (streaming con ijson)
  2) Costruzione lookup MMS @id → nodo (streaming con ijson)
  3) Fusione finale: per ogni nodo MMS si fa lookup Foundation via
     campo "source", si risolve la gerarchia parent, e si produce
     un documento testuale strutturato per l'LLM

Output:  icd11_vectordb_base.jsonl  (un JSON per riga)

Dipendenze:
    pip install ijson

Uso:
    python build_vectordb_base.py
"""

import ijson
import sqlite3
import json
import logging
import os
import re
import sys
import time

# ─── Configurazione ──────────────────────────────────────────────────────
MMS_FILE = "mms_completo.json"
FOUNDATION_FILE = "foundation_full.json"
OUTPUT_FILE = "icd11_vectordb_base.jsonl"
SQLITE_INDEX = "foundation_index.sqlite"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("icd11_etl")


# ═══════════════════════════════════════════════════════════════════════════
# Utility
# ═══════════════════════════════════════════════════════════════════════════

def extract_value(field, default=""):
    """Estrae testo da {'@language': ..., '@value': ...} o stringa diretta."""
    if isinstance(field, dict):
        val = field.get("@value", default)
        if isinstance(val, str):
            # Rimuovi eventuale prefisso markdown di ICD-11
            val = re.sub(r"^!markdown\s*\n?", "", val)
            return val.strip()
        return default
    if isinstance(field, str):
        return field.strip()
    return default


def extract_labels(items_list):
    """Estrae le stringhe da una lista di oggetti {'label': {'@value': ...}}."""
    results = []
    if not items_list:
        return results
    if not isinstance(items_list, list):
        items_list = [items_list]
    for item in items_list:
        try:
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            if isinstance(label, dict):
                val = label.get("@value")
                if isinstance(val, str) and val.strip():
                    results.append(val.strip())
            elif isinstance(label, str) and label.strip():
                results.append(label.strip())
        except Exception:
            pass
    return results


def dedup_ordered(*lists):
    """Unisce più liste deduplicando e preservando l'ordine."""
    merged = []
    for lst in lists:
        if lst:
            merged.extend(lst)
    return list(dict.fromkeys(merged))


def extract_entity_id(uri):
    """Estrae l'ID numerico dall'URI WHO o localhost.
    
    http://id.who.int/icd/entity/1435254666       → 1435254666
    http://id.who.int/icd/release/11/2026-01/mms/1435254666 → 1435254666
    http://localhost/icd/entity/1435254666          → 1435254666
    """
    if not uri or not isinstance(uri, str):
        return None
    # Prendi l'ultimo segmento numerico dell'URI
    match = re.search(r"/(\d+)$", uri)
    if match:
        return match.group(1)
    return None


# ═══════════════════════════════════════════════════════════════════════════
# FASE 1: Indicizzazione Foundation su SQLite
# ═══════════════════════════════════════════════════════════════════════════

def build_foundation_index(foundation_path, db_path, batch_size=5000):
    """
    foundation_full.json è un DIZIONARIO con chiavi tipo:
      "http://localhost/icd/entity/12345": { ... }
    
    Usiamo ijson per parsare le coppie chiave-valore senza caricare
    tutto in RAM. Le indicizziamo per entity_id numerico.
    """
    log.info("📦 Fase 1/3 — Indicizzazione Foundation su SQLite...")
    
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("""
        CREATE TABLE foundation (
            entity_id TEXT PRIMARY KEY,
            payload   TEXT NOT NULL
        )
    """)

    count = 0
    errors = 0
    batch = []

    with open(foundation_path, "rb") as f:
        # ijson: iteriamo sulle coppie chiave-valore del dizionario radice.
        # Il prefisso vuoto "" con items ci dà l'intero dict; usiamo
        # invece un approccio più efficiente: leggiamo ogni sotto-oggetto.
        #
        # Per un dict top-level, ijson non ha un modo diretto di iterare
        # k-v in streaming. Usiamo il pattern con kvitems che ci dà
        # (key, value) per ogni entry del dizionario radice.
        parser = ijson.kvitems(f, "")
        for key, entity in parser:
            try:
                # Salta la root metadata
                if not isinstance(entity, dict):
                    continue
                
                entity_id = extract_entity_id(key)
                if not entity_id:
                    # Prova con @id interno
                    entity_id = extract_entity_id(entity.get("@id", ""))
                if not entity_id:
                    continue

                # Salva solo i campi necessari per la fusione
                compact = {
                    "definition": extract_value(entity.get("definition")),
                    "longDefinition": extract_value(entity.get("longDefinition")),
                    "fullySpecifiedName": extract_value(entity.get("fullySpecifiedName")),
                    "synonym": extract_labels(entity.get("synonym", [])),
                    "indexTerm": extract_labels(entity.get("indexTerm", [])),
                    "inclusion": extract_labels(entity.get("inclusion", [])),
                    "exclusion": extract_labels(entity.get("exclusion", [])),
                    "narrowerTerm": extract_labels(entity.get("narrowerTerm", [])),
                    "title": extract_value(entity.get("title")),
                }

                batch.append((entity_id, json.dumps(compact, ensure_ascii=False)))
                count += 1

                if len(batch) >= batch_size:
                    conn.executemany(
                        "INSERT OR REPLACE INTO foundation (entity_id, payload) VALUES (?, ?)",
                        batch,
                    )
                    conn.commit()
                    batch.clear()
                    log.info("   Foundation indicizzata: %d nodi...", count)

            except Exception as e:
                errors += 1
                if errors <= 10:
                    log.warning("   Nodo Foundation scartato: %s", e)

    if batch:
        conn.executemany(
            "INSERT OR REPLACE INTO foundation (entity_id, payload) VALUES (?, ?)",
            batch,
        )
        conn.commit()

    conn.execute("CREATE INDEX IF NOT EXISTS idx_fnd_eid ON foundation(entity_id)")
    conn.commit()
    conn.close()

    log.info("   ✅ Foundation: %d nodi indicizzati, %d errori/scarti", count, errors)


# ═══════════════════════════════════════════════════════════════════════════
# FASE 2: Costruzione lookup MMS per gerarchia parent
# ═══════════════════════════════════════════════════════════════════════════

def build_mms_title_lookup(mms_path):
    """
    Costruisce un dizionario {mms_uri: title} per risolvere
    la gerarchia dei parent. Usiamo solo @id e title, ~50 MB
    non dovrebbe essere un problema.
    """
    log.info("📦 Fase 2/3 — Costruzione lookup titoli MMS per gerarchia...")
    
    lookup = {}
    count = 0
    
    with open(mms_path, "rb") as f:
        for node in ijson.items(f, "item"):
            try:
                node_id = node.get("@id", "")
                title = extract_value(node.get("title"))
                if node_id and title:
                    lookup[node_id] = {
                        "title": title,
                        "code": node.get("code", ""),
                        "classKind": node.get("classKind", ""),
                        "parent": node.get("parent", []),
                    }
                count += 1
                if count % 10000 == 0:
                    log.info("   MMS scansionati per lookup: %d...", count)
            except Exception:
                pass

    log.info("   ✅ Lookup MMS: %d nodi con titolo", len(lookup))
    return lookup


def resolve_hierarchy(mms_node, mms_lookup, max_depth=10):
    """
    Risale l'intera gerarchia parent→grandparent→...→chapter
    costruendo il percorso completo:
    'Diseases of the circulatory system [11] > Cardiac arrhythmias [MC80-MC8Z] > ...'
    """
    parents = mms_node.get("parent", [])
    if not parents:
        return "N/A"
    
    chain = []
    visited = set()
    current_uri = parents[0] if parents else None
    
    while current_uri and current_uri not in visited and len(chain) < max_depth:
        visited.add(current_uri)
        
        # Fermiamoci prima della root MMS
        if current_uri.endswith("/mms"):
            break
        
        info = mms_lookup.get(current_uri)
        if not info:
            break
        
        title = info["title"]
        code = info.get("code", "")
        
        label = f"{title}" + (f" [{code}]" if code else "")
        chain.append(label)
        
        # Risali al parent successivo
        parent_parents = info.get("parent", [])
        current_uri = parent_parents[0] if parent_parents else None
    
    chain.reverse()
    return " > ".join(chain) if chain else "N/A"


# ═══════════════════════════════════════════════════════════════════════════
# FASE 3: Fusione e produzione output
# ═══════════════════════════════════════════════════════════════════════════

def build_hybrid_dataset(mms_path, db_path, output_path, mms_lookup):
    """
    Scorre tutti i nodi MMS in streaming.
    Per ognuno:
     - Risolve il Foundation corrispondente via campo "source"
     - Costruisce la gerarchia parent
     - Produce un documento testuale strutturato
     - Scrive in JSONL
    """
    log.info("📦 Fase 3/3 — Fusione MMS + Foundation → %s", output_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    count = 0
    matched = 0
    errors = 0
    skipped_no_code = 0

    with open(mms_path, "rb") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        for mms_node in ijson.items(fin, "item"):
            try:
                code = mms_node.get("code", "")
                title = extract_value(mms_node.get("title"))
                class_kind = mms_node.get("classKind", "")
                
                # Salta nodi senza codice e senza titolo (root, metadata)
                if not title:
                    skipped_no_code += 1
                    continue
                
                # ── Gerarchia parent (catena completa fino al capitolo) ──
                hierarchy = resolve_hierarchy(mms_node, mms_lookup)
                
                # ── Dati MMS ──
                mms_synonyms = extract_labels(mms_node.get("indexTerm", []))
                mms_inclusions = extract_labels(mms_node.get("inclusion", []))
                mms_exclusions = extract_labels(mms_node.get("exclusion", []))
                mms_definition = extract_value(mms_node.get("definition"))
                mms_long_def = extract_value(mms_node.get("longDefinition"))
                coding_note = extract_value(mms_node.get("codingNote"))
                block_id = mms_node.get("blockId", "")
                code_range = mms_node.get("codeRange", "")
                
                # Dati specifici MMS per foundationChildElsewhere
                fce_terms = extract_labels(mms_node.get("foundationChildElsewhere", []))
                
                # ── Lookup Foundation ──
                source_uri = mms_node.get("source", "")
                entity_id = extract_entity_id(source_uri)
                
                fnd_definition = ""
                fnd_long_def = ""
                fnd_fully_specified = ""
                fnd_synonyms = []
                fnd_index_terms = []
                fnd_inclusions = []
                fnd_exclusions = []
                fnd_narrower = []
                
                if entity_id:
                    cur.execute(
                        "SELECT payload FROM foundation WHERE entity_id = ?",
                        (entity_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        fnd = json.loads(row[0])
                        fnd_definition = fnd.get("definition", "")
                        fnd_long_def = fnd.get("longDefinition", "")
                        fnd_fully_specified = fnd.get("fullySpecifiedName", "")
                        fnd_synonyms = fnd.get("synonym", [])
                        fnd_index_terms = fnd.get("indexTerm", [])
                        fnd_inclusions = fnd.get("inclusion", [])
                        fnd_exclusions = fnd.get("exclusion", [])
                        fnd_narrower = fnd.get("narrowerTerm", [])
                        matched += 1
                
                # ── Composizione campi fusi ──
                
                # Definizione: preferisci Foundation, poi MMS
                definition = fnd_long_def or fnd_definition or mms_long_def or mms_definition or ""
                
                # Sinonimi unificati (deduplicati)
                all_synonyms = dedup_ordered(mms_synonyms, fnd_synonyms, fnd_index_terms)
                # Rimuovi il titolo stesso dai sinonimi se presente
                all_synonyms = [s for s in all_synonyms if s.lower() != title.lower()]
                
                # Inclusioni unificate
                all_inclusions = dedup_ordered(
                    mms_inclusions, fnd_inclusions, fnd_narrower, fce_terms
                )
                
                # ── Record JSON ──
                record = {
                    "mms_uri": mms_node.get("@id", ""),
                    "foundation_uri": source_uri,
                    "code": code or block_id or "N/A",
                    "title": title,
                    "fullySpecifiedName": fnd_fully_specified if fnd_fully_specified and fnd_fully_specified.lower() != title.lower() else "",
                    "classKind": class_kind,
                    "blockId": block_id,
                    "codeRange": code_range,
                    "hierarchy": hierarchy,
                    "definition": definition,
                    "coding_note": coding_note,
                    "synonyms": all_synonyms,
                    "inclusions": all_inclusions,
                    "exclusions_foundation": fnd_exclusions,
                    "exclusions_mms": mms_exclusions,
                    "foundation_matched": entity_id is not None and matched > 0,
                }
                
                fout.write(json.dumps(record, ensure_ascii=False))
                fout.write("\n")
                
                count += 1
                if count % 5000 == 0:
                    log.info("   Nodi fusi: %d (matched Foundation: %d)...", count, matched)

            except Exception as e:
                errors += 1
                if errors <= 20:
                    log.warning("   Errore su nodo MMS: %s", e)

    conn.close()
    
    log.info("═" * 60)
    log.info("✅ FUSIONE COMPLETATA")
    log.info("   Nodi totali scritti:      %d", count)
    log.info("   Match con Foundation:     %d (%.1f%%)",
             matched, (matched / count * 100) if count else 0)
    log.info("   Nodi senza titolo saltati: %d", skipped_no_code)
    log.info("   Errori/scarti:            %d", errors)
    log.info("   Output: %s", output_path)
    log.info("═" * 60)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    start = time.time()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    mms_path = os.path.join(script_dir, MMS_FILE)
    fnd_path = os.path.join(script_dir, FOUNDATION_FILE)
    out_path = os.path.join(script_dir, OUTPUT_FILE)
    db_path = os.path.join(script_dir, SQLITE_INDEX)
    
    # Verifica file esistenti
    for label, path in [("MMS", mms_path), ("Foundation", fnd_path)]:
        if not os.path.isfile(path):
            log.error("❌ File %s non trovato: %s", label, path)
            sys.exit(1)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        log.info("📄 %s: %s (%.1f MB)", label, path, size_mb)
    
    log.info("")
    
    # Fase 1: Indicizza Foundation
    build_foundation_index(fnd_path, db_path)
    log.info("")
    
    # Fase 2: Lookup titoli MMS per gerarchia
    mms_lookup = build_mms_title_lookup(mms_path)
    log.info("")
    
    # Fase 3: Fusione
    build_hybrid_dataset(mms_path, db_path, out_path, mms_lookup)
    
    elapsed = time.time() - start
    log.info("")
    log.info("⏱  Tempo totale: %.1f secondi (%.1f minuti)", elapsed, elapsed / 60)
    
    # Cleanup opzionale dell'indice SQLite
    log.info("💡 L'indice SQLite '%s' può essere eliminato se non serve più.", db_path)


if __name__ == "__main__":
    main()
