import json 
import re

#creo il pattern e 

PATTERN_ID_ICD = re.compile(r'(?:/entity/|/mms/|#)(\d+)')

def estrai_id_numerico(url: str) -> str:

    if not isinstance(url, str) or not url:
        return ""
    
    match = PATTERN_ID_ICD.search(url)
    return match.group(1) if match else ""


def controllo_uri(uri,set_id):  #controlla se l'uri è presente o meno nel nostro set di uri dal merge di mms ocn foundation

    if uri and uri in set_id:
        return True,uri
    else:
        return None,uri
        
print("carico i dati")
with open("../fusione_sostituzione_link_dict_2.json","r",encoding="utf-8") as f:
    data=json.load(f)

with open("../../mms/mms_completo.json","r",encoding="utf-8") as g:
    data_mms=json.load(g)
with open("../../foundation/icd11_foundation_completo.json","r",encoding="utf-8") as h:
    data_foundation=json.load(h)
title_external={}

# come negli altri script creo la mappatura della foundation per trovare subito i dati di cu ho bisogno, questa volta salvando il title e l'id
foundation_map={}
for item in data_foundation:
    if "@id" in item:
        uri_key_f = item["@id"].split('/entity/')[-1].split('/')[0] #estraggo l'uri'
        if uri_key_f:
            title_foundation=item.get("title","")
            title_text=title_foundation.get("@value","")
            foundation_map[uri_key_f]={"title": title_text, "foundation_uri":item["@id"]}

id_unici = set() #per rendere più veloce il controllo pr i codici univoci 

# eseguo questo salvataggio prima per poi effettuare il controllo dei link e delle entità come al solito set degli uri per trovarli subito
for item in data_mms:
    source_uri = item.get("source", "") #ottengo l'uri completo
    if source_uri: 
        uri = source_uri.split('/entity/')[-1].split('/')[0] #estraggo solo la parte numerica 
        id_unici.add(uri) #l'aggiungo all'insieme 


campi_da_controllare=["exclusion_mms",
                      "foundationChildElsewhere",
                      "index_term_synonyms",
                      "parent_foundation",
                      "postcoordination_scale",
                      "elatedEntitiesInMaternalChapter",
                      "relatedEntitiesInPerinatalChapter"]

#per ebitare doppie entità
valori_esterni=set()

for item in data:

    for key in campi_da_controllare:
        #print(key)
        valore_temp=item.get(key,"") 

        if len(valore_temp)>0: #controllo che non sia vuota
            valore=item.get(key,"")
            #print(valore)
            
            if isinstance(valore,list):
                for elemento in valore: #elemento è un dict 
                    #ho fatto controlli elemento sono solo dict 
                   
                    da_controllare=elemento.values()
                    #print(da_controllare)

                    for singolo in da_controllare:
                        #print(singolo) #è il valore che devo controlalre 
                        if isinstance(singolo,str) and singolo.startswith("http"):
                           uri_da_controllare=estrai_id_numerico(singolo)

                           if uri_da_controllare: #se ho un riscontro ottengo l'uri che mi serve 
                              risultato,uri=controllo_uri(uri_da_controllare,id_unici)
                              #print(singolo,risultato,uri)

                              if risultato == None: # se l'uri non è nell'mms printo il mesaggio e lo aggiungo al map
                                 valori_esterni.add(uri)
                                 print(f"l'uri {uri} non è presente nell mms appartiene alla key {key}" )
                                 title_external[uri]=foundation_map[uri]
                                 #print(singolo,risultato,uri,title_external)



                                


print("sto scrivendo il file con le entità esterne")                               
with open("external_entities.json","w",encoding="utf-8") as j:
     json.dump(title_external, j, indent=4, ensure_ascii=False)

                            


                    



"""

            if isinstance(valore,dict):
                print("c'è almeno un dict")
            elif isinstance(valore,str):
                print("c'è almeno una str")
             elif isinstance(elemento,list):
                print("c'è almeno una lista")


                        if singolo.startswith("http://"):
                            uri_da_controllare=estrai_id_numerico(singolo)

                            if uri_da_controllare:
                                risultato,uri=controllo_uri(uri_da_controllare,id_unici)

                                if risultato == None:
                                    valori_esterni.add(uri)
                                    print(f"l'uri {uri} non è presente nell mms appartiene alla key {key}" )

    
"""

