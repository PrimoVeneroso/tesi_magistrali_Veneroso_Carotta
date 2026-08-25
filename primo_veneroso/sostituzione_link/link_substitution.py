import json
import re 


ENTITY_BASE_URI_FOUNDATION = "http://id.who.int/icd/entity/"
ENTITY_BASE_URI_MMS = "http://id.who.int/icd/release/11/2026-01/mms/"
def estrai_id(uri):
    if not isinstance(uri, str):
        return ""

    # Pattern unificato e corretto che supporta sia ID semplici che gerarchici
    match = re.search(r"/(?:entity|mms|foundation/en#|mms/en#)/(\d+(?:/[a-zA-Z0-9_-]+)*)", uri)

    if match:
        return match.group(1)

    return ""



def sostituzione_link_titolo(link, titolo_fallback, dizionario_foundation, dizionario_mms):
    not_mms_not_foundation=set()
    entity_id= estrai_id(link)
    


    if entity_id in dizionario_mms:
        print(f"{entity_id},mms")        
        nuovo_link=f"{ENTITY_BASE_URI_MMS}{entity_id}"
        titolo_risolto = dizionario_mms[entity_id].get("title","")
        titolo_finale = titolo_fallback if (titolo_fallback and titolo_fallback.strip() != "") else (titolo_risolto or "")

    elif entity_id not in dizionario_mms and entity_id in dizionario_foundation:
        
        print(f"{entity_id},foundation")
        nuovo_link = f"{ENTITY_BASE_URI_FOUNDATION}{entity_id}"

        titolo_risolto = dizionario_foundation[entity_id].get("title","")
        

        # Usiamo il titolo_risolto solo se il sinonimo è completamente vuoto.
        titolo_finale = titolo_fallback if (titolo_fallback and titolo_fallback.strip() != "") else (titolo_risolto or "")
    else:
        if entity_id:
            not_mms_not_foundation.add(entity_id)
            print("l'entity_id è saltato: ", entity_id)
        nuovo_link= link if link else ""
        titolo_finale=titolo_fallback if titolo_fallback else ""

   

    return { "title":titolo_finale, "link": nuovo_link}

    

print("caricamento datasets...")

with open("../mms_foundation_merge/fusione_con_campi_mancanti.json","r",encoding="utf-8") as f:
     data=json.load(f)

with open("../foundation/icd11_foundation_completo.json","r",encoding="utf-8") as g:
    foundation=json.load(g)

with open("../mms/mms_completo.json","r",encoding="utf-8") as h:
    mms=json.load(h) 

with open("../creazione_dict_insiemi_per_controlli/file_controllo_uri_links_mms.json","r",encoding="utf-8") as h:
    controllo_mms=json.load(h)

with open("../creazione_dict_insiemi_per_controlli/file_controllo_uri_links_foundation.json","r",encoding="utf-8") as h:
    controllo_foundation=json.load(h)

print("datasets caricati ")


new_fusione=[]


campi_da_controllare_lista_stringhe=[
        "parent_mms", #lista con solo link (con release), 
        "parent_foundation", #lista di link (ha link con entity)
        "relatedEntitiesInMaternalChapter", #ha lista solo link (con entity)
        "relatedEntitiesInPerinatalChapter" #ha lista solo link (con enity)
        ]
campi_da_controllare_dict=[
        "index_term_synonyms",#lista con dict con foundationReference come key (ha link con entity) alcuni non lo hanno 
        # CONTROLLARE PER VEDERE SE POSO CREARE UN SET DI PRIME ENTITÀ SENZA LINK 


       # "postcoordination_scale", # ha "scaleEntity" come chiave di un dict all'interno di una lista, (ha link con release) 
        "foundationChildElsewhere" #ha foundationReference in un dict (link con entity)
        ]


for item in data: #ciclo nel mio dataset
    
    #parto dai cmapi con le stringhe 
    for key in campi_da_controllare_lista_stringhe:
        valori = item.get(key)

        if isinstance(valori,list) and valori:
            nuova_lista=[]

            for raw_link in valori:
                if isinstance(raw_link,str):
                    nodo_trasformato= sostituzione_link_titolo(link=raw_link,titolo_fallback="",dizionario_foundation=controllo_foundation,dizionario_mms=controllo_mms)
                    nuova_lista.append(nodo_trasformato)
            item[key]=nuova_lista



    for key in campi_da_controllare_dict:
        valori =item.get(key)
        if isinstance(valori,list) and valori:
            nuova_lista=[]
            
            for elemento in valori:
                if isinstance(elemento,dict):
                    raw_link=elemento.get("foundationReference") or elemento.get("link") or elemento.get("@id") or ""
                    raw_titolo = elemento.get("title") or elemento.get("label","")
                    if isinstance(raw_titolo,dict):
                        raw_titolo=raw_titolo.get("@value","")

                    nodo_trasformato=sostituzione_link_titolo(link=raw_link,
                                                              titolo_fallback=raw_titolo,
                                                              dizionario_foundation=controllo_foundation,
                                                              dizionario_mms=controllo_mms)
                    nuova_lista.append(nodo_trasformato)
            item[key]= nuova_lista

    # caso della postcoordination_scale che è un caso particolare 
    postcoord = item.get("postcoordination_scale")
    if isinstance(postcoord,list) and postcoord:
        nuovo_postcoord=[]
        for scale_item in postcoord:
            if isinstance(scale_item,dict):
                #clono il sotto-dict perchè ha tatni campi
                postsc_modificato= dict(scale_item)
                postsc_entities = scale_item.get("scaleEntity",[])

                if isinstance(postsc_entities,list):
                    nuove_entity=[]
                    for raw_link in postsc_entities:
                        if isinstance(raw_link, str): #controllo e sostituisco i link con inuovi link e 
                            nodo_trasformato=sostituzione_link_titolo(link=raw_link,titolo_fallback="",dizionario_foundation=controllo_foundation,dizionario_mms=controllo_mms)
                            nuove_entity.append(nodo_trasformato)
                    postsc_modificato["scaleEntity"]=nuove_entity

                nuovo_postcoord.append(postsc_modificato)
            item["postcoordination_scale"]=nuovo_postcoord

print("sto scrivendo il file")
file_output = "fusione_sostituzione_link_dict_2.json"
with open(file_output, "w", encoding="utf-8") as h:
    json.dump(data, h, indent=4, ensure_ascii=False)

print(f"Processo concluso. Dataset serializzato in: {file_output}")
