# Integrazione ICD-11 (MMS & Foundation) per Sistemi RAG e Database Relazionali

Repository dedicato alla pipeline di elaborazione, normalizzazione e modellazione dei dataset di ICD-11, finalizzata alla strutturazione di una base dati relazionale e alla successiva vettorializzazione per l'interrogazione semantica mediante Large Language Models (LLM).

---

##  Obiettivi e Fasi del Progetto (al momento)

1. Estrazione e parsing dati ottenuti tramite i servizi containerizzati ufficiali dell'OMS (Docker) e parsing.
2. Fusione e ormalizzazione dei due dataset.
3. Modellazione relazionale (ER), definizione dello schema concettuale e logico per la memorizzazione strutturata su PostgreSQL.
4. Embedding e vettorializzazione dei dati per rappresentarli attraverso dei vettoriali

---

##  Accesso ai Dataset (Data Storage Esterno)

A causa delle limitazioni dimensionali imposte da GitHub, i dump JSON intermedi e finali generati sono ospitati su drive esterni.

| Risorsa | Dimensione Approssimativa | Descrizione | Link di Download |
| :--- | :--- | :--- | :--- |
| `mms_completo.json` | ~70 MB | Dump integrale della linearizzazione MMS | [Download Risorsa](https://drive.google.com/file/d/1n1QZtD0xo4Fc0ybf5CSfL9wirnpT9Cnw/view?usp=drive_link) |
| `icd11_foundation_completo.json` | ~50 MB | Dump integrale della Foundation | [Download Risorsa](https://drive.google.com/file/d/13VLy0HJjoTiamg-m80_612Xzs53qo7OF/view?usp=drive_link) |
| `fusione_con_campi_mancanti.json` | ~87 MB | merge dei due dataset | [Download Risorsa](https://drive.google.com/file/d/1DtW2znWHLLoROAp1HY3sD9OE11akLhXB/view?usp=drive_link)|

---
