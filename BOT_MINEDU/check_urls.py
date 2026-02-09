import requests

urls = [
    "https://titulosinstitutos.minedu.gob.pe/",
    "http://titulosinstitutos.minedu.gob.pe/",
    "https://constanciasweb.sunedu.gob.pe/",
    "https://www.gob.pe/941-consultar-titulos-de-instituciones-tecnologicas-y-pedagogicas"
]

for url in urls:
    try:
        print(f"Checking {url}...")
        r = requests.get(url, timeout=5, verify=False)
        if "gobpe-consulta-busca" in r.text or "DOCU_NUM" in r.text:
            print(f"MATCH FOUND: {url}")
        else:
            print(f"No match for {url}")
    except Exception as e:
        print(f"Error {url}: {e}")
