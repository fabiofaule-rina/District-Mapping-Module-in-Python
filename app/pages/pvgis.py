# app/pages/pvgis.py
import reflex as rx
from app.states.main_state import MainState
#from app.states.map_state import MapState



def building_result_card(building_id, res) -> rx.Component:
    return rx.vstack(
        rx.text("Edificio ", building_id, weight="bold"),
        rx.text("Energia annua: ", res["energy"], " kWh"),
        rx.text("Capacity factor: ", res["cf"]),
        rx.text("Produttività specifica: ", res["yield"], " kWh/kW"),
        rx.text("Potenza media: ", res["avg_power"], " W"),
        rx.text("Potenza massima: ", res["max_power"], " W"),
        rx.text("Ore equivalenti: ", res["peak_hours"], " h"),
        style={"marginBottom": "1em", "padding": "0.5em", "background": "#f7f7fa"},
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
        # --- Pannello mappa edifici: riuso dello stato di map.py ---
        rx.card(
            rx.hstack(
                rx.heading("Mappa edifici – Folium", size="5"),
                rx.spacer(),
                rx.button(
                    "Build / Refresh Map",
                    on_click=MainState.pvgis_generate_base_map,   # <--- richiama l'evento già pronto
                    variant="solid",
                    color_scheme="blue",
                ),
                spacing="3",
                align="center",
            ),
            rx.box(
                rx.el.iframe(

                    src = rx.cond(
                        MainState.pvgis_map_iframe != "",
                        MainState.pvgis_map_iframe,
                        "/404",
                    ),

                    style={"width": "100%", "height": "65vh", "border": "none"},
                ),
                width="100%",
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
                                building_result_card(res["building_id"], res),
                                rx.fragment(),
                            )

                        ),
                        # Grafico horizon (se disponibile)
                        rx.cond(
                            MainState.pvgis_horizon_map_html != "",
                            rx.card(
                                rx.heading("Grafico Horizon"),
                                rx.html(MainState.pvgis_horizon_map_html)
                            )
                        ),
                        # Esempio di grafico energetico (se disponibile)


                        rx.cond(
                            MainState.pvgis_plots.length() > 0,
                            rx.card(
                                rx.heading("Grafico energetico"),
                                rx.foreach(
                                    MainState.pvgis_plots,
                                    # ❗️Scelta safe: mostriamo come immagine. Se alcuni sono HTML, vedi nota sotto.
                                    lambda plot: rx.image(src=plot),
                                ),
                            ),
                        )

                    )
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