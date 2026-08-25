import json 


print("carico dataset")
with open("./icd11_mms_completo.json","r",encoding="utf-8") as a:
    mms=json.load(a)
with open("./icd11_foundation_completo.json","r",encoding="utf-8") as b:
    foundation=json.load(b)
print("dataset caricati")

insieme_mms=set()
elementi_saltati_mms=set()
for item in mms:
    if "@id" in item:
        link_mms=item.get("@id","")
        if len(link_mms) > 0:
            insieme_mms.add(link_mms)
        else:
            print("un mms è saltato devi controllare\n")

print(f"la lunghezza dell'insieme_mms è {len(insieme_mms)} ")
print("sctrivo il file con tutti i links mms")

titolo="link_mms.txt"
with open(titolo,"w",encoding="utf-8") as c:
    for elemento in insieme_mms:
        c.writelines(elemento+"\n")

insieme_foundation=set()
elementi_saltati_foundation=set()
for item in foundation:
    if "@id" in item:
        link_foundation=item.get("@id","")
        if len(link_foundation)>0:
            insieme_foundation.add(link_foundation)
        else:
            print("un link founadation è saltato devi controllare\n")

print(f"la lunghezza dell'insieme_mms è {len(insieme_foundation)} ")
print("scrivo il file con tutti i link foundation")
titolo="links_foundation.txt"
with open(titolo,"w",encoding="utf-8") as d:
    for elemento in insieme_foundation:
        d.writelines(elemento+"\n")

