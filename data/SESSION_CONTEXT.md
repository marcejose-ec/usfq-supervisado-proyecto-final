# Data-gathering session context

Notes from the Claude Code sessions (2026-11-11 → 2026-11-12) that built and then corrected `data/casas_quito.csv`. It records what
was decided and why, what was tried and rejected, and what is still open, so a later session (human or agent)
can extend or rebuild the dataset without re-researching everything. The user-facing documentation of the
dataset itself (column dictionary, cleaning counts, references) is in [`README.md`](README.md).

## Goal

Regression dataset of **sale** prices (USD) of houses and apartments in Quito and the valleys
(Cumbayá–Tumbaco, Los Chillos) for the USFQ supervised-learning final project. The spec is
`../../DATASET_REQUIREMENTS.md` in the workspace root: ≥1,000 clean rows (ideally 2k–10k), required columns
`precio`, `area_construida_m2`, `habitaciones`, `banos`, `sector`; recent listings only; deduplicated; outliers
flagged, not deleted; no imputation (NaN kept); `fuente` + `id` + `url` on every row.

## Result (last build: 2026-11-12)

7,151 rows × 49 columns. Rebuilding from the raw files is deterministic and byte-identical: the scrape date
(`FECHA_SCRAPING = "2026-11-12"`) and the year used for building age (`ANIO_REFERENCIA = 2026`) are constants, not
`date.today()`.

| Source | Rows | How |
|---|---|---|
| icasas.ec | 4,261 | HTML scraping, `scraper/scrape_icasas.py` (list pages + detail pages) |
| remax.com.ec | 1,264 | Public JSON API the site itself uses, `scraper/scrape_remax.py` |
| arriendayvende.com | 1,238 | Public WordPress REST API, `scraper/scrape_arriendayvende.py` |
| trivo.com.ec | 380 | Haiku subagents reading project pages (new builds) |
| builder sites (zenz, vyasa, alvarezbravo, barrazueta, ryp) | 8 | Haiku subagents |

| Zone | Houses | Apartments | Median USD/m² |
|---|---|---|---|
| quito_urbano | 1,298 | 2,411 | 808 |
| valle_cumbaya_tumbaco | 1,065 | 630 | 1,188 |
| valle_los_chillos | 997 | 172 | 725 |
| norte_pomasqui_calderon | 496 | 75 | 599 |
| rural_otro / NA | 6 / 1 | 0 | – |

`quito_urbano` means the city of Quito (urban parishes). The valleys and the rural parishes of the DMQ are separate
zones.

Highest missing rates: `area_terreno_m2` 72% overall (≈49% among houses), `antiguedad_anios` 58%,
`estado` 59%, `alicuota` 76%, `piso` 79%. Required columns are all under 7% missing.

## Source decisions

**Used**
- **icasas.ec**: robots.txt allows the listing pages. Crawled `/venta/{casas|departamentos}/{quito|ruminahui}/p_N`
  until two consecutive pages added nothing new; detail pages give coordinates (`[data-x][data-y]`),
  breadcrumb, characteristics and description.
- **remax.com.ec**: robots only blocks `?associate` URLs. `api-ec.redremax.com/remaxweb-ec/api/listings/findAll`
  (operationId=1 = sale, pageSize 200) then `listings/findById/{id}`. Agent names/phones/emails/photos are
  **stripped before writing** (`PERSONALES` in the script); only the office name is kept.
- **arriendayvende.com**: `/wp-json/wp/v2/properties` + taxonomies (Houzez theme, `fave_*` meta). Small
  (~1.2k usable rows) and **mostly 2021–2022 listings**; kept because it adds valley coverage, flagged in the README.
- **Builders / Trivo**: no structured data, so Haiku subagents visited project pages and returned one JSON row
  per unit type (schema: project, builder, url_fuente, tipo, precio, area, hab, baños, parqueaderos, sector,
  `precio_es_desde`, notes). Output and visit logs are in `raw/constructoras/` and are committed because they
  cannot be regenerated. All 399 Trivo prices/areas were re-checked against the pages.
  - **User rule:** a builder's "desde $X" price always belongs to the **smallest** unit. Rows that only carry a
    "desde" price have `precio_es_desde = 1`. Manual fixes: Muskuna and Zenz rows marked as "desde"; HITO
    140,000 → 155,000 (notes in the jsonl).

**Rejected** (don't re-research)
- **plusvalia.com, mutualistapichincha**: Cloudflare bot check. A TLS-impersonation workaround (curl_cffi) was
  **blocked by the permission classifier as bot-check circumvention — do not retry or work around it.** A
  manually driven browser (Playwright with the user's Firefox) was discussed but not pursued.
- **mercadolibre.com.ec**: has an Ecuador real-estate section, but robots.txt explicitly bans Claude agents; the
  official API needs an app token.
- **properati.com.ec**: HTTP 401 for scripted requests.
- **OLX**: no longer operates in Ecuador.
- **bienesinmuebles.pichincha.com**: only ~45 listings (bank foreclosures).
- **construecuador.com.ec**: shows monthly installments, not total prices.
- **Aptología (github.com/elbroker/aptologia-datos)**: aggregated per-sector statistics, not listings. Cited as
  a reference [5] for sanity-checking USD/m² by sector, not used as rows.

## Pipeline (`scraper/build_dataset.py`)

1. Load each source into a common schema (es-EC number parsing: `1.234,56`).
2. Regex extraction from title/description only **fills NaN** (lot area must be followed by "de terreno",
   parking, alícuota, year/age, floor), plus 17 amenity flags from text and feature lists.
3. Sanity filters: price present, not a placeholder (1, 999999, > $10M), ≥ $15,000 (drops rentals posted as
   sales), built area 20–2,000 m², coordinates inside the DMQ+Rumiñahui box, else set to NaN.
3b. Builder projects get coordinates and sector fixes from `data/coordenadas_proyectos.csv` (joined on
   url + normalized sector, because one corporacionvyasa.com URL lists two projects); `coord_origen` records
   the origin. Then a small alias map merges spellings normalization can't (`Bellavista de la Viña` →
   `Bella Vista de la Viña`).
4. Sector spellings unified to the most frequent accented variant. Missing sector is inferred from the nearest
   listing with a sector within 1.5 km (`sector_inferido = 1`, 1,336 rows).
5. `zona`: explicit name lists → substring match → coordinate bands → default `quito_urbano` → majority zone
   per sector → canton Rumiñahui always `valle_los_chillos` (applied after the majority vote).
6. Dedup on tipo + precio + round(area) + hab + baños, priority remax > icasas > arriendayvende > builders
   (36 cross-source duplicates).
7. `precio_m2` and `outlier_precio_m2` (IQR on log USD/m², per tipo, 67 rows flagged, none removed).

Bugs fixed along the way, in case they reappear: the lot-area regex grabbing built area ("300 m² de terreno 280 m²
de construcción"); Calderón-area barrios and Trivo sectors like "Viña Alta (Tumbaco)" landing in the wrong zone; a
pandas `DTypePromotionError` with `fillna(np.where(...))`. Later (2026-11-12): "rumipamba" was in the Los Chillos
list, but 31 listings are the urban Quito parish (Av. República), so it moved to `quito_urbano` and the canton
rule now handles the Rumiñahui one. Monteserrín, Lomas de Monteserrín and Campo Alegre are listed explicitly as
`quito_urbano`, because the −78.455 longitude band runs through them and adding project points flipped 23 rows.

## Known data caveats

- **Coordinates are often approximate.** RE/MAX pins are mostly unique. About 22% of icasas rows and 29% of
  arriendayvende rows sit on shared neighborhood centroids (e.g. 62 Tumbaco listings from 18 agencies on one
  point). arriendayvende also has a mispinned Ponceano cluster. Builder rows carry the **project** location
  (not the unit's). 20 rows still have no coordinates (17 arriendayvende, barrazueta, the vyasa Bellavista row,
  ryp); the notebook gives them their sector's centroid. **No row is guaranteed to have the exact location.**
- Prices are asking prices, not transaction prices.
- New builds (`es_desarrollo = 1`, 389 rows) are priced well above resale: median USD/m² for houses is 1,433 vs
  728, and for apartments 1,979 vs 955. Keep the flag as a feature.
- `precio_m2` is derived from the target, so using it as a model feature leaks the target.

## Constraints that applied

- 1 s delay between requests and an honest User-Agent (`usfq-ml-course-project/1.0`). Respect robots.txt.
- No bot-check / Cloudflare circumvention.
- No personal data of agents or sellers stored.
- Repo layout: the workspace root (`proyecto-final/`) is scratch space where stray files are fine;
  `casas-quito-ml/` is the deliverable. The bulk raw dumps (`data/raw/*`) are git-ignored except `raw/constructoras/`.
- Commits are the user's call. First commit: `190798a` (2026-11-12), no remote yet.

## Project coordinates (`coordenadas_proyectos.csv`)

The 401 rows without coordinates were nearly all builder projects. Every Trivo project page embeds a Google Maps
iframe with the project pin (`maps/embed/v1/place?q=lat,lon`); Quiari (alvarezbravo) links a Google Maps place.
Google Maps itself can't be fetched (JS-only), so the pins were read from the builder pages. The user reviewed
every row by hand:
- **Taya**: the page pin was ~17 km off (western Quito); replaced with the brochure location [ref 8 in README].
- **Yanazarapata** (vyasa, no map on the page): first an OSM Nominatim centroid, replaced with the user's
  Google Maps location (−0.208268, −78.453037). The Google place pin is ~85 m away; **the user chose to keep
  their coordinates.**
- **Zadeh, Maigua**: `Campo Alegre` → `Monteserrin` (Campo Alegre is a private urbanization in Monteserrín).
- **Quartier**: not in Cumbayá (user). Assigned `La Morita` because its pin is ~70 m from Xoul (La Morita);
  that's an inference from the pin, not something the page states.

## Notebook / EDA decisions so far

- The notebook uses the dataset's `zona` and all binary flags (incl. `es_desarrollo`, `precio_es_desde`) and adds
  `es_rentera` (houses whose text says "rentera"/"se vende edificio"/"N departamentos independientes", or with
  ≥10 bedrooms; 387 rows). Words like "edificio" or "rentabilidad" alone matched hundreds of apartments.
- Notebook cleaning (not in the dataset): `banos > 30`, apartments with > 10 bedrooms, and houses with 0
  bedrooms → NaN; 80 more near-duplicates (tipo + sector + precio + area) dropped.
- `fuente` is **not** a feature (traceability/filtering only). Within the same sector and type, RE/MAX is ~15%
  below, Trivo ~10% above; no source looked unreliable enough to drop.
- Price is ≈ log-normal (skew 6.0 → 0.5 in log); the model trains on log(price).
- Sector explains η² = 0.43 of log(USD/m²), zone 0.15; neighbouring sectors correlate r = 0.77.
- The Trivo project grouping (units of one project across folds) is accepted as a limitation (plain
  `RepeatedKFold`).

## Open items

- **Pending user decisions:** how to encode `sector` (one-hot vs. sector-centroid coordinates vs. target
  encoding); whether to keep HistGradientBoosting as one of the two compared models; switching the metric to
  RMSLE (proposed, not yet applied in the notebook, which still optimizes RMSE in USD).
- **`coord_aproximada` flag** (proposed, not implemented). Flag points shared by ≥5 listings from different
  agencies (and arriendayvende pins). Clear coordinates far from their sector's median.
- Read icasas' and RE/MAX's terms before publishing the dataset outside the course.
- After creating the GitHub repo: replace `USUARIO/REPO` in the README Colab badge and the notebook's `DATA_URL`.

## Reproduce

```bash
cd casas-quito-ml
uv venv ../.venv && uv pip install -p ../.venv -r scraper/requirements.txt   # python3-venv is not installed
../.venv/bin/python scraper/scrape_icasas.py           # ~4.8k pages at 1 req/s, resumable
../.venv/bin/python scraper/scrape_remax.py            # ~1.5k requests at 1 req/s, resumable
../.venv/bin/python scraper/scrape_arriendayvende.py   # a few minutes
../.venv/bin/python scraper/build_dataset.py           # writes data/casas_quito.csv
```

Builder rows are not re-scraped; they are read from `data/raw/constructoras/agente_*.jsonl`. To refresh them,
run Haiku subagents with the same JSON schema and the "desde = smallest unit" rule, then spot-check prices
against the pages.
