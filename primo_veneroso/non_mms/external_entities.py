import json

print("carico i dati")
with open ("../fusione_sostituzione_link_dict_2.json","r",encoding="utf-8") as f:
    data=json.load(f)

lista_index= "index_term_synonyms"
sinonimi_f="synonyms_foundation"
inclusion="inclusion_mms"
exclusion="exclusion_mms"

#creo il set per non avere ripetizioni
other_entities=set()

for item in data:

    if sinonimi_f in item and len(item.get("synonyms_foundation",""))>0:
        for entity in item.get("synonyms_foundation",""):
            other_entities.add(entity)
    if lista_index in item:# and isinstance(item.get("index_term_synonyms",""),dict):
        lista_temporanea_index=item.get("index_term_synonyms","")
        for elemento in lista_temporanea_index:
            if len(elemento.get("link","")) == 0:
                #print(elemento.get("link",""))
                other_entities.add(elemento.get("title",""))
    if exclusion in item:
        lista_temporanea_exclusion=item.get("exclusion_mms","")
        for elemento in lista_temporanea_exclusion:
            if len(elemento.get("link","")) == 0:
                other_entities.add(elemento.get("title",""))
    if inclusion in item:
        lista_temporanea_inclusion=item.get("inclusion_mms","")
        for elemento in lista_temporanea_inclusion:
            other_entities.add(elemento)

print("creo il nuovo file")

with open("lista_nuove_entity.md","w",encoding="utf") as g:

    for entity in other_entities:
        g.write(entity+";\n")





