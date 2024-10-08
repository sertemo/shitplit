# Usa una imagen base de Python ligera
FROM python:3.11-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar solo los archivos necesarios para instalar dependencias (mejora el caché)
COPY requirements.txt /app

# Instalar dependencias del sistema y Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get remove -y build-essential && apt-get autoremove -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copiar el resto de la aplicación
COPY . /app

# Asegurar que el directorio /app esté en el PYTHONPATH
ENV PYTHONPATH="/app"

# Exponer los puertos que utiliza la aplicación
EXPOSE 60751 8000

# Comando para ejecutar la aplicación
CMD ["sh", "-c", "uvicorn src.shitplit.backend.main:app --host 0.0.0.0 --port 8000 & flet run src/shitplit/frontend/main.py --web --port 60751"]
