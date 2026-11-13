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
5. **Comparación estadística: MLP vs. Random Forest** con *repeated k-fold* 10×10, usando la prueba de Wilcoxon y el
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
└── requirements.txt
```

## Cómo ejecutar

**Google Colab (recomendado):** abrir el notebook con el botón de arriba y ejecutar todas las celdas. El dataset se
descarga desde este repositorio (`DATA_URL` en la sección de configuración).

**Localmente:**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab proyecto_ml_casas_quito.ipynb
```

Con `MODO_RAPIDO = True` el notebook corre de principio a fin en pocos minutos para pruebas. Los resultados
finales se obtienen con `MODO_RAPIDO = False` (Optuna con 60 *trials* por modelo, comparación 10×10).
