import reflex as rx
from app.states.main_state import MainState


def sidebar_item(name: str, icon: str, page: str) -> rx.Component:
    return rx.el.button(
        rx.icon(icon, class_name="w-5 h-5 mr-3"),
        rx.el.span(name),
        on_click=lambda: MainState.set_active_page(page),
        class_name=rx.cond(
            MainState.active_page == page,
            "flex items-center w-full text-left px-4 py-3 text-sm font-semibold text-white bg-sky-500 rounded-lg",
            "flex items-center w-full text-left px-4 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-100 rounded-lg transition-colors",
        ),
    )


def sidebar() -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            rx.icon("map-pin", class_name="w-8 h-8 text-sky-500"),
            rx.el.h1("DistrictMapper", class_name="text-2xl font-bold ml-2"),
            class_name="flex items-center p-4 border-b border-gray-200",
        ),
        rx.el.nav(
            sidebar_item("Progetto", "folder-kanban", "project"),
            sidebar_item("Dati & Import", "database", "data_import"),
            sidebar_item("Mappa", "map", "map"),
            sidebar_item("Parametri", "sliders-horizontal", "parameters"),
            sidebar_item("KPI & Esporta", "bar-chart-3", "kpi"),
            sidebar_item("PVGIS", "sun", "pvgis"),
            class_name="flex flex-col gap-2 p-4",
        ),
        class_name="w-64 bg-white border-r border-gray-200 flex flex-col",
    )