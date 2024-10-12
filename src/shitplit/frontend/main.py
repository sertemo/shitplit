from datetime import datetime
from typing import Any

import flet as ft
import pandas as pd
from icecream import ic
import requests

from src.shitplit.frontend.styles import Sizes
import src.shitplit.settings as settings


def get_cuadrilla() -> list[dict[str, Any]]:
    response = requests.get(settings.LOAD_CUADRILLA_URL)
    if response.status_code != 200:
        return []
    return response.json()

# Cargar la lista de barbacoas desde base de datos
def load_barbacoas() -> list[dict[str, Any]]:
    """
    Carga todas las barbacoas de la base de datos MongoDB.
    Llama a la API
    """
    data: list[dict[str, Any]] = requests.get(settings.OBTENER_BARBACOAS_GUARDADAS_URL).json()
    return data


# Eliminar una barbacoa de base de datos
def delete_barbacoa(barbacoa_nombre: str) -> None:
    """
    Elimina una barbacoa de la base de datos MongoDB.
    Llama a la API
    """
    response = requests.delete(settings.ELIMINAR_BARBACOA_URL, json={"nombre": barbacoa_nombre})
    return response.status_code


def main(page: ft.Page):
    page.fonts = settings.APP_FONTS
    page.theme = ft.Theme(font_family="Poppins")
    page.title = "Ajustar gastos de barbacoas"
    page.padding = 20
    page.favicon = "assets/favicon.ico"
    page.scroll = ft.ScrollMode.AUTO
    page.session.cuadrilla = get_cuadrilla()
    page.session.colores = {persona['nombre']: persona['color'] for  persona in page.session.cuadrilla}
    page.session.barbacoas = load_barbacoas()

    listview_bbq_container = ft.Container(width=420)

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
    def add_expense(e: ft.ControlEvent):
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


    # Funcion para crear el grafico de tarta
    def create_pie_chart(gastos: list[dict[str, Any]], colores_dict: dict[str, str]) -> ft.PieChart:
        """
        Crea una gráfica de tarta con los gastos de una barbacoa.
        """
        # Filtramos gastos con personas que tengan un importe mayor que cero
        personas_pago = [gasto for gasto in gastos if gasto["Importe"] > 0]

        # Encontrar el valor máximo para calcular la posición dinámica
        max_importe = max(gasto["Importe"] for gasto in personas_pago) if personas_pago else 1

        gastos_chart_data = [
            ft.PieChartSection(
                value=persona["Importe"], 
                title=f"{persona['Persona']}\n{persona['Importe']:.2f} €\n{persona['Concepto']}",
                title_style=ft.TextStyle(color=ft.colors.WHITE),
                # Ajustar la posición del título basado en el valor relativo del importe
                title_position=max(0.4, 1 - (persona["Importe"] / max_importe) * 0.95),
                color=colores_dict[persona['Persona']], 
                radius=160
                ) for persona in personas_pago
            ]
        gastos_chart = ft.PieChart(
            sections=gastos_chart_data, 
            # width=400, 
            # height=400, 
            center_space_radius=0,
            #expand=True
            )
        
        return gastos_chart


    def create_ajustes(ajustes: list[dict[str, Any]], colores_dict: dict[str, str]) -> ft.Column:
        """
        Crea los ajustes de una barbacoa.
        """
        ajustes_list = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
        ajustes_list.controls.extend([ft.Row(
            [ft.Text(ajuste["deudor"], color=colores_dict[ajuste["deudor"]], size=Sizes.LARGE), 
            ft.Text("pagó a"), ft.Text(ajuste["acreedor"], color=colores_dict[ajuste["acreedor"]], size=Sizes.LARGE), 
            ft.Text(f"{ajuste['pago']:.2f} €")], 
            alignment=ft.MainAxisAlignment.CENTER
            ) for ajuste in ajustes])

        return ajustes_list


    # Botón para ajustar cuentas y crear gráficos
    def calculate_balances(e: ft.ControlEvent) -> None:
        # Generamos el dict para enviar al backend
        ic(page.session.expenses.Persona.tolist())
        gastos = [
            {"Persona": row["Persona"], "Concepto": row["Concepto"], "Importe": row["Importe"]} 
            for index, row in page.session.expenses.iterrows()
            ]
        colores_dict = page.session.colores
        # Calculamos el gasto total y el gasto medio y guardamos en sesión
        gasto_total = page.session.expenses["Importe"].sum()
        gasto_medio = gasto_total / len(gastos) if len(gastos) > 0 else 0

        page.session.gasto_total = gasto_total
        page.session.gasto_medio = gasto_medio

        if gastos and len(gastos) > 1 and gasto_total > 0.0:
            response = requests.post(f"{settings.BACKEND_URL}/calcular_ajustes", json=gastos)
            if response.status_code == 200:
                ajustes: dict[str, Any] = response.json()["ajustes"]
                ic(ajustes)
                # Guardamos en sesión los ajustes
                page.session.ajustes = ajustes

                # Mostramos los resultados
                ajustes_list = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=10)
                ajustes_list.controls.extend([ft.Row(
                    [ft.Text(ajuste["deudor"], color=colores_dict[ajuste["deudor"]], size=Sizes.LARGE), 
                    ft.Text("debe pagar a"), ft.Text(ajuste["acreedor"], color=colores_dict[ajuste["acreedor"]], size=Sizes.LARGE), 
                    ft.Text(f"{ajuste['pago']:.2f} €")], 
                    alignment=ft.MainAxisAlignment.CENTER
                    ) for ajuste in ajustes])
                ajustes_list.controls.append(ft.Divider())
                ajustes_list.controls.append(ft.Text(f"Gasto Total: {gasto_total:.2f} €", size=Sizes.LARGE))
                ajustes_list.controls.append(ft.Text(f"Gasto medio: {gasto_medio:.2f} €", size=Sizes.LARGE))

                # Crear gráficos
                gastos_chart = create_pie_chart(gastos, colores_dict)

                # Mostrar ajustes y gráficos
                ajustes_section.controls.clear()
                ajustes_section.controls.extend([ajustes_list, ft.Divider(), gastos_chart])
                save_button.disabled = False
                page.update()
        else:
            show_snack_bar("No hay gastos para ajustar.", "red")


    # Guardar barbacoa
    def save_current_barbacoa(e):
        # Validamos que hayan puesto un nombre de barbacoa
        if not barbacoa_field.value:
            show_snack_bar("Debes introducir un nombre de barbacoa.", "red")
            return

        # Armamos el objeto dict para enviar a db
        barbacoa = {
            "fecha": datetime.now().strftime("%d-%m-%Y"),
            "nombre": str(barbacoa_field.value).strip(),
            "ajustes": page.session.ajustes,
            "gastos": page.session.expenses.to_dict(orient="records"),
            "gasto_total": page.session.gasto_total,
            "gasto_medio": page.session.gasto_medio,
            "participantes": page.session.expenses.Persona.tolist()
        }
        ic("OBJETO BARBACOA PARA GUARDAR EN DB")
        ic(barbacoa)
        response = requests.post(settings.GUARDAR_BARBACOA_URL, json=barbacoa)
        if response.status_code == 200:
            display_saved_barbacoas()
            show_snack_bar("Barbacoa guardada correctamente.", "green")
        else:
            msg = response.json().get("detail", "Error guardando la barbacoa.")
            show_snack_bar(msg, "red")


# Popup confirmación para borrar bbq
    def confirm_delete(barbacoa_name):
        def on_confirm(e):
            status_code = delete_barbacoa(barbacoa_name)
            if status_code == 200:
                display_saved_barbacoas()
                show_snack_bar(f"Barbacoa {barbacoa_name} eliminada.", "green")
            else:
                show_snack_bar(f"Error al borrar la barbacoa {barbacoa_name}.", "red")
            
            dialog.open = False
            page.update()
        
        def on_cancel(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirmación"),
            content=ft.Text(f"¿Estás seguro de que deseas eliminar la barbacoa '{barbacoa_name}'?"),
            actions=[
                ft.TextButton("Eliminar", on_click=on_confirm, icon_color=ft.colors.GREEN_700, icon=ft.icons.CHECK),
                ft.TextButton("Cancelar", on_click=on_cancel, icon_color=ft.colors.RED_700, icon=ft.icons.CLOSE),
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()


    # Mostrar ventana con detalles de la barbacoa
    def display_barbacoa_details(barbacoa: dict[str, Any]):
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        ic("BARBACOA A MOSTRAR")
        ic(barbacoa)
        participantes: list[str] = sorted(barbacoa.get("participantes", []))
        dialog = ft.AlertDialog(
            title=ft.Text(f"Barbacoa '{barbacoa.get('nombre', 'Barbacoa sin nombre')}'", text_align=ft.TextAlign.CENTER),
            content=ft.Container(
                    content=ft.Column([
                    ft.Row(
                        [ft.Text("Participantes", size=Sizes.XXLARGE, weight=ft.FontWeight.BOLD), ft.Text(":"), ft.Text(f"{len(participantes)}", weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER),
                    ft.Text(f"{', '.join(participantes)}.", text_align=ft.TextAlign.CENTER),
                    ft.Divider(),
                    ft.Column(
                        [
                            ft.Text(f"Gasto total: {barbacoa['gasto_total']:.2f} €"),
                            ft.Text(f"Gasto medio: {barbacoa['gasto_medio']:.2f} €"),   
                        ]
                    ),                
                    ft.Divider(),
                    create_ajustes(barbacoa['ajustes'], page.session.colores),
                    ft.Divider(),
                    create_pie_chart(barbacoa['gastos'], page.session.colores),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, width=400,
                spacing=20,
                scroll=ft.ScrollMode.AUTO
                ), 
                padding=ft.padding.all(5)),
            actions=[
                ft.TextButton("Cerrar", on_click=close_dialog, icon=ft.icons.CLOSE, icon_color=ft.colors.RED_700),
                ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()


    # Mostrar todas las barbacoas guardadas
    def display_saved_barbacoas():
        barbacoas: list[dict[str, Any]] = load_barbacoas()
        list_view = ft.ListView(expand=True, spacing=10)

        for idx, barbacoa in enumerate(barbacoas, 1):
            ic(barbacoa)
            barbacoa_item = ft.Container(ft.Row([
                ft.Row([ft.Text(f"{idx}"), ft.Text(barbacoa.get('nombre', 'Barbacoa sin nombre'), weight=ft.FontWeight.BOLD), ft.Text('-'),ft.Text(barbacoa['fecha'])]),
                ft.IconButton(
                    icon=ft.icons.DELETE,
                    on_click=lambda e, barbacoa_name=barbacoa.get('nombre', 'Barbacoa'): confirm_delete(barbacoa_name),
                    tooltip="Eliminar",
                    icon_color=ft.colors.RED_700
                )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                border_radius=ft.border_radius.all(10),
                padding=ft.padding.all(10),
                #bgcolor=ft.colors.GREY_50,
                border=ft.border.all(1, ft.colors.GREY_300),
                on_click=lambda e, barbacoa=barbacoa: display_barbacoa_details(barbacoa),
                ink=True
            )
            list_view.controls.append(barbacoa_item)
        
        listview_bbq_container.content = list_view


    # Componentes de la página
    # Título principal
    titulo_ppal_container = ft.Container(
        ft.Text("Añade una nueva barbacoa", size=30, weight="bold"), 
        #bgcolor="blue", 
        padding=10)

    # Inicialización del DataFrame
    if not hasattr(page.session, "expenses"):
        page.session.expenses = pd.DataFrame(columns=["Persona", "Concepto", "Importe"])
    if not hasattr(page.session, "remaining_personas"):
        page.session.remaining_personas = [persona["nombre"] for persona in page.session.cuadrilla]

    INPUT_HEIGHT = 40
    # Nombre de la barbacoa
    barbacoa_field = ft.TextField(
        label="Nombre de la barbacoa", 
        width=400, 
        border_radius=10,
        height=INPUT_HEIGHT,
        content_padding=ft.padding.symmetric(5, 8),
        text_size=Sizes.XLARGE,
        )

    # Input de la persona
    persona_field = ft.Dropdown(
        label="Persona",
        options=[ft.dropdown.Option(persona) for persona in page.session.remaining_personas],
        #width=200,
        expand=True,
        border_radius=ft.border_radius.all(10),
        height=INPUT_HEIGHT,
        content_padding=ft.padding.symmetric(5, 8)
    )
    # Concepto de la compra
    concepto_field = ft.TextField(
        label="Concepto de gasto", 
        #width=persona_field.width, 
        expand=True,
        border_radius=10,
        height=INPUT_HEIGHT,
        content_padding=persona_field.content_padding
        )
    # Importe
    importe_field = ft.TextField(
        label="Importe", 
        #width=persona_field.width, 
        expand=True,
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

    # input_container__ = ft.Container(
    #     ft.Column(
    #         [
    #             ft.Row([barbacoa_field], alignment=ft.MainAxisAlignment.CENTER),
    #             ft.Row(
    #                 [persona_field, concepto_field, importe_field, add_expense_button],
    #                 alignment=ft.MainAxisAlignment.CENTER,
    #                 scroll=ft.ScrollMode.AUTO
    #             )
    #         ],
    #         horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    #         spacing=30
    #     ),
    #     #bgcolor="green",
    #     padding=10,
    # )
    input_container = ft.Container(
        ft.Column(
            [
                ft.Row(
                    [barbacoa_field], 
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                ft.ResponsiveRow(
                    controls=[
                        ft.Column(
                            controls=[persona_field], 
                            col={"xs": 12, "sm": 6, "md": 3},  # Se ajusta según el tamaño de la pantalla
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        ft.Column(
                            controls=[concepto_field], 
                            col={"xs": 12, "sm": 6, "md": 3},  # Se ajusta según el tamaño de la pantalla
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        ft.Column(
                            controls=[importe_field], 
                            col={"xs": 12, "sm": 6, "md": 3},  # Se ajusta según el tamaño de la pantalla
                            expand=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                        ft.Column(
                            controls=[add_expense_button], 
                            col={"xs": 12, "sm": 6, "md": 3},  # Se ajusta según el tamaño de la pantalla
                            expand=False,  # Los botones no necesitan expandirse,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=30
        ),
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
        rows=[],
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
        #width=600,
        #bgcolor=ft.colors.GREY_100,
        border=ft.border.all(width=1, color=ft.colors.GREY_300),
        padding=10,
        border_radius=ft.border_radius.all(20),
    )

    
    # Contenedor para los ajustes
    ajustes_section = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=20)
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
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=40
        ),
        #bgcolor="green",
        padding=20,
        border=expenses_table_container.border,
        border_radius=expenses_table_container.border_radius,
        width=420,
    )
    
    display_saved_barbacoas()
    # Añadir los elementos al layout de la página
    saved_bbq_container = ft.Container(
        ft.Column(
            [
                ft.Text("Barbacoas Guardadas", size=25, weight="bold"),
                listview_bbq_container
                ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        ),
        #bgcolor="blue",
    )
    layout = ft.Column(
        [
            ft.Column([titulo_ppal_container, input_container], horizontal_alignment="center"),
            ft.Column([ft.Text("Gastos", size=25, weight="bold"), expenses_table_container], horizontal_alignment="center"),
            ft.Column([ft.Text("Ajustes", size=25, weight="bold"), ajustes_container], horizontal_alignment="center"),
            saved_bbq_container
        ],
        spacing=50,
        horizontal_alignment="center",
        )
    page.add(layout)


if __name__ == '__main__':
    ft.app(target=main, assets_dir="assets")