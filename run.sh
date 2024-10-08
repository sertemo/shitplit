# Para correr en local la aplicación

uvicorn src.shitplit.backend.main:app --host 0.0.0.0 --port 8000 & flet run src/shitplit/frontend/main.py --web --port 60751