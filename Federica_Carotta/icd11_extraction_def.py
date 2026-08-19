
import requests, json

def extraction_icd11(root_link, output_file, localhost="http://localhost", ufficialhost="http://id.who.int"):
    headers = {
        "Accept": "application/json",
        "API-Version": "v2",
        "Accept-Language": "en",
    }

    request_session = requests.Session()
    id_list = [root_link]
    id_already_seen = set()
    download_count = 0

    print(f"Inizio download da: {root_link}")
    
    with open(output_file, "w", encoding="utf-8") as file:
        file.write("[\n")
        first_element = True 
        
        while len(id_list) > 0:
            current_link = id_list.pop(0)
            
            if current_link in id_already_seen:
                continue
                
            id_already_seen.add(current_link)
            local_link = current_link.replace(ufficialhost, localhost)
            
            try:
                call = request_session.get(local_link, headers=headers)
                data = call.json()
            except Exception as e:
                print(f"Errore con {local_link}: {e}")
                continue
                
            download_count += 1

            if not first_element:
                file.write(",\n")
            
            json.dump(data, file, indent=2)
            first_element = False

            # cerca i figli e li aggiunge alla coda da visitare
            children = data.get("child", [])
            for child in children:
                if child not in id_already_seen:
                    id_list.append(child)
                    
        file.write("\n]")

    print(f"Salvato in '{output_file}'. Totale entità: {download_count} ---")
    return download_count

if __name__ == "__main__":
    #richiamo la funzione passando gli argomenti specifici

    ## per MMS
    ROOT_MMS = "http://id.who.int/icd/release/11/2026-01/mms"
    FILE_MMS = "icd11_mms_full.json"
    
    extraction_icd11(root_link=ROOT_MMS, output_file=FILE_MMS)

    ## per FOUNDATION
    ROOT_FOUNDATION = "http://id.who.int/icd/entity"
    FILE_FOUNDATION = "icd11_foundation_full.json"

    extraction_icd11(root_link=ROOT_FOUNDATION, output_file=FILE_FOUNDATION)

    print("Download finito")






