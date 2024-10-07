# Dockerfile para la aplicación de Streamlit

# Imagen base de Python
FROM python:3.11-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos de la aplicación al contenedor
COPY . /app

# Instalar las dependencias necesarias
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto que utiliza Streamlit
EXPOSE 60751 8000

# Comando para ejecutar la aplicación utilizando la variable de entorno PORT
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & flet run main.py --web --port 60751"]