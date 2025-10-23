# Dockerfile

# --- Etapa 1: Builder ---
# Usamos una imagen completa de Python para instalar dependencias.
FROM python:3.11-slim as builder

WORKDIR /usr/src/app

# Instalar dependencias del sistema para faiss-cpu
RUN apt-get update && apt-get install -y libgomp1

# Copiar solo el fichero de requisitos e instalar dependencias
# Esto aprovecha la caché de Docker si los requisitos no cambian
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# --- Etapa 2: Final ---
# Usamos una imagen slim para que la imagen final sea más ligera.
FROM python:3.11-slim

WORKDIR /usr/src/app

# Instalar dependencias del sistema de nuevo
RUN apt-get update && apt-get install -y libgomp1

# Copiar las dependencias instaladas de la etapa 'builder'
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copiar el código de la aplicación
COPY ./app ./app

# Exponer el puerto en el que correrá la aplicación
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app.interfaces.api:app", "--host", "0.0.0.0", "--port", "8000"]