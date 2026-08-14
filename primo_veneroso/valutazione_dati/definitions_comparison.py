import json 

def confronto_campi(campo1,campo2,data,pk):
    confronto_dict={}
    for entity in data:
        if campo1 in entity:
            nuova_chiave=entity[pk]
            campo1_confronto=entity.get(campo1,"")
            campo2_confronto=entity.get(campo2,"")
            if campo1_confronto != "" and campo2_confronto != "":
                confronto_dict[nuova_chiave]=dict(campo1=campo1_confronto, campo2=campo2_confronto)

    return confronto_dict

with open("/home/primo/Scaricati/ICD11_progetto/hybrid/fusion_sostituzione.json", "r",encoding="utf-8") as f:
    data=json.load(f)

risultato=confronto_campi("definition_mms","definition_foundation",data,"mms_link")


with open("risultato.json","w",encoding="utf-8") as h:
    json.dump(risultato, h, indent=4, ensure_ascii=False)


