import json


def transformation_mms(elemento):

    
    coding_og = elemento.get("codingNote")
    coding_val = coding_og.get("@value", "") if isinstance(coding_og,dict) else ""
    
    title_og=elemento.get("title") #salva in una variabile il valore title che è formato da più campi 
    title_val=title_og.get("@value","") if isinstance(title_og,dict) else "" #salva il campo value che essendo la chiave di un dict devo prendere il suo value 

    def_og=elemento.get("definition") #stessa cosa per definition è un dict 
    def_val = def_og.get("@value","") if isinstance(def_og,dict) else ""
   
    fsn_og=elemento.get("fullySpecifiedName") #identico con fullySpecifiedName
    fsn_val=fsn_og.get("@value","") if isinstance(fsn_og,dict) else ""

    inclusion_list=[] #dato che la inclusion è una lista devo prendere tutti i suoi elementi sono dict e salvarli all'interno della lista per il nuovo db
    if "inclusion" in elemento and isinstance(elemento["inclusion"],list): #controlal se è inclision ed è formato da una lista
        for item in elemento["inclusion"]:
            if isinstance(item,dict) and "label" in item:
                val= item["label"].get("@value")
                if val:
                    inclusion_list.append(val)

    exclusion_list = [] #devo prendere non solo il @value ma anche il link che è esterno al dict del @value
    if "exclusion" in elemento and isinstance(elemento["exclusion"], list): #controllo se è una lista 
        for item in elemento["exclusion"]: #ciclo  
            if isinstance(item, dict) and "label" in item: #controllo se è un dict e se presente la chiave label
                label_item=item.get("label") #metto label in una variabile 
                if isinstance(label_item,dict): #controllo se è un dict 
                    val = label_item.get("@value") #prendo il value 
                    if val: 
                       link_exc=item.get("foundationReference", "") #estraggo il link 
                       exclusion_list.append({ #aggiungo alla lista 
                         "title":val,
                         "foundationReference": link_exc
                         })

  
    index_term_list = [] #devo prendere non solo il @value ma anche il link che è esterno al dict del @value
    if "indexTerm" in elemento and isinstance(elemento["indexTerm"], list): #controllo se è una lista 
        for item in elemento["indexTerm"]: #ciclo  
            if isinstance(item, dict) and "label" in item: #controllo se è un dict e se presente la chiave label
                label_item=item.get("label") #metto label in una variabile 
                if isinstance(label_item,dict): #controllo se è un dict 
                    val = label_item.get("@value") #prendo il value 
                    if val: 
                       link_index=item.get("foundationReference", "") #estraggo il link 
                       index_term_list.append({ #aggiungo alla lista 
                         "title":val,
                         "foundationReference": link_index
                         })


    foundationChildElsewhere_list = [] #lo stesso per childElsewhere 
    if "foundationChildElsewhere" in elemento and isinstance(elemento["foundationChildElsewhere"],list):
        for item in elemento["foundationChildElsewhere"]:
            if isinstance(item,dict) and "label" in item:
                foundationChild_item=item.get("label")
                if isinstance(foundationChild_item,dict):
                    val = foundationChild_item.get("@value")
                    if val:
                        link_inc = item.get("foundationReference","")
                        foundationChildElsewhere_list.append({
                        "title": val,
                        "foundationReference": link_inc
                        })

        

    #creo lo scheletro del nuovo dizionario per la singola entità 
    nuovo_dict = {
        "code": elemento.get("code", ""),
        "foundation_uri": elemento.get("source", ""),
        "mms_link": elemento.get("@id", ""),
        "browserUrl":elemento.get("browserUrl",""),
        "title": title_val,
        "fully_specified_name": fsn_val,
        "parent_mms": elemento.get("parent", []),
        "class_kind_mms": elemento.get("classKind", ""),
        "definition_mms": def_val,
        "inclusion_mms": inclusion_list,
        "exclusion_mms": exclusion_list,
        "index_term_synonyms": index_term_list,
        "relatedEntitiesInMaternalChapter": elemento.get("relatedEntitiesInMaternalChapter", []),
        "relatedEntitiesInPerinatalChapter": elemento.get("relatedEntitiesInPerinatalChapter",[]),
        "codingNote": coding_val,
        "foundationChildElsewhere": foundationChildElsewhere_list,
        "postcoordination_scale": elemento.get("postcoordinationScale", [])

    }

    return nuovo_dict

def transformation_foundation(elemento):
    #title_og = elemento.get("title")
    #title_val = title_og.get("@value", "") if isinstance(title_og, dict) else ""

    #def_og = elemento.get("definition")
    #def_val = def_og.get("@value", "") if isinstance(def_og, dict) else ""

    long_def_og = elemento.get("longDefinition")
    long_def_val = long_def_og.get("@value", "") if isinstance(long_def_og, dict) else ""

    fsn_og = elemento.get("fullySpecifiedName")
    fsn_val = fsn_og.get("@value", "") if isinstance(fsn_og, dict) else ""

    #inclusion_list = []
    #if "inclusion" in elemento and isinstance(elemento["inclusion"], list):
     #   for item in elemento["inclusion"]:
     #       if isinstance(item, dict) and "label" in item:
      #         label_item=item.get("label")
       #        if isinstance(label_item,dict):
        #          val = label_item.get("@value")   
         #         if val:
          #           link_inc=item.get("foundationReference", "")
           #          inclusion_list.append({
            #             "title":val,
             #            "foundationReference": link_inc
              #           })

   

    synonyms_list = []
    if "synonym" in elemento and isinstance(elemento["synonym"], list):
        for item in elemento["synonym"]:
            if isinstance(item, dict) and "label" in item:
                val = item["label"].get("@value")
                if val:
                    synonyms_list.append(val)
    
    nuovo_dict = {
        #"title_foundation": title_val,
        "browserUrl_foundation":elemento.get("browserUrl",""),
        "fully_specified_name_foundation": fsn_val,
        #"definition_foundation": def_val,
        "long_definition_foundation": long_def_val,
        "parent_foundation": elemento.get("parent", []),
        #"child_foundation": elemento.get("child", []),
        #"inclusion_foundation": inclusion_list,
        #"exclusion_foundation": exclusion_list,
        "synonyms_foundation": synonyms_list,
           }

    return nuovo_dict


print("Caricamento files JSON...")

with open("/home/primo/Scaricati/ICD11_progetto/mms/mms_completo.json", "r", encoding="utf-8") as f: #carico il file mms
    data_mms = json.load(f)

with open("/home/primo/Scaricati/ICD11_progetto/foundation/icd11_foundation_completo.json", "r", encoding="utf-8") as g: #carico il file foundation 
    data_foundation = json.load(g)


foundation_map = {}
id_unici = set() #per rendere più veloce il controllo pr i codici univoci
mms_trasformati = [] # lista entità trasformate per creare il nuovo json 

# eseguo questo salvataggio prima per poi effettuare il controllo dei link e delle entità 
for item in data_mms:
    source_uri = item.get("source", "") #ottengo l'uri completo
    if source_uri: 
        uri = source_uri.split('/entity/')[-1].split('/')[0] #estraggo solo la parte numerica 
        id_unici.add(uri) #l'aggiungo all'insieme 
    mms_clean = transformation_mms(item) #faccio girare il singolo item nella funzione 
    mms_trasformati.append(mms_clean) # lo aggiungo alla mia lista di elementi che andrò poi ad unire


print(f"MMS trasformati: {len(mms_trasformati)}. ID unici estratti: {len(id_unici)}")


for item in data_foundation:
    if "@id" in item:
        uri_key_f = item["@id"].split('/entity/')[-1].split('/')[0] #estraggo l'uri'
        if uri_key_f in id_unici:
            foundation_clean= transformation_foundation(item) #procrsso solo quelli che sono presenti nell'mms e li pulisco 
            foundation_map[uri_key_f]=foundation_clean # in questo modo azzero i tempi di ricerca per unirli perchè avrò un richiamo diretto ceracto uri_key che saranno uguali tra mms_clean e foundation_clean 


print(f"Elementi Foundation mappati con successo: {len(foundation_map)}")


dati_fusi = []
for mms in mms_trasformati:
    uri = mms.get("foundation_uri", "")
        # estraggo l'ID solo se l'URI esiste
    if uri:#se esiste lo isolo per trovare la rispettiva chive nel foundation_map 
        id_numerico = uri.split('/entity/')[-1].split('/')[0]
        if id_numerico in foundation_map: 
        
            mms.update(foundation_map[id_numerico]) #aggiorno con i dati della Foundation

    dati_fusi.append(mms)


print(f"Totale elementi fusi pronti per il salvataggio: {len(dati_fusi)}")

with open("fusione_con_campi_mancanti.json", "w", encoding="utf-8") as h:
    json.dump(dati_fusi, h, indent=4, ensure_ascii=False)










