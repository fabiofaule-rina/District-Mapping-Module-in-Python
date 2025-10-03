# app/pages/data_import.py
import reflex as rx
from app.states.main_state import MainState, PLANHEAT_FIELDS


def _field_row(label: str, key: str, required: bool) -> rx.Component:
    """Riga: etichetta + select (colonne disponibili) + stellina se required."""
    # Selettore: lega al var "flat" corrispondente
    value_var = {
        "id": MainState.map_id,
        "buildingUse": MainState.map_buildingUse,
        "year": MainState.map_year,
        "gfa": MainState.map_gfa,
        "roof": MainState.map_roof,
        "height": MainState.map_height,
        "floors": MainState.map_floors,
    }[key]

    return rx.hstack(
        rx.box(
            rx.text(label),
            rx.badge("obbl.", color_scheme="red", variant="soft") if required else rx.fragment(),
            width="40%",
            style={"display": "flex", "gap": "0.5rem", "alignItems": "center"},
        ),
        rx.select(
            MainState.di_available_columns,
            placeholder="Seleziona colonna…",
            value=value_var,
            on_change=lambda col, k=key: MainState.di_set_map_field(k, col),  # k fissata
            width="320px",
        ),
        spacing="3",
        align="center",
        wrap="wrap",
    )


def planheat_mapping_card() -> rx.Component:
    rows = [
        _field_row(label, key, required)
        for (key, label, required, _typ) in PLANHEAT_FIELDS
    ]
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Mappatura campi Planheat", size="5"),
                rx.spacer(),
                rx.badge(MainState.planheat_mapping_badge, variant="soft", color_scheme="gray"),
                spacing="3",
                align="center",
            ),
            rx.text(
                "Collega ogni campo richiesto da Planheat alla colonna corrispondente nella attribute table "
                "del progetto attivo.",
                size="3",
                color="gray",
            ),
            *rows,
            rx.hstack(
                rx.button("Valida", on_click=MainState.di_validate_planheat_mapping, variant="outline"),
                rx.button("Salva mappatura", on_click=MainState.di_save_planheat_mapping, variant="solid", color_scheme="blue"),
                rx.spacer(),
                spacing="3",
            ),
            rx.cond(MainState.di_error != "", rx.callout(MainState.di_error, color_scheme="red"), rx.fragment()),
            rx.cond(MainState.di_info != "", rx.callout(MainState.di_info, color_scheme="green"), rx.fragment()),
            spacing="4",
        ),
        width="100%",
    )


def id_selector_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Colonna ID Building (per mappa e mappatura)", size="5"),
                rx.spacer(),
                rx.button("Ricarica colonne", on_click=MainState.di_refresh_columns, variant="outline"),
                spacing="3",
                align="center",
            ),
            rx.hstack(
                rx.text("Progetto attivo:", weight="bold"),
                rx.select(
                    MainState.projects,
                    placeholder="Seleziona progetto…",
                    value=MainState.active_project_slug,
                    on_change=MainState.di_set_project_and_refresh,
                    width="320px",
                ),
                spacing="3",
                wrap="wrap",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                MainState.di_error != "",
                rx.callout(MainState.di_error, color_scheme="red"),
                rx.vstack(
                    rx.text("Scegli la colonna che identifica univocamente ogni building."),
                    rx.select(
                        MainState.di_available_columns,
                        placeholder="Seleziona colonna…",
                        value=MainState.di_selected_id_field,
                        on_change=MainState.di_set_selected_id_field,
                        width="320px",
                    ),
                    rx.hstack(
                        rx.button("Salva", on_click=MainState.di_save_id_field, variant="solid", color_scheme="blue"),
                        rx.badge(MainState.di_id_badge_text, color_scheme="gray", variant="soft"),
                        spacing="3",
                    ),
                    spacing="3",
                ),
            ),
            rx.cond(MainState.di_info != "", rx.callout(MainState.di_info, color_scheme="green"), rx.fragment()),
            spacing="4",
        ),
        width="100%",
    )


def data_import_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Importazione Dati", size="7"),
        id_selector_card(),
        planheat_mapping_card(),
        spacing="6",
        width="100%",
        on_mount=MainState.di_init,
    )