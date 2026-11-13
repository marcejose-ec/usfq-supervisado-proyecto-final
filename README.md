# Predicción de precios de viviendas en Quito y los valles

Proyecto final de **Aprendizaje Supervisado** (USFQ, 202610).

Modelo de regresión que predice el precio de venta (USD) de casas y departamentos en el Distrito Metropolitano de
Quito, incluidos los valles de Cumbayá, Tumbaco y Los Chillos, a partir de sus características (área, habitaciones,
baños, parqueaderos, ubicación, amenidades).

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/marcejose-ec/usfq-supervisado-proyecto-final/blob/main/proyecto_ml_casas_quito.ipynb)

## Integrantes

- Nombre 1
- Nombre 2
- Nombre 3

## Metodología

Todo el proyecto está en el notebook [`proyecto_ml_casas_quito.ipynb`](proyecto_ml_casas_quito.ipynb):

1. **EDA**: calidad de datos, valores anómalos, distribución del precio (≈ log-normal), relación precio–área, Quito
   vs. valles, sectores y suavidad espacial del precio, fuentes, faltantes informativos y amenidades.
2. **Objetivo en escala log**: se modela log(precio) y la métrica es el **RMSLE**. Los resultados finales también se
   reportan en USD.
3. **Pipeline de scikit-learn** común a todos los modelos: log de áreas, imputación con indicadores de faltante,
   coordenadas faltantes completadas con el centroide del sector (transformador propio), escalado, one-hot y
   selección de características tipo filtro (`SelectPercentile` + `f_regression`).
4. **Optimización de hiperparámetros** con [Optuna](https://optuna.org) y *repeated k-fold CV*, más curvas de
   validación y de aprendizaje.
5. **Comparación estadística: MLP (PyTorch Lightning) vs. Random Forest** con *repeated k-fold* 10×10, usando la prueba de Wilcoxon y el
   t-test pareado corregido (Nadeau & Bengio). Ridge (modelo hedónico lineal) sirve de referencia.
6. **Evaluación final** en un conjunto de prueba reservado (RMSLE, MAPE, MAE en USD).
7. **t-SNE** del espacio de características coloreado por precio y por zona.

## Resultados

| Modelo | RMSLE test | MAPE test (%) | Error mediano (USD) |
|---|---|---|---|
| MLP | _TODO_ | _TODO_ | _TODO_ |
| Random Forest | _TODO_ | _TODO_ | _TODO_ |
| Ridge (referencia) | _TODO_ | _TODO_ | _TODO_ |

Resultado de la comparación estadística: _TODO_.

Las tablas completas se guardan en [`resultados/`](resultados/).

## Datos

`data/casas_quito.csv`: 7.151 anuncios de venta de casas y departamentos en Quito y los valles, recolectados el 11–12 de noviembre de 2026 de icasas.ec, remax.com.ec, arriendayvende.com, trivo.com.ec y sitios de constructoras (scripts en [`scraper/`](scraper/)). Ver [`data/README.md`](data/README.md)
para el diccionario de variables y los pasos de limpieza.

## Estructura

```
.
├── proyecto_ml_casas_quito.ipynb   # notebook principal (todo el proyecto)
├── data/
│   ├── casas_quito.csv             # dataset
│   ├── coordenadas_proyectos.csv   # coordenadas de proyectos nuevos (revisadas a mano)
│   ├── README.md                   # fuente y diccionario de variables
│   └── raw/constructoras/          # datos de constructoras recopilados por agentes
├── scraper/                        # scripts de scraping y build_dataset.py
├── resultados/                     # CSV/JSON generados por el notebook
├── Dockerfile                      # entorno para la corrida completa
└── requirements.txt                # versiones probadas
```

## Cómo ejecutar

**Google Colab:** abrir el notebook con el botón de arriba (se abre con GPU) y ejecutar todas las celdas. La primera
celda instala Optuna y PyTorch Lightning si faltan, y el dataset se descarga desde este repositorio (`DATA_URL`).
Con `MODO_RAPIDO = True` corre de principio a fin en pocos minutos.

**Corrida completa en un servidor con Docker** (así se obtuvieron los resultados publicados):

```bash
git clone https://github.com/marcejose-ec/usfq-supervisado-proyecto-final.git
cd usfq-supervisado-proyecto-final
docker build -t casas-quito-ml .
docker run --rm --cpus=16 -e N_JOBS=16 -u "$(id -u):$(id -g)" -v "$PWD":/work casas-quito-ml
```

El contenedor ejecuta el notebook y guarda las salidas en el mismo archivo y en `resultados/`. `--cpus` y `N_JOBS`
limitan los núcleos usados (importante en un servidor compartido). La imagen usa PyTorch solo-CPU: la red es pequeña
y la GPU no acelera este problema.

**Localmente:**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt jupyterlab
jupyter lab proyecto_ml_casas_quito.ipynb
```

Los resultados finales se obtienen con `MODO_RAPIDO = False` (Optuna con 60 *trials* por modelo, comparación 10×10).
