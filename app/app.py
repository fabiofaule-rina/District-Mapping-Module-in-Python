import reflex as rx
from app.states.main_state import MainState
from app.components.sidebar import sidebar
from app.pages.project import project_page
from app.pages.data_import import data_import_page
from app.pages.map import map_page
from app.pages.parameters import parameters_page
from app.pages.kpi import kpi_page
from app.pages.pvgis import pvgis_page

# app/app.py (esempio)
from app.db.init_db import ensure_db
ensure_db()


def index() -> rx.Component:
    return rx.el.div(
        sidebar(),
        rx.el.main(
            rx.match(
                MainState.active_page,
                ("project", project_page()),
                ("data_import", data_import_page()),
                ("map", map_page()),
                ("parameters", parameters_page()),
                ("kpi", kpi_page()),
                ("pvgis", pvgis_page()),
                project_page(),
            ),
            class_name="flex-1 p-8 bg-gray-50 overflow-y-auto",
        ),
        class_name="flex h-screen bg-white font-['Montserrat'] text-gray-800",
    )


app = rx.App(
    theme=rx.theme(appearance="light", accent_color="sky"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(index)