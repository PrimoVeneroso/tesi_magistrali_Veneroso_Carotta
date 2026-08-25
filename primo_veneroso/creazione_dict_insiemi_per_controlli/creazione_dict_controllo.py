import json 
import re 


PATTERN_MMS_ID_COMPLETO = re.compile(r'/(?:mms|entity)/(\d+(?:/[a-zA-Z0-9_-]+)*)(?:/|$)')

def estrai_id_mms(url: str) -> str:

    if not isinstance(url, str) or not url:
        return ""

    url_pulito = url.rstrip('/')

    # Gestione esplicita del nodo top-level
    if url_pulito.endswith('/mms') or url_pulito.endswith('/entity'):
        return "root"

    match = PATTERN_MMS_ID_COMPLETO.search(url)
    return match.group(1) if match else ""


print("carico dataset")
with open("../mms/mms_completo.json","r",encoding="utf-8") as a:
    mms=json.load(a)
with open("../foundation/icd11_foundation_completo.json","r",encoding="utf-8") as b:
    foundation=json.load(b)
print("dataset caricati")

dict_mms={}
for item in mms:
    if "@id" in item:
        link_mms=item.get("@id","")
        if len(link_mms) > 0:
            uri=estrai_id_mms(link_mms)
            titolo_mms_parziale=item.get("title","")
            source_mms=item.get("source","")
            browserl_Url=item.get("browserUrl","")

            if uri and len(uri)>0:
                titolo_mms=titolo_mms_parziale.get("@value")
                dict_mms[uri]={"link":link_mms,
                               "title":titolo_mms, 
                               "foundation_uri": source_mms,
                               "browserUrl": browserl_Url
                               } 
        else:
            print("un mms è saltato devi controllare\n")

print(f"la lunghezza del dict_mms è {len(dict_mms)} ")
print("sctrivo il file con tutti i links mms")

titolo="file_controllo_uri_links_mms.json"
with open(titolo,"w",encoding="utf-8") as c:
    json.dump(dict_mms, c, indent=4, ensure_ascii=False)


dict_foundation={}
for item in foundation:
    if "@id" in item:
        link_foundation=item.get("@id","")
        if len(link_foundation)>0:
            uri_foundation=estrai_id_mms(link_foundation)
            titolo_foundation_parziale=item.get("title","")
            browserl_Url_f=item.get("browserUrl","")

            if uri_foundation and len(uri_foundation)>0:
                titolo_foundation=titolo_foundation_parziale.get("@value")
                dict_foundation[uri_foundation]={"link":link_foundation,
                                      "title":titolo_foundation, 
                                      "browserUrl": browserl_Url_f
                                      } 

print(f"la lunghezza dell'insieme_mms è {len(dict_foundation)} ")
print("scrivo il file con tutti i link foundation")
titolo="links_foundation.txt"

titolo="file_controllo_uri_links_foundation.json"
with open(titolo,"w",encoding="utf-8") as d:
    json.dump(dict_foundation, d, indent=4, ensure_ascii=False)

