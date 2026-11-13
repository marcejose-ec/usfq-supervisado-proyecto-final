"""Descarga todas las propiedades de arriendayvende.com mediante su API REST pública de WordPress
(/wp-json/wp/v2/properties, tema Houzez) y las taxonomías necesarias para decodificarlas.

Salida: data/raw/arriendayvende_properties.jsonl  y  data/raw/arriendayvende_taxonomias.json
El filtrado (venta, casa/departamento, Quito y valles) se hace en build_dataset.py.

Uso:  python scraper/scrape_arriendayvende.py
"""
import json
import sys
import time
from pathlib import Path

import requests

BASE = "https://arriendayvende.com/wp-json/wp/v2"
UA = "Mozilla/5.0 (compatible; usfq-ml-course-project/1.0)"
DELAY = 1.0
TAXONOMIAS = ["property_type", "property_status", "property_city", "property_area",
              "property_state", "property_label", "property_feature"]
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

s = requests.Session()
s.headers.update({"User-Agent": UA})


def paginar(endpoint, params=None):
    pagina, total = 1, None
    while total is None or pagina <= total:
        for intento in range(3):
            r = s.get(f"{BASE}/{endpoint}", params={"per_page": 100, "page": pagina, **(params or {})}, timeout=60)
            time.sleep(DELAY)
            if r.status_code == 200:
                break
            print(f"  HTTP {r.status_code} {endpoint} p{pagina}", file=sys.stderr)
            time.sleep(5 * (intento + 1))
        else:
            raise RuntimeError(f"no se pudo descargar {endpoint} p{pagina}")
        total = int(r.headers.get("X-WP-TotalPages", 1))
        print(f"{endpoint}: página {pagina}/{total}")
        yield from r.json()
        pagina += 1


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    tax = {t: {str(x["id"]): x["name"] for x in paginar(t, {"_fields": "id,name"})} for t in TAXONOMIAS}
    (RAW / "arriendayvende_taxonomias.json").write_text(json.dumps(tax, ensure_ascii=False, indent=1), encoding="utf-8")
    campos = "id,date,modified,link,title,content," + ",".join(TAXONOMIAS) + ",property_meta"
    n = 0
    with (RAW / "arriendayvende_properties.jsonl").open("w", encoding="utf-8") as out:
        for p in paginar("properties", {"_fields": campos}):
            meta = p.get("property_meta") or {}
            # quitar metadatos pesados que no se usan (imágenes, agentes, planos)
            p["property_meta"] = {k: v for k, v in meta.items()
                                  if not any(x in k for x in ("image", "attach", "agent", "floor_plan", "video", "virtual"))}
            out.write(json.dumps(p, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} propiedades guardadas")


if __name__ == "__main__":
    main()
