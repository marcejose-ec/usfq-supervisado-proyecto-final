# Agente B: log de extracción (Trivo, Quito)

Fecha de consulta: 2026-11-11. Fetches usados: 22 de ~45 (16 proyectos + 2 listados + 4 proyectos adicionales de los listados).
Bloqueos (403 / Cloudflare / login): ninguno.

## Proyectos de la lista asignada

| Proyecto | URL | Resultado | Filas |
|---|---|---|---|
| Beat | https://trivo.com.ec/propiedades/beat/ | filas (precio propio por unidad; 'desde' coincide con mini estudio) | 77 |
| Bloom | https://trivo.com.ec/propiedades/bloom/ | filas (constructora Bentho) | 24 |
| Denver | https://trivo.com.ec/propiedades/denver/ | filas | 15 |
| Kalani | https://trivo.com.ec/propiedades/kalani/ | filas (casas, suites, deptos) | 36 |
| Lum | https://trivo.com.ec/propiedades/lum/ | filas | 8 |
| Maia | https://trivo.com.ec/propiedades/maia/ | filas (casas, entrega inmediata) | 9 |
| Maigua | https://trivo.com.ec/propiedades/maigua/ | filas (una tipologia: casa 4 dorm.) | 1 |
| Muskuna | https://trivo.com.ec/propiedades/muskuna/ | filas (Puembo, entrega inmediata) | 15 |
| Parkside | https://trivo.com.ec/propiedades/parkside/ | filas | 5 |
| Quartier | https://trivo.com.ec/propiedades/quartier/ | filas solo departamentos y suites; oficinas (15) y locales comerciales (9) excluidos por no ser residenciales | 30 |
| Sendero | https://trivo.com.ec/propiedades/sendero/ | filas (casas, deptos, penthouses) | 28 |
| Tao | https://trivo.com.ec/propiedades/tao/ | filas (incluye estudios mapeados a suite) | 35 |
| Terra Gardens | https://trivo.com.ec/propiedades/terra-gardens/ | 1 fila (12 unidades listadas al mismo precio, deduplicadas) | 1 |
| Xoul | https://trivo.com.ec/propiedades/xoul/ | filas (precios de tarjeta sin mapeo a unidad) | 17 |
| Zadeh | https://trivo.com.ec/propiedades/zadeh/ | filas (constructora Alvarez Bravo Constructores) | 3 |
| Zefra | https://trivo.com.ec/propiedades/zefra/ | filas (oficinas no incluidas) | 6 |

## Proyectos adicionales encontrados en los listados

| Proyecto | URL | Resultado | Filas |
|---|---|---|---|
| Taya (Puembo) | https://trivo.com.ec/propiedades/taya/ | filas | 27 |
| Kanso (Cumbaya) | https://trivo.com.ec/propiedades/kanso/ | filas | 24 |
| Syrah Hills (Cumbaya/Tumbaco) | https://trivo.com.ec/propiedades/syrah-hills/ | filas | 18 |
| Hygge (Santa Monica, Cumbaya) | https://trivo.com.ec/propiedades/hygge/ | filas; 4 locales comerciales excluidos | 20 |

## Listados revisados

| Pagina | Resultado |
|---|---|
| https://trivo.com.ec/suites-en-venta-en-quito/ | 8 proyectos Quito (Tao, Beat, Lum, Quartier, Bloom, Denver, Zefra, Taya); todos ya cubiertos |
| https://trivo.com.ec/departamentos-en-venta-en-cumbaya/ | 8 proyectos Cumbaya (Parkside, Tao, Lum, Quartier, Kanso, Syrah Hills, Sendero, Hygge); todos ya cubiertos |

## Sin fila / fuera de alcance

- Ibis Mila y Las Bromelias (Monteserrin, Quito): aparecen solo como enlaces de "proyectos similares" en la pagina de Maigua, sin enlace de proyecto ni listado; no se buscaron (sin datos de tipologia).
- Ningun proyecto de la lista fue fuera de Quito/Rumiñahui o no residencial en su totalidad.

## Decisiones de codificacion

- Una fila por tarjeta de unidad con precio propio (no se agrupan tipologias con precios distintos). Las tarjetas con precio identico y mismo area se dedupican solo en Terra Gardens (12 unidades, 1 fila). Taya tiene 2 tarjetas duplicadas (filas 19 y 25 de la fuente) registradas como una fila cada una con nota.
- Ningun proyecto tiene solo precio "desde": en todos hay precio propio por unidad, asi que precio_es_desde = false en todas las filas. Los precios "desde" de cabecera se anotan en notas cuando coinciden con una unidad.
- tipo: 'Estudio' y 'Mini estudio' se mapean a "suite" (en la categoria de la fuente son unidades de un dormitorio). Penthouses, duplex y PB con jardin se mapean a "departamento".
- area_construida_m2: se toma el valor "Area" de la ficha tal como aparece. En Beat, Parkside, Quartier y Zefra la fuente no distingue construida vs. total; se anota en notas.
- area_terreno_m2: null en todas las filas. Las cifras de "terraza", "jardin" y "balcon" van en notas, no como terreno.
- banos: null salvo Maigua (4) y Terra Gardens (1.5, segun descripcion de la fuente). Ninguna otra ficha los indica.
- parqueaderos: 0 cuando la fuente dice que se compra aparte. Zadeh indica "mas de 3" y se deja null.
- Inconsistencias de la fuente, anotadas en notas: Maigua (2 vs 4 parqueos; encabezado "desde" vs tarjeta "Precio"; entrega 1er semestre 2026 ya vencida); Terra Gardens (titulo 3 dorm vs fichas 2 dorm; se registra 3); Bloom fila 14 (titulo 3 dorm vs campo 2 dorm; se registra 3); Xoul (una tarjeta "2 dorm" con 94.47 m2 y 114,500 USD, registrada como 3 dorm).
- Xoul: los precios son de tarjeta y no se pueden vincular a un numero de unidad; se registra cada variante de precio observada.
- Latitud/longitud: no aparecen en ninguna pagina; null.
- Sector: indicado tal como aparece en la fuente (algunas paginas se contradicen, p. ej. Xoul "Cumbaya" en el encabezado y "La Morita, Tumbaco" en la descripcion; Syrah Hills "Cumbaya" vs "Tumbaco").
- constructora: null salvo Bloom (Bentho Constructora) y Zadeh (Alvarez Bravo Constructores), que son los unicos nombres de constructora que aparecen en la pagina. El resto no la indica.
- Sin datos personales (vendedores, telefonos, correos, WhatsApp) en el archivo.

## Totales

- Filas en agente_b.jsonl: 399
- Proyectos con filas: 20 (16 de la lista + 4 adicionales), todos en Quito (incluye Puembo, Pifo, Tumbaco y Cumbaya, que pertenecen al DMQ)
- Bloqueados: 0
- Paginas sin precio: 0
