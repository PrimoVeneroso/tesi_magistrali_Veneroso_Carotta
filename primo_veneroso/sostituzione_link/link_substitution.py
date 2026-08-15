import json


def sostituzione_link(link):
    if not isinstance(link,str) or not link:
        return "",""

    partial_link=""
    reg_exp_entity="http://id.who.int/icd/entity/"
    reg_exp_release="http://id.who.int/icd/release/11/2026-01/mms/"
    reg_exp_browser="https://icd.who.int/browse/2026-01/foundation/en#"

    if reg_exp_entity in link:
       partial_link=link.split('/entity/')[-1].split('/')[0]
    elif reg_exp_release in link:
         partial_link=link.split('/mms/')[-1].split('/')[0]
    if partial_link:
       return reg_exp_browser+ partial_link, partial_link

    return link, ""


print("caricamento datasets")

with open("../mms_foundation_merge/fusione_con_campi_mancanti.json","r",encoding="utf-8") as f:
     data=json.load(f)

with open("../foundation/icd11_foundation_completo.json","r",encoding="utf-8") as g:
    foundation=json.load(g)


# creo set per il controllo degli uri non presenti nell'mms ma nella foundation
foundation_id_and_title={}
for item in foundation:
    source_uri = item.get("@id", "") #ottengo l'uri completo
    #transient_dict= {"@id": source_uri, "title": title_f}

    if source_uri:
       uri_key_f = source_uri.split('/entity/')[-1].split('/')[0] #estraggo solo la parte numerica

       title_obj = item.get("title")
       title_val = title_obj.get("@value", "") if isinstance(title_obj, dict) else ""

        # Memorizzazione atomica: ID -> Titolo testuale
       foundation_id_and_title[uri_key_f] = title_val



# creo set per il controllo degli uri  potrebbe non servire
id_unici=set()
for item in data:
    source_uri = item.get("foundation_uri", "") #ottengo l'uri completo
    if source_uri:
        uri = source_uri.split('/entity/')[-1].split('/')[0] #estraggo solo la parte numerica
        id_unici.add(uri) #l'aggiungo all'insieme

new_fusione=[]


campi_da_controllare=[
        "parent_mms", #lista con solo link (con release)
        "exclusion_mms", #lista di dict con foundationReference (ha link con entity)
        "index_term_synonyms",#lista con dict con foundationReference come key (ha link con entity)
        "postcoordination_scale", # ha "scaleEntity" come chiave di un dict all'interno di una lista, (ha link con release)
        "parent_foundation", #lista di link (ha link con entity)
        "relatedEntitiesInMaternalChapter", #ha lista solo link (con entity)
        "relatedEntitiesInPerinatalChapter", #ha lista solo link (con enity)
        "foundationChildElsewhere" #ha foundationReference in un dict (link con entity)
        ]


for item in data: #ciclo nel mio dataset

       for key in campi_da_controllare:
        valore = item.get(key)

        if isinstance(valore, list) and valore:
            nuova_lista=[]

            for elemento in valore: #ciclo nella lista

               if isinstance(elemento, str):

                  vecchio_link=elemento #variabile temporanea da inserire nella funzione
                  nuovo_link, id_num =sostituzione_link(vecchio_link) #ottengo il nuovo link

                  #devo ottenere il title per il dict che creo
                  titolo=foundation_id_and_title.get(id_num,"")
                  nuova_lista.append({
                            "link": nuovo_link,
                            "title": titolo
                        })
                #parte più complessa andrebbe resa più generale
               elif isinstance(elemento,dict): #l'altra opzione se è un dict

                    vecchio_link=(elemento.get("foundationReference") or
                                   elemento.get("scaleEntity") or
                                   elemento.get("id") or ""
                                    )

                    nuovo_link, id_num =sostituzione_link(vecchio_link) #ottengo il nuovo link
                    titolo=""


                    if isinstance(elemento.get("label"), dict):
                        titolo= elemento["label"].get("@value","")


                    elif "title" in elemento and isinstance(elemento["title"],str):
                        titolo= elemento["title"]

                    elif key == "postcoordination_scale":

                        id_temporaneo = elemento.get("scaleEntity") or elemento.get("axisName") or ""

                        # Se è una lista, estrae il primo elemento valido o itera
                        if isinstance(id_temporaneo, list) and id_temporaneo:
                            uri_target = str(id_temporaneo[0])
                        elif isinstance(id_temporaneo, str):
                            uri_target = id_temporaneo
                        else:
                            uri_target = ""

                        # Parsing sicuro dell'identificativo numerico
                        if "/mms/" in uri_target:
                            id_ricerca = uri_target.split('/mms/')[-1].split('/')[0]
                        elif "/entity/" in uri_target:
                            id_ricerca = uri_target.split('/entity/')[-1].split('/')[0]
                        else:
                            id_ricerca = id_num  # Fallback sull'id_num estratto in precedenza

                        titolo = foundation_id_and_title.get(id_ricerca, "")

                        titolo=foundation_id_and_title.get(id_ricerca,"")


                    if not titolo and id_num:
                        titolo = foundation_id_and_title.get(id_num, "")



                    # si crea un dict intermedio per poterlo arricchire con campi

                    nuovo_dict = {
                        "link": nuovo_link,
                        "title": titolo
                    }

                    # si aggiungono i campi extra che altrimenti sarebbero assenti nel nuovo json
                    if key == "postcoordination_scale":
                        for campo_extra in ("@id", "axisName", "requiredPostcoordination", "allowMultipleValues", "scaleEntity"):
                            if campo_extra in elemento:
                                nuovo_dict[campo_extra] = elemento[campo_extra]

                    nuova_lista.append(nuovo_dict)


            item[key] = nuova_lista

# 3. Salvataggio su file finale
file_output = "fusione_sostituzione_link_dict.json"
with open(file_output, "w", encoding="utf-8") as h:
    json.dump(data, h, indent=4, ensure_ascii=False)

print(f"Trasformazione completata con successo! Salvato in: {file_output}")
