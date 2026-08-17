import json 
import re

PATTERN_ID_ICD = re.compile(r'(?:/entity/|/mms/|#)(\d+)')

def estrai_id_numerico(url: str) -> str:

    if not isinstance(url, str) or not url:
        return ""
    
    match = PATTERN_ID_ICD.search(url)
    return match.group(1) if match else ""


print("carico i dati")

with open("../fusione_sostituzione_link_dict_2.json","r",encoding="utf-8") as f:
    data=json.load(f)
with open("./external_entities.json","r",encoding="utf-8") as f:
    data_external_entities=json.load(f)


insieme_esterni=set()

#prendo tutte le chiavi che poi userò per cercarle dentro i link dei campi 
chaivi=data_external_entities.keys()

#aggiungo queste chiavi in un insieme così la ricerca è più veloce 
for chiave in chaivi:
    insieme_esterni.add(chiave)

campi_da_controllare=["exclusion_mms", 
                     "foundationChildElsewhere",
                     "index_term_synonyms",
                     "parent_foundation",
                     "postcoordination_scale",
                     "relatedEntitiesInMaternalChapter",
                     "relatedEntitiesInPerinatalChapter"]

campi_contenenti_esterni=set()

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

                           if uri_da_controllare and uri_da_controllare in insieme_esterni : #se ho un riscontro ottengo l'uri che mi serve
                               campi_contenenti_esterni.add(key)
     
print(campi_contenenti_esterni)
     
with open("campi_contenenti_uri_esterni.txt","w",encoding="utf-8") as j:
     for elemento in campi_contenenti_esterni:
         j.write(f"{elemento}\n")
         
print("scritto il file")
                              
    






