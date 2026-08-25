# Integrazione ICD-11 (MMS & Foundation) per Sistemi RAG e Database Relazionali

Repository dedicato alla pipeline di elaborazione, normalizzazione e modellazione dei dataset di ICD-11, finalizzata alla strutturazione di una base dati relazionale e alla successiva vettorializzazione per l'interrogazione semantica mediante Large Language Models (LLM).

---

##  Obiettivi e Fasi del Progetto (al momento)

1. Estrazione e parsing dati ottenuti tramite i servizi containerizzati ufficiali dell'OMS (Docker) e parsing.
Updated upstream
2. Fusione e normalizzazione dei due dataset.

   L'obiettivo di questa fase è arricchire il dataset MMS di base integrandolo con le informazioni aggiuntive presenti nel dataset Foundation, evitando duplicati. La logica di unione prevede:
   * **Selezione e normalizzazione:** per ogni dataset vengono filtrate solo le classi di interesse e, per semplificare la struttura, si estrae direttamente il valore testuale (es. il contenuto della chiave `@value`) scartando l'intero dizionario originale.
   * **Arricchimento (Merge):** partendo dalla base MMS, si aggiungono i dati esclusivi della Foundation. Ad esempio, si confrontano i `parent` (creando un campo `other_parent`/`parent_foundation` per i genitori multipli della Foundation), si conservano entrambe le `definition` in caso di discordanza, e si uniscono `indexTerm` (MMS), i `synonym` (Foundation) e le `inclusion` (MMS e Foundation) in un unico campo consolidato privo di ripetizioni.

   -- Campi di Interesse (Dataset MMS) selezionati e normalizzati:
   * **`@id`**: solo link univoco MMS dell'entità (Stringa/URL).
   * **`title`**: nome dell'entità, estratto dal dizionario sotto la chiave `@value` (Stringa).
   * **`code`**: codice identificativo MMS (Testo).
   * **`source`**: solo link di riferimento all'entità corrispondente nella Foundation (Stringa/URL).
   * **`definition`** e **`longDefinition`**: testo della definizione, estratto dalla chiave `@value` (Stringa).
   * **`parent`** (e **`other_parent`/`parent_foundation`**): link MMS dell'entità padre. Durante l'unione viene creato `other_parent`/`parent_foundation` per accogliere eventuali padri multipli provenienti dalla Foundation (Link / Lista di Link).
   * **`child`**: lista dei link MMS diretti alle entità figlie (Lista di URL).
   * **`foundationChildElsewhere`**: rappresentazione dei figli nella Foundation che si trovano altrove nella gerarchia MMS (Lista di dizionari con label, foundationReference, linearizationReference).
   * **`indexTerm`** (MMS) / **`synonym`** (FOUND): campo unificato senza ripetizioni che raggruppa i termini di indicizzazione e i sinonimi (Lista di link).
   * **`inclusion`**: elenco delle condizioni/termini inclusi nella classificazione di quel codice (Lista di dizionari).
   * **`exclusion`**: elenco delle condizioni/termini esclusi dalla classificazione di quel codice (Lista di dizionari).
   * **`relatedEntitiesInMaternalChapter`** e **`relatedEntitiesInPerinatalChapter`**: riferimenti a entità correlate nei capitoli materno o perinatale (Lista di link FOUND).
   * **`classKind`**: tipologia di classe dell'entità, ad esempio "chapter", "block", "category", "window" (Testo).
   * **`postCoordinationScale`**: informazioni sulle scale di post-coordinazione (Lista di dizionari).
   * **`codingNote`**: note su come usare il codice, informazione estratta dalla chiave `@value` (Stringa).

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
   * **`EE` (Entità Esterne / Indici e Sinonimi Privi di URI)**: Lemmi diagnostici, descrittori lessicali, varianti sinonimiche e modificatori postcoordinativi estratti dagli array di indicizzazione (`indexTerms`, `synonyms`) che non corrispondono ad alcun URI formale all'interno del grafo primario.


4. Embedding e vettorializzazione dei dati per rappresentarli attraverso dei vettoriali

---

##  Accesso ai Dataset (Data Storage Esterno)

A causa delle limitazioni dimensionali imposte da GitHub, i dump JSON intermedi e finali generati sono ospitati su drive esterni.


| Risorsa | Dimensione Approssimativa | Descrizione | Download Primo | Download Federica |
| :--- | :--- | :--- | :--- | :--- |
| `mms_completo.json``icd11_mms_full.json` | ~70-45 MB | Dump integrale della linearizzazione MMS | [Download Primo](https://drive.google.com/file/d/1n1QZtD0xo4Fc0ybf5CSfL9wirnpT9Cnw/view?usp=drive_link) | [Download Federica](https://drive.google.com/file/d/13y-OjEhNrhZmHvwCnW6JB5bqCsDMbNRg/view?usp=sharing) |
| `icd11_foundation_completo.json``icd11_foundation_full.json` | ~50-60 MB | Dump integrale della Foundation | [Download Primo](https://drive.google.com/file/d/13VLy0HJjoTiamg-m80_612Xzs53qo7OF/view?usp=drive_link) | [Download Federica](https://drive.google.com/file/d/1NaJQ45s2uLXIX7fNncq6SwvYI3llsbYo/view?usp=sharing) |
| `fusione_con_campi_mancanti.json``icd11_dati_uniti.json` | ~87MB-1GB | merge dei due dataset | [Download Primo](https://drive.google.com/file/d/1YNA6ffvtgXQdevWvzx2XNWP5maRKdjG9/view?usp=sharings) | [Download Federica](https://drive.google.com/file/d/1NaJQ45s2uLXIX7fNncq6SwvYI3llsbYo/view?usp=sharing) |
---


```
===================================================================================
                                 PROBLEMI
===================================================================================

```


- Problemi generici nel corso della stesura degli script:
   - come articolare la puliza del dataset (quali dati togliere e quali tenere, quali link usare)
   - come normalizzarlo (quante enetità sono davvero Esterne, come lo controllo se ho sbglaito o meno?)
   - generalizzazione a altre versioni ??
