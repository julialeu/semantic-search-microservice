# --- 1. Builder Stage ---
# Usamos esta etapa para instalar dependencias, incluyendo las de compilación.
FROM python:3.11-slim as builder

# Instalar dependencias del sistema necesarias para compilar algunas librerías (ej. faiss-cpu)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar solo el archivo de requerimientos para aprovechar el cache de Docker
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt


# --- 2. Runtime Stage ---
# Esta es la imagen final, mucho más ligera.
FROM python:3.11-slim

# Instalar curl para que el HEALTHCHECK funcione
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar las dependencias instaladas desde la etapa 'builder'
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar el código de la aplicación
COPY ./app ./app

# Exponer el puerto en el que correrá la aplicación
EXPOSE 8000

# Health Check: Docker verificará periódicamente si el servicio está saludable.
# Espera 15s para que inicie, reintenta 3 veces con un timeout de 5s.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8000/health || exit 1

# Comando para iniciar la aplicación
CMD ["uvicorn", "app.interfaces.api:app", "--host", "0.0.0.0", "--port", "8000"]