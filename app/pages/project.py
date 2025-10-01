import reflex as rx
from app.states.project_state import ProjectState, REQUIRED_BUILDING_FIELDS

from app.models import COUNTRY_OPTIONS


def project_metadata_card() -> rx.Component:
    return rx.el.div(
        rx.el.h2("1. Crea Progetto", class_name="text-xl font-bold text-gray-800 mb-4"),
        rx.el.div(
            rx.el.label(
                "Nome Progetto", class_name="text-sm font-medium text-gray-700 mb-1"
            ),
            rx.el.input(
                placeholder="Es. Analisi Quartiere Centro",
                on_change=ProjectState.set_project_name,
                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500",
            ),
            class_name="mb-4",
        ),
        rx.el.div(
            rx.el.label(
                "Descrizione (Opzionale)",
                class_name="text-sm font-medium text-gray-700 mb-1",
            ),
            rx.el.textarea(
                placeholder="Es. Valutazione del potenziale di teleriscaldamento...",
                on_change=ProjectState.set_project_description,
                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500",
            ),
            class_name="mb-4",
        ),
        rx.el.div(
            rx.el.label(
                "Paese di destinazione",
                class_name="text-sm font-medium text-gray-700 mb-1",
            ),
            rx.el.select(
                rx.foreach(
                    COUNTRY_OPTIONS,
                    lambda country: rx.el.option(
                        country["label"], value=country["value"]
                    ),
                ),
                default_value=ProjectState.country,
                #on_change=ProjectState.set_country,
                on_change=ProjectState.set_country_code,
                class_name="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500",
            ),
        ),
        class_name="bg-white p-6 rounded-lg border border-gray-200",
    )


def building_layer_upload_card() -> rx.Component:
    return rx.el.div(
        rx.el.h2(
            "2. Carica Layer Edifici", class_name="text-xl font-bold text-gray-800 mb-4"
        ),
        rx.upload.root(
            rx.el.div(
                rx.icon("cloud_upload", class_name="w-10 h-10 text-gray-400"),
                rx.el.p(
                    "Trascina qui i file o clicca per selezionare",
                    class_name="text-sm text-gray-600",
                ),
                rx.el.p(".shp, .geojson, .gpkg", class_name="text-xs text-gray-500"),
                class_name="flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-300 rounded-lg hover:bg-gray-50 transition-colors",
            ),
            id="upload-buildings",
            multiple=False,
            accept={
                "application/zip": [".zip"],
                "application/geo+json": [".geojson", ".json"],
                "application/x-sqlite3": [".gpkg"],
            },
            class_name="w-full cursor-pointer",
        ),
        rx.el.button(
            rx.icon("upload", class_name="mr-2 h-4 w-4"),
            "Carica e Analizza",
            on_click=ProjectState.handle_upload(rx.upload_files(upload_id="upload-buildings")),
            is_loading=ProjectState.uploading,
            class_name="mt-4 w-full flex items-center justify-center px-4 py-2 bg-sky-500 text-white font-semibold rounded-lg hover:bg-sky-600 disabled:opacity-50",
            disabled=rx.selected_files("upload-buildings").length() == 0,
        ),
        rx.cond(
            rx.selected_files("upload-buildings").length() > 0,
            rx.el.div(
                rx.el.p("File selezionato:", class_name="font-semibold"),
                rx.foreach(
                    rx.selected_files("upload-buildings"),
                    lambda file: rx.el.div(
                        file,
                        class_name="text-sm text-gray-700 bg-gray-100 p-2 rounded-md",
                    ),
                ),
                class_name="mt-4 text-sm",
            ),
        ),
        class_name="bg-white p-6 rounded-lg border border-gray-200",
    )


def column_mapping_card() -> rx.Component:
    def mapping_row(field_key: str, field_name: str):
        return rx.el.div(
            rx.el.label(field_name, class_name="font-medium text-gray-700"),
            rx.el.select(
                rx.el.option("Seleziona colonna...", value="", disabled=True),
                rx.foreach(
                    ProjectState.source_columns,
                    lambda col: rx.el.option(col, value=col),
                ),
                on_change=lambda selected_col: ProjectState.update_mapping(
                    field_key, selected_col
                ),
                default_value=ProjectState.column_mapping[field_key],
                class_name="w-full mt-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500",
            ),
            class_name="grid grid-cols-2 items-center gap-4",
        )

    return rx.el.div(
        rx.el.h2(
            "3. Mappa Campi Obbligatori",
            class_name="text-xl font-bold text-gray-800 mb-4",
        ),
        rx.el.p(
            "Associa le colonne del tuo file sorgente ai campi standard richiesti.",
            class_name="text-sm text-gray-600 mb-4",
        ),
        rx.el.div(
            rx.foreach(
                REQUIRED_BUILDING_FIELDS,
                lambda field_key: mapping_row(field_key, field_key),
            ),
            class_name="space-y-4",
        ),
        class_name="bg-white p-6 rounded-lg border border-gray-200",
    )


def data_preview_card() -> rx.Component:
    return rx.el.div(
        rx.el.h2(
            "4. Anteprima Dati (prime 20 righe)",
            class_name="text-xl font-bold text-gray-800 mb-4",
        ),
        rx.el.div(
            rx.el.table(
                rx.el.thead(
                    rx.el.tr(
                        rx.foreach(
                            ProjectState.source_columns,
                            lambda col: rx.el.th(
                                col,
                                class_name="px-4 py-2 text-left text-sm font-semibold text-gray-600",
                            ),
                        ),
                        class_name="bg-gray-50",
                    )
                ),
                rx.el.tbody(
                    rx.foreach(
                        ProjectState.preview_data,
                        lambda row: rx.el.tr(
                            rx.foreach(
                                ProjectState.source_columns,
                                lambda col: rx.el.td(
                                    row[col].to_string(),
                                    class_name="px-4 py-2 text-sm text-gray-700",
                                ),
                            ),
                            class_name="border-b border-gray-200",
                        ),
                    )
                ),
                class_name="w-full border-collapse",
            ),
            class_name="overflow-x-auto rounded-lg border border-gray-200",
        ),
        class_name="bg-white p-6 rounded-lg border border-gray-200",
    )


def project_page() -> rx.Component:
    return rx.el.div(
        rx.el.h1(
            "Creazione Progetto e Upload Dati",
            class_name="text-3xl font-bold text-gray-900 mb-6",
        ),
        rx.el.div(
            project_metadata_card(),
            building_layer_upload_card(),
            rx.cond(
                ProjectState.file_name,
                rx.el.div(
                    column_mapping_card(), data_preview_card(), class_name="space-y-6"
                ),
            ),
            rx.el.div(
                rx.el.button(
                    "Conferma e Crea Progetto",
                    on_click=ProjectState.create_project,
                    disabled=~ProjectState.is_project_creatable,
                    class_name="w-full px-6 py-3 bg-green-600 text-white font-bold rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors",
                ),
                class_name="mt-6 bg-white p-6 rounded-lg border border-gray-200",
            ),
            class_name="space-y-6",
        ),
        class_name="w-full",
    )