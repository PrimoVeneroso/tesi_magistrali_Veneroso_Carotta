
import json
import re

PATTERN_MMS_ID = re.compile(r'/(?:mms|entity)/(\d+(?:/[a-zA-Z0-9_-]+)*)(?:/|$)')

def estrai_id_mms(url: str) -> str:

    if not isinstance(url, str) or not url:
        return ""

    url_pulito = url.rstrip('/')

    # Assegna un ID dedicato al nodo radice per non perderlo
    if url_pulito.endswith('/mms') or url_pulito.endswith('/entity'):
        return "root"

    match = PATTERN_MMS_ID.search(url)
    return match.group(1) if match else ""
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
                        link_mms= item.get("linearizationReference","")
                        foundationChildElsewhere_list.append({
                        "title": val,
                        "foundationReference": link_inc,
                        "linearizationReference": link_mms
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

    long_def_og = elemento.get("longDefinition")
    long_def_val = long_def_og.get("@value", "") if isinstance(long_def_og, dict) else ""

    fsn_og = elemento.get("fullySpecifiedName")
    fsn_val = fsn_og.get("@value", "") if isinstance(fsn_og, dict) else ""

    synonyms_list = []
    if "synonym" in elemento and isinstance(elemento["synonym"], list):
        for item in elemento["synonym"]:
            if isinstance(item, dict) and "label" in item:
                val = item["label"].get("@value")
                if val:
                    synonyms_list.append(val)

    nuovo_dict = {
        "browserUrl_foundation":elemento.get("browserUrl",""),
        "fully_specified_name_foundation": fsn_val,
        "long_definition_foundation": long_def_val,
        "parent_foundation": elemento.get("parent", []),
        #inclusion uguali in 1.412 casi, e divergono in circa 143 casi
        "synonyms_foundation": synonyms_list,
           }

    return nuovo_dict

#• In MMS: Su 2.443 inclusioni totali presenti, 2.194 si trovano anche negli index_term o nei synonym, mentre 249 ne sono esclusi.
#• In Foundation: Su 2.390 inclusioni analizzate, 2.017 si trovano nei sinonimi/index_term, mentre 373 non ci sono.

print("Caricamento files JSON...")

with open("../mms/mms_completo.json", "r", encoding="utf-8") as f: #carico il file mms
    data_mms = json.load(f)

with open("../foundation/icd11_foundation_completo.json", "r", encoding="utf-8") as g: #carico il file foundation
    data_foundation = json.load(g)

id_non_unici=set()
foundation_map = {}
elementi_senza_uri=[]
id_unici =set()  #per rendere più veloce il controllo pr i codici univoci
mms_trasformati = [] # lista entità trasformate per creare il nuovo json

# eseguo questo salvataggio prima per poi effettuare il controllo dei link e delle entità
for item in data_mms:

    mms_id_raw = item.get("@id", "")
    uri = estrai_id_mms(mms_id_raw)

    if uri:
        if uri in id_unici:
            #print(f"questo uri era già presente nell' insieme id_unici {uri}\n")
            id_non_unici.add(uri)
        else:
            id_unici.add(uri) #l'aggiungo all'insieme
    else:
        elementi_senza_uri.append(item)

    mms_clean = transformation_mms(item) #faccio girare il singolo item nella funzione
    mms_trasformati.append(mms_clean) # lo aggiungo alla mia lista di elementi che andrò poi ad unire


print(f"MMS trasformati: {len(mms_trasformati)}. ID unici estratti: {len(id_unici)}\n")
print(f"la lunghezza dell'insieme degli id non unici è {len(id_non_unici)}\n")
print(f"la lunghezza della lista elementi_senza_uri è {len(elementi_senza_uri)}\n")

titolo_output="id_uri_non_unici_mancanti.json"
with open(titolo_output,"w",encoding="utf-8") as z:
    json.dump(elementi_senza_uri, z, indent=4, ensure_ascii=False)


for item in data_foundation:
    #Estrazione dell'ID dal campo @id del file Foundation
    foundation_id_raw = item.get("@id", "")
    uri_key_f = estrai_id_mms(foundation_id_raw)

    if uri_key_f and uri_key_f in id_unici:
        foundation_clean = transformation_foundation(item) #processo solo quelli che sono presenti nell'mms e li pulisco
        foundation_map[uri_key_f] = foundation_clean # in questo modo azzero i tempi di ricerca per unirli perchè avrò un richiamo diretto ceracto uri_key che saranno uguali tra mms_clean e foundation_clean


print(f"Elementi Foundation mappati con successo: {len(foundation_map)}")


dati_fusi = []
for mms in mms_trasformati:
    # Mappatura sicura tramite il solo campo mms_link (che contiene @id)
    mms_link = mms.get("mms_link", "")

    if mms_link:
        id_numerico = estrai_id_mms(mms_link)
        if id_numerico in foundation_map:
            mms.update(foundation_map[id_numerico]) #aggiorno con i dati della Foundation

    dati_fusi.append(mms)


print(f"Totale elementi fusi pronti per il salvataggio: {len(dati_fusi)}")

with open("fusione_con_campi_mancanti.json", "w", encoding="utf-8") as h:
    json.dump(dati_fusi, h, indent=4, ensure_ascii=False)
