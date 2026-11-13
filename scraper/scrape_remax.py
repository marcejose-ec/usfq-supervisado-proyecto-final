"""Descarga anuncios de venta de RE/MAX Ecuador (remax.com.ec) mediante la API JSON pública que usa
su propio sitio web (api-ec.redremax.com). robots.txt de remax.com.ec solo prohíbe URLs con ?associate.

Fase 1: pagina /listings/findAll (operación = venta) y conserva casas/departamentos dentro del
        rectángulo de Quito + valles -> data/raw/remax_listings.jsonl
Fase 2: /listings/findById/{id} de cada uno (parqueaderos, año de construcción, estado, amenidades,
        descripción) -> data/raw/remax_details.jsonl

NO se guardan datos personales de los agentes (nombres, teléfonos, correos): solo el nombre de la oficina.
Reanudable. Uso:  python scraper/scrape_remax.py [--fase 1|2|todo]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import requests

API = "https://api-ec.redremax.com/remaxweb-ec/api"
UA = "Mozilla/5.0 (compatible; usfq-ml-course-project/1.0)"
DELAY = 1.0
TIPOS = {"casa", "departamento"}
# rectángulo Distrito Metropolitano de Quito + Rumiñahui (lat, lon)
LAT, LON = (-0.60, 0.20), (-78.80, -78.20)
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
LISTINGS, DETAILS = RAW / "remax_listings.jsonl", RAW / "remax_details.jsonl"
PERSONALES = ("associate", "listBroker", "coAssociates", "photos", "photos360", "virtualTours", "video")

s = requests.Session()
s.headers.update({"User-Agent": UA})


def get_json(path, params=None, intentos=3):
    for i in range(intentos):
        try:
            r = s.get(f"{API}/{path}", params=params, timeout=60)
            time.sleep(DELAY)
            if r.status_code == 200:
                return r.json().get("data")
            if r.status_code == 404:
                return None
            print(f"  HTTP {r.status_code} {path}", file=sys.stderr)
        except (requests.RequestException, ValueError) as e:
            print(f"  error {e} {path}", file=sys.stderr)
        time.sleep(5 * (i + 1))
    return None


def limpiar(x):
    """Quita datos personales y pesados; conserva solo el nombre de la oficina."""
    oficina = ((x.get("associate") or {}).get("office") or {}).get("name")
    x = {k: v for k, v in x.items() if k not in PERSONALES}
    x["oficina"] = oficina
    return x


def en_quito(x):
    c = (x.get("location") or {}).get("coordinates")
    return bool(c) and LAT[0] < c[1] < LAT[1] and LON[0] < c[0] < LON[1]


def fase1():
    pagina, total, n = 0, None, 0
    with LISTINGS.open("w", encoding="utf-8") as out:
        while total is None or pagina < total:
            d = get_json("listings/findAll", {"page": pagina, "pageSize": 200, "sort": "-createdAt",
                                              "in:operationId": 1})
            if d is None:
                raise RuntimeError(f"falló la página {pagina}")
            total = d["totalPages"]
            for x in d["data"]:
                if (x.get("type") or {}).get("value") in TIPOS and en_quito(x):
                    out.write(json.dumps(limpiar(x), ensure_ascii=False) + "\n")
                    n += 1
            print(f"página {pagina + 1}/{total}: {n} casas/departamentos en Quito+valles")
            pagina += 1


def fase2():
    ids = [json.loads(l)["id"] for l in LISTINGS.open(encoding="utf-8")]
    hechos = {json.loads(l)["id"] for l in DETAILS.open(encoding="utf-8")} if DETAILS.exists() else set()
    pend = [i for i in ids if i not in hechos]
    print(f"{len(pend)} detalles pendientes ({len(hechos)} ya descargados)")
    with DETAILS.open("a", encoding="utf-8") as out:
        for k, i in enumerate(pend, 1):
            d = get_json(f"listings/findById/{i}")
            out.write(json.dumps(limpiar(d) if d else {"id": i, "error": "no_disponible"}, ensure_ascii=False) + "\n")
            out.flush()
            if k % 100 == 0:
                print(f"  {k}/{len(pend)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fase", default="todo", choices=["1", "2", "todo"])
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    if a.fase in ("1", "todo"):
        fase1()
    if a.fase in ("2", "todo"):
        fase2()
