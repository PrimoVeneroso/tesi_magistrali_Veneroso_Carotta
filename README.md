# Integrazione ICD-11 (MMS & Foundation) per Sistemi RAG e Database Relazionali

Repository dedicato alla pipeline di elaborazione, normalizzazione e modellazione dei dataset di ICD-11, finalizzata alla strutturazione di una base dati relazionale e alla successiva vettorializzazione per l'interrogazione semantica mediante Large Language Models (LLM).

---

##  Obiettivi e Fasi del Progetto (al momento)

1. Estrazione e parsing dati ottenuti tramite i servizi containerizzati ufficiali dell'OMS (Docker) e parsing.
2. Fusione e normalizzazione dei due dataset.

   L'obiettivo di questa fase è arricchire il dataset MMS di base integrandolo con le informazioni aggiuntive presenti nel dataset Foundation, evitando duplicati. La logica di unione prevede:
   * **Selezione e normalizzazione:** per ogni dataset vengono filtrate solo le classi di interesse e, per semplificare la struttura, si estrae direttamente il valore testuale (es. il contenuto della chiave `@value`) scartando l'intero dizionario originale.
   * **Arricchimento (Merge):** partendo dalla base MMS, si aggiungono i dati esclusivi della Foundation (entità EF incluse, non scartate). Si confrontano i `parent` (campo `other_parents` per i genitori extra della Foundation) e si conservano entrambe le `definition` in caso di discordanza. `indexTerm`, `synonym` e `inclusion` restano campi distinti.

   -- Campi di Interesse (Dataset MMS) selezionati e normalizzati:
   * **`@id`**: solo link univoco MMS dell'entità (Stringa/URL).
   * **`title`**: nome dell'entità, estratto dal dizionario sotto la chiave `@value` (Stringa).
   * **`code`**: codice identificativo MMS (Testo).
   * **`source`**: solo link di riferimento all'entità corrispondente nella Foundation (Stringa/URL).
   * **`definition`** e **`longDefinition`**: testo della definizione, estratto dalla chiave `@value` (Stringa).
   * **`parent`** (e **`other_parent`/`parent_foundation`**): link MMS dell'entità padre. Durante l'unione viene creato `other_parent`/`parent_foundation` per accogliere eventuali padri multipli provenienti dalla Foundation (Link / Lista di Link).
   * **`child`**: lista dei link MMS diretti alle entità figlie (Lista di URL).
   * **`foundationChildElsewhere`**: rappresentazione dei figli nella Foundation che si trovano altrove nella gerarchia MMS (Lista di dizionari con label, foundationReference, linearizationReference).
   * **`indexTerm`** (MMS) e **`synonym`** (Foundation): campi distinti; non vanno uniti alle `inclusion`.
   * **`inclusion`**: elenco delle condizioni/termini inclusi nella classificazione di quel codice (Lista di dizionari).
   * **`exclusion`**: elenco delle condizioni/termini esclusi dalla classificazione di quel codice (Lista di dizionari).
   * **`relatedEntitiesInMaternalChapter`** e **`relatedEntitiesInPerinatalChapter`**: riferimenti a entità correlate nei capitoli materno o perinatale (Lista di link FOUND).
   * **`classKind`**: tipologia di classe dell'entità, ad esempio "chapter", "block", "category", "window" (Testo).
   * **`postCoordinationScale`**: informazioni sulle scale di post-coordinazione (Lista di dizionari).
   * **`codingNote`**: note su come usare il codice, informazione estratta dalla chiave `@value` (Stringa).
   
   -- Dove presenti solo link il dato è stato successivamente modificato in modo da avere sempre un dizionario con Title, foundationReference e linearizationReference

3. Modellazione relazionale (ER), definizione dello schema concettuale e logico per la memorizzazione strutturata su PostgreSQL.

   La sfida principale in questa fase è la definizione delle chiavi e delle relazioni, poiché manca un URI universale utilizzabile come ID univoco assoluto. 
  Molti elementi presentano asimmetrie: alcuni sinonimi sono privi di reference, mentre diverse entità esistono esclusivamente nel dataset Foundation o solo in quello MMS. 
   Sarà quindi necessario prendere una decisione architetturale cruciale: 
   * Generare e assegnare un nuovo **ID univoco sintetico** (surrogate key) a livello di database per mantenere tutti i dati consolidati in un'unica struttura coerente?
   * Oppure dividere e normalizzare i dati in tabelle separate? (vedi schema sotto)
  
   ```
                           ┌──────────────────────────┐
                           │   ENTITÀ ICD-11 GLOBALI  │
                           └─────────────┬────────────┘
                                          │
               ┌──────────────────────────┼──────────────────────────┐
               ▼                          ▼                          ▼
   ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
   │         EM          │    │         EF          │    │         EE          │
   │   (Entità MMS +     │    │  (Entità Foundation │    │   (Entità Esterne / │
   │    Foundation)      │    │        Only)        │    │    Index & Synonym) │
   └─────────────────────┘    └─────────────────────┘    └─────────────────────┘

   ```

   * **`EM` (Entità MMS / Fusa)**: Concetti ontologici presenti nella linearizzazione MMS, ma non tutti  provvisti di corrispondenza nella Foundation(es. gli other o gli unspecified che hanno un codice ICD ma non un'entità nel grafo e vengono generati unicamente durante la linearizzazione). Possiedono codifica nosologica alfanumerica, URI Foundation e `browserUrl` MMS.
   * **`EF` (Entità Foundation Only)**: Nodi ontologici appartenenti unicamente alla Foundation Component, privi di codice statistico MMS primario, ma fungenti da collegamento concettuale o entità progenitrici/discendenti non linearizzate.
   * **EE (Entità Esterne / Indici e Sinonimi senza URI):** Termini diagnostici, sinonimi e descrittori (estratti dagli array `indexTerms` e `synonyms`) che non sono collegati ad alcun URI ufficiale all'interno della struttura principale.


4. Embedding e vettorializzazione dei dati per rappresentarli attraverso dei vettoriali

---

##  Accesso ai Dataset (Data Storage Esterno)

A causa delle limitazioni dimensionali imposte da GitHub, i dump JSON intermedi e finali generati sono ospitati su drive esterni.


| Risorsa | Dimensione Approssimativa | Descrizione | Download Primo | Download Federica |
| :--- | :--- | :--- | :--- | :--- |
| `mms_completo.json``icd11_mms_full.json` | ~70-45 MB | Dump integrale della linearizzazione MMS | [Download Primo](https://drive.google.com/file/d/1n1QZtD0xo4Fc0ybf5CSfL9wirnpT9Cnw/view?usp=drive_link) | [Download Federica](https://drive.google.com/file/d/13y-OjEhNrhZmHvwCnW6JB5bqCsDMbNRg/view?usp=sharing) |
| `icd11_foundation_completo.json``icd11_foundation_full.json` | ~50-60 MB | Dump integrale della Foundation | [Download Primo](https://drive.google.com/file/d/13VLy0HJjoTiamg-m80_612Xzs53qo7OF/view?usp=drive_link) | [Download Federica](https://drive.google.com/file/d/1NaJQ45s2uLXIX7fNncq6SwvYI3llsbYo/view?usp=sharing) |
| `fusione_con_campi_mancanti.json` / `icd11_dati_uniti.json` | ~87MB–1GB | merge dei due dataset | [Download Primo](https://drive.google.com/file/d/1YNA6ffvtgXQdevWvzx2XNWP5maRKdjG9/view?usp=sharing) | (il link Drive coincidente con la Foundation va sostituito con il file di merge reale) |

---

## Decisioni sui tre problemi aperti

Le risposte operative sono nel pacchetto `pipeline/` e sono verificate da `pytest`.
Gli script in `primo_veneroso/` e `Federica_Carotta/` restano il lavoro originale; per pulizia, classificazione e versioni usare la pipeline condivisa.

### 1. Pulizia: cosa tenere, cosa togliere, quali link usare

Tenere solo i campi utili a RAG e allo schema relazionale. Scartare `@context` e i wrapper linguistici: di `title`, `definition`, `longDefinition`, `codingNote`, `fullySpecifiedName` si conserva `@value`.

**Non collassare** `indexTerm`, `synonym` e `inclusion` in un unico campo: sono ruoli diversi (indicizzazione MMS, variante lessicale Foundation, diagnosi compresa nella categoria).

Identità e join:

1. **Foundation URI** (`source` in MMS, `@id` in Foundation) = identità ontologica. È la chiave di join.
2. **MMS URI** (`@id` della linearizzazione) = identità statistica; contiene la release e non va usata come PK universale.
3. **Il titolo non è una chiave.** In ICD-11 è ambiguo (`Other`, `Unspecified`, titoli ripetuti).

Ogni riferimento (parent, child, exclusion, …) va materializzato come `{title, foundationReference, linearizationReference}`, tenendo entrambi i link quando esistono. Policy eseguibile: `pipeline/fields.py`.

### 2. Normalizzazione EM / EF / EE e come verificare di non aver sbagliato

Non sono tre “tipi di malattia”. Sono tre ruoli rispetto al grafo WHO:

| Classe | Cos'è | Come si ottiene |
| :--- | :--- | :--- |
| **EM** | Nodo della linearizzazione MMS, *inclusi* radice e residui `other`/`unspecified` | 1-1 con il dump MMS |
| **EF** | Nodo Foundation il cui `@id` non è mai `source` di un EM | Foundation dump − `{mms.source}` |
| **EE** | Termine lessicale (index/synonym/inclusion/exclusion/…) senza URI | Non è un nodo ICD; in PostgreSQL è una tabella di termini con surrogate key `ee:…` |

Recupero dei “falsi orfani”: se un termine non ha URI ma il titolo coincide **in modo univoco** con un EM/EF, e non è un residuo corto (`other`, `unspecified`, …), il link si ricostruisce. Se il titolo è ambiguo, **non** si assegna un URI.

Controllo automatico (`python -m pipeline audit`):

- `|EM| = |dump MMS|` e nessuna Foundation-only persa
- ogni EF è una Foundation mai usata come `source`
- nessuna EE ha un titolo univoco tra EM/EF
- gli URI citati ma assenti dai dump sono elencati come *dangling*, non silenziati

Se l'audit è `PASS`, i numeri di EE sono quelli veri (termini lessicali), non un misto di orfani, residui e Foundation perse.

### 3. Generalizzazione ad altre versioni

La release (`2024-01`, `2025-01`, `2026-01`, …) e la linearizzazione (`mms`) non vanno scritte negli script. Si passano da CLI o da variabili d'ambiente (`ICD11_RELEASE`, `ICD11_LINEARIZATION`, `ICD11_LANGUAGE`, `ICD11_API_BASE`).

L'identità dell'entità è l'ID numerico (più `/other` o `/unspecified`); la release sta in un campo `release` del record. Per elencare le release esposte dall'ICD-API Docker:

```bash
python -m pipeline releases
```

Estrazione di un'altra annualità:

```bash
python -m pipeline extract --target mms --release 2025-01 --out data/mms_2025-01.json
python -m pipeline extract --target foundation --out data/foundation.json
```

Anche gli script originali di estrazione accettano `--release`.

### Come eseguire la pipeline

```bash
python -m pip install -r requirements.txt

# 1. crawl (ICD-API Docker in ascolto su localhost)
python -m pipeline extract --target mms --release 2026-01 --out data/mms.json
python -m pipeline extract --target foundation --out data/foundation.json

# 2. fusione + classificazione + verifica
python -m pipeline merge --mms data/mms.json --foundation data/foundation.json --out data/merged.json
python -m pipeline classify --merged data/merged.json --out data/classified.json
python -m pipeline audit --merged data/classified.json --mms data/mms.json --foundation data/foundation.json --out data/audit.json

# test della logica (non servono i dump da 50–80 MB)
python -m pytest
```

Bug corretti negli script originali mentre si lavorava a questi tre punti:

- `Federica_Carotta/icd11_union_aggiornato.py`: in `create_lookup_title` si usava `mms_data` (l'intera lista) al posto di `element_mms`; lo script andava in crash. Lo stesso file duplicava ogni `postcoordinationScale`.
- `primo_veneroso/api/import_requests_json.py`: `le(...)` e `ensue_ascii=Flase`.
- Path assoluti `/home/primo/Scaricati/...` in export CSV e confronto definizioni.
- URI MMS con release hardcodata `2026-01` in estrazione e sostituzione link.
