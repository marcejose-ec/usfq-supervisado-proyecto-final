# Datos: precios de viviendas en venta en Quito y los valles

`casas_quito.csv` — **7.151 anuncios** de casas y departamentos **en venta** en el Distrito Metropolitano de Quito
(urbano y valles) y el cantón Rumiñahui. Una fila por anuncio, UTF-8, separado por comas, precios en USD.

- **Fecha de recolección:** 11–12 de noviembre de 2026
- **Objetivo (target):** `precio` (precio de venta publicado, USD)
- **Tamaño:** ~11 MB (la mayor parte es el texto de `descripcion`)

## Fuentes

| `fuente` | Filas | Método | Qué aporta |
|---|---|---|---|
| `icasas.ec` | 4.261 | Scraping HTML de páginas de resultados y de detalle (`scraper/scrape_icasas.py`) | Mayor volumen; coordenadas, barrio, amenidades |
| `remax.com.ec` | 1.264 | API JSON pública que usa el propio sitio, `api-ec.redremax.com` (`scraper/scrape_remax.py`) | Campos estructurados: parqueaderos, año de construcción, alícuota, estado ("a estrenar") |
| `arriendayvende.com` | 1.238 | API REST pública de WordPress, `/wp-json/wp/v2/properties` (`scraper/scrape_arriendayvende.py`) | Área de terreno, parqueaderos, antigüedad, fecha de publicación |
| `trivo.com.ec` | 380 | Recopilado por agentes de IA (ver abajo) | Precios por unidad de 20 proyectos nuevos |
| sitios de constructoras* | 8 | Recopilado por agentes de IA (ver abajo) | Proyectos nuevos en los sitios de las propias constructoras |

\* `casasventacumbaya.zenz.ec` (3), `corporacionvyasa.com` (2), `alvarezbravo.com.ec`, `barrazueta.com`, `ryp.com.ec` (1 c/u).

Cada fila tiene `fuente` (sitio de origen) y `url` (página exacta del anuncio) para trazabilidad.

### Datos de constructoras (recopilados por agentes)

Los sitios de constructoras no tienen una estructura común, así que tres agentes de IA (Claude Haiku) visitaron las
páginas y transcribieron una fila por tipología con precio. Reglas que siguieron: no inventar valores (lo que falta queda
vacío), no evadir bloqueos y no guardar datos personales. Además, un precio "desde $X" se asigna **siempre a la unidad
más pequeña** del proyecto (`precio_es_desde = 1`). La salida y el registro de cada sitio visitado están en
`raw/constructoras/` (agente A: constructoras indicadas por el equipo; B: proyectos de Trivo; C: búsqueda de otras
constructoras).

**Verificación:** los 399 precios y áreas de Trivo se contrastaron automáticamente con el HTML de cada página y
coincidieron todos. Las filas de los agentes A y C se revisaron a mano contra las páginas, con dos correcciones anotadas
en `notas`. Se descartaron proyectos que solo publican cuotas mensuales o piden "cotizar".

### Fuentes evaluadas y descartadas

| Sitio | Motivo |
|---|---|
| plusvalia.com, mutualistapichincha.com | Protegidos por Cloudflare (403); no se intentó evadir la protección |
| mercadolibre.com.ec | Su robots.txt prohíbe el acceso de agentes de IA; la alternativa legítima es su API oficial con token |
| properati.com.ec | Responde 401 a todo, incluido robots.txt |
| olx.com.ec | El sitio ya no existe en Ecuador |
| bienesinmuebles.pichincha.com | Solo ~45 inmuebles de todo tipo |
| Construecuador | Solo publica cuotas mensuales, no precios de venta |

## Limpieza (filas antes → después)

Todos los pasos están en `scraper/build_dataset.py`, que imprime estos conteos.

| Paso | Filas |
|---|---|
| icasas.ec: anuncios únicos (por id) | 4.615 |
| icasas.ec: sin rangos de área/habitaciones (proyectos con varias tipologías) | 4.612 |
| arriendayvende.com: todas las propiedades del sitio | 2.928 |
| arriendayvende.com: venta de casas/departamentos | 1.602 |
| arriendayvende.com: ciudad = Quito (incluye valles) | 1.387 |
| remax.com.ec: venta de casas/departamentos dentro del rectángulo Quito + valles | 1.499 |
| remax.com.ec: rectángulo estricto (excluye Machachi, Mindo, Cayambe) | 1.495 |
| constructoras: tipologías recopiladas | 422 |
| constructoras: residenciales con precio, sin duplicados ni filas "desde" redundantes | 401 |
| **Total combinado** | **7.893** |
| precio presente y > 0 | 7.891 |
| sin precios placeholder (1, 999999, > $10M) | 7.888 |
| precio ≥ $15.000 (descarta arriendos que se colaron) | 7.679 |
| área construida entre 20 y 2.000 m² | 7.459 |
| sin duplicados (mismo tipo + precio + área + habitaciones + baños; 36 eran entre fuentes) | **7.151** |

Al deduplicar se conserva primero RE/MAX (más campos estructurados), luego icasas y al final arriendayvende (anuncios
más antiguos).

**Lo que NO se hace:** no se imputan faltantes (quedan como NaN; la imputación va en el pipeline del notebook) y no se
borran los atípicos de precio/m², que solo se **marcan** en `outlier_precio_m2` (67 filas, IQR en escala log por tipo).

## Diccionario de columnas

| Columna | Tipo | Unidad / valores | % faltante | Notas |
|---|---|---|---|---|
| `id` | str | `<fuente>_<id>` | 0 | Único |
| `fuente` | str | dominio | 0 | Sitio de origen |
| `url` | str | | 0 | Página del anuncio |
| `fecha_publicacion` | fecha | AAAA-MM-DD | 82,7 | Solo arriendayvende (casi todo 2021–2022) |
| `fecha_scraping` | fecha | AAAA-MM-DD | 0 | |
| `tipo` | cat | `casa`, `departamento` | 0 | Las suites cuentan como departamento |
| **`precio`** | float | USD | 0 | **Objetivo** |
| `area_construida_m2` | float | m² | 0 | |
| `habitaciones` | float | | 1,7 | |
| `banos` | float | | 6,9 | Medio baño = 0,5 (RE/MAX) |
| `canton` | cat | `Quito`, `Rumiñahui` | 0 | |
| `sector` | cat | barrio o parroquia | 0,1 | Grafía unificada entre fuentes |
| `sector_inferido` | 0/1 | | 0 | 1 = RE/MAX no trae sector; se tomó el del anuncio más cercano (< 1,5 km) |
| `zona` | cat | `quito_urbano`, `valle_cumbaya_tumbaco`, `valle_los_chillos`, `norte_pomasqui_calderon`, `rural_otro` | 0 | Por nombre del sector, luego por coordenadas. `quito_urbano` = la ciudad de Quito (parroquias urbanas); los valles y las parroquias rurales del DMQ son zonas aparte |
| `es_valle` | 0/1 | | 0 | Cumbayá–Tumbaco o Los Chillos |
| `latitud`, `longitud` | float | grados WGS84 | 0,3 | **Ver advertencia abajo** |
| `coord_origen` | cat | `anuncio`, `google_maps_embed`, `google_maps_link`, `revision_manual` | 0,3 | De dónde viene la coordenada (ver sección de coordenadas de proyectos) |
| `area_terreno_m2` | float | m² | 72,1 (48,8 en casas) | Solo casas; en departamentos no aplica |
| `parqueaderos` | float | | 22,2 | |
| `antiguedad_anios` | float | años | 58,1 | 0 = a estrenar |
| `piso` | float | | 78,5 | Solo departamentos; extraído del texto |
| `alicuota` | float | USD/mes | 75,8 | |
| `estado` | cat | `nuevo`, `usado`, `en_planos` | 59,4 | |
| `es_desarrollo` | 0/1 | | 0 | Proyecto nuevo de constructora (389 filas) |
| `precio_es_desde` | 0/1 | | 0 | Precio "desde" asignado a la unidad más pequeña |
| `amoblado` | 0/1 | | 36,8 | |
| `piscina`, `jardin`, `gimnasio`, `ascensor`, `seguridad`, `bbq`, `terraza`, `balcon`, `bodega`, `zona_ninos`, `estacionamiento`, `cocina_equipada`, `calefaccion`, `vista_panoramica`, `patio`, `jacuzzi_sauna`, `acceso_discapacitados` | 0/1 | | 0 | De la lista de características de cada portal |
| `precio_m2` | float | USD/m² | 0 | `precio / area_construida_m2`. **No usar como predictor (fuga del objetivo)** |
| `outlier_precio_m2` | 0/1 | | 0 | Marca, no filtro |
| `agencia` | str | | 35,9 | Inmobiliaria, oficina o constructora (nunca nombres de personas) |
| `titulo`, `descripcion` | str | | 0 | Texto del anuncio |

**Campos extraídos del texto.** `area_terreno_m2`, `parqueaderos`, `antiguedad_anios`, `alicuota`, `piso` y `estado`
vienen estructurados en RE/MAX y arriendayvende. En el resto de filas se extraen del título y la descripción con
expresiones regulares, solo cuando el texto lo dice explícitamente (p. ej. "300 m2 de terreno", "2 parqueaderos"). Los
valores implausibles se descartan.

## Advertencias

- **Coordenadas aproximadas.** RE/MAX usa pines puestos por los agentes. En icasas (~22 %) y arriendayvende (~29 %)
  muchos anuncios comparten el mismo punto: es el centroide geocodificado del barrio, no la casa (p. ej., 62 anuncios
  de Tumbaco de 18 inmobiliarias distintas en un mismo punto). Sirven a escala de barrio, no para ubicar la vivienda.
  Los proyectos de constructoras se ubican con el mapa de su página (ver abajo): ubicación del proyecto, no de la unidad.
- **Precios pedidos, no de cierre.** Son precios de publicación.
- **Antigüedad de los anuncios.** Los de arriendayvende son mayormente de 2021–2022; icasas, RE/MAX y constructoras
  están vigentes en nov. 2026. `fuente` y `fecha_publicacion` permiten controlarlo.
- **Proyectos nuevos.** Su precio/m² mediano es ~2× el de los anuncios (casa $1.433 vs $728; departamento $1.979 vs
  $955), en parte porque se concentran en Cumbayá y La Carolina. Conviene incluir `es_desarrollo` como variable.

## Coordenadas de proyectos nuevos (`coordenadas_proyectos.csv`)

De los 401 anuncios sin coordenadas, 382 son proyectos de constructoras (Trivo y sitios propios). Para ubicarlos se
tomaron las coordenadas **del mapa de Google Maps que publica cada página de proyecto** (12 nov. 2026). Después, el
equipo revisó a mano cada punto. `scraper/build_dataset.py` aplica el archivo cruzando por `url` + `sector`, y la
columna `coord_origen` del dataset indica de dónde viene cada coordenada:

| `coord_origen` | Proyectos | Filas | Origen |
|---|---|---|---|
| `anuncio` | – | 6.749 | Coordenadas del propio anuncio (portal) |
| `google_maps_embed` | 19 | 353 | Pin del mapa de Google Maps embebido en la página de cada proyecto de Trivo [6] |
| `google_maps_link` | 1 | 1 | Enlace "Encuéntranos en Google Maps" de la página del proyecto Quiari (Álvarez Bravo) [6] |
| `revision_manual` | 2 | 28 | Corregidas en la revisión manual: Taya (27 filas; el pin de la página caía en el oeste de Quito, a ~17 km de Puembo, y se usó la ubicación del folleto del proyecto [8]) y Yanazarapata (1 fila; la página no tiene mapa; ubicación tomada de Google Maps [9]) |
| vacío | – | 20 | Sin coordenadas: 17 de arriendayvende, 1 de barrazueta.com, 1 de corporacionvyasa.com (Bellavista de la Viña), 1 de ryp.com.ec. En el notebook reciben el centroide de su sector |

**Correcciones de sector** (de la misma revisión, columna `sector_corregido`):
- Zadeh y Maigua (Trivo): `Campo Alegre` → `Monteserrin`. Campo Alegre es una urbanización privada dentro de
  Monteserrín.
- Quartier (Trivo): `Cumbayá` → `La Morita`. El proyecto no está en Cumbayá; Trivo lo describe "entre Cumbayá y
  Puembo", y su pin queda a ~70 m del proyecto Xoul (La Morita).
- `Bellavista de la Viña` se unifica con `Bella Vista de la Viña` (misma urbanización, grafía distinta).

**Correcciones de zona** encontradas al revisar:
- `Rumipamba` (31 filas del cantón Quito) estaba en `valle_los_chillos`. Rumipamba también es parroquia urbana de
  Quito (centro-norte), así que ahora es `quito_urbano`. La del cantón Rumiñahui sigue en `valle_los_chillos`.
- `Monteserrin`, `Lomas de Monteserrin` y `Campo Alegre` se fijan explícitamente como `quito_urbano`. Antes su zona
  dependía de un corte por longitud que pasa justo por ese barrio.

## Términos de uso

- Se respetó el `robots.txt` de cada sitio (las rutas usadas no están prohibidas), con 1 s de pausa entre peticiones y
  un User-Agent que identifica el proyecto académico.
- arriendayvende.com: sus términos y condiciones no tienen cláusulas sobre acceso automatizado.
- icasas.ec y remax.com.ec: no se revisaron sus términos en detalle. **Revisarlos antes de redistribuir el dataset**
  fuera del curso.
- No se guardan datos personales: ni nombres, teléfonos o correos de agentes y vendedores, ni fotos.
- Los datos se usan con fines académicos (proyecto de curso, USFQ). Los anuncios son propiedad de sus portales y
  anunciantes.

## Cómo reproducirlo

```bash
pip install -r scraper/requirements.txt
python scraper/scrape_icasas.py           # ~2,5 h; reanudable si se interrumpe
python scraper/scrape_arriendayvende.py   # ~1 min
python scraper/scrape_remax.py            # ~1,5 h; reanudable
python scraper/build_dataset.py           # segundos -> data/casas_quito.csv
```

Los crudos se guardan en `data/raw/` y no se suben a git, salvo `raw/constructoras/`, que no puede regenerarse con un
script. Los anuncios cambian con el tiempo, así que una nueva ejecución dará datos distintos.

## Referencias (IEEE)

[1] icasas.ec, "Casas y departamentos en venta en Quito," 2026. [En línea]. Disponible:
https://www.icasas.ec/venta/casas/quito. Accedido: 11 nov. 2026.

[2] RE/MAX Ecuador, "Comprar propiedades," 2026. [En línea]. Disponible: https://www.remax.com.ec/comprar-propiedades.
Accedido: 11 nov. 2026.

[3] Arrienda y Vende, "Casas de venta en Quito," 2026. [En línea]. Disponible:
https://arriendayvende.com/label/casa-de-venta-en-quito/. Accedido: 11 nov. 2026.

[4] Trivo, "Casas en venta en Quito," 2026. [En línea]. Disponible: https://trivo.com.ec/casas-en-venta-en-quito/.
Accedido: 11 nov. 2026.

[5] D. M. Pinzón Pineda, "Vivienda en Quito: precio por m², arriendo, habitaciones y rentabilidad (octubre 2026),"
Aptología, 2026. [En línea]. Disponible:
https://github.com/elbroker/aptologia-datos/tree/main/estudios/vivienda-quito-por-sector-2026. Licencia CC BY 4.0.

[6] Google, "Google Maps," 2026. [En línea]. Disponible: https://www.google.com/maps. Coordenadas de los mapas
embebidos en las páginas de los proyectos de Trivo (https://trivo.com.ec/propiedades/) y Álvarez Bravo
(https://alvarezbravo.com.ec/proyectos/quiari/). Accedido: 12 nov. 2026.

[7] OpenStreetMap contributors, "Nominatim," 2026. [En línea]. Disponible: https://nominatim.openstreetmap.org. Datos
bajo licencia ODbL. Usado solo en la primera versión de la coordenada de Yanazarapata, reemplazada en la revisión
manual. Accedido: 12 nov. 2026.

[8] Trivo, "Taya – Folleto del proyecto," 2026. [En línea]. Disponible:
https://trivo.com.ec/wp-content/uploads/2026/09/TayaBrochure.pdf. Accedido: 12 nov. 2026.

[9] Google, "Lotización Yanazarapata, 170157 Quito," Google Maps, 2026. [En línea]. Disponible:
https://www.google.com/maps/place/Lotizaci%C3%B3n+Yanazarapata,+170157+Quito/@-0.2089705,-78.4558207,17z.
Accedido: 12 nov. 2026.
