import json
import re


ENTITY_BASE_URI = "http://id.who.int/icd/entity/"

def estrai_id(uri):

    if not isinstance(uri,str):
       return ""
    match = re.search(r"/(?:entity|mms|foundation/en#|mms/en#)/(\d+)", uri)
    if match:
        return match.group(1)

    return ""




def sostituzione_link_titolo(link, titolo_fallback, dizionario_foundation):

    entity_id= estrai_id(link)

    if entity_id:
        nuovo_link = f"{ENTITY_BASE_URI}{entity_id}"
        titolo_risolto= dizionario_foundation.get(entity_id,"")
        titolo_finale = titolo_risolto if titolo_risolto else (titolo_fallback or "")
    else:
        nuovo_link= link if link else ""
        titolo_finale=titolo_fallback if titolo_fallback else ""
    return {"link": nuovo_link, "title":titolo_finale}



print("caricamento datasets...")

with open("../../fusione_con_campi_mancanti.json","r",encoding="utf-8") as f:
     data=json.load(f)

with open("../../../foundation/icd11_foundation_completo.json","r",encoding="utf-8") as g:
    foundation=json.load(g)

print("datasets caricati ")





# creo set per il controllo degli uri non presenti nell'mms ma nella foundation
foundation_id_and_title={}
for item in foundation:
    source_uri = item.get("@id", "") #ottengo l'uri completo
    #transient_dict= {"@id": source_uri, "title": title_f}
    if source_uri:
       uri_key_f = estrai_id(source_uri) #estraggo solo la parte numerica
       if uri_key_f:

        title_obj = item.get("title")
        if isinstance(title_obj, dict):
            title_val = title_obj.get("@value", "")
        elif isinstance(title_obj, str):
            title_val = title_obj
        else:
            title_val = ""
        foundation_id_and_title[uri_key_f] = title_val



# creo set per il controllo degli uri  potrebbe non servire
id_unici=set()
for item in data:
    source_uri = item.get("foundation_uri", "") #ottengo l'uri completo
    if source_uri:
        uri = source_uri.split('/entity/')[-1].split('/')[0] #estraggo solo la parte numerica
        id_unici.add(uri) #l'aggiungo all'insieme

new_fusione=[]


campi_da_controllare_lista_stringhe=[
        "parent_mms", #lista con solo link (con release),
        "parent_foundation", #lista di link (ha link con entity)
        "relatedEntitiesInMaternalChapter", #ha lista solo link (con entity)
        "relatedEntitiesInPerinatalChapter" #ha lista solo link (con enity)
        ]
campi_da_controllare_dict=[
         "exclusion_mms", #lista di dict con foundationReference (ha link con entity)
        "index_term_synonyms",#lista con dict con foundationReference come key (ha link con entity)
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
                    nodo_trasformato= sostituzione_link_titolo(link=raw_link,titolo_fallback="",dizionario_foundation=foundation_id_and_title)
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
                    nodo_trasformato= sostituzione_link_titolo(link=raw_link,titolo_fallback=raw_titolo,dizionario_foundation=foundation_id_and_title)
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
                            nodo_trasformato=sostituzione_link_titolo(link=raw_link,titolo_fallback="",dizionario_foundation=foundation_id_and_title)

                            nuove_entity.append(nodo_trasformato)
                    postsc_modificato["scaleEntity"]=nuove_entity

                nuovo_postcoord.append(postsc_modificato)
            item["postcoordination_scale"]=nuovo_postcoord

print("sto scrivendo il file")
file_output = "fusione_sostituzione_link_dict_2.json"
with open(file_output, "w", encoding="utf-8") as h:
    json.dump(data, h, indent=4, ensure_ascii=False)

print(f"Processo concluso. Dataset serializzato in: {file_output}")
