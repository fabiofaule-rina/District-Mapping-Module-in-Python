# app/pages/map.py
from __future__ import annotations
from pathlib import Path
import json
import reflex as rx
from app.services.folium_map import build_map_from_shp

ASSETS_MAP = Path("assets/map.html")

def _current_project_buildings_shp() -> Path | None:
    # TODO: leggere il project_slug dallo state globale; per ora rimane hard-coded
    project_slug = "genova-center"
    proj_json = Path(f"data/projects/{project_slug}/project.json")
    if not proj_json.exists():
        return None
    data = json.loads(proj_json.read_text(encoding="utf-8"))
    shp = data["layers"]["buildings_shp"]
    return Path(shp)

# Mini-state per forzare il reload dell'iframe dopo il build
class MapPageState(rx.State):
    reload_token: int = 0

    @rx.var
    def map_src(self) -> str:
        # Cambiando la query string, l'iframe ricarica sempre la mappa aggiornata
        return f"/map.html?ver={self.reload_token}"

    def bump(self):
        self.reload_token += 1

def map_page() -> rx.Component:
    def _build():
        shp = _current_project_buildings_shp()
        if not shp:
            return rx.toast.error(
                "No project/layer found. Finalize a project with a buildings shapefile first."
            )
        try:
            ASSETS_MAP.parent.mkdir(parents=True, exist_ok=True)
            build_map_from_shp(shp, ASSETS_MAP)
            # Forza il reload dell'iframe + toast
            return [MapPageState.bump, rx.toast.success("Map built.")]
        except Exception as e:
            return rx.toast.error(str(e))

    return rx.vstack(
        rx.heading("Map", size="6"),
        rx.text("Base: OpenStreetMap • Overlay: Buildings (from shapefile)"),
        rx.button(
            "Build / Refresh Map",
            on_click=_build,  # ritorna un event spec valido
            variant="solid",
            color_scheme="blue",
        ),
        rx.box(
            # Opzione A: iframe come elemento nativo (consigliata)
            rx.el.iframe(
                src=MapPageState.map_src,
                style={"width": "100%", "height": "70vh", "border": "none"},
            ),
            # Opzione B (fallback): usare HTML raw (scommentare se A non è disponibile)
            # rx.html(f'{MapPageState.map_src}</iframe>'),
            width="100%",
        ),
        spacing="4",
        width="100%",
    )