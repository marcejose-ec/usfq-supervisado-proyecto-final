"""Convierte los JSONL crudos de icasas.ec en data/casas_quito.csv (limpio, sin imputar).

Uso:  python scraper/build_dataset.py
Imprime el conteo de filas en cada paso de limpieza (copiado a data/README.md).
"""
import json
import sys
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "casas_quito.csv"
# Fecha fija de la recolección (11–12 nov. 2026; los crudos no guardan la fecha por fila). No usar date.today():
# volver a correr este script otro día no debe cambiar el dataset.
FECHA_SCRAPING = "2026-11-12"
ANIO_REFERENCIA = 2026  # para convertir año de construcción en antigüedad


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()


def num(s):
    """'1.234,5' -> 1234.5 (formato es-EC: punto miles, coma decimal)."""
    if s is None:
        return np.nan
    m = re.search(r"\d[\d.,]*", str(s))
    if not m:
        return np.nan
    t = m.group().rstrip(".,")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return np.nan


def es_rango(s):
    return bool(s) and bool(re.search(r"\d\s*-\s*\d", str(s)))


# --- zona a partir de la parroquia (breadcrumb de icasas) -------------------
ZONAS = {
    "quito_urbano": ["norte quito", "centro quito", "sur quito", "sur de quito", "norte de quito",
                     "centro de quito", "quito", "ponceano", "carcelen", "el condado",
                     "centro norte de quito", "la carolina", "el batan", "san isidro del inca",
                     # Monteserrín está en el límite de longitud con Cumbayá; se fija explícitamente
                     "monteserrin", "lomas de monteserrin", "campo alegre",
                     # Rumipamba también es parroquia urbana de Quito; la de Rumiñahui se asigna por cantón
                     "rumipamba"],
    "valle_cumbaya_tumbaco": ["cumbaya", "tumbaco", "puembo", "pifo", "tababela", "yaruqui",
                              "checa", "checa (chilpa)", "quinche", "el quinche", "nayon",
                              "miravalle", "tanda", "la primavera", "lumbisi", "santa lucia",
                              "bellavista de la vina", "bella vista de la vina", "yanazarapata", "la ceramica",
                              "la morita", "san patricio", "santa monica", "vina alta", "nuevo pifo",
                              "san juan de cumbaya", "escalon de tumbaco", "el arenal", "collaqui"],
    "rural_otro": ["nono", "nanegal", "nanegalito", "puellaro", "perucho", "chavezpamba",
                   "atahualpa", "pacto", "gualea", "lloa", "calacali", "mindo"],
    "valle_los_chillos": ["conocoto", "alangasi", "amaguana", "guangopolo", "merced", "la merced",
                          "pintag", "ruminahui", "sangolqui", "san rafael", "san pedro de taboada",
                          "cotogchoa", "los chillos", "valle de los chillos",
                          "la armenia", "capelo", "san pedro"],
    "norte_pomasqui_calderon": ["pomasqui", "san antonio", "calderon", "carapungo", "llano chico",
                                "guayllabamba", "zambiza", "mitad del mundo",
                                "llano grande", "marianitas", "pusuqui"],
}
PARR2ZONA = {p: z for z, ps in ZONAS.items() for p in ps}

# --- amenidades: (columna, patrones en la lista de características) ---------
AMENIDADES = {
    "piscina": ["piscina", "pileta"],
    "jardin": ["jardin"],
    "gimnasio": ["gimnasio"],
    "ascensor": ["ascensor"],
    "seguridad": ["seguridad", "caseta de vigilancia", "portero", "guardiania"],
    "bbq": ["bbq", "parrilla"],
    "terraza": ["terraza"],
    "balcon": ["balcon"],
    "bodega": ["bodega", "baulera"],
    "zona_ninos": ["zona ninos", "juegos infantiles"],
    "estacionamiento": ["estacionamiento"],
    "cocina_equipada": ["cocina equipada"],
    "calefaccion": ["calefaccion", "chimenea"],
    "vista_panoramica": ["vista panoramica"],
    "patio": ["patio"],
    "jacuzzi_sauna": ["jacuzzi", "sauna", "turco", "hidromasaje"],
    "acceso_discapacitados": ["discapacitados", "movilidad reducida"],
}

# "300 m2 de terreno"  o  "terreno de 600 metros" / "lote: 1.125 m2" (sin texto intermedio)
RE_TERRENO_ANTES = re.compile(r"(\d[\d.,]*)\s*(?:m2|mts2?|metros(?: cuadrados)?)\s*de\s+(?:terreno|lote)")
RE_TERRENO = re.compile(r"(?:terreno|lote)(?:\s|:|de\b|con\b|total\b|aprox\.?|aproximad[oa]\b)*(\d[\d.,]*)\s*(?:m2|mts2?|metros)")
RE_PARQ = re.compile(r"(\d{1,2}|un|uno|dos|tres|cuatro)\s+(?:parqueaderos?|estacionamientos?|garajes?|puestos de parqueo)")
RE_ALICUOTA = re.compile(r"alicuota[^\d]{0,25}?(\d[\d.,]*)")
RE_ANIO = re.compile(r"(?:construid[ao]|construccion|ano de construccion)\D{0,15}((?:19[5-9]|20[0-2])\d)")
RE_ANTIG = re.compile(r"(\d{1,2})\s*anos de (?:construccion|construida|construido|antiguedad)")
RE_PISO = re.compile(r"(?:piso|planta)\s*(\d{1,2})\b|(\d{1,2})\s*(?:er|do|to|vo|no|mo)?\s*piso")
PALABRAS = {"uno": 1, "un": 1, "dos": 2, "tres": 3, "cuatro": 4}


def extraer_texto(t):
    t = norm(t or "")
    r = {}
    m = RE_TERRENO_ANTES.search(t) or RE_TERRENO.search(t)
    r["area_terreno_m2"] = num(m.group(1)) if m else np.nan
    m = RE_PARQ.search(t)
    r["parqueaderos"] = (PALABRAS.get(m.group(1)) or num(m.group(1))) if m else np.nan
    m = RE_ALICUOTA.search(t)
    r["alicuota"] = num(m.group(1)) if m else np.nan
    m = RE_ANIO.search(t)
    r["anio_construccion"] = float(m.group(1)) if m else np.nan
    m = RE_ANTIG.search(t)
    r["antiguedad_anios"] = float(m.group(1)) if m else np.nan
    m = RE_PISO.search(t)
    r["piso"] = num(m.group(1) or m.group(2)) if m else np.nan
    if re.search(r"en planos|preventa|pre-venta|en construccion", t):
        r["estado"] = "en_planos"
    elif re.search(r"a estrenar|para estrenar|nuev[ao]s?\b", t):
        r["estado"] = "nuevo"
    elif re.search(r"remodelad|usad[ao]|anos de construccion|anos de antiguedad", t):
        r["estado"] = "usado"
    else:
        r["estado"] = np.nan
    return r


def flags_amenidades(textos):
    """textos: Serie con la lista de características ya normalizada (o None si no hay detalle)."""
    return pd.DataFrame({col: textos.apply(lambda t: np.nan if t is None else float(any(x in t for x in pats)))
                         for col, pats in AMENIDADES.items()}, index=textos.index)


# ---------------------------------------------------------------- icasas.ec
def cargar_icasas(pasos):
    L = pd.read_json(RAW / "icasas_listings.jsonl", lines=True)
    D = pd.read_json(RAW / "icasas_details.jsonl", lines=True)
    df = L.merge(D, on="id", how="left")
    pasos.append(("icasas.ec: anuncios únicos scrapeados (por id)", len(df)))

    if "error" in df:
        df = df[df["error"].isna()]
    df = df[df["latitud"].notna() | df["breadcrumb"].notna()]
    pasos.append(("icasas.ec: con página de detalle disponible", len(df)))

    bc = df["breadcrumb"].apply(lambda b: b if isinstance(b, list) else [])
    det = df["detalles"].apply(lambda x: x if isinstance(x, list) else [])
    rango = det.apply(lambda xs: any(es_rango(x) for x in xs)) | df["area_raw"].apply(es_rango) | \
        df["habitaciones_raw"].apply(es_rango)
    df, bc = df[~rango], bc[~rango]
    pasos.append(("icasas.ec: sin rangos de área/habitaciones (proyectos con varias tipologías)", len(df)))

    out = pd.DataFrame({
        "id": "icasas_" + df["id"].astype(str),
        "fuente": "icasas.ec",
        "url": df["url"],
        "fecha_publicacion": np.nan,  # icasas no muestra la fecha de publicación
        "tipo": df["tipo_busqueda"].map({"casas": "casa", "departamentos": "departamento"}),
        "precio": df["precio_raw"].apply(num),
        "area_construida_m2": df["area_raw"].apply(num),
        "habitaciones": df["habitaciones_raw"].apply(num),
        "banos": df["banos_raw"].apply(num),
        "canton": df["canton_busqueda"].map({"quito": "Quito", "ruminahui": "Rumiñahui"}),
        "sector": bc.apply(lambda b: b[-1] if len(b) >= 5 else np.nan),
        "latitud": pd.to_numeric(df["latitud"], errors="coerce"),
        "longitud": pd.to_numeric(df["longitud"], errors="coerce"),
        "es_desarrollo": (bc.apply(lambda b: any("desarrollo" in norm(x) for x in b)) |
                          df["precio_raw"].fillna("").str.contains("Desde")).astype(int),
        "agencia": df["agencia"],
        "titulo": df["titulo"],
        "descripcion": df["descripcion"].fillna(df["descripcion_corta"]),
    }, index=df.index)
    caracts = df["caracteristicas"].apply(
        lambda c: norm(" | ".join(sum(c.values(), []))) if isinstance(c, dict) else None)
    out = pd.concat([out, flags_amenidades(caracts)], axis=1)
    amueb = caracts.fillna("").str.extract(r"amueblado: ([a-z ]+?)(?: \||$)")[0]
    out["amoblado"] = amueb.map(lambda v: np.nan if pd.isna(v) else float(not v.startswith("sin")))
    # icasas no tiene estos campos estructurados -> se extraen del texto más abajo
    for c in ["area_terreno_m2", "parqueaderos", "antiguedad_anios", "alicuota"]:
        out[c] = np.nan
    return out


# ------------------------------------------------------- arriendayvende.com
def cargar_arriendayvende(pasos):
    T = json.loads((RAW / "arriendayvende_taxonomias.json").read_text(encoding="utf-8"))
    P = [json.loads(l) for l in (RAW / "arriendayvende_properties.jsonl").open(encoding="utf-8")]
    pasos.append(("arriendayvende.com: propiedades descargadas (todas las operaciones/ciudades)", len(P)))

    def nombres(p, t):
        return [T[t].get(str(i), str(i)) for i in p.get(t, [])]

    def m(p, k):
        v = (p.get("property_meta") or {}).get(k) or [None]
        return v[0] if v[0] not in ("", None) else None

    P = [p for p in P if "Venta" in nombres(p, "property_status")
         and set(nombres(p, "property_type")) & {"Casa", "Departamento"}]
    pasos.append(("arriendayvende.com: venta de casas/departamentos", len(P)))
    P = [p for p in P if "Quito" in nombres(p, "property_city")]
    pasos.append(("arriendayvende.com: ciudad = Quito (incluye valles: Conocoto, Sangolquí, Cumbayá…)", len(P)))

    filas = []
    for p in P:
        tipos = nombres(p, "property_type")
        tipo = "casa" if "Casa" in tipos else "departamento"
        anio_txt = norm(m(p, "fave_property_year") or "")
        if "estrenar" in anio_txt or "construccion" in anio_txt:
            antig = 0.0
        else:
            antig = num(anio_txt)
            if antig and antig > 1900:  # a veces ponen el año en lugar de la antigüedad
                antig = ANIO_REFERENCIA - antig
        postfix = norm(m(p, "fave_property_price_postfix") or "")
        lat = m(p, "houzez_geolocation_lat")
        lon = m(p, "houzez_geolocation_long")
        if lat is None and m(p, "fave_property_location"):
            lat, lon, *_ = (m(p, "fave_property_location").split(",") + [None, None])
        sector = nombres(p, "property_area")
        caracts = norm(" | ".join(nombres(p, "property_feature")))
        filas.append({
            "id": f"arriendayvende_{p['id']}",
            "fuente": "arriendayvende.com",
            "url": p["link"],
            "fecha_publicacion": p["date"][:10],
            "tipo": tipo,
            "precio": num(m(p, "fave_property_price")),
            "area_construida_m2": num(m(p, "fave_property_size")),
            "habitaciones": num(m(p, "fave_property_bedrooms")),
            "banos": num(m(p, "fave_property_bathrooms")),
            "canton": "Rumiñahui" if any(norm(s) in ("sangolqui", "san rafael") for s in sector) else "Quito",
            "sector": sector[0] if sector else np.nan,
            "latitud": pd.to_numeric(lat, errors="coerce"),
            "longitud": pd.to_numeric(lon, errors="coerce"),
            "es_desarrollo": 0,
            "agencia": np.nan,
            "titulo": re.sub(r"<[^>]+>", " ", p["title"]["rendered"]),
            "descripcion": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p["content"]["rendered"])).strip(),
            "caracts": caracts,
            # en departamentos el "terreno" suele repetir el área construida -> no se usa
            "area_terreno_m2": num(m(p, "fave_property_land")) if tipo == "casa" else np.nan,
            "parqueaderos": num(m(p, "fave_property_garage")),
            "antiguedad_anios": antig if antig is not None else np.nan,
            "alicuota": num(m(p, "fave_property_sec_price")) if "alicuota" in postfix else np.nan,
            "amoblado": 1.0 if "amoblado" in caracts else 0.0,
        })
    out = pd.DataFrame(filas)
    out.index = "a" + out.index.astype(str)
    out = pd.concat([out, flags_amenidades(out.pop("caracts"))], axis=1)
    return out



# ------------------------------------------------------------- remax.com.ec
def cargar_remax(pasos):
    L = [json.loads(l) for l in (RAW / "remax_listings.jsonl").open(encoding="utf-8")]
    D = {}
    if (RAW / "remax_details.jsonl").exists():
        for l in (RAW / "remax_details.jsonl").open(encoding="utf-8"):
            d = json.loads(l)
            if "error" not in d:
                D[d["id"]] = d
    pasos.append(("remax.com.ec: venta casas/departamentos en Quito+valles (rectángulo de coordenadas)", len(L)))
    L = [x for x in L if x["id"] in D]
    pasos.append(("remax.com.ec: con detalle disponible", len(L)))
    # rectángulo más estricto: excluye Machachi/Tambillo (Mejía), Mindo y Cayambe
    L = [x for x in L if -0.40 < x["location"]["coordinates"][1] < 0.10
         and -78.60 < x["location"]["coordinates"][0] < -78.25]
    pasos.append(("remax.com.ec: dentro de DMQ urbano + valles (lat -0.40..0.10, lon -78.60..-78.25)", len(L)))
    filas = []
    for x in L:
        d = {**x, **D[x["id"]]}
        if (d.get("currency") or {}).get("value") != "USD" or d.get("priceExposure") is False:
            continue
        lon, lat = (d.get("location") or {}).get("coordinates", [np.nan, np.nan])
        conds = {c["value"] for c in d.get("conditions") or []}
        feats = norm(" | ".join(f["lang"].replace("_", " ") for f in d.get("features") or []))
        anio = d.get("yearBuilt")
        tipo = d["type"]["value"]
        filas.append({
            "id": f"remax_{d['id']}",
            "fuente": "remax.com.ec",
            "url": f"https://www.remax.com.ec/listings/{d['slug']}",
            "fecha_publicacion": np.nan,
            "tipo": tipo,
            "precio": d.get("price"),
            "area_construida_m2": d.get("dimensionTotalBuilt") or d.get("dimensionCovered") or np.nan,
            "habitaciones": d.get("bedrooms") if d.get("bedrooms") is not None else np.nan,
            "banos": (d.get("bathrooms") or 0) + 0.5 * (d.get("toilets") or 0) if d.get("bathrooms") is not None else np.nan,
            "canton": "Quito",
            "sector": np.nan,
            "latitud": lat, "longitud": lon,
            "es_desarrollo": 0,
            "agencia": d.get("oficina"),
            "titulo": d.get("title"),
            "descripcion": re.sub(r"\s+", " ", d.get("description") or "").strip(),
            "caracts": feats,
            "area_terreno_m2": (d.get("dimensionLand") or np.nan) if tipo == "casa" else np.nan,
            "parqueaderos": d.get("parkingSpaces") if d.get("parkingSpaces") is not None else np.nan,
            "antiguedad_anios": (ANIO_REFERENCIA - anio) if anio and anio > 1900 else np.nan,
            "alicuota": d.get("expensesPrice") or np.nan,
            "amoblado": float(bool(d.get("furnished")) or "amoblado" in feats),
            "estado_fuente": "nuevo" if "a_estrenar" in conds else ("en_planos" if "en_construccion" in conds
                                                                    else ("usado" if conds else np.nan)),
        })
    out = pd.DataFrame(filas)
    out.index = "r" + out.index.astype(str)
    out = pd.concat([out, flags_amenidades(out.pop("caracts"))], axis=1)
    return out


# ------------------------------------------- sitios de constructoras (agentes)
def cargar_constructoras(pasos):
    """Tipologías de proyectos nuevos recopiladas a mano por agentes (data/raw/constructoras/*.jsonl).
    Un precio "desde" corresponde siempre a la unidad más pequeña del proyecto (precio_es_desde=1)."""
    from urllib.parse import urlparse
    filas = []
    for fp in sorted((RAW / "constructoras").glob("agente_*.jsonl")):
        for l in fp.open(encoding="utf-8"):
            if l.strip():
                try:
                    filas.append({**json.loads(l), "_archivo": fp.stem})
                except json.JSONDecodeError:
                    print(f"  línea inválida en {fp.name}", file=sys.stderr)
    if not filas:
        return pd.DataFrame()
    c = pd.DataFrame(filas)
    pasos.append(("constructoras: tipologías recopiladas por agentes", len(c)))
    c = c[c["tipo"].isin(["casa", "departamento", "suite"]) & pd.to_numeric(c["precio_usd"], errors="coerce").notna()]
    c = c.drop_duplicates(subset=["proyecto", "tipologia", "precio_usd", "area_construida_m2"])
    # mismo proyecto en dos agentes (p. ej. Muskuna en alvarezbravo.com.ec y en trivo.com.ec):
    # si un archivo tiene precios por unidad (no "desde"), se descartan las filas "desde" de los otros
    c["_clave"] = c["proyecto"].map(lambda p: norm(p).split(" (")[0].split()[0])
    exactos = c[~c["precio_es_desde"].astype(bool)].groupby("_clave")["_archivo"].agg(set)
    redund = c.apply(lambda r: r["precio_es_desde"] and r["_clave"] in exactos
                     and r["_archivo"] not in exactos[r["_clave"]], axis=1)
    c = c[~redund.astype(bool)]
    pasos.append(("constructoras: residenciales con precio, sin duplicados ni filas 'desde' redundantes", len(c)))
    dominio = c["url_fuente"].map(lambda u: urlparse(str(u)).netloc.removeprefix("www."))
    estado = c["estado_obra"].map({"entrega_inmediata": "nuevo", "en_planos": "en_planos",
                                   "en_construccion": "en_planos"})
    amen = c["amenidades"].map(lambda a: norm(" | ".join(a)) if isinstance(a, list) else "")
    out = pd.DataFrame({
        "id": "constructora_" + (dominio + "_" + c["proyecto"].map(norm) + "_" +
                                 c["tipologia"].fillna("").map(norm)).str.replace(r"[^a-z0-9_.]+", "-", regex=True),
        "fuente": dominio,
        "url": c["url_fuente"],
        "fecha_publicacion": np.nan,
        "tipo": c["tipo"].replace({"suite": "departamento"}),
        "precio": pd.to_numeric(c["precio_usd"], errors="coerce"),
        "area_construida_m2": pd.to_numeric(c["area_construida_m2"], errors="coerce"),
        "habitaciones": pd.to_numeric(c["habitaciones"], errors="coerce"),
        "banos": pd.to_numeric(c["banos"], errors="coerce"),
        "canton": c["canton"].fillna("Quito"),
        # "Viña Alta (Tumbaco)" -> "Viña Alta"; "Cumbayá-Puembo" -> "Cumbayá"; el texto completo se usa para la zona
        "sector": c["sector"].map(lambda x: re.split(r"\s*[(\-–]", str(x))[0].strip() if isinstance(x, str) else np.nan),
        "_sector_txt": c["sector"],
        "latitud": pd.to_numeric(c.get("latitud"), errors="coerce"),
        "longitud": pd.to_numeric(c.get("longitud"), errors="coerce"),
        "es_desarrollo": 1,
        "precio_es_desde": c["precio_es_desde"].astype(bool).astype(int),
        "agencia": c["constructora"],
        "titulo": c["proyecto"] + " – " + c["tipologia"].fillna(""),
        "descripcion": c["notas"],
        "area_terreno_m2": pd.to_numeric(c["area_terreno_m2"], errors="coerce"),
        "parqueaderos": pd.to_numeric(c["parqueaderos"], errors="coerce"),
        "antiguedad_anios": 0.0,
        "alicuota": np.nan,
        "amoblado": np.nan,
        "estado_fuente": estado,
    })
    out.index = "c" + pd.RangeIndex(len(out)).astype(str)
    return pd.concat([out, flags_amenidades(amen.set_axis(out.index))], axis=1)

# ---------------------------------------------------------------- pipeline
def main():
    pasos = []
    partes = [cargar_icasas(pasos), cargar_arriendayvende(pasos), cargar_remax(pasos), cargar_constructoras(pasos)]
    out = pd.concat(partes)
    out["fecha_scraping"] = FECHA_SCRAPING
    out["precio_es_desde"] = out["precio_es_desde"].fillna(0).astype(int) if "precio_es_desde" in out else 0
    pasos.append(("total combinado (todas las fuentes)", len(out)))

    # campos extraídos con regex del título + descripción: SOLO rellenan lo que la fuente no trae
    texto = (out["titulo"].fillna("") + " . " + out["descripcion"].fillna(""))
    ext = pd.DataFrame(texto.apply(extraer_texto).tolist(), index=out.index)
    for c in ["area_terreno_m2", "parqueaderos", "antiguedad_anios", "alicuota"]:
        out[c] = out[c].fillna(ext[c])
    ext["antiguedad_anios"] = ext["antiguedad_anios"].fillna(ANIO_REFERENCIA - ext["anio_construccion"])
    out["antiguedad_anios"] = out["antiguedad_anios"].fillna(ext["antiguedad_anios"])
    out["piso"] = ext["piso"]
    out["estado"] = out["estado_fuente"].fillna(ext["estado"]) if "estado_fuente" in out else ext["estado"]
    out.loc[out["antiguedad_anios"] == 0, "estado"] = out["estado"].fillna("nuevo")

    # sanity de los campos (si no es plausible -> NaN, nunca se imputa)
    out.loc[~out["area_terreno_m2"].between(20, 100_000), "area_terreno_m2"] = np.nan
    out.loc[~out["parqueaderos"].between(0, 10), "parqueaderos"] = np.nan
    out.loc[~out["alicuota"].between(5, 2_000), "alicuota"] = np.nan
    out.loc[~out["piso"].between(0, 40) | (out["tipo"] == "casa"), "piso"] = np.nan
    out.loc[~out["antiguedad_anios"].between(0, 80), "antiguedad_anios"] = np.nan
    fuera = ~(out["latitud"].between(-0.60, 0.20) & out["longitud"].between(-78.80, -78.20))
    out.loc[fuera, ["latitud", "longitud"]] = np.nan

    # proyectos de constructoras: coordenadas tomadas del mapa de cada página de proyecto y correcciones de
    # sector, revisadas a mano (data/coordenadas_proyectos.csv; ver data/README.md). Se cruza por url + sector
    # porque una misma url puede listar varios proyectos (corporacionvyasa.com).
    out["coord_origen"] = np.where(out["latitud"].notna(), "anuncio", None)
    cp = pd.read_csv(ROOT / "data" / "coordenadas_proyectos.csv", keep_default_na=False)
    sector_n = out["sector"].map(lambda x: norm(x) if isinstance(x, str) else "")
    for _, r in cp.iterrows():
        m = (out["url"] == r["url"]) & (sector_n == norm(r["sector"]))
        sin_coord = m & out["latitud"].isna()
        out.loc[sin_coord, "latitud"] = float(r["latitud"])
        out.loc[sin_coord, "longitud"] = float(r["longitud"])
        out.loc[sin_coord, "coord_origen"] = r["metodo"]
        if r["sector_corregido"]:
            out.loc[m, "sector"] = r["sector_corregido"]
            if "_sector_txt" in out:
                out.loc[m, "_sector_txt"] = r["sector_corregido"]
    pasos.append(("constructoras: filas con coordenadas del mapa del proyecto",
                  int(out["coord_origen"].isin(cp["metodo"].unique()).sum())))

    # variantes de nombre que la normalización no une (espacios distintos)
    ALIAS_SECTOR = {"bellavista de la vina": "Bella Vista de la Viña"}
    out["sector"] = out["sector"].map(lambda x: ALIAS_SECTOR.get(norm(x), x) if isinstance(x, str) else x)

    # unificar la grafía del sector entre fuentes ("Cumbaya"/"Cumbayá", "Sur De Quito"/"Sur de Quito"):
    # se usa la variante con tilde más frecuente para cada nombre normalizado
    clave_s = out["sector"].map(lambda x: norm(x) if isinstance(x, str) else np.nan)
    variantes = out.assign(_k=clave_s).dropna(subset=["_k"]).groupby("_k")["sector"].agg(
        lambda v: max(v.value_counts().items(), key=lambda kv: (kv[0] != norm(kv[0]), kv[1]))[0])
    out["sector"] = clave_s.map(variantes)

    # sector faltante (RE/MAX no lo trae): el del anuncio con sector más cercano a < 1,5 km
    out["sector_inferido"] = 0
    con = out[out["sector"].notna() & out["latitud"].notna()]
    falta = out["sector"].isna() & out["latitud"].notna()
    if falta.any() and len(con):
        A = con[["latitud", "longitud"]].to_numpy()
        for i, (la, lo) in out.loc[falta, ["latitud", "longitud"]].iterrows():
            d2 = (A[:, 0] - la) ** 2 + ((A[:, 1] - lo) * np.cos(np.radians(la))) ** 2
            j = d2.argmin()
            if d2[j] ** 0.5 * 111 < 1.5:  # grados -> km
                out.at[i, "sector"] = con["sector"].iat[j]
                out.at[i, "sector_inferido"] = 1

    ruminahui = out["sector"].map(lambda x: isinstance(x, str) and norm(x) in
                                  ("sangolqui", "san rafael", "capelo", "san pedro de taboada", "cotogchoa"))
    out.loc[ruminahui, "canton"] = "Rumiñahui"

    # sector -> zona: 1) nombre conocido  2) Rumiñahui -> Los Chillos  3) coordenadas  4) quito_urbano
    p = out["sector"].fillna("").map(norm)
    out["zona"] = p.map(PARR2ZONA)
    out.loc[out["canton"] == "Rumiñahui", "zona"] = "valle_los_chillos"
    # 1b) nombre de parroquia contenido en el texto del sector ("Bella Vista de la Viña (Tumbaco)")
    txt = (out["_sector_txt"].fillna(out["sector"]) if "_sector_txt" in out else out["sector"]).fillna("").map(norm)
    claves = sorted((k for k in PARR2ZONA if k != "quito"), key=len, reverse=True)
    sub = txt.map(lambda t: next((PARR2ZONA[k] for k in claves if re.search(rf"\b{re.escape(k)}\b", t)), np.nan))
    out["zona"] = out["zona"].fillna(sub)
    lat, lon = out["latitud"], out["longitud"]
    sin = out["zona"].isna()
    out.loc[sin & ((lat > -0.08) | ((lon > -78.44) & (lat > -0.14))), "zona"] = "norte_pomasqui_calderon"
    sin = out["zona"].isna()
    out.loc[sin & (lon > -78.455) & lat.between(-0.255, -0.14), "zona"] = "valle_cumbaya_tumbaco"
    out.loc[sin & (lon > -78.495) & (lat < -0.255), "zona"] = "valle_los_chillos"
    out.loc[out["zona"].isna() & ((p != "") | lat.notna()), "zona"] = "quito_urbano"
    # cada sector toma su zona mayoritaria (corrige anuncios sueltos con coordenadas erróneas)
    moda = out.dropna(subset=["sector"]).groupby("sector")["zona"].agg(lambda z: z.mode().iat[0])
    out["zona"] = out["sector"].map(moda).fillna(out["zona"])
    # el cantón manda sobre la moda del sector (p. ej. "Rumipamba" existe en Quito y en Rumiñahui)
    out.loc[out["canton"] == "Rumiñahui", "zona"] = "valle_los_chillos"
    out["es_valle"] = out["zona"].str.startswith("valle").astype(float).where(out["zona"].notna())

    # ---- filtros de calidad (documentados) ----
    out = out[out["precio"].notna() & (out["precio"] > 0)]
    pasos.append(("precio presente y > 0", len(out)))
    placeholder = out["precio"].isin([1, 11, 111, 1111, 9999, 99999, 999999, 9999999]) | (out["precio"] > 10_000_000)
    out = out[~placeholder]
    pasos.append(("sin precios placeholder (1, 999999, > $10M)", len(out)))
    out = out[out["precio"] >= 15_000]
    pasos.append(("precio ≥ $15.000 (descarta arriendos colados)", len(out)))
    out = out[out["area_construida_m2"].between(20, 2000)]
    pasos.append(("área construida entre 20 y 2.000 m²", len(out)))

    # duplicados: mismo tipo + precio + área (redondeada) + habitaciones + baños.
    # No se usa el sector porque cada portal nombra los barrios distinto (duplicados entre fuentes).
    # Prioridad: remax (más campos estructurados) > icasas > arriendayvende (más antiguo).
    out["_area_r"] = out["area_construida_m2"].round(0)
    clave = ["tipo", "precio", "_area_r", "habitaciones", "banos"]
    out = out.sort_values("fuente", key=lambda s: s.map({"remax.com.ec": 0, "icasas.ec": 1, "arriendayvende.com": 2}).fillna(3))
    dup = out.duplicated(subset=clave, keep="first")
    entre = dup & out.assign(_f=out["fuente"]).groupby(clave, dropna=False)["_f"].transform("nunique").gt(1)
    out = out[~dup].drop(columns="_area_r")
    pasos.append((f"sin duplicados (tipo+precio+área+hab+baños); {int(entre.sum())} eran entre fuentes", len(out)))

    # outliers de precio/m² se MARCAN, no se borran (IQR en log por tipo)
    out["precio_m2"] = (out["precio"] / out["area_construida_m2"]).round(2)
    lp = np.log(out["precio_m2"])
    q1 = lp.groupby(out["tipo"]).transform(lambda s: s.quantile(.25))
    q3 = lp.groupby(out["tipo"]).transform(lambda s: s.quantile(.75))
    out["outlier_precio_m2"] = ((lp < q1 - 1.5 * (q3 - q1)) | (lp > q3 + 1.5 * (q3 - q1))).astype(int)

    cols = ["id", "fuente", "url", "fecha_publicacion", "fecha_scraping", "tipo", "precio",
            "area_construida_m2", "habitaciones", "banos", "canton", "sector", "sector_inferido", "zona", "es_valle",
            "latitud", "longitud", "coord_origen", "area_terreno_m2", "parqueaderos", "antiguedad_anios", "piso",
            "alicuota", "estado", "es_desarrollo", "precio_es_desde", "amoblado"] + list(AMENIDADES) + \
           ["precio_m2", "outlier_precio_m2", "agencia", "titulo", "descripcion"]
    out = out[cols].sort_values("id").reset_index(drop=True)
    OUT.parent.mkdir(exist_ok=True)
    out.to_csv(OUT, index=False, encoding="utf-8")

    print("\n## Pasos de limpieza")
    for k, v in pasos:
        print(f"| {k} | {v} |")
    print(f"\nFilas finales: {len(out)}  ->  {OUT}")
    print("\n## Filas por zona / tipo\n", pd.crosstab(out["zona"].fillna("NA"), out["tipo"], margins=True))
    print("\n## Filas por fuente / tipo\n", pd.crosstab(out["fuente"], out["tipo"], margins=True))
    print("\n## % faltantes")
    for c in cols:
        print(f"| `{c}` | {out[c].dtype} | {100 * out[c].isna().mean():.1f}% |")
    print("\nSectores (top 40):", out["sector"].value_counts(dropna=False).head(40).to_dict())


if __name__ == "__main__":
    main()
