import json
import re


ENTITY_BASE_URI = "http://id.who.int/icd/entity/"

def estrai_id(uri):
    if not isinstance(uri, str):
        return ""

    match = re.search(r"/(?:entity|mms|foundation/en#|mms/en#)/(\d+)", uri)
    if match:
        return match.group(1)

    return uri


print("carico i dati")

with open ("../sostituzione_link/fusione_sostituzione_link_dict_2.json","r",encoding="utf-8") as f:
    data=json.load(f)

with open("../foundation/icd11_foundation_completo.json","r",encoding="utf-8") as g:
    foundation=json.load(g)

with open("../mms/mms_completo.json","r",encoding="utf-8") as h:
    mms=json.load(h)

print("dati caricati")




#questi sono insieme per non avere ripetizioni e il dict per collegare i title al rispettivo link per i file merge
merge_titles=set()
merge_dict={}

print("--------------------------------------------------")
print("INIZIA LO SCRIPT CON CREAZIONE DI SET E DICT MERGE")
print("--------------------------------------------------\n")
print("sta girando prima di creare insieme del merge\n ")


for item in data:
    if "title" in item:
        titolo=item.get("title","")
        link=item.get("mms_link","")
        uri_m=estrai_id(link)
        if titolo:
            merge_titles.add(titolo.lower()) # questo contiene i titoli usare successivamente
            if len(link)>0:
                merge_dict[titolo.lower()]={"title":titolo,"link":link,"uri":uri_m}




print(f"la lunghezza del set dei titoli del merge è: {len(merge_titles)},invece la lunghezza del dict con titolo e link é:{ len(merge_dict.items())}\n")

print("--------------------------------------------------")
print("CREAZIONE DI SET E DICT DELLA FOUNDATION")
print("---------------------------------------------------------\n")

#stessa cosa che ho fatto per il merge(che è lo stesso dell'mms) lo faccio per la foundation
foundation_titles=set()
foundation_dict={}

for item in foundation:
    if "title" in item:
        titolo_parziale =item.get("title","")
        titolo=titolo_parziale.get("@value","")
        link_f=item.get("@id","")
        uri_f=estrai_id(link_f)
        if titolo:
           foundation_titles.add(titolo.lower())
           if  len(link_f)>0:
               foundation_dict[titolo.lower()]={"title":titolo,"link":link_f,"uri":uri_f}


print(f"la lunghezza del set foundation è:  {len(foundation_titles)} la lunghezza del dict della foundation è {len(foundation_dict)}\n ")


print("----------------------------------------------------------\n")
print("OTTENGO SET DEI TITLE SENZA LINK IN ALCUNI DEI CAMPI DEL MERGE PER VEDERE SE ALL'INTERNO DEL MERGE STESSO SONO GIÀ PRESENTI  MA NON COLLEGATI AI RISPETTIVI LINK ")
print("----------------------------------------------------------\n")

# questo è l'insieme per i title senza link all'interno dei campi del merge, il secondo serve per salvare i titoli che in verità sono nel merge
merge_orphan=set()
fake_orphan_merge=set()



for item in data:

    if "synonyms_foundation" in item and len(item.get("synonyms_foundation",""))>0:
        for elemento in item.get("synonyms_foundation",""):
           #per essere sicuro di riconscerli metto il controllo con lower
            if elemento.lower() not in merge_titles:
                merge_orphan.add(elemento)
            else:
                fake_orphan_merge.add(elemento)


    if "index_term_synonyms" in item:
        lista_temporanea_index=item.get("index_term_synonyms","")
        for elemento in lista_temporanea_index:
            titolo_el = elemento.get("title","")
            link_el = elemento.get("link","")

            if len(link_el) == 0:
                if titolo_el.lower() not in merge_titles:
                   merge_orphan.add(titolo_el)
                else:

                    fake_orphan_merge.add(titolo_el)
            else:
                if titolo_el.lower() in merge_titles:
                    fake_orphan_merge.add(titolo_el)


    if "exclusion_mms" in item:
        lista_temporanea_exclusion=item.get("exclusion_mms","")
        for elemento in lista_temporanea_exclusion:
            titolo_el = elemento.get("title","")
            link_el = elemento.get("link","")


            if len(link_el) == 0:
                if titolo_el.lower() not in merge_titles:
                   merge_orphan.add(titolo_el)
                else:
                    fake_orphan_merge.add(titolo_el)
            else:
                if titolo_el.lower() in merge_titles:
                    fake_orphan_merge.add(titolo_el)



    if "inclusion_mms" in item:
        lista_temporanea_inclusion=item.get("inclusion_mms","")
        for elemento in lista_temporanea_inclusion:

            if elemento.lower() not in merge_titles:
                merge_orphan.add(elemento)
            else:
                fake_orphan_merge.add(elemento)

print(f"ho finito di creare l'insieme dei titoli orfani presenti nei campi dal merge e la sua lunghezza è {len(merge_orphan)}\n")
print(f" ho finito anche di creare l'insieme dei titoli che sembravano essere orfani del link e  invece lo avevano, la lunghezza è di : {len(fake_orphan_merge)}")
print("ora devo controllare se questi merge_orphan non sono presenti nemmeno nella foundation e così ho la certezza che siano davvero senza alcun link ")


print("----------------------------------------------------------\n")
print("OTTENGO GLI ORFANI TOTALI ITERANDO SUL SET DEI TITOLI DEL MERGE")
print("----------------------------------------------------------\n")

set_ee=set()
non_orphan_but_foundation=set()


#creo un set in minuscolo una sola volta fuori dal ciclo
for elemento in merge_orphan:

        if elemento.lower() not in foundation_titles:
            set_ee.add(elemento)
        else:
            non_orphan_but_foundation.add(elemento)


print(f"ha finito di creare l'insieme dei titoli orfani NON presenti nei titoli dal merge e della foundation ed ha una lunghezza di {len(set_ee)}, questo valoire indica i veri titoli mancanti di link perchè sono stati iterati sia all'interno dell'insieme dei titoli del merge(= mms) sia all'interno dei titoli della foundation \n")


print("creo il file csv delle entità senza nessun link = entità esterne \n")
nome_output="nuove_entity_esterne_finale.csv"
with open(nome_output,"w",encoding="utf-8") as o:
     for elemento in set_ee:
        o.write(elemento +";\n")


# da qui in poi bisogna trovare i link dei titoli a cui mancano


print("ora devo ottenre un dizionario con contiene i fake_orphan_merge e con la chiave dell'uri ci aggiunge un dict che collega il title al link mms corrispondente\n  ")

# insieme copia per eleiminare i title che hanno un link mms e  link foundation
fake_orphan_merge_copy=fake_orphan_merge.copy()
dizionario_fake_orphan_merge={}

for titolo in fake_orphan_merge:
    titolo_lower=titolo.lower()

    #cerco prima in merge_dict
    if titolo_lower in merge_dict:
        dizionario_fake_orphan_merge[titolo]=merge_dict[titolo_lower]
        fake_orphan_merge_copy.discard(titolo)
    elif titolo_lower in foundation_dict:
        dizionario_fake_orphan_merge[titolo]=foundation_dict[titolo_lower]
        fake_orphan_merge_copy.discard(titolo)

print(f"il mio dict che contiene i fintie orphan ora è lungo: {len(dizionario_fake_orphan_merge)}\n")


print("scrivo il file json")
titolo="titoli_con_link_recuperati.json"
with open(titolo,"w",encoding="utf-8") as z:
    json.dump(dizionario_fake_orphan_merge, z, indent=4, ensure_ascii=False)


#DEVO AGGIUNGERE LA PARTE IN CUI NEL MIO MERGE SOSTITUISCO I TITLE SENZA LINK CON I RISPETTIVI MERGE/FOUDNATION






