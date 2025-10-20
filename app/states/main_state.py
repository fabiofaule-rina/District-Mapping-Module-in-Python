# app/states/main_state.py
from __future__ import annotations
from pathlib import Path
from typing import Literal, Dict
import json
import pandas as pd
import geopandas as gpd  # modulo-level, non dentro la classe
import reflex as rx

from app.services.pv_overlay import build_pv_geojson_layers

# --- Costanti & tipi ---
PROJECTS_DIR = Path("data/projects")
PageLiteral = Literal["project", "data_import", "map", "parameters", "kpi", "pvgis"]

# Campi Planheat richiesti/facoltativi: (key, label, required, expected_type)
PLANHEAT_FIELDS = [
    ("id", "ID", True, "any"),
    ("buildingUse", "buildingUse", True, "any"),
    ("year", "Year of construction", False, "int"),
    ("gfa", "Gross floor Area", True, "float"),
    ("roof", "Roof Area", False, "float"),
    ("height", "Height", False, "float"),
    ("floors", "Num of floors", False, "int"),
]


class MainState(rx.State):
    # --- PROGETTI ---
    projects: list[str] = []
    di_available_uses: list[str] = []          # unique values da buildingUse nello shapefile
    di_planheat_uses: list[str] = []           # usi standard Planheat da DB
    use_map_by_project: dict[str, dict[str, str]] = {}  # mappatura salvata per progetto

    # --- ID field per progetto ---
    id_field_by_project: dict[str, str] = {}

    # Supporto UI "Dati e Import"
    di_available_columns: list[str] = []  # colonne non-geometry trovate per il progetto selezionato
    di_selected_id_field: str = ""
    di_error: str = ""
    di_info: str = ""  # messaggi informativi (validazione/salvataggio)

    # --- Mappatura Planheat per progetto: slug -> {key: column} ---
    planheat_map_by_project: dict[str, dict[str, str]] = {}

    # --- Binding UI "flat" per i 7 campi ---
    map_id: str = ""
    map_buildingUse: str = ""
    map_year: str = ""
    map_gfa: str = ""
    map_roof: str = ""
    map_height: str = ""
    map_floors: str = ""

    # Stato app
    active_project_slug: str = ""
    active_page: PageLiteral = "project"

    # Overlay generati lato PVGIS/foglio mappa
    pvgis_overlay_geojsons: list[str] = []

    # --- Navigazione ---
    @rx.event
    def set_active_page(self, page: PageLiteral):
        self.active_page = page

    # --- Helpers ---
    def _list_projects(self) -> list[str]:
        if not PROJECTS_DIR.exists():
            return []
        return sorted(
            [
                p.name
                for p in PROJECTS_DIR.iterdir()
                if p.is_dir() and (p / "project.json").exists()
            ]
        )

    def _resolve_project_shp(self, slug: str) -> Path | None:
        proj_dir = PROJECTS_DIR / slug
        if not proj_dir.exists():
            return None
        shp_list = list(proj_dir.rglob("*.shp"))
        return max(shp_list, key=lambda p: p.stat().st_size) if shp_list else None

    def _mapping_path(self, slug: str) -> Path:
        return PROJECTS_DIR / slug / "planheat_mapping.json"

    # --- Computed ---
    @rx.var
    def di_id_badge_text(self) -> str:
        if self.active_project_slug and self.active_project_slug in self.id_field_by_project:
            return f"ID attuale: {self.id_field_by_project[self.active_project_slug]}"
        return "Nessuna colonna salvata"

    @rx.var
    def planheat_mapping_badge(self) -> str:
        slug = self.active_project_slug
        if not slug:
            return "Nessuna mappatura salvata"
        m = self.planheat_map_by_project.get(slug, {})
        done = sum(1 for k, _, req, _ in PLANHEAT_FIELDS if m.get(k))
        total = len(PLANHEAT_FIELDS)
        return f"Mappatura: {done}/{total} campi"

    # --- Init / selezione progetto ---
    @rx.event
    def di_init(self) -> None:
        """Popola la lista progetti e carica le colonne per il progetto attivo."""
        self.projects = self._list_projects()
        if not self.active_project_slug:
            self.active_project_slug = self.projects[0] if self.projects else ""
        self.di_refresh_columns()

    @rx.event
    def set_active_project(self, slug: str) -> None:
        self.active_project_slug = slug

    @rx.event
    def di_set_project_and_refresh(self, slug: str) -> None:
        self.active_project_slug = slug
        self.di_refresh_columns()

    @rx.event
    def di_refresh_columns(self) -> None:
        """
        Legge le colonne non geometriche e imposta selezioni ID e mappatura Planheat
        per il progetto attivo.
        """
        slug = self.active_project_slug
        self.di_info = ""
        if not slug:
            self.di_error = "Seleziona un progetto."
            self.di_available_columns = []
            self.di_selected_id_field = ""
            return

        shp = self._resolve_project_shp(slug)
        if not shp:
            self.di_error = "Nessuno shapefile 'buildings' trovato."
            self.di_available_columns = []
            self.di_selected_id_field = ""
            return

        try:
            gdf = gpd.read_file(str(shp))
            cols = [c for c in gdf.columns if c != "geometry"] if "geometry" in gdf.columns else list(gdf.columns)

            # Selezione colonna ID (preferisci quella salvata o euristica)
            saved = self.id_field_by_project.get(slug, "")
            if saved and saved in cols:
                chosen = saved
            else:
                lower = {c.lower(): c for c in cols}
                guess = None
                for k in ["building_id", "b_id", "id", "fid", "objectid", "objectid_1", "gid"]:
                    if k in lower:
                        guess = lower[k]
                        break
                chosen = guess or (cols[0] if cols else "")

            self.di_available_columns = cols
            self.di_selected_id_field = chosen
            self.di_error = ""

            # 2) Mappatura Planheat: carica da memoria o da file; popola i 7 campi UI
            mapping = self.planheat_map_by_project.get(slug, {})
            mp_path = self._mapping_path(slug)
            if not mapping and mp_path.exists():
                try:
                    loaded = json.loads(mp_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        mapping = loaded
                        self.planheat_map_by_project[slug] = mapping
                except Exception:
                    pass
            def _sel(key: str, fallback: str = "") -> str:
                v = mapping.get(key, "")
                return v if v in cols else fallback

            self.map_id = _sel("id", chosen)
            self.map_buildingUse = _sel("buildingUse")
            self.map_year = _sel("year")
            self.map_gfa = _sel("gfa")
            self.map_roof = _sel("roof")
            self.map_height = _sel("height")
            self.map_floors = _sel("floors")

        except Exception as e:
            self.di_error = f"Errore lettura attributi: {e}"
            self.di_available_columns = []
            self.di_selected_id_field = ""

    # --- Aggiornamento singoli campi mappatura ---
    @rx.event
    def di_set_map_field(self, key: str, col: str) -> None:
        if key == "id":
            self.map_id = col
        elif key == "buildingUse":
            self.map_buildingUse = col
        elif key == "year":
            self.map_year = col
        elif key == "gfa":
            self.map_gfa = col
        elif key == "roof":
            self.map_roof = col
        elif key == "height":
            self.map_height = col
        elif key == "floors":
            self.map_floors = col

    @rx.event
    def di_set_selected_id_field(self, col: str) -> None:
        self.di_selected_id_field = col

    @rx.event
    def di_save_id_field(self) -> None:
        """Salva solo il campo ID 'semplice' e sincronizza 'map_id' UI."""
        slug = self.active_project_slug
        if not slug or not self.di_selected_id_field:
            self.di_error = "Seleziona un progetto e una colonna ID."
            return
        self.id_field_by_project[slug] = self.di_selected_id_field
        # sync anche mappatura Planheat (id)
        self.map_id = self.di_selected_id_field
        mp = self.planheat_map_by_project.get(slug, {})
        mp["id"] = self.map_id
        self.planheat_map_by_project[slug] = mp
        self.di_info = "Colonna ID salvata."
        self.di_error = ""

    @rx.event
    def di_save_planheat_mapping(self) -> None:
        """
        Salva la mappatura Planheat per il progetto (memoria + file JSON)
        e sincronizza id_field_by_project.
        """
        slug = self.active_project_slug
        if not slug:
            self.di_error = "Seleziona un progetto."
            return

        mapping = {
            "id": self.map_id,
            "buildingUse": self.map_buildingUse,
            "year": self.map_year,
            "gfa": self.map_gfa,
            "roof": self.map_roof,
            "height": self.map_height,
            "floors": self.map_floors,
        }

        # requisiti minimi
        missing = []
        for key, label, required, _ in PLANHEAT_FIELDS:
            if required and not mapping.get(key):
                missing.append(label)
        if missing:
            self.di_error = "Mancano campi obbligatori: " + ", ".join(missing)
            self.di_info = ""
            return

        # persist in memoria
        self.planheat_map_by_project[slug] = mapping
        # sincronizza anche l'ID usato dalla mappa
        if mapping.get("id"):
            self.id_field_by_project[slug] = mapping["id"]

        # persist su file del progetto
        try:
            mp_path = self._mapping_path(slug)
            mp_path.parent.mkdir(parents=True, exist_ok=True)
            mp_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
            self.di_error = ""
            self.di_info = "Mappatura Planheat salvata."
        except Exception as e:
            self.di_error = f"Errore salvataggio mappatura: {e}"
            self.di_info = ""

    @rx.event
    def di_validate_planheat_mapping(self) -> None:
        """Controlli base: esistenza colonne e numericità ragionevole dove attesa."""
        slug = self.active_project_slug
        if not slug:
            self.di_error = "Seleziona un progetto."
            return

        shp = self._resolve_project_shp(slug)
        if not shp:
            self.di_error = "Nessuno shapefile 'buildings' trovato."
            return
        mapping = {
            "id": self.map_id,
            "buildingUse": self.map_buildingUse,
            "year": self.map_year,
            "gfa": self.map_gfa,
            "roof": self.map_roof,
            "height": self.map_height,
            "floors": self.map_floors,
        }

        try:
            gdf = gpd.read_file(str(shp))
            cols = set([c for c in gdf.columns if c != "geometry"])

            # 1) esistenza
            not_found = [lbl for key, lbl, _, _ in PLANHEAT_FIELDS if mapping.get(key) and mapping[key] not in cols]
            if not_found:
                self.di_error = "Colonne non trovate: " + ", ".join(not_found)
                self.di_info = ""
                return

            # 2) numericità per alcuni campi (sample)
            numeric_keys = [("year", "int"), ("gfa", "float"), ("roof", "float"), ("height", "float"), ("floors", "int")]
            bad = []
            sample = gdf.sample(min(500, len(gdf)), random_state=42) if len(gdf) > 500 else gdf
            for key, expected in numeric_keys:
                col = mapping.get(key)
                if not col:
                    continue
                s = pd.to_numeric(sample[col], errors="coerce")
                ratio = float(s.notna().mean()) if len(s) else 0.0
                if ratio < 0.8:  # almeno 80% convertibile
                    label_map = {k: lbl for k, lbl, *_ in PLANHEAT_FIELDS}
                    bad.append(f"{label_map[key]} ({col}) ~{int(ratio*100)}% numerico")
            if bad:
                self.di_error = "Valori non numerici in: " + "; ".join(bad)
                self.di_info = ""
                return

            self.di_error = ""
            self.di_info = "Validazione OK."
        except Exception as e:
            self.di_error = f"Errore validazione: {e}"
            self.di_info = ""

    # --- PVGIS ---
    # Stato/avanzamento
    pvgis_total_buildings: int = 0
    pvgis_current_idx: int = 0
    pvgis_gdf_path: str = ""
    pvgis_results: Dict[int, dict] = {}
    pvgis_progress: int = 0
    pvgis_running: bool = False
    pvgis_error: str = ""
    pvgis_plots: list[str] = []
    pvgis_horizon_map_html: str = ""
    pvgis_map_html_str: str = ""
    auto_step_pvgis: bool = False  # <--- dichiarato

    @rx.var
    def pvgis_map_html(self) -> str:
        """Restituisce l'HTML della mappa Folium generata in memoria."""
        return self.pvgis_map_html_str if self.pvgis_map_html_str else ""

    @rx.var
    def pvgis_map_png(self) -> str:
        """Restituisce il percorso della mappa PNG del potenziale FV se esiste."""
        png_path = Path("assets/pv_potential_map.png")
        if png_path.exists():
            return str(png_path)
        return ""

    # URL (iframe) della mappa interattiva generata su file
    pvgis_map_url: str = ""

    @rx.var
    def pvgis_map_iframe(self) -> str:
        """Restituisce l'URL della mappa Folium per iframe."""
        return self.pvgis_map_url if self.pvgis_map_url else ""

    # Id edifici con risultati PVGIS (una sola versione)
    @rx.var
    def pvgis_building_ids(self) -> list[str]:
        """Lista degli ID edifici con risultati PVGIS."""
        if not self.pvgis_results:
            return []
        return [str(k) for k in sorted(self.pvgis_results.keys()) if self.pvgis_results[k] is not None]

    # Getter numerici per KPI
    def get_building_energy(self, building_id: str) -> float:
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['energy_kwh'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    def get_building_cf(self, building_id: str) -> float:
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['capacity_factor'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    def get_building_yield(self, building_id: str) -> float:
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['specific_yield_kwh_kw'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    def get_building_avg_power(self, building_id: str) -> float:
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['avg_power_w'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    def get_building_max_power(self, building_id: str) -> float:
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['max_power_w'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    def get_building_peak_hours(self, building_id: str) -> float:
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['peak_hours_h'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    @rx.var
    def pvgis_results_list(self) -> list[tuple[str, dict]]:
        """Converte pvgis_results dict in lista di tuple per rx.foreach tipizzato."""
        if not self.pvgis_results:
            return []
        return [(str(k), v) for k, v in self.pvgis_results.items() if v is not None]

    @rx.event
    async def start_pvgis_analysis(self):
        try:
            self.pvgis_running = True
            self.pvgis_progress = 5

            # Carica shapefile buildings per il progetto attivo
            slug = self.active_project_slug
            shp = self._resolve_project_shp(slug)
            if not shp:
                self.pvgis_error = "Nessuno shapefile 'buildings' trovato."
                return

            gdf = gpd.read_file(str(shp))

            # Calcola i risultati PVGIS per tutti gli edifici
            from app.services.pv_overlay import process_all_buildings
            results = process_all_buildings(gdf)

            # Costruisci gli overlay per la mappa
            overlays = build_pv_geojson_layers(gdf, results, project_slug=self.active_project_slug or "default")
            # overlays: {"buildings_cf": "...", "panels_quintiles": "..."}

            self.pvgis_overlay_geojsons = [overlays["buildings_cf"], overlays["panels_quintiles"]]
            self.pvgis_results = results
            self.pvgis_progress = 95


            try:
                # Import lazy per evitare dipendenze circolari
                from app.states.map_state import MapState  # type: ignore

                mps = await self.get_state(MapState)
                # build_map è sincrona e non richiede argomenti
                mps.build_map()
            except ImportError as ie:
                print(f"[PVGIS] Import MapState non riuscito: {ie}")
            except AttributeError as ae:
                print(f"[PVGIS] MapState.build_map non trovato o firma diversa: {ae}")
            except Exception as e:
                print(f"[PVGIS] Errore rigenerazione mappa: {e}")


            self.pvgis_progress = 100
            self.pvgis_error = ""
        except Exception as e:
            self.pvgis_error = f"Errore analisi PVGIS: {e}"
        finally:
            self.pvgis_running = False

    @rx.event
    def toggle_auto_step_pvgis(self) -> None:
        self.auto_step_pvgis = not self.auto_step_pvgis

    @rx.var
    def pvgis_results_ui(self) -> list[dict]:
        """Restituisce i risultati PVGIS già formattati per la UI."""
        out: list[dict] = []
        for idx, res in self.pvgis_results.items():
            if res is not None:
                out.append({
                    "building_id": str(idx),
                    "energy": f"{res['annual_metrics']['energy_kwh']:.2f}",
                    "cf": f"{res['annual_metrics']['capacity_factor']:.3f}",
                    "yield": f"{res['annual_metrics']['specific_yield_kwh_kw']:.2f}",
                    "avg_power": f"{res['annual_metrics']['avg_power_w']:.2f}",
                    "max_power": f"{res['annual_metrics']['max_power_w']:.2f}",
                    "peak_hours": f"{res['annual_metrics']['peak_hours_h']:.2f}",
                })
        return out

    # Selezione edificio
    selected_building: str = ""

    @rx.event
    def set_selected_building(self, building_id: str) -> None:
        self.selected_building = building_id

    # Generazione mappa base
    @rx.event
    def pvgis_generate_base_map(self) -> None:
        """Genera la mappa base degli edifici (senza layer FV) all'avvio della pagina PVGIS."""
        slug = self.active_project_slug
        if not slug:
            self.pvgis_map_url = ""
            return

        shp = self._resolve_project_shp(slug)
        if not shp:
            self.pvgis_map_url = ""
            return

        try:
            gdf = gpd.read_file(str(shp))
            from PVGIS.plot_viewer_folium import plot_pv_potential_folium_file

            # Log (opzionale)
            print(f"[DEBUG] Generazione mappa base: {shp}")
            print("[DEBUG] Percorso output mappa base: uploaded_files/maps/pv_potential_map.html")

            plot_pv_potential_folium_file(
                gdf,
                {},  # layer opzionali
                output_html="uploaded_files/maps/pv_potential_map.html",
            )
            self.pvgis_map_url = "/uploaded_files/maps/pv_potential_map.html"
        except Exception as e:
            print(f"[PVGIS] Errore generazione mappa base: {e}")
            self.pvgis_map_url = ""