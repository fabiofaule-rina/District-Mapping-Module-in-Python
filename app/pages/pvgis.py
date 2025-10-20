# app/pages/pvgis.py
import reflex as rx
from app.states.main_state import MainState


def building_result_card(building_id: str, result: dict) -> rx.Component:
    """Crea una card per un singolo edificio (workaround per typing)."""
    return rx.vstack(
        rx.text(f"Edificio {building_id}", weight="bold"),
        rx.text(f"Energia annua: {result['annual_metrics']['energy_kwh']} kWh"),
        rx.text(f"Capacity factor: {result['annual_metrics']['capacity_factor']:.3f}"),
        rx.text(f"Produttività specifica: {result['annual_metrics']['specific_yield_kwh_kw']} kWh/kW"),
        rx.text(f"Potenza media: {result['annual_metrics']['avg_power_w']} W"),
        rx.text(f"Potenza massima: {result['annual_metrics']['max_power_w']} W"),
        rx.text(f"Ore equivalenti: {result['annual_metrics']['peak_hours_h']} h"),
        style={"marginBottom": "1em", "padding": "0.5em", "background": "#f7f7fa"}
    )


def pvgis_page() -> rx.Component:
    return rx.container(
        rx.heading("Analisi PVGIS", size="4"),
        rx.text("Analizza i dati del progetto attivo tramite i moduli PVGIS. Visualizza risultati energetici, grafici e mappa orizzonte."),
        rx.divider(),

        rx.hstack(
            rx.button(
                "Avvia Analisi PVGIS",
                on_click=MainState.start_pvgis_analysis,
                color="primary",
                margin_y="1em"
            ),
        ),

        # Genera la mappa base all'avvio della pagina
        rx.script("window.addEventListener('DOMContentLoaded', function() { window.dispatchEvent(new CustomEvent('pvgis_generate_base_map')); });"),

        # Progress bar
        rx.cond(
            MainState.pvgis_running,
            rx.card(
                rx.text("Calcolo in corso... Chiamata PVGIS in esecuzione."),
                rx.progress(value=MainState.pvgis_progress, max=100, color="blue"),
                style={"marginBottom": "1em"}
            ),
        ),

        # Error message
        rx.cond(
            MainState.pvgis_error != "",
            rx.card(
                rx.text(MainState.pvgis_error, color="red"),
                style={"background": "#ffeaea", "border": "1px solid #ffcccc"}
            ),
        ),

        # Dropdown per selezionare il building
        rx.cond(
            MainState.pvgis_results_ui.length() > 0,
            rx.card(
                rx.heading("Risultati energetici"),
                rx.select(
                    items=MainState.pvgis_building_ids,
                    value=MainState.selected_building,
                    on_change=MainState.set_selected_building,
                    placeholder="Seleziona edificio...",
                    style={"marginBottom": "1em"}
                ),
                # Mostra solo il building selezionato
                rx.cond(
                    MainState.selected_building != "",
                    rx.vstack(
                        rx.foreach(
                            MainState.pvgis_results_ui,
                            lambda res: rx.cond(
                                res["building_id"] == MainState.selected_building,
                                rx.vstack(
                                    rx.text(f"Edificio {res['building_id']}", weight="bold"),
                                    rx.text(f"Energia annua: {res['energy']} kWh"),
                                    rx.text(f"Capacity factor: {res['cf']}"),
                                    rx.text(f"Produttività specifica: {res['yield']} kWh/kW"),
                                    rx.text(f"Potenza media: {res['avg_power']} W"),
                                    rx.text(f"Potenza massima: {res['max_power']} W"),
                                    rx.text(f"Ore equivalenti: {res['peak_hours']} h"),
                                    style={"marginBottom": "1em", "padding": "0.5em", "background": "#f7f7fa"}
                                ),
                                rx.fragment()
                            )
                        ),
                        # Grafico horizon (se disponibile)
                        rx.cond(
                            MainState.pvgis_horizon_map_html != "",
                            rx.card(
                                rx.heading("Grafico Horizon"),
                                rx.html(MainState.pvgis_horizon_map_html)
                            ),
                        ),
                        # Esempio di grafico energetico (se disponibile)
                        rx.cond(
                            MainState.pvgis_plots.length() > 0,
                            rx.card(
                                rx.heading("Grafico energetico"),
                                rx.foreach(
                                    MainState.pvgis_plots,
                                    lambda plot: rx.cond(
                                        plot.contains(".html"),
                                        rx.html(plot),
                                        rx.image(src=plot)
                                    )
                                )
                            ),
                        ),
                    ),
                ),
            ),
        ),

        # Mappa interattiva degli edifici con potenziali colorati (Folium, link esterno)
        rx.cond(
            MainState.pvgis_map_iframe != "",
            rx.card(
                rx.heading("Mappa edifici - Potenziale FV"),
                rx.link(
                    "Apri mappa interattiva in una nuova scheda",
                    href=MainState.pvgis_map_iframe,
                    is_external=True,
                    style={"fontWeight": "bold", "fontSize": "1.2em", "marginTop": "2em"}
                )
            ),
            rx.card(
                rx.heading("Mappa edifici - Potenziale FV"),
                rx.text("La mappa non è ancora disponibile. Esegui l'analisi o verifica la presenza di dati.", style={"color": "#888", "marginTop": "2em"})
            )
        ),

        padding="2em"
    )