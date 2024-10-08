from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
from icecream import ic

from src.shitplit.backend.db.client import collection
import shitplit.settings as settings

app = FastAPI()

# Definición del modelo de los gastos
class Gasto(BaseModel):
    persona: str
    concepto: str
    importe: float

class BarbacoaMongo(BaseModel):
    fecha: str
    nombre: str
    ajustes: list[dict[str, Any]]
    gastos: list[dict[str, Any]]


@app.post(settings.CALCULAR_AJUSTES_ENDPOINT)
async def calcular_ajustes(gastos: list[Gasto]):
    ic("RECIBIDO POR EL BACKEND")
    ic(gastos)
    df = pd.DataFrame([g.model_dump() for g in gastos])
    total_gasto = df["importe"].sum()
    personas = df["persona"].unique()
    gasto_medio = total_gasto / len(personas) if len(personas) > 0 else 0

    pagos = df.groupby("persona")["importe"].sum().reindex(personas, fill_value=0)
    deudas = gasto_medio - pagos

    # Calcular deudores y acreedores
    deudores = deudas[deudas > 0].to_dict()
    acreedores = (-deudas[deudas < 0]).to_dict()

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
    # TODO Validar para no poder guardar 2 veces la misma BBQ
    # TODO Discriminar por nombre y fecha ?
    barbacoa_dict = barbacoa.model_dump()
    ic("METEMOS EN DB")
    ic(barbacoa_dict)
    try:
        collection.insert_one(barbacoa_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))