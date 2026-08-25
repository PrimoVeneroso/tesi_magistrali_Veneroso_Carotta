import requests, json
from collections import deque

BASE_LOCAL = "http://localhost"
CANONICAL_HOST = "http://id.who.int"

HEADERS = {
    "Accept": "application/json",
    "API-Version": "v2",
    "Accept-Language": "en",
}

def to_local(uri: str) -> str:
    return uri.replace(CANONICAL_HOST, BASE_LOCAL)

def fetch(session, uri):
    r = session.get(to_local(uri), headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def crawl(root_uri):
    session = requests.Session()
    seen = set()
    queue = deque([root_uri])
    entities = []

    while queue:
        uri = queue.popleft()
        if uri in seen:
            continue
        seen.add(uri)
        try:
            data = fetch(session, uri)
        except Exception as e:
            print(f"Errore su {uri}: {e}")
            continue

        entities.append(data)
        for child_uri in data.get("child", []):
            if child_uri not in seen:
                queue.append(child_uri)

        if len(entities) % 200 == 0:
            print(f"Scaricate {len(entities)} entità...")

    return entities

if __name__ == "__main__":
    # controlla nel browser quale release è caricata e aggiorna qui
    root = "http://id.who.int/icd/release/11/2026-01/mms"

    entities = crawl(root)
    print(f"Totale entità scaricate: {len(entities)}")

    with open("icd11_mms_completo.json", "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)
        
