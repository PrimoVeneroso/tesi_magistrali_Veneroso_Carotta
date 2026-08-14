import json 

with open("/home/primo/Scaricati/ICD11_progetto/foundation/icd11_foundation_completo.json","r",encoding="utf-8") as f:

    foundation=json.load(f)

dict_foundation_uri_title={}
for item in foundation:
    if "@id" in item:
        uri = item.get("@id", "")
        title_og=item.get("title")
        title_text=title_og.get("@value","") if isinstance(title_og,dict) else  ""

        if uri:
            dict_foundation_uri_title[uri]= title_text
#print(dict_foundation_uri_title)

with open ("fusione.json","r",encoding="utf-8") as g:
    dataset_da_sostituire=json.load(g)

for item in dataset_da_sostituire:
    if "parent_mms" in item and isinstance(item["parent_mms"], list):
        nuova_lista_parent=[]

        for link in item["parent_mms"]:

            if link in dict_foundation_uri_title:

                titolo = dict_foundation_uri_title[link]
                nuova_lista_parent.append(titolo)
            else:
                nuova_lista_parent.append(link)
        item["parent_mms"]=nuova_lista_parent

    if "child_foundation" in item and isinstance(item["child_foundation"],list):
        nuova_lista_child=[]
        for link in item["child_foundation"]:
            if link in dict_foundation_uri_title:
                titolo= dict_foundation_uri_title[link]
                nuova_lista_child.append(titolo)
            else:
                nuova_lista_child.append(link)
        item["child_foundation"]=nuova_lista_child
    
with open("fusione_con_titoli.json", "w", encoding="utf-8") as h:
    json.dump(dataset_da_sostituire, h, indent=4, ensure_ascii=False)




print("Sostituzione URI con dizionari (URI + Titolo)...")

# Elenco dei campi che contengono link ad altre entità da convertire
campi_con_uri = [
    "mms_link",
    "parent_mms",
    "parent_foundation",
    "child_foundation",
    "relatedEntitiesInMaternalChapter",
    "relatedEntitiesInPerinatalChapter"
]

dati_fusi_sostituzione = []

for elemento in dati_fusi:
    # Creo una copia per non sovrascrivere direttamente durante l'iterazione
    nuovo_elemento = elemento.copy()

    for campo in campi_con_uri:
        if campo in nuovo_elemento:
            # Sostituiamo le URI con il dizionario con i titoli
            # 'foundation_uri' è escluso perché non presente in 'campi_con_uri'
            nuovo_elemento[campo] = risolvi_uri(nuovo_elemento[campo])

    dati_fusi_sostituzione.append(nuovo_elemento)

nome_file_output = "fusion_sostituzione.json"
with open(nome_file_output, "w", encoding="utf-8") as h:
    json.dump(dati_fusi_sostituzione, h, indent=4, ensure_ascii=False)

print(f"\nOperazione completata con successo! Salfato in '{nome_file_output}'.")

print("FILE SAVATO")


            
    
        
