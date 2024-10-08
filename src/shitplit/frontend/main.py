from datetime import datetime
import json
import os
from typing import Any

import flet as ft
import pandas as pd
from icecream import ic
import requests

from src.shitplit.frontend.styles import Sizes
import src.shitplit.settings as settings


def load_cuadrilla() -> list[dict[str, Any]]:
    # Cargamos la cuadrilla desde el json
    if os.path.exists(settings.PERSONAS_FILE):
        with open(settings.PERSONAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return []

# Cargar la lista de barbacoas desde un archivo JSON
def load_barbacoas() -> list[dict[str, Any]]:  # TODO De mongodb
    if os.path.exists(settings.BARBACOAS_FILE):
        with open(settings.BARBACOAS_FILE, "r") as f:
            return json.load(f)
    return []

# Guardar la lista de barbacoas en un archivo JSON
def save_barbacoa(barbacoa):  # TODO Meter en mongodb
    barbacoas = load_barbacoas()
    barbacoas.append(barbacoa)
    with open(settings.BARBACOAS_FILE, "w") as f:
        json.dump(barbacoas, f, indent=4)

# Flet Web App
def main(page: ft.Page):
    page.fonts = settings.APP_FONTS
    page.theme = ft.Theme(font_family="Poppins")
    page.title = "Ajustar gastos de barbacoas"
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.session.cuadrilla = load_cuadrilla()
    page.session.colores = {persona['nombre']: persona['color'] for  persona in page.session.cuadrilla}

    ic(page.session.cuadrilla)

    # Contenedor para la tabla
    def update_expenses_table():
        expenses_table.rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(row["Persona"], size=Sizes.LARGE)),
                ft.DataCell(ft.Text(row["Concepto"], size=Sizes.LARGE)),
                ft.DataCell(ft.Text(f"{row['Importe']:.2f} €", size=Sizes.LARGE)),
                ft.DataCell(
                    ft.IconButton(
                        ft.icons.DELETE, 
                        on_click=lambda e, idx=index: delete_expense(idx), 
                        icon_color=ft.colors.RED_700,
                        tooltip="Eliminar"
                        )
                    )
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
            show_snack_bar("Debes añadir la persona", "red")

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
        gastos = [
            {"persona": row["Persona"], "concepto": row["Concepto"], "importe": row["Importe"]} 
            for index, row in page.session.expenses.iterrows()
            ]
        colores_dict = page.session.colores
        ic(gastos)
        if gastos:
            response = requests.post(f"{settings.BACKEND_URL}/calcular_ajustes", json=gastos)
            if response.status_code == 200:
                ajustes: dict[str, Any] = response.json()["ajustes"]
                ic(ajustes)
                ajustes_list = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
                ajustes_list.controls.extend([ft.Row(
                    [ft.Text(ajuste["deudor"], color=colores_dict[ajuste["deudor"]], size=Sizes.LARGE), 
                    ft.Text("debe pagar a"), ft.Text(ajuste["acreedor"], color=colores_dict[ajuste["acreedor"]], size=Sizes.LARGE), 
                    ft.Text(f"{ajuste['pago']:.2f} €")],
                    ) for ajuste in ajustes])
                page.update()

                ic(page.session.expenses)
                personas = [row["Persona"] for index, row in page.session.expenses.iterrows() if row["Importe"] > 0]
                pagos = page.session.expenses.groupby("Persona")["Importe"].sum().reindex(personas, fill_value=0)
                ic(pagos)
                ic(personas)
                # Crear gráficos
                gastos_chart_data = [  # TODO SACAR EN OTRA FUNCIÓN
                    ft.PieChartSection(
                        value=pagos[persona], title=persona, color=colores_dict[persona], title_style=ft.TextStyle(bgcolor=ft.colors.WHITE),
                        radius=160
                        ) for persona in personas
                    ]
                gastos_chart = ft.PieChart(
                    sections=gastos_chart_data, 
                    width=400, 
                    height=400, 
                    center_space_radius=0,
                    expand=True
                    )

                # Mostrar ajustes y gráficos
                ajustes_section.controls.clear()
                ajustes_section.controls.extend([ajustes_list, gastos_chart])
                save_button.disabled = False
                page.update()
        else:
            show_snack_bar("No hay gastos para ajustar.", "red")

    # Guardar barbacoa
    def save_current_barbacoa(e):
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
            return ft.Container(
                ft.Column(
                    [barbacoa_text, gastos_table, ajustes_list],
                    alignment=ft.MainAxisAlignment.CENTER
                    ), 
                    bgcolor="blue",
                    padding=10
                    )

    # Componentes de la página
    # Título principal
    titulo_ppal_container = ft.Container(
        ft.Text("Añade gastos para nueva barbacoa", size=30, weight="bold"), 
        #bgcolor="blue", 
        padding=10)

    # Inicialización del DataFrame
    if not hasattr(page.session, "expenses"):
        page.session.expenses = pd.DataFrame(columns=["Persona", "Concepto", "Importe"])
    if not hasattr(page.session, "remaining_personas"):
        page.session.remaining_personas = [persona["nombre"] for persona in page.session.cuadrilla]

    # Input de la persona
    INPUT_HEIGHT = 40
    persona_field = ft.Dropdown(
        label="Quien",
        options=[ft.dropdown.Option(persona) for persona in page.session.remaining_personas],
        width=300,
        border_radius=ft.border_radius.all(10),
        height=INPUT_HEIGHT,
        content_padding=ft.padding.symmetric(5, 8)
    )
    # Concepto de la compra
    concepto_field = ft.TextField(
        label="Concepto de gasto", 
        width=300, 
        border_radius=10,
        height=INPUT_HEIGHT,
        content_padding=persona_field.content_padding
        )
    # Importe
    importe_field = ft.TextField(
        label="Importe", 
        width=300, 
        border_radius=10, 
        height=INPUT_HEIGHT,
        content_padding=persona_field.content_padding
        )
    add_expense_button = ft.IconButton(
        icon=ft.icons.ADD, 
        tooltip="Añadir Gasto", 
        on_click=add_expense, 
        icon_size=INPUT_HEIGHT,
        #bgcolor=ft.colors.GREY_300
        )

    input_container = ft.Container(
        ft.Row(
            [persona_field, concepto_field, importe_field, add_expense_button],
            alignment=ft.MainAxisAlignment.CENTER
        ),
        #bgcolor="green",
        padding=10,
    )
    # Tabla de gastos
    expenses_table = ft.DataTable(
        columns=[
            ft.DataColumn(label=ft.Text("Persona", size=Sizes.LARGE, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(label=ft.Text("Concepto", size=Sizes.LARGE, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(label=ft.Text("Importe", size=Sizes.LARGE, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(label=ft.Text("Acciones", size=Sizes.LARGE, weight=ft.FontWeight.BOLD)),
        ],
        rows=[]
    )
    update_expenses_table()
    calculate_button = ft.IconButton(
        icon=ft.icons.CALCULATE,        
        tooltip="Ajustar Cuentas", 
        on_click=calculate_balances,
        icon_size=40,
        #bgcolor=ft.colors.GREY_300
        )
    expenses_table_container = ft.Container(
        ft.Column(
            [
                expenses_table,
                calculate_button
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        width=500,
        #bgcolor=ft.colors.GREY_100,
        border=ft.border.all(width=1, color=ft.colors.GREY_300),
        padding=10,
        border_radius=ft.border_radius.all(20),
    )

    
    # Contenedor para los ajustes
    ajustes_section = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
    save_button = ft.IconButton(
        icon=ft.icons.SAVE, 
        tooltip="Guardar Barbacoa", 
        on_click=save_current_barbacoa, 
        disabled=True,
        icon_size=40,
        #icon_color=ft.colors.BLUE_700,
        #bgcolor=ft.colors.GREY_300
        )

    ajustes_container = ft.Container(
        ft.Column(
            [
                ft.Container(ajustes_section, alignment=ft.alignment.center),
                save_button
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        ),
        #bgcolor="green",
        padding=20,
        border=expenses_table_container.border,
        border_radius=expenses_table_container.border_radius,
        width=500,
    )
    # Añadir los elementos al layout de la página
    saved_bbq_container = ft.Container(
        ft.Column(
            [ft.Text("Barbacoas Guardadas", size=25, weight="bold")],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        ),
        #bgcolor="blue",
    )
    layout = ft.Column(
        [
            titulo_ppal_container,
            input_container,
            expenses_table_container,
            ajustes_container,
            saved_bbq_container
        ],
        spacing=20,
        horizontal_alignment="center",
        )
    page.add(layout)


if __name__ == '__main__':
    ft.app(target=main, assets_dir="assets")