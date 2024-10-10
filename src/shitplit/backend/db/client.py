import os

from dotenv import load_dotenv
from pymongo import MongoClient

# Cargar las variables de entorno del archivo .env si está disponible
# Para manejar desde el contenedor Docker
env_path = "/app/.env" if os.path.exists("/app/.env") else ".env"
load_dotenv(env_path)

print(os.getenv("DB_MONGO"))

client = MongoClient(os.getenv("DB_MONGO"))
db = client["shitplit"]
collection = db["barbacoas"]