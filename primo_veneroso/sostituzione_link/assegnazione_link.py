import json


def inserimento_link_titolo_(elemento, dizionario_titles_lower, altre_entita_lower):

    #Risolve e associa il link a un'entità/titolo solo se ne è sprovvista.


    # Disambiguazione del tipo di dato (Dizionario vs Stringa)
    if isinstance(elemento, dict):
        titolo = elemento.get("title") or elemento.get("label", "")
        link_esistente = elemento.get("link")

        # Controllo preventivo: se il dizionario possiede già un link valido e non vuoto, lo restituisce intatto evitando elaborazioni ridondanti o sovrascritture.

        if link_esistente and str(link_esistente).strip() != "":
            print("link già presente: operazione non necessaria")
            return elemento
    elif isinstance(elemento, str):
        titolo = elemento
    else:
        print("c'è un errore: tipo di dato non valido\n")
        return {}

    #  Validazione del titolo
    if not titolo or not isinstance(titolo, str) or len(titolo.strip()) == 0:
        print("c'è un errore: stringa vuota\n")
        return {}

    # Applicazione di .strip() per rimuovere spaziature spurie ai margini
    titolo = titolo.strip()

    #converto il titolo in minuscolo per fare il match
    titolo_lower = titolo.lower()


    if titolo_lower in dizionario_titles_lower:
        dati_riferimento = dizionario_titles_lower[titolo_lower]
        if isinstance(dati_riferimento, dict):
            link_recuperato = dati_riferimento.get("link", "")
        else:
            link_recuperato = str(dati_riferimento)


        return {"title": titolo, "link": link_recuperato}

    #Risoluzione in entità note senza link (entità esterne già targettizzate)
    elif titolo_lower in altre_entita_lower:
        print("l'entità non ha link, ma è targettizzata come entità esterna. Return dict senza link.")
        return {"title": titolo, "link": ""}

    #Caso orfano (non ha link e non è nelle entità esterne targettizzate)
    else:
        print(f"titolo orfano (non presente né nei link né nelle entità esterne): {titolo}")
        return {"title": titolo, "link": ""}


print("carico i dati\n")

with open("fusione_sostituzione_link_dict_2.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("../non_mms/titoli_con_link_recuperati.json", "r", encoding="utf-8") as g:
    dict_titoli_links = json.load(g) # SONO DELL'MMMS NON FOUNDATIOJ

dict_titoli_links_lower = {}
for k, v in dict_titoli_links.items():
    dict_titoli_links_lower[k.lower()] = v

with open("../non_mms/nuove_entity_esterne_finale.csv", "r", encoding="utf-8") as h:
    entity_without_links_lower = set()  # Creiamo un insieme vuoto
    #Salvo tutte le entità direttamente in minuscolo
    for line in h:
            if line.strip():  # Se la riga non è vuota
                # Puliamo la riga, togliamo il punto e virgola e mettiamo in minuscolo
                riga_pulita = line.strip().replace(";", "").lower()
                entity_without_links_lower.add(riga_pulita)

print("dati caricati\n")

campi_da_controllare_liste = ["synonyms_foundation", "inclusion_mms"]
campi_da_controllare_dict = ["index_term_synonyms", "exclusion_mms"]

for item in data:


    for key in campi_da_controllare_liste:
        valori = item.get(key)
        if isinstance(valori, list) and valori:
            nuova_lista = []
            for elem in valori:
                if elem:  # Se l'elemento non è vuoto
                    # Chiamo la funzione ed estraggo il risultato
                    risultato = inserimento_link_titolo_(elem, dict_titoli_links_lower, entity_without_links_lower)
                    # Aggiungo il risultato alla nuova lista temporanea
                    nuova_lista.append(risultato)

    # Sostituisco la vecchia lista nell'item con quella nuova elaborata
            item[key] = nuova_lista



    # Passando direttamente il dizionario 'elem', la funzione estrae titolo e link internamente
    # e preserva gli elementi che possiedono già un link.
    for key in campi_da_controllare_dict:
        valori = item.get(key)
        if isinstance(valori, list) and valori:

            nuova_lista = []
            for elem in valori:
                if elem:  # Se l'elemento non è vuoto

                # Chiamo la funzione ed estraggo il risultato
                    risultato = inserimento_link_titolo_(elem, dict_titoli_links_lower, entity_without_links_lower)

                # Aggiungo il risultato alla nuova lista temporanea
                    nuova_lista.append(risultato)

            # Sostituisco la vecchia lista nell'item con quella nuova elaborata
            item[key] = nuova_lista


print("sto scrivendo il file...")
file_output = "fusione_per_db.json"
with open(file_output, "w", encoding="utf-8") as out:
    json.dump(data, out, indent=4, ensure_ascii=False)

print(f"Processo concluso. Dataset serializzato in: {file_output}")
