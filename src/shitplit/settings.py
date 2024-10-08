from pathlib import Path

PERSONAS_FILE = Path("src/shitplit/backend/db") / "personas.json"
BARBACOAS_FILE = "barbacoas.json"
BACKEND_URL = "http://localhost:8000"
APP_FONTS = {
    "Poppins": "fonts/Poppins-Medium.ttf",
}

CALCULAR_AJUSTES_ENDPOINT = "/calcular_ajustes"
CALCULAR_AJUSTES_URL = f"{BACKEND_URL}{CALCULAR_AJUSTES_ENDPOINT}"
GUARDAR_BARBACOA_ENDPOINT = "/guardar_barbacoa"
GUARDAR_BARBACOA_URL = f"{BACKEND_URL}{GUARDAR_BARBACOA_ENDPOINT}"