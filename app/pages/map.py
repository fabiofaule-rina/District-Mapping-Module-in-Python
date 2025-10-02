# app/pages/map.py
from __future__ import annotations
from pathlib import Path
import json
from typing import Optional, Tuple, List

import reflex as rx

# Servizio Folium esistente
from app.services.folium_map import build_map_from_shp

ASSETS_MAP = Path("assets/map.html")
PROJECTS_DIR = Path("data/projects")


# ---------- Utility ----------
def _list_available_projects() -> List[str]:
    """Slug progetti con un project.json valido."""
    if not PROJECTS_DIR.exists():
        return []
    slugs: List[str] = []
    for p in PROJECTS_DIR.iterdir():
        if p.is_dir() and (p / "project.json").exists():
            slugs.append(p.name)
    return sorted(slugs)


def _read_project_json(project_slug: str) -> Optional[dict]:
    pj = PROJECTS_DIR / project_slug / "project.json"
    if not pj.exists():
        return None
    try:
        return json.loads(pj.read_text(encoding="utf-8"))
    except Exception:
        return None


def _resolve_buildings_vector(project_slug: str) -> Tuple[Optional[Path], Optional[str]]:
    """
    Restituisce (path_vector, tipo) con tipo ∈ {"shp","geojson"} se trovato,
    altrimenti (None, None).
    Priorità:
      1) project.json.layers.{buildings_shp|buildings_geojson}
      2) scansione ricorsiva .shp / .geojson (sceglie il file più grande)
    """
    proj_dir = PROJECTS_DIR / project_slug
    if not proj_dir.exists():
        return None, None

    data = _read_project_json(project_slug) or {}
    layers = data.get("layers", {}) if isinstance(data, dict) else {}

    # 1) Metadati
    shp = layers.get("buildings_shp")
    if isinstance(shp, str) and shp:
        p = (proj_dir / shp) if not shp.startswith("/") else Path(shp)
        if p.exists() and p.suffix.lower() == ".shp":
            return p, "shp"

    gj = layers.get("buildings_geojson") or layers.get("buildings_geo")
    if isinstance(gj, str) and gj:
        p = (proj_dir / gj) if not gj.startswith("/") else Path(gj)
        if p.exists() and p.suffix.lower() == ".geojson":
            return p, "geojson"

    # 2) Scansione ricorsiva
    candidates_shp = list(proj_dir.rglob("*.shp"))
    candidates_gj = list(proj_dir.rglob("*.geojson")) + list(proj_dir.rglob("*.json"))

    if candidates_shp:
        shp_biggest = max(candidates_shp, key=lambda p: p.stat().st_size)
        return shp_biggest, "shp"

    if candidates_gj:
        valid_gj = []
        for c in candidates_gj:
            try:
                js = json.loads(c.read_text(encoding="utf-8", errors="ignore"))
                if js and isinstance(js, dict) and js.get("type") in {"FeatureCollection", "Feature"}:
                    valid_gj.append(c)
            except Exception:
                pass
        if valid_gj:
            gj_biggest = max(valid_gj, key=lambda p: p.stat().st_size)
            return gj_biggest, "geojson"

    return None, None


# ---------- State ----------
class MapPageState(rx.State):
    # Vars
    project_slug: str = ""
    available_projects: list[str] = []
    tile_provider: str = "OpenStreetMap"
    reload_token: int = 0
    last_status: str = ""
    # percorso relativo (dentro upload dir) del file HTML della mappa
    map_relpath: str = ""

    # Lifecycle
    def on_load(self):
        """All'avvio popola la lista progetti e seleziona il primo disponibile."""
        self.available_projects = _list_available_projects()
        if not self.project_slug and self.available_projects:
            self.project_slug = self.available_projects[0]

    # Mutators
    def set_project(self, slug: str):
        self.project_slug = slug

    # Computed
    @rx.var
    def map_src(self) -> str:
        # cambiando query forziamo il reload dell'iframe
        return f"/map.html?ver={self.reload_token}"

    # Event Handlers (wrapper -> runtime)
    # dentro class MapPageState(rx.State):

    @rx.event
    def build_map(self, _evt: rx.event.PointerEventInfo | None = None) -> None:
        # 1) Project slug
        slug = self.project_slug
        if not slug:
            self.available_projects = _list_available_projects()
            if self.available_projects:
                slug = self.available_projects[0]
                self.project_slug = slug
            else:
                self.last_status = "No projects found."
                self.map_relpath = ""
                return

        # 2) Risolvi layer edifici
        p, kind = _resolve_buildings_vector(slug)
        if not p:
            self.last_status = "Nessun layer 'buildings' trovato."
            self.map_relpath = ""
            return

        # 3) Directory di output runtime (NO assets/)
        out_root = rx.get_upload_dir()           # Path backend "pubblico" a runtime
        maps_dir = out_root / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)

        # filename unico per bustare la cache (incorporo slug e contatore)
        fname = f"map_{slug}_{self.reload_token + 1}.html"
        out_html = maps_dir / fname

        try:
            if kind == "shp":
                build_map_from_shp(p, out_html)
            elif kind == "geojson":
                try:
                    from app.services.folium_map import build_map_from_geojson  # type: ignore
                except Exception:
                    self.last_status = "GeoJSON trovato, ma manca build_map_from_geojson() in folium_map."
                    self.map_relpath = ""
                    return
                build_map_from_geojson(p, out_html)
            else:
                self.last_status = f"Tipo layer non supportato: {kind}"
                self.map_relpath = ""
                return

            # 4) Aggiorna stato e src per l'iframe
            self.map_relpath = f"maps/{fname}"   # <-- relativo alla upload dir
            self.reload_token += 1
            self.last_status = f"Map built for '{slug}' ({kind})."

        except Exception as e:
            self.last_status = f"Errore: {e}"
            self.map_relpath = ""
            return

# ---------- UI ----------
def map_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Mappe progetto", size="6"),
        rx.text("Base: OpenStreetMap • Overlay: Buildings (shp/geojson)"),
        rx.hstack(
            rx.select(
                MapPageState.available_projects,
                placeholder="Seleziona progetto…",
                value=MapPageState.project_slug,
                on_change=MapPageState.set_project,
                width="280px",
            ),
            rx.button(
                "Build / Refresh Map",
                on_click=MapPageState.build_map,   # <-- riferimento, non chiamata
                variant="solid",
                color_scheme="blue",
            ),
            rx.badge(MapPageState.last_status, color_scheme="gray", variant="soft"),
            spacing="3",
            wrap="wrap",
        ),
        rx.box(
            rx.el.iframe(
                    src=rx.cond(
                        MapPageState.map_relpath != "",
                        rx.get_upload_url(MapPageState.map_relpath),  # URL runtime pubblico
                        "/404"
                    ),
                    style={"width": "100%", "height": "70vh", "border": "none"},
                ),
                width="100%",
            ),
        spacing="4",
        width="100%",
        on_mount=MapPageState.on_load,  # popola la select al primo render (runtime)
    )
