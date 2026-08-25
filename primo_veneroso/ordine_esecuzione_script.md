# Ordine di Esecuzione degli Script

## FASE 1: Estrazione dati grezzi

1. `mms/estrazione_mms.py`
   (Genera `mms_completo.json`)
2. `foundation/estrazione_foundation.py`
   (Genera `icd11_foundation_completo.json`)

---

## FASE 2: Creazione Dizionari di Supporto

3. `creazione_dict_insiemi_per_controlli/creazione_dict_controllo.py`
   (Legge i dati generati in Fase 1 e genera i file `file_controllo_uri_links_mms.json` e `file_controllo_uri_links_foundation.json`)

---

## FASE 3: Fusione Primaria (Merge)

4. `mms_foundation_merge/fusione_finale.py`
   (Unisce i dati e genera `fusione_con_campi_mancanti.json` oltre a `id_uri_non_unici_mancanti.json` per il debug)

---

## FASE 4: Sostituzione dei Link con Titoli

5. `sostituzione_link/link_substitution.py`
   (Legge `fusione_con_campi_mancanti.json` e i dizionari di controllo, e genera `fusione_sostituzione_link_dict_2.json`)

---

## FASE 5: Identificazione degli Orfani e delle Entità Esterne
Cerca di individuare quali titoli non possiedono un link all'interno del DB e li confrontiamo con MMS/Foundation per capire se sono davvero entità esterne (orfani totali) o se possiedono dei match nasconti ("fake orphans").
6. `non_mms/external_entities.py`
   (Legge `fusione_sostituzione_link_dict_2.json` e genera due file chiave: `titoli_con_link_recuperati.json` e `nuove_entity_esterne_finale.csv`)

---

### Altri Script Accessori (Opzionali/Post-Processing)
- `converti_csv/json_to_csv.py`: Da lanciare alla fine di tutto se hai bisogno di visualizzare o esportare i risultati JSON in formato tabellare.
- `valutazione_dati/definitions_comparison.py`: Si può usare per generare metriche e statistiche di discrepanza sui dati fusi.
- `creazione_dict_insiemi_per_controlli/creazione_insiemi.py` / `non_mms/not_mms_but_foundation.py`: Script utili solo a fini di debug o estrazione di sotto-elenchi, eseguibili indipendentemente sul DB già formato.
