import os
import json
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
from icecream import ic

from src.shitplit.backend.db.client import collection
import src.shitplit.settings as settings

app = FastAPI()

# Definición del modelo de los gastos
class Gasto(BaseModel):
    Persona: str
    Concepto: str
    Importe: float

class BarbacoaMongo(BaseModel):
    fecha: str
    nombre: str
    ajustes: list[dict[str, Any]]
    gastos: list[dict[str, Any]]
    gasto_total: float
    gasto_medio: float
    participantes: list[str]

class BarbacoaDelete(BaseModel):
    nombre: str

# Cargamos la cuadrilla desde el json
def load_cuadrilla():
    if os.path.exists(settings.PERSONAS_FILE):
        with open(settings.PERSONAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return []


@app.get(settings.LOAD_CUADRILLA_ENDPOINT)
async def get_cuadrilla():
    cuadrilla: list[dict[str, Any]] = load_cuadrilla()
    return cuadrilla


@app.post(settings.CALCULAR_AJUSTES_ENDPOINT)
async def calcular_ajustes(gastos: list[Gasto]):
    df = pd.DataFrame([g.model_dump() for g in gastos])
    ic(df)
    total_gasto = df["Importe"].sum()
    personas = df["Persona"].unique()
    gasto_medio = total_gasto / len(personas) if len(personas) > 0 else 0

    pagos = df.groupby("Persona")["Importe"].sum().reindex(personas, fill_value=0)
    deudas = gasto_medio - pagos

    ic(deudas)

    # Calcular deudores y acreedores
    deudores = deudas[deudas > 0].to_dict()
    acreedores = (-deudas[deudas < 0]).to_dict()

    ic(deudores)
    ic(acreedores)

    # Cargar la cuadrilla para acceder a la información de parejas
    cuadrilla = {persona["nombre"]: persona["pareja"] for persona in load_cuadrilla()}

    ajustes: list[dict[str, Any]] = []
    for deudor, deuda in deudores.items():
        pareja_deudor = cuadrilla.get(deudor)
        # Primero intentamos ajustar con la pareja si es acreedora
        if pareja_deudor and pareja_deudor in acreedores:
            credito_pareja = acreedores[pareja_deudor]
            pago = min(deuda, credito_pareja)
            ajustes.append({
                "deudor": deudor,
                "acreedor": pareja_deudor,
                "pago": pago
            })
            deuda -= pago
            acreedores[pareja_deudor] -= pago
            if acreedores[pareja_deudor] == 0:
                del acreedores[pareja_deudor]
            if deuda == 0:
                continue  # Deuda completamente saldada con la pareja, seguimos con el siguiente deudor

        # Si aún hay deuda, ajustamos con otros acreedores
        for acreedor, credito in list(acreedores.items()):
            if deuda == 0:
                break
            pago = min(deuda, credito)
            ajustes.append({
                "deudor": deudor,
                "acreedor": acreedor,
                "pago": pago
            })
            deuda -= pago
            acreedores[acreedor] -= pago
            if acreedores[acreedor] == 0:
                del acreedores[acreedor]

    return {"ajustes": ajustes}

@app.post("/old")
async def calcular_ajustes_old(gastos: list[Gasto]):
    df = pd.DataFrame([g.model_dump() for g in gastos])
    ic(df)
    total_gasto = df["Importe"].sum()
    personas = df["Persona"].unique()
    gasto_medio = total_gasto / len(personas) if len(personas) > 0 else 0

    pagos = df.groupby("Persona")["Importe"].sum().reindex(personas, fill_value=0)
    deudas = gasto_medio - pagos

    ic(deudas)

    # Calcular deudores y acreedores
    deudores = deudas[deudas > 0].to_dict()
    acreedores = (-deudas[deudas < 0]).to_dict()

    ic(deudores)
    ic(acreedores)

    ajustes: list[str] = []
    for deudor, deuda in deudores.items():
        for acreedor, credito in list(acreedores.items()):
            if deuda == 0:
                break
            pago = min(deuda, credito)
            transaccion = {
                "deudor": deudor,
                "acreedor": acreedor,
                "pago": pago
            }
            ajustes.append(transaccion)
            deuda -= pago
            acreedores[acreedor] -= pago
            if acreedores[acreedor] == 0:
                del acreedores[acreedor]

    return {"ajustes": ajustes}


@app.post(settings.GUARDAR_BARBACOA_ENDPOINT)
async def guardar_barbacoa(barbacoa: BarbacoaMongo):
    # Convertir el modelo en un diccionario
    barbacoa_dict = barbacoa.model_dump()
    ic("METEMOS EN DB")
    ic(barbacoa_dict)
    
    try:
        # Comprobar si ya existe una barbacoa con el mismo nombre
        existing_barbacoa = collection.find_one({"nombre": barbacoa_dict["nombre"]})
        ic(existing_barbacoa)
        if existing_barbacoa:
            raise HTTPException(status_code=400, detail="Una barbacoa con este nombre ya existe.")
        
        # Insertar la nueva barbacoa si no existe duplicado
        collection.insert_one(barbacoa_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(settings.OBTENER_BARBACOAS_GUARDADAS_ENDPOINT)
async def get_barbacoas():
    barbacoas = list(collection.find({}, {"_id": 0}))
    ic(barbacoas)
    return barbacoas


@app.delete(settings.ELIMINAR_BARBACOA_ENDPOINT)
async def delete_barbacoa(barbacoa: BarbacoaDelete):
    collection.delete_one({"nombre": barbacoa.nombre})
    return {"message": "ok"}