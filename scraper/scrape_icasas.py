"""Scraper de anuncios de venta (casas y departamentos) de icasas.ec para Quito y Rumiñahui.

Fase 1: recorre las páginas de resultados (/venta/{tipo}/{canton}/p_N) y guarda los
        datos de cada tarjeta en data/raw/icasas_listings.jsonl
Fase 2: visita la página de detalle de cada anuncio y guarda coordenadas, parroquia,
        características (amenidades) y descripción en data/raw/icasas_details.jsonl

Es reanudable: si se interrumpe, al volver a ejecutarlo continúa donde quedó.
Respeta robots.txt de icasas.ec (las rutas usadas no están prohibidas) y espera
DELAY segundos entre peticiones.

Uso:  python scraper/scrape_icasas.py [--fase 1|2|todo]
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.icasas.ec"
UA = "Mozilla/5.0 (compatible; usfq-ml-course-project/1.0)"
DELAY = 1.0
BUSQUEDAS = [  # (tipo, canton)
    ("casas", "quito"),
    ("departamentos", "quito"),
    ("casas", "ruminahui"),
    ("departamentos", "ruminahui"),
]
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
LISTINGS = RAW / "icasas_listings.jsonl"
DETAILS = RAW / "icasas_details.jsonl"

session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept-Language": "es-EC,es;q=0.9"})


def get(url, intentos=3):
    for i in range(intentos):
        try:
            r = session.get(url, timeout=30)
            time.sleep(DELAY)
            if r.status_code == 200:
                return r.text
            if r.status_code in (404, 410):
                return None
            print(f"  HTTP {r.status_code} en {url}", file=sys.stderr)
        except requests.RequestException as e:
            print(f"  error {e} en {url}", file=sys.stderr)
        time.sleep(5 * (i + 1))
    return None


def leer_jsonl(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def txt(el):
    return el.get_text(" ", strip=True) if el else None


def parse_tarjeta(li, tipo, canton):
    a = li.select_one("h2.title a")
    agencia = li.select_one('.agencyLogo meta[itemprop="name"]')
    return {
        "id": li.get("id"),
        "url": BASE + a["href"] if a else None,
        "tipo_busqueda": tipo,
        "canton_busqueda": canton,
        "titulo": txt(a),
        "precio_raw": txt(li.select_one(".price")),
        "area_raw": txt(li.select_one(".areaBuilt")),
        "habitaciones_raw": txt(li.select_one(".rooms")),
        "banos_raw": txt(li.select_one(".bathrooms")),
        "descripcion_corta": txt(li.select_one(".description")),
        "agencia": agencia["content"] if agencia else None,
        "clases": " ".join(li.get("class", [])),
    }


def fase1():
    ya = {d["id"] for d in leer_jsonl(LISTINGS)}
    with LISTINGS.open("a", encoding="utf-8") as out:
        for tipo, canton in BUSQUEDAS:
            pagina, sin_nuevos = 1, 0
            while True:
                url = f"{BASE}/venta/{tipo}/{canton}" + (f"/p_{pagina}" if pagina > 1 else "")
                html = get(url)
                if html is None:
                    break
                lis = BeautifulSoup(html, "lxml").select("li.serp-snippet")
                nuevos = 0
                for li in lis:
                    d = parse_tarjeta(li, tipo, canton)
                    if d["id"] and d["id"] not in ya:
                        ya.add(d["id"])
                        out.write(json.dumps(d, ensure_ascii=False) + "\n")
                        nuevos += 1
                out.flush()
                print(f"{tipo}/{canton} p{pagina}: {len(lis)} tarjetas, {nuevos} nuevas (total {len(ya)})")
                # icasas repite la última página al pasarse del final; paramos tras 2 páginas sin novedades
                sin_nuevos = sin_nuevos + 1 if nuevos == 0 else 0
                if not lis or sin_nuevos >= 2 or pagina >= 200:
                    break
                pagina += 1


def parse_detalle(html, id_):
    s = BeautifulSoup(html, "lxml")
    d = {"id": id_}
    mapa = s.select_one("[data-x][data-y]")
    d["latitud"] = mapa.get("data-x") if mapa else None
    d["longitud"] = mapa.get("data-y") if mapa else None
    d["breadcrumb"] = [txt(x) for x in s.select("li.detail-bread-li")]
    d["titulo_detalle"] = txt(s.select_one("section.detail_scroll .title"))
    d["precio_detalle"] = txt(s.select_one("section.detail_scroll .price"))
    d["detalles"] = [txt(x) for x in s.select("section.detail_scroll ul.details_list li")]
    caracts = {}
    for bloque in s.select("div.dropdown-list"):
        h = txt(bloque.select_one("h2.title"))
        if h:
            caracts[h] = [txt(x) for x in bloque.select("li")]
    d["caracteristicas"] = caracts
    # descripción completa: bloque .info que contiene la localización y el texto
    info = [txt(x) for x in s.select(".info")]
    d["descripcion"] = max(info, key=lambda t: len(t or ""), default=None)
    ref = s.find(string=re.compile(r"Número de referencia"))
    d["referencia"] = txt(ref.parent) if ref else None
    return d


def fase2():
    listings = leer_jsonl(LISTINGS)
    hechos = {d["id"] for d in leer_jsonl(DETAILS)}
    pendientes = [d for d in listings if d["id"] not in hechos and d.get("url")]
    print(f"{len(pendientes)} detalles pendientes ({len(hechos)} ya descargados)")
    with DETAILS.open("a", encoding="utf-8") as out:
        for i, d in enumerate(pendientes, 1):
            html = get(d["url"])
            det = parse_detalle(html, d["id"]) if html else {"id": d["id"], "error": "no_disponible"}
            out.write(json.dumps(det, ensure_ascii=False) + "\n")
            out.flush()
            if i % 50 == 0:
                print(f"  {i}/{len(pendientes)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fase", default="todo", choices=["1", "2", "todo"])
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    if a.fase in ("1", "todo"):
        fase1()
    if a.fase in ("2", "todo"):
        fase2()
