# backend.py
from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from icecream import ic

app = FastAPI()

# Definición del modelo de los gastos
class Gasto(BaseModel):
    persona: str
    concepto: str
    importe: float

@app.post("/calcular_ajustes")
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
