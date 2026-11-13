# Predicción de precios de viviendas en Quito y los valles

Proyecto final de **Aprendizaje Supervisado** (USFQ, 202610).

Modelo de regresión que predice el precio de venta (USD) de casas y departamentos en el Distrito Metropolitano de
Quito, incluidos los valles de Cumbayá, Tumbaco y Los Chillos, a partir de sus características (área, habitaciones,
baños, parqueaderos, ubicación, amenidades).

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/USUARIO/REPO/blob/main/proyecto_ml_casas_quito.ipynb)

## Integrantes

- Nombre 1
- Nombre 2
- Nombre 3

## Metodología

Todo el proyecto está en el notebook [`proyecto_ml_casas_quito.ipynb`](proyecto_ml_casas_quito.ipynb):

1. **EDA**: calidad de datos, distribución del precio, correlaciones, Quito vs. valles, mapa de precios y atípicos.
2. **Pipeline de scikit-learn**: imputación → escalado / one-hot → selección de características tipo filtro
   (`SelectPercentile` + `f_regression`) → modelo, con el objetivo en escala logarítmica
   (`TransformedTargetRegressor`).
3. **Optimización de hiperparámetros** con [Optuna](https://optuna.org) y *repeated k-fold CV*, más curvas de
   validación y de aprendizaje.
4. **Comparación estadística** entre HistGradientBoosting y Random Forest con *repeated k-fold* 10×10: prueba de
   Wilcoxon y t-test pareado corregido (Nadeau & Bengio).
5. **Evaluación final** en un conjunto de prueba reservado (RMSE, MAE, MAPE, R²).
6. **t-SNE** del espacio de características coloreado por precio.

## Resultados

| Modelo | RMSE test (USD) | MAPE test (%) | R² |
|---|---|---|---|
| HistGradientBoosting | _TODO_ | _TODO_ | _TODO_ |
| Random Forest | _TODO_ | _TODO_ | _TODO_ |

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
│   └── README.md                   # fuente y diccionario de variables
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
finales se obtienen con `MODO_RAPIDO = False` (Optuna con 60 *trials*, comparación 10×10).
