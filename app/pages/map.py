# app/pages/map.py
from __future__ import annotations
from app.states.main_state import MainState
from pathlib import Path
import json
from typing import Optional, Tuple, List

import reflex as rx
import geopandas as gpd

# app/pages/map.py



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
    # --- Attribute table state ---
    attr_open: bool = False                 # Mostra/nascondi sezione tabella
    attr_columns: list[str] = []            # Intestazioni
    attr_rows: list[list[str]] = []         # Righe visibili (già pronte come lista di stringhe)
    attr_total: int = 0                     # Numero totale di righe
    attr_page: int = 1                      # Pagina corrente
    attr_page_size: int = 50                # Righe per pagina (modificabile)
    attr_error: str = ""                    # Messaggio errore eventuale

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
    async def build_map(self, _evt: rx.event.PointerEventInfo | None = None) -> None:
        
        from app.states.main_state import MainState 
        ms = await self.get_state(MainState)
        


        # 1) Project slug
        slug = self.project_slug or (ms.active_project_slug or "")
        id_field = ms.id_field_by_project.get(slug, "")
        if not slug:
            slug = ms.active_project_slug or ""

        if not slug:
            self.last_status = "No project selected."
            self.map_relpath = ""
            return


        # 2) Risolvi layer edifici
        p, kind = _resolve_buildings_vector(slug)
        if not p:
            self.last_status = "Nessun layer 'buildings' trovato."
            self.map_relpath = ""
            return

        #id_field = MainState.id_field_by_project.get(slug, "") or None

 #        3) Cartella output runtime
        out_root = rx.get_upload_dir()
        maps_dir = out_root / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)

        fname = f"map_{slug}_{self.reload_token + 1}.html"
        out_html = maps_dir / fname

        # --- NEW: collect overlay paths (se presenti) ---
        overlay_geojsons = []
        if isinstance(ms.pvgis_overlay_geojsons, list):
            for rel in ms.pvgis_overlay_geojsons:
                p = out_root / rel  # i rel path vengono dal servizio
                if p.exists():
                    overlay_geojsons.append(p)

        try:
            if kind == "shp":
                from app.services.folium_map import build_map_from_shp
                build_map_from_shp(p, out_html, id_field=id_field, overlay_geojsons=overlay_geojsons)
            elif kind == "geojson":
                from app.services.folium_map import build_map_from_geojson
                build_map_from_geojson(p, out_html, id_field=id_field, overlay_geojsons=overlay_geojsons)
            else:
                # ...

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

    

    @rx.event
    def open_attributes(self, _evt: rx.event.PointerEventInfo | None = None) -> None:
        """Mostra la tabella e carica la prima pagina."""
        self.attr_open = True
        self.load_attr_page(1)

    @rx.event
    def close_attributes(self, _evt: rx.event.PointerEventInfo | None = None) -> None:
        """Nasconde la tabella."""
        self.attr_open = False

    @rx.event
    def next_attr_page(self, _evt: rx.event.PointerEventInfo | None = None) -> None:
        """Pagina successiva."""
        if self.attr_page * self.attr_page_size < self.attr_total:
            self.load_attr_page(self.attr_page + 1)

    @rx.event
    def prev_attr_page(self, _evt: rx.event.PointerEventInfo | None = None) -> None:
        """Pagina precedente."""
        if self.attr_page > 1:
            self.load_attr_page(self.attr_page - 1)

    def _resolve_active_slug(self) -> str:
        """Slug progetto attivo o auto-selezione del primo disponibile."""
        slug = self.project_slug
        if not slug:
            self.available_projects = _list_available_projects()
            if self.available_projects:
                slug = self.available_projects[0]
                self.project_slug = slug
        return slug or ""
    
    @rx.var
    def attr_range_text(self) -> str:
        if self.attr_total == 0:
            return "Nessuna riga"
        start = (self.attr_page - 1) * self.attr_page_size + 1
        end = min(self.attr_page * self.attr_page_size, self.attr_total)
        return f"Righe {start}-{end} di {self.attr_total}"

    @rx.event
    def load_attr_page(self, page: int) -> None:
        """Carica gli attributi (solo colonne non geometriche) e ne mostra una pagina."""
        slug = self._resolve_active_slug()
        if not slug:
            self.attr_error = "No project selected."
            return

        p, kind = _resolve_buildings_vector(slug)
        if not p:
            self.attr_error = "No buildings layer found."
            return

        try:
            # 1) Leggi attributi
            gdf = gpd.read_file(str(p))
            df = gdf.drop(columns=["geometry"]) if "geometry" in gdf.columns else gdf

            # 2) Metadati e bound pagina
            total = len(df)
            self.attr_total = int(total)
            self.attr_page_size = 50 if self.attr_page_size <= 0 else self.attr_page_size
            max_page = max(1, (total + self.attr_page_size - 1) // self.attr_page_size)
            page = min(max(1, page), max_page)

            # 3) Slice
            start = (page - 1) * self.attr_page_size
            end = min(start + self.attr_page_size, total)

            # 4) Scrivi nello state (converti a str per robustezza)
            self.attr_columns = [str(c) for c in df.columns]
            self.attr_rows = df.iloc[start:end].astype(str).values.tolist()
            self.attr_page = page
            self.attr_error = ""

        except Exception as e:
            self.attr_error = f"Errore tabella: {e}"
            self.attr_rows = []
            self.attr_columns = []


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
            rx.button(
                "Tabella attributi",
                on_click=MapPageState.open_attributes,
                variant="surface",
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

        # SOTTO all'iframe della mappa
        rx.cond(
            MapPageState.attr_open,
            rx.card(
                rx.hstack(
                    rx.heading("Attribute table", size="5"),
                    rx.spacer(),
                    rx.button("Chiudi", on_click=MapPageState.close_attributes, variant="outline"),
                    spacing="3",
                    align="center",
                ),
                rx.cond(
                    MapPageState.attr_error != "",
                    rx.callout(MapPageState.attr_error, color_scheme="red"),
                    rx.fragment(
                        # Tabella
                        rx.box(
                            rx.el.table(
                                rx.el.thead(
                                    rx.el.tr(
                                        rx.foreach(
                                            MapPageState.attr_columns,
                                            lambda c: rx.el.th(rx.text(c))
                                        )
                                    )
                                ),
                                rx.el.tbody(
                                    rx.foreach(
                                        MapPageState.attr_rows,
                                        lambda row: rx.el.tr(
                                            rx.foreach(
                                                row,
                                                lambda v: rx.el.td(rx.text(v))
                                            )
                                        ),
                                    )
                                ),
                            ),
                            style={"overflowX": "auto", "maxHeight": "50vh"},
                            width="100%",
                        ),
                        # Paginazione
                        rx.hstack(
                            rx.button("« Prev", on_click=MapPageState.prev_attr_page,
                                    disabled=MapPageState.attr_page <= 1),
                            rx.text(MapPageState.attr_range_text),
                            rx.button(
                                "Next »",
                                on_click=MapPageState.next_attr_page,
                                disabled=(MapPageState.attr_page * MapPageState.attr_page_size) >= MapPageState.attr_total
                            ),
                            spacing="3",
                            align="center",
                        ),
                    ),
                ),
                spacing="4",
                width="100%",
            ),
        ),

        spacing="4",
        width="100%",
        on_mount=MapPageState.on_load,  # popola la select al primo render (runtime)
        
    )
