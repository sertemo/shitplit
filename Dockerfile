# Usa una imagen base de Python ligera
FROM python:3.11-slim AS generate-requirements

# Instalamos poetry primero
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN curl -sSL https://install.python-poetry.org | python3 -
RUN apt-get purge -y --auto-remove curl && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY pyproject.toml poetry.lock ./
RUN /root/.local/bin/poetry export --output requirements.txt

# Instalamos las dependencias
FROM python:3.11-slim AS production
WORKDIR /app

COPY --from=generate-requirements /requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY . .

# Asegurar que el directorio /app esté en el PYTHONPATH
ENV PYTHONPATH="/app"

# Exponer los puertos que utiliza la aplicación
EXPOSE 60751 8000

# Comando para ejecutar la aplicación
CMD ["sh", "-c", "uvicorn src.shitplit.backend.main:app --host 0.0.0.0 --port 8000 & flet run src/shitplit/frontend/main.py --web --port 60751"]
