import json


# Caricamento dei dataset in formato JSON
with open("icd11_mms_full.json", "r", encoding="utf-8") as file:
    mms_data = json.load(file)

with open("icd11_foundation_full.json", "r", encoding="utf-8") as f:
    foundation_data = json.load(f)


### funzione di estrazione dei dati  
def extract_data1(dataset, fields_to_extract): ## quindi qui poi chiamo la funzione con il mio dataset e i miei fields_of_interest

    if not fields_to_extract: # se non c'è il mio campo di interesse, allora niente
        return []

    if isinstance(dataset, list): # se il dataset è una lista, creo una nuova lista dove metterò quello che mi interessa
        list_of_elements = []

        for element in dataset: # per ogni elemento nel dataset
            if isinstance(element, dict): # se l'elemento è un dizionario, creo un nuovo dizionario 
                    new_dict = {}

                    for field in fields_to_extract: # per ogni campo, dei miei campi di interesse, se il campo è nell'elemento allora lo aggiugno al nuovo dizionario 
                        if field in element:
                            new_dict[field] = element.get(field)
                    
                    list_of_elements.append(new_dict) # e poi aggiungo i nuovi dizionari alla mia nuova lista
        
        return list_of_elements

    elif isinstance(dataset, dict): # se il dataset invece è un dizionario, allora creo un nuovo dizionario dove metterò quello che mi interessa
        new_dict = {}
        for field in fields_to_extract: # per ogni campo quindi aggiungo al nuovo dizionario 
            new_dict[field] = dataset.get(field) 
        
        return new_dict

    else: # se il dataset non è nè una lista nè un dizionario (cosa che non dovrebbe essere, ma per stare certi lo mettiamo per evitare l'errore)
        print("i dati non sono nè una lista nè un dizionario")
        return []
    
### Funzione per creare un lookup per collegare ID - link di ogni elemento al suo titolo, prendendo i dati sia dalla Foundation che dall’MMS
def create_lookup_title(foundation_full_data, mms_full_data):
    lookup_title = {}

    # aggiungo i titoli della foundation
    for element_foundation in foundation_full_data: #per ogni elemeneto, recupero l'ID
        current_id_found = element_foundation.get("@id")

        if current_id_found: #se trovo l'ID, allora recupero il campo title 
            title_foundation_dict = element_foundation.get("title", {})

            if isinstance(title_foundation_dict, dict): #se il title però è un dizionario, estraggo il value e associo il suo valore all'id
                titolo_found = title_foundation_dict.get("@value", "")
                lookup_title[current_id_found] = titolo_found
            elif isinstance(title_foundation_dict, str): #se è una stringa 
                lookup_title[current_id_found] = title_foundation_dict

    # aggiungo/sovrascrivo i titoli dell'mms allo stesso modo 
    for mms_data in mms_full_data: #per ogni elemento prendo il titolo, se è dizionario estraggo value 
        title_mms_dict = mms_data.get("title", {})
        if not title_mms_dict:
            continue

        if isinstance(title_mms_dict, dict):
            titolo_mms = title_mms_dict.get("@value", "")
        else:
            titolo_mms = str(title_mms_dict)

        current_mms_link = mms_data.get("@id") #estraggo anche l'id e associo con il titolo 
        if current_mms_link: 
            lookup_title[current_mms_link] = titolo_mms
        
        current_source_uri = mms_data.get("source") #estraggo anche il campo source, e associo anche quello allo stesso titolo 
        if current_source_uri: 
            lookup_title[current_source_uri] = titolo_mms 

    return lookup_title

#### funzione per selezionare che informazioni prendere di quelle che ho estratto
def select_information(dataset, fields_to_extract, lookup_title=None, nome_dataset=""):

    if lookup_title is None: 
        lookup_title = {}
    
    elements_without_ref = {} ## mi serve dopo per vedere quanti elementi sono senza links

    extracted_data = extract_data1(dataset, fields_to_extract) ## uso la funzione di prima per estrarre intanto le info dei campi che mi interessano 

    selected_data = [] # creo una lista dove andrò a mettere le mie informazioni

    for element in extracted_data: # quindi per ogni elemento (che è un dizionario) di quelli estratti, creo un nuovo dizionario 
        processed_element = {} 

        for chiave, valore in element.items(): # per ogni chiave e valore 

            if isinstance (valore,str) or valore is None: # se il valore è una stringa, allora top tengo quel chiave:valore
                processed_element[chiave] = valore
            
            elif isinstance (valore,dict): # se il valore è un dizionario, sappiamo che quello che ci interessa è il @value, quindi prendo solo il @value
                processed_element[chiave] = valore.get("@value","")

            elif isinstance (valore,list): # se il valore è una lista, allora l'elaborazione è un po' più complicata ... cioè si ricomincia 
                processed_list = [] # creo una nuova lista dove mettere le info che mi interessano

                if chiave == "postcoordinationScale":
                    for scale_item in valore:
                        scale_entity_list = []
                        for entity_url in scale_item.get("scaleEntity", []):
                            if entity_url in lookup_title:
                                title_found = lookup_title[entity_url]
                            else:
                                url_parts = entity_url.rstrip('/').split('/')
                                last_element = url_parts[-1]
                                if last_element in ["other", "unspecified"]:
                                    entity_id = f"{url_parts[-2]}/{last_element}"
                                else:
                                    entity_id = last_element

                                if entity_id == "mms":
                                    title_found = "Nodo radice ICD-11"
                                else:
                                    title_found = "Titolo mancante"

                            chiave_ref = "foundationReference" if "/entity/" in entity_url else "linearizationReference"

                            scale_entity_list.append({
                                "title": title_found,
                                chiave_ref: entity_url
                            })

                        processed_list.append({
                            "@id": scale_item.get("@id", ""),
                            "requiredPostcoordination": scale_item.get("requiredPostcoordination", ""),
                            "allowMultipleValues": scale_item.get("allowMultipleValues", ""),
                            "scaleEntity": scale_entity_list
                        })

                else: 
                    for element_list in valore: # per ogni elemento vado a vedere di che tipo è: 
                        if isinstance(element_list,str): # se è una stringa, allora devo fare due cose (anche se so già che quasi sempre un link, ma meglio verificarlo)
                            if element_list.startswith("http"): #se l'elemento è un link, allora prima lo cerco nel mio lookup_title, se lo trovo allora salva il titolo associato --> così poi potrò avere titolo e link
                                if element_list in lookup_title:
                                    title_found = lookup_title[element_list]
                                else: 
                                    url_parts = element_list.rstrip('/').split('/') #se l'elemento è un link ma non è nel mio lookup_title, allora rimuove gli slash finali, spezza l'url in una lista di parole ogni volta che incontra uno slash e salva 
                                    last_element = url_parts[-1]
                                    if last_element in ["other", "unspecified"]:
                                        entity_id = f"{url_parts[-2]}/{last_element}" #così salvo l'ID/other o unspecified per non confonderli con l'elemeneto che ha solo lo stesso id
                                    else: 
                                        entity_id = last_element

                                    if entity_id == "mms": #invece del numero ID ci potrebbere essere mms se siamo alla radice 
                                        title_found = "Nodo radice ICD-11"
                                    else: 
                                        title_found = "Titolo mancante" #alla fine si arrende 

                                chiave_ref = "foundationReference" if "/entity/" in element_list else "linearizationReference" #se trova entity nella parola è una foundationReference, altrimenti una linearizationReference --
                            
                                processed_list.append({
                                "title": title_found,
                                chiave_ref: element_list
                                })

                            else: 
                                processed_list.append(element_list)
                        
                        elif isinstance(element_list,dict): # nel caso in cui invece avessimo a che fare con un dizionario (vedi il caso indexTerm)
                            title = element_list.get("label", {}).get("@value", "") #per label devo entrare fino a value 
                            foundation_ref = element_list.get("foundationReference", "") #poi estraggo le reference
                            linearization_ref = element_list.get("linearizationReference", "")
                            
                            if not foundation_ref and not linearization_ref:
                                elements_without_ref.setdefault(chiave, [])
                                if title not in elements_without_ref[chiave]:
                                    elements_without_ref[chiave].append(title)


                            processed_list.append({
                                "title": title,
                                "foundationReference": foundation_ref,
                                "linearizationReference": linearization_ref
                            })
                processed_element[chiave] = processed_list

        selected_data.append(processed_element)
        
    return selected_data


#### definire il confronto tra l'mms e la foundation per recuperare il massimo delle informazioni senza duplicati 

## funzione per confronto di testi (definition)
def confronta_text(mms_text, found_text): #testo mms e testo foundation
    other_definitions = [] # apro questa lista in cui mettere definizioni diverse (non ce ne dovrebbero essere)
    
    if not mms_text: # se non c'è testo,
        return found_text, None
    if not found_text: 
        return mms_text, None
    
    if mms_text.strip().lower() == found_text.strip().lower(): #confronto i due testi eliminando spazi all'inizio e alla fine, e tutto minuscolo per evitare che li trovi diversi solo per quello 
        return mms_text, None #se sono uguali tiene mms, se sono diverse mette quella foundation in other_definitions
    other_definitions.append(found_text)
 
    return mms_text, other_definitions

## funzione per confronto di liste con title e reference (exclusions)
def confronta_list(mms_list, found_list, entity_title=""):
    titles = [] #lista per mettere i titoli già incontrati
    list_fin = [] #lista finale
    entity_title_norm = entity_title.strip().lower() if entity_title else ""

    for element in mms_list: #per ogni elemento nell'MMS, 
        if isinstance(element, dict): #se è un dizionario, recupero il titolo
            title = element.get("title", "")
        else:
            title = ""
        
        if title.strip().lower() == entity_title_norm and entity_title_norm:
            continue
        
        if title not in titles: #controllo non sia già nella lista di titoli incontrato, se è nuovo lo aggiungo sia alla lista finale che alla lista di controllo
            list_fin.append(element)
            titles.append(title)


    for element in found_list: #stessa cosa, ma passando ora la foundation, mi aggiugnerà alla lista finale SOLO quelli che non si ripetono
        if isinstance(element, dict):
            title = element.get("title", "")
        else:
            title = ""
        
        if title.strip().lower() == entity_title_norm and entity_title_norm:
            continue

        if title not in titles:
            list_fin.append(element)
            titles.append(title)
        
    return list_fin

## funzione per trattare i parent 
def confronta_parents(parent_mms, parent_foundation):
    id_parent_mms = [] #lista parent già presenti 
    for element in parent_mms: #per ogni parent nell'mms 
        if not isinstance(element, dict): #se è un dizionario vado avanti... perché dovrei avere una lista a questo punto 
            continue
        link = element.get("foundationReference") or element.get("linearizationReference") #recupero il link del parent, ed estraggo solo l'ID finale per confrontarli 
        if link:
            id_parent_mms.append(link.rstrip('/').split('/')[-1])
 
    other_parents = []
    for element in parent_foundation: #stessa cosa per la foundation
        if not isinstance(element, dict):
            continue
        link = element.get("foundationReference") or element.get("linearizationReference")
        if link and link.rstrip('/').split('/')[-1] not in id_parent_mms: #qui solo aggiungo che estratto l'ID e se non è già in parents MMS allora lo aggiungo a otherparents
            other_parents.append(element)
 
    return other_parents

## funzione per confrontare mms e foundation
def add_information(dataset_mms, dataset_foundation): ## qui ci faccio passare mms e foundation GIA' passati da select_information 
    # come prima cosa indicizzo il dataset_foundation
    foundation_indicizzata = {}
 
    for element_foundation in dataset_foundation:
        current_id = element_foundation.get("@id") # utilizzo l'ID della foundation per indicizzare --> perché poi lo posso confrontare con la source dell'mms
        # se l'id esiste, allora creo la voce nell'indice, quindi ID diventa la chiave e tutto il contenuto il suo valore
        if current_id:
            foundation_indicizzata[current_id] = element_foundation
 
    # controllo di aver tutti gli elementi e che non ci siano duplicati
    lunghezza_foundation_full_data = len(dataset_foundation)
    lunghezza_foundation_indicizzata = len(foundation_indicizzata)
    if lunghezza_foundation_full_data == lunghezza_foundation_indicizzata:
        print(f"Indicizzati tutti gli {lunghezza_foundation_full_data} elementi della foundation")
 
    mancanti_foundation_in_mms = 0 # conto quante entità mms non trovano corrispondenza nella foundation
 
    for data in dataset_mms:
        source_foundation_uri = data.get("source")
        data_foundation = foundation_indicizzata.get(source_foundation_uri) #cerco nell'INDICE, non nella lista originale
 
        #considero il caso in cui l'id nella foundation non ci sia nella mms
        if data_foundation is None:
            mancanti_foundation_in_mms += 1
            data_foundation = {}
 
        ## parents: quelli che la foundation ha in più rispetto all'mms
        other_parents = confronta_parents(data.get("parent", []), data_foundation.get("parent", []))
        if other_parents:
            data["other_parents"] = other_parents
 
        ## definition (avendo già prima tirato fuori solo il testo, è confronto solo tra i testi)
        definition, other_definition = confronta_text(data.get("definition", ""), data_foundation.get("definition", ""))
        if definition:
            data["definition"] = definition
        if other_definition:
            data["other_definition"] = other_definition
 
        ## longDefinition: stessa cosa
        longDefinition, other_longDefinition = confronta_text(data.get("longDefinition", ""), data_foundation.get("longDefinition", ""))
        if longDefinition:
            data["longDefinition"] = longDefinition
        if other_longDefinition:
            data["other_long_definition"] = other_longDefinition
 
        ## inclusion: unisco mms e foundation senza duplicati 
        data["inclusion_mms_foundation"] = confronta_list(data.get("inclusion", []), data_foundation.get("inclusion", []), entity_title=data.get("title", ""))
        data.pop("inclusion", None) ## dovuto aggiungere perché mi restituiva una copia dell'inclusion originale (boh)
 
        ## exclusion: stessa cosa
        data["exclusion_mms_foundation"] = confronta_list(data.get("exclusion", []), data_foundation.get("exclusion", []))
        data.pop("exclusion", None)
 
        ## indexTerm (mms) + synonym (foundation sono stessa cosa, sono concettualmente la stessa informazione
        data["index_term_synonym"] = confronta_list(data.get("indexTerm", []), data_foundation.get("synonym", []), entity_title=data.get("title", ""))
        data.pop("indexTerm", None)

        #dato che ho visto che spesso i sinonimi e le inclusioni sono spesso identiche, allora le unisco 
        # ha senso metterlo qui o potevo fare un ciclo prima? 
        data["synonyms_and_inclusions"] = confronta_list(data["index_term_synonym"], data["inclusion_mms_foundation"])
        data.pop("index_term_synonym", None)
        data.pop("inclusion_mms_foundation", None)

 
    print(f"Entità mms senza corrispondenza in foundation: {mancanti_foundation_in_mms}")
 
    return dataset_mms

### funzione per contare gli elementi senza reference 
def count_entity_without_reference(dataset, campo):
    titoli_unici = set()
    for entity in dataset:
        for element in entity.get(campo, []):
            if isinstance(element, dict):
                foundation_ref = element.get("foundationReference", "")
                linearization_ref = element.get("linearizationReference", "")
                if not foundation_ref and not linearization_ref:
                    titoli_unici.add(element.get("title", ""))
    return titoli_unici

##### esecuzione: prima pulisco mms e foundation separatamente con select_information, poi le unisco con add_information
fields_of_interest_mms = ["code", "@id", "source", "title", "parent", "child", "foundationChildElsewhere", "definition", "longDefinition", "indexTerm", "inclusion", "exclusion", "relatedEntitiesInMaternalChapter", "relatedEntitiesInPerinatalChapter", "postcoordinationScale", "codingNote" ]
fields_of_interest_foundation = ["@id", "title", "parent", "definition", "longDefinition", "synonym", "inclusion", "exclusion"] # la foundation non ha "source" né "indexTerm" (ha "synonym" al posto suo), mi interessano solo quei campi che devo andare a confrontare con l'mms
 
lookup_titoli = create_lookup_title(foundation_full_data=foundation_data, mms_full_data=mms_data)
print(f"lookup creato - trovati {len(lookup_titoli)} titoli")
 
data_mms_interest = select_information(dataset=mms_data, fields_to_extract=fields_of_interest_mms, lookup_title=lookup_titoli)
data_foundation_interest = select_information(dataset=foundation_data, fields_to_extract=fields_of_interest_foundation, lookup_title=lookup_titoli)
 
data_mmms_foundation = add_information(data_mms_interest, data_foundation_interest)

titoli_senza_reference_totali = set()
for campo in ["synonyms_and_inclusions", "exclusion_mms_foundation"]:
    unici = count_entity_without_reference(data_mmms_foundation, campo)
    print(f"Entità senza reference: - {campo}: {len(unici)}")
    titoli_senza_reference_totali.update(unici)

file_senza_ref = "titoli_senza_reference.txt"
with open(file_senza_ref, "w", encoding="utf-8") as f:
    # Li ordino alfabeticamente per comodità di lettura
    for titolo in sorted(titoli_senza_reference_totali):
        f.write(f"{titolo}\n")
    

 
file_output = "icd11_dati_uniti.json" 
with open(file_output, "w", encoding="utf-8") as f:
    json.dump(data_mmms_foundation, f, indent=4, ensure_ascii=False)
 
print(f"Salvate {len(data_mmms_foundation)} entità in '{file_output}'")



###### statistiche #####

total_entities = len(data_mmms_foundation) # non len(mms_data): extract_data1 può scartare elementi non-dict, i due numeri potrebbero non coincidere più
stats_counts = {} #dizionario vuoto dove aggionrare i contatori
word_counts = {"definition": [], "longDefinition": [], "other_definition": [], "other_long_definition": []}
item_counts = {"synonym": [], "parent": [], "other_parents": [], "child": [], "foundationChildElsewhere": [], "exclusion": [], "relatedEntitiesInMaternalChapter": [], "relatedEntitiesInPerinatalChapter": [], "synonyms_and_inclusions": [], "exclusion_mms_foundation": []}
 
# elenco dei campi presenti nelle entità finali, tenuto solo come riferimento/documentazione
# (il conteggio qui sotto scorre comunque tutte le chiavi di ogni entità con entity.items(), non filtra su questa lista)
field_of_interests = ["code", "@id", "source", "title", "parent", "other_parents", "child", "foundationChildElsewhere", "definition", "longDefinition", "other_definition", "other_long_definition", "synonyms_and_inclusions" , "exclusion_mms_foundation", "relatedEntitiesInMaternalChapter", "relatedEntitiesInPerinatalChapter"]
 
for entity in data_mmms_foundation: #scorro tutte le entità e tutti i campi (e i suoi valori)
    for field, value in entity.items(): 
        if value:  # Contiamo solo se il campo non è vuoto
            stats_counts[field] = stats_counts.get(field, 0) + 1 # se il campo  non è ancora presente lo aggiunge partnedo da zero e poi aumenta di uno
 
            # contatori parole
            if field in word_counts: #per ogni campo tra quelli selezionati prima, divide la frase e conta le parole
                words = len(str(value).split())
                word_counts[field].append(words)
 
            # contatori elementi (liste) 
            if isinstance(value, list) and field in item_counts:
                item_counts[field].append(len(value))
 
 
print("\n" + "="*150)
print("STATISTICHE")
print("="*130)
print(f"{'Campo':<35} | {'Valori trovati':<15} | {'Tot. Elementi':<15} | {'% sul totale':<1} | {'Media su tutte':<15} | {'Media su chi ce l\'ha'}")
print("-" * 100)
 
for field, count in sorted(stats_counts.items(), key=lambda x: x[1], reverse=True):
    percentage = (count / total_entities) * 100
 
    # due medie diverse, perché rispondono a due domande diverse:
    # "su tutte": diluita su TUTTE le entità (comprese quelle con 0, es. le foglie senza figli) --> utile per dire "quanto pesa il campo sul dataset"
    # "su chi ce l'ha": calcolata solo tra le entità che hanno valorizzato il campo --> risponde a "quanti figli ha in media un'entità che ne ha"
    media_su_tutte = "N/A"
    media_su_chi_ce_lha = "N/A"
    totale_elementi = "N/A"
 
    if field in word_counts:
        valori = word_counts[field]
        unita = "parole"
        totale_elementi = f"{sum(valori)} {unita}"
        media_su_tutte = f"{sum(valori) / total_entities:.1f} {unita}"
        media_su_chi_ce_lha = f"{sum(valori) / len(valori):.1f} {unita}" if valori else f"0 {unita}"
        
    elif field in item_counts:
        valori = item_counts[field]
        unita = "elementi"
        totale_elementi = f"{sum(valori)} {unita}" # Calcola la somma totale di tutti gli elementi
        media_su_tutte = f"{sum(valori) / total_entities:.1f} {unita}"
        media_su_chi_ce_lha = f"{sum(valori) / len(valori):.1f} {unita}" if valori else f"0 {unita}"
 
    print(f"{field:<35} | {count:<15} | {totale_elementi:<15} | {percentage:>9.2f}% | {media_su_tutte:<16} | {media_su_chi_ce_lha}")
 