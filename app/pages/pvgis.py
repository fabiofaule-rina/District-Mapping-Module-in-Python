import reflex as rx
from app.states.main_state import MainState


def pvgis_page() -> rx.Component:
    return rx.container(
        rx.heading("Analisi PVGIS", size="4"),
        rx.text("Analizza i dati del progetto attivo tramite i moduli PVGIS. Visualizza risultati energetici, grafici e mappa orizzonte."),
        rx.divider(),
        rx.button(
            "Avvia Analisi PVGIS",
            on_click=MainState.start_pvgis_analysis,
            color="primary",
            margin_y="1em"
        ),
        rx.cond(
            (MainState.pvgis_progress > 0) & (MainState.pvgis_progress < 100),
            rx.card(
                rx.text(f"Avanzamento: {MainState.pvgis_progress}%"),
                rx.progress(value=MainState.pvgis_progress, max=100, color="blue"),
                style={"marginBottom": "1em"}
            ),
            None
        ),
        rx.cond(
            MainState.pvgis_error != "",
            rx.card(
                rx.text(MainState.pvgis_error, color="red"),
                style={"background": "#ffeaea", "border": "1px solid #ffcccc"}
            ),
            None
        ),
        rx.cond(
            MainState.pvgis_results != {},
            rx.card(
                rx.heading("Risultati energetici"),
                rx.foreach(
                    MainState.pvgis_results.items(),
                    lambda item: rx.vstack(
                        rx.text(f"Edificio {item[0]}", weight="bold"),
                        rx.text(f"Energia annua: {item[1]['annual_metrics']['energy_kwh']} kWh"),
                        rx.text(f"Capacity factor: {item[1]['annual_metrics']['capacity_factor']:.3f}"),
                        rx.text(f"Produttività specifica: {item[1]['annual_metrics']['specific_yield_kwh_kw']} kWh/kW"),
                        rx.text(f"Potenza media: {item[1]['annual_metrics']['avg_power_w']} W"),
                        rx.text(f"Potenza massima: {item[1]['annual_metrics']['max_power_w']} W"),
                        rx.text(f"Ore equivalenti: {item[1]['annual_metrics']['peak_hours_h']} h"),
                        style={"marginBottom": "1em", "padding": "0.5em", "background": "#f7f7fa"}
                    )
                )
            ),
            None
        ),
        rx.cond(
            MainState.pvgis_plots != [],
            rx.card(
                rx.heading("Grafici energetici"),
                rx.foreach(
                    MainState.pvgis_plots,
                    lambda plot: rx.cond(
                        plot.endswith(".html"),
                        rx.html(plot),
                        rx.image(src=plot)
                    )
                )
            ),
            None
        ),
        rx.cond(
            MainState.pvgis_horizon_map_html != "",
            rx.card(
                rx.heading("Mappa Orizzonte (primo edificio)"),
                rx.html(MainState.pvgis_horizon_map_html)
            ),
            None
        ),
        padding="2em"
    )
