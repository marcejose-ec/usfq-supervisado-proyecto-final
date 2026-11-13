# Entorno reproducible para ejecutar el notebook completo (CPU), p. ej. en los servidores de la universidad.
#   docker build -t casas-quito-ml .
#   docker run --rm --cpus=16 -e N_JOBS=16 -u "$(id -u):$(id -g)" -v "$PWD":/work casas-quito-ml
FROM python:3.12-slim

# HOME=/tmp: el contenedor corre con el usuario del host, que no tiene home dentro de la imagen.
# *_NUM_THREADS=1: el paralelismo viene de los folds de CV (N_JOBS); sin esto cada proceso abriría varios hilos
# de BLAS/OpenMP y la carga superaría los núcleos asignados.
ENV PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 HOME=/tmp MPLBACKEND=Agg \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

WORKDIR /work
COPY requirements.txt /tmp/requirements.txt

# PyTorch solo CPU (~200 MB en lugar de ~2 GB con CUDA): la red es pequeña y la GPU no acelera este problema
RUN pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r /tmp/requirements.txt

# Ejecuta el notebook del repositorio montado en /work y guarda las salidas en el mismo archivo
CMD ["jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace", \
     "--ExecutePreprocessor.timeout=-1", "proyecto_ml_casas_quito.ipynb"]
