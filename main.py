import flet as ft
import json
import pandas as pd
from datetime import datetime
import os
from icecream import ic
import requests
import random

from typing import Any

# Archivos JSON para almacenar los datos
PERSONAS_FILE = "personas.json"
BARBACOAS_FILE = "barbacoas.json"
BACKEND_URL = "http://localhost:8000"

def generar_color_aleatorio():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

# Cargar la lista de personas desde un archivo JSON
def load_personas():
    if os.path.exists(PERSONAS_FILE):
        with open(PERSONAS_FILE, "r") as f:
            personas = json.load(f)
        return [persona["nombre"] for persona in personas]
    else:
        return []

# Cargar la lista de barbacoas desde un archivo JSON
def load_barbacoas() -> list[dict[str, Any]]:  # TODO De mongodb
    if os.path.exists(BARBACOAS_FILE):
        with open(BARBACOAS_FILE, "r") as f:
            return json.load(f)
    return []

# Guardar la lista de barbacoas en un archivo JSON
def save_barbacoa(barbacoa):  # TODO Meter en mongodb
    barbacoas = load_barbacoas()
    barbacoas.append(barbacoa)
    with open(BARBACOAS_FILE, "w") as f:
        json.dump(barbacoas, f, indent=4)

# Flet Web App
def main(page: ft.Page):
    page.title = "Ajustar gastos de barbacoas"
    page.theme = ft.Theme(color_scheme_seed='green')
    page.theme_mode = "light"
    page.padding = 20
    page.vertical_alignment = "start"

    

    # Contenedor para la tabla
    def update_expenses_table():
        expenses_table.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(row["Persona"])),
                ft.DataCell(ft.Text(row["Concepto"])),
                ft.DataCell(ft.Text(f"{row['Importe']:.2f} €")),
                ft.DataCell(ft.IconButton(ft.icons.DELETE, on_click=lambda e, idx=index: delete_expense(idx)))
            ]) for index, row in page.session.expenses.iterrows()
        ]
        page.update()

    # Botón para añadir el gasto
    def add_expense(e):
        persona = persona_field.value
        concepto = concepto_field.value
        try:
            importe = float(importe_field.value) if importe_field.value else 0.0
        except ValueError:
            show_snack_bar("Importe debe ser un número válido.", "red")
            return

        if persona:
            new_expense = pd.DataFrame({"Persona": [persona], "Concepto": [concepto], "Importe": [importe]}, dtype=object)
            page.session.expenses = pd.concat([page.session.expenses, new_expense], ignore_index=True, sort=False)
            ic(page.session.expenses)
            page.session.remaining_personas.remove(persona)
            persona_field.options = [ft.dropdown.Option(p) for p in page.session.remaining_personas]
            update_expenses_table()
            persona_field.value = ""
            concepto_field.value = ""
            importe_field.value = ""
            page.update()
        else:
            show_snack_bar("Todos los campos son requeridos.", "red")

    # Mostrar mensajes de snack bar
    def show_snack_bar(message, color):
        snack_bar = ft.SnackBar(content=ft.Text(message), bgcolor=color)
        page.overlay.append(snack_bar)
        snack_bar.open = True
        page.update()

    # Botón para eliminar un gasto
    def delete_expense(index):
        persona = page.session.expenses.loc[index, "Persona"]
        ic(persona)
        page.session.expenses.drop(index, inplace=True)
        page.session.expenses.reset_index(drop=True, inplace=True)
        page.session.remaining_personas.append(persona)
        persona_field.options = [ft.dropdown.Option(p) for p in page.session.remaining_personas]
        update_expenses_table()
        page.update()

    # Botón para ajustar cuentas y crear gráficos
    def calculate_balances(e):
        ic("ENVIADO AL BACKEND")
        gastos = [{"persona": row["Persona"], "concepto": row["Concepto"], "importe": row["Importe"]} for index, row in page.session.expenses.iterrows()]
        ic(gastos)
        if gastos:
            response = requests.post(f"{BACKEND_URL}/calcular_ajustes", json=gastos)
            if response.status_code == 200:
                ajustes = response.json()["ajustes"]
                ic(ajustes)
                ajustes_list = ft.Column()
                ajustes_list.controls.extend([ft.Text(ajuste) for ajuste in ajustes])
                page.update()

                ic(page.session.expenses)
                personas = [row["Persona"] for index, row in page.session.expenses.iterrows() if row["Importe"] > 0]
                pagos = page.session.expenses.groupby("Persona")["Importe"].sum().reindex(personas, fill_value=0)
                ic(pagos)
                ic(personas)
                # Crear gráficos
                gastos_chart_data = [
                    ft.PieChartSection(
                        value=pagos[persona], title=persona, color=generar_color_aleatorio()
                        ) for persona in personas
                    ]
                gastos_chart = ft.PieChart(sections=gastos_chart_data, width=300, height=300, center_space_radius=100)

                # Mostrar ajustes y gráficos
                ajustes_section.controls.clear()
                ajustes_section.controls.extend([ajustes_list, gastos_chart])
                page.session.adjustments_made = True
                page.update()
        else:
            show_snack_bar("No hay gastos para ajustar.", "red")

    # Guardar barbacoa
    def save_current_barbacoa(e):
        if not hasattr(page.session, "adjustments_made") or not page.session.adjustments_made:
            show_snack_bar("Debes ajustar las cuentas antes de guardar la barbacoa.", "red")
            return

        ajustes = calculate_balances(None)
        if ajustes is None:
            ajustes = []
        barbacoa = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "gastos": page.session.expenses.to_dict(orient="records"),
            "ajustes": ajustes
        }
        save_barbacoa(barbacoa)
        show_snack_bar("Barbacoa guardada correctamente.", "green")

    # Mostrar todas las barbacoas guardadas
    def display_saved_barbacoas():
        barbacoas = load_barbacoas()
        ic(barbacoas)
        for idx, barbacoa in enumerate(barbacoas):
            barbacoa_text = ft.Text(f"Barbacoa {idx + 1} - Fecha: {barbacoa['fecha']}")
            gastos_df = pd.DataFrame(barbacoa['gastos'])
            gastos_table = ft.DataTable(
                columns=[
                    ft.DataColumn(label=ft.Text("Persona")),
                    ft.DataColumn(label=ft.Text("Concepto")),
                    ft.DataColumn(label=ft.Text("Importe"))
                ],
                rows=[
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(row["Persona"])),
                        ft.DataCell(ft.Text(row["Concepto"])),
                        ft.DataCell(ft.Text(f"{row['Importe']:.2f} €"))
                    ]) for _, row in gastos_df.iterrows()
                ]
            )
            ajustes = barbacoa.get('ajustes', [])
            ic(ajustes)
            ajustes_list = ft.Column([ft.Text(ajuste) for ajuste in ajustes])
            page.add(ft.Column([barbacoa_text]))

    # Componentes de la página
    # Título principal
    titulo_ppal_container = ft.Container(ft.Text("Añade gastos para nueva barbacoa", size=30, weight="bold"), bgcolor="blue", padding=10)

    # Inicialización del DataFrame
    if not hasattr(page.session, "expenses"):
        page.session.expenses = pd.DataFrame(columns=["Persona", "Concepto", "Importe"])
    if not hasattr(page.session, "remaining_personas"):
        page.session.remaining_personas = load_personas()

    # Input de la persona
    persona_field = ft.Dropdown(
        label="Persona que ha pagado:",
        options=[ft.dropdown.Option(persona) for persona in page.session.remaining_personas],
        width=300
    )
    # Concepto de la compra
    concepto_field = ft.TextField(label="Concepto de la compra:", width=300, border_radius=8)
    # Importe
    importe_field = ft.TextField(label="Importe pagado:", width=300)
    add_expense_button = ft.ElevatedButton("Añadir Gasto", on_click=add_expense)

    input_container = ft.Container(
        ft.Row(
            [persona_field, concepto_field, importe_field, add_expense_button],
        ),
        bgcolor="green",
        padding=10
    )
    # Tabla de gastos
    expenses_table = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("Persona")),
            ft.DataColumn(label=ft.Text("Concepto")),
            ft.DataColumn(label=ft.Text("Importe")),
            ft.DataColumn(label=ft.Text("Acciones"))
        ],
        rows=[]
    )
    update_expenses_table()
    calculate_button = ft.ElevatedButton("Ajustar Cuentas", on_click=calculate_balances)
    expenses_table_container = ft.Container(
        ft.Column(
            [
                expenses_table,
                calculate_button
            ]
        ),
        bgcolor="blue",
        padding=10
    )

    
    save_button = ft.ElevatedButton("Guardar Barbacoa", on_click=save_current_barbacoa)

    # Contenedor para los ajustes
    ajustes_section = ft.Column()

    # Añadir los elementos al layout de la página
    page.add(
        ft.Row([persona_field, concepto_field, importe_field, add_expense_button]),
        expenses_table,
        ft.Row([calculate_button, save_button]),
        ajustes_section
    )

    # Mostrar las barbacoas guardadas
    page.add(ft.Text("Barbacoas Guardadas", size=25, weight="bold"))
    display_saved_barbacoas()

ft.app(target=main)