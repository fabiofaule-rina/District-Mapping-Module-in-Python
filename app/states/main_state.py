# app/states/main_state.py
from __future__ import annotations

from pathlib import Path
import reflex as rx
import geopandas as gpd  # <— a livello di modulo, NON dentro la classe
import pandas as pd
import json
from typing import Literal, Dict

PROJECTS_DIR = Path("data/projects")


PageLiteral = Literal["project", "data_import", "map", "parameters", "kpi", "pvgis"]


# Costante (fuori dallo State) con i campi richiesti
PLANHEAT_FIELDS = [
    ("id", "ID", True,  "any"),    # (key, label, required, expected_type)
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

    di_available_uses: list[str] = []      # Valori unici dalla colonna buildingUse dello shapefile
    di_planheat_uses: list[str] = []       # Usi standard Planheat da DB
    use_map_by_project: dict[str, dict[str, str]] = {}  # Mappatura salvata per progetto

    # --- SCELTA COLONNA ID per progetto ---
    id_field_by_project: dict[str, str] = {}


    # Supporto per la UI "Dati e Import"
    di_available_columns: list[str] = []  # colonne non-geometry trovate per il progetto selezionato
    di_selected_id_field: str = ""
    di_error: str = ""
    di_info: str = ""  # messaggi informativi (validazione / salvataggio)


    # --- mappatura Planheat per progetto: slug -> {key: column}
    planheat_map_by_project: dict[str, dict[str, str]] = {}

    
    # --- binding UI "flat" per i 7 campi (più robusto nelle select) ---
    map_id: str = ""
    map_buildingUse: str = ""
    map_year: str = ""
    map_gfa: str = ""
    map_roof: str = ""
    map_height: str = ""
    map_floors: str = ""

    # Indica quale progetto è attivo a livello app (se già lo gestisci altrove, riusa quello)
    active_project_slug: str = ""

    active_page: PageLiteral = "project"

    @rx.event
    def set_active_page(self, page: PageLiteral):
        self.active_page = page

    # @rx.event
    # def set_active_project(self, slug: str) -> None:
    #     self.active_project_slug = slug

    # def _resolve_project_shp(self, slug: str) -> Path | None:
    #     """Trova lo shapefile buildings (come in map.py)."""
    #     proj_dir = PROJECTS_DIR / slug
    #     if not proj_dir.exists():
    #         return None
    #     # ricerca ricorsiva .shp (qui semplice)
    #     candidates = list(proj_dir.rglob("*.shp"))
    #     if candidates:
    #         # prendi il più grande
    #         return max(candidates, key=lambda p: p.stat().st_size)
    #     return None
    
    # ---------------- Helpers ----------------

    def _list_projects(self) -> list[str]:
        if not PROJECTS_DIR.exists():
            return []
        return sorted([p.name for p in PROJECTS_DIR.iterdir() if p.is_dir() and (p / "project.json").exists()])


    def _resolve_project_shp(self, slug: str) -> Path | None:
        proj_dir = PROJECTS_DIR / slug
        if not proj_dir.exists():
            return None
        shp_list = list(proj_dir.rglob("*.shp"))
        return max(shp_list, key=lambda p: p.stat().st_size) if shp_list else None

    
    def _mapping_path(self, slug: str) -> Path:
        return PROJECTS_DIR / slug / "planheat_mapping.json"


    # ---------------- Computed ----------------
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


    #@rx.event
    #def di_refresh_columns(self) -> None:
        """Carica le colonne non geometriche dello shapefile buildings del progetto attivo."""
        slug = self.active_project_slug
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
            if "geometry" in gdf.columns:
                cols = [c for c in gdf.columns if c != "geometry"]
            else:
                cols = list(gdf.columns)
            # ordina e rimuovi duplicati conservando ordine
            seen = set()
            cols = [c for c in cols if not (c in seen or seen.add(c))]
            self.di_available_columns = cols

            # precompila la selezione:
            #  - se già salvata per il progetto, la riprendi
            #  - altrimenti euristica su nomi comuni
            saved = self.id_field_by_project.get(slug, "")
            if saved and saved in cols:
                self.di_selected_id_field = saved
            else:
                # euristica semplice
                candidates = ["building_id", "b_id", "id", "ID", "fid", "FID", "objectid", "OBJECTID", "OBJECTID_1", "gid", "GID"]
                lower_map = {c.lower(): c for c in cols}
                chosen = None
                for c in candidates:
                    if c in lower_map:
                        chosen = lower_map[c]
                        break
                self.di_selected_id_field = chosen or (cols[0] if cols else "")
            self.di_error = ""
        except Exception as e:
            self.di_error = f"Errore lettura attributi: {e}"
            self.di_available_columns = []
            self.di_selected_id_field = ""

    #@rx.event
    #def di_set_selected_id_field(self, col: str) -> None:
        self.di_selected_id_field = col

    #@rx.event
    #def di_save_id_field(self) -> None:
        """Persisti la scelta per il progetto attivo."""
        slug = self.active_project_slug
        if not slug or not self.di_selected_id_field:
            self.di_error = "Nessun progetto o colonna selezionata."
            return
        self.id_field_by_project[slug] = self.di_selected_id_field
        self.di_error = ""

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
        """Legge colonne non geometriche e imposta selezioni ID 
        e mappatura Planheat per il progetto attivo."""
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
            saved = self.id_field_by_project.get(slug, "")
            if saved and saved in cols:
                chosen = saved
            else:
                lower = {c.lower(): c for c in cols}
                guess = None
                for k in ["building_id","b_id","id","ID","fid","FID","objectid","OBJECTID","OBJECTID_1","gid","GID"]:
                    if k in lower:
                        guess = lower[k]; break
                chosen = guess or (cols[0] if cols else "")
            self.di_available_columns = cols
            self.di_selected_id_field = chosen
            self.di_error = ""
        except Exception as e:
            self.di_error = f"Errore lettura attributi: {e}"
            self.di_available_columns = []
            self.di_selected_id_field = ""

            
# 2) Mappatura Planheat: carica da memoria o da file; popola i 7 campi UI
            mapping = self.planheat_map_by_project.get(slug, {})
            mp_path = self._mapping_path(slug)
            if not mapping and mp_path.exists():
                try:
                    mapping = json.loads(mp_path.read_text(encoding="utf-8"))
                    if isinstance(mapping, dict):
                        self.planheat_map_by_project[slug] = mapping
                except Exception:
                    pass

            
    # Se non c'è una scelta per "id", usa quella dell'ID selezionato sopra
            def _sel(key: str, fallback: str = "") -> str:
                v = mapping.get(key, "")
                return v if v in cols else fallback

            self.map_id          = _sel("id", chosen)
            self.map_buildingUse = _sel("buildingUse")
            self.map_year        = _sel("year")
            self.map_gfa         = _sel("gfa")
            self.map_roof        = _sel("roof")
            self.map_height      = _sel("height")
            self.map_floors      = _sel("floors")

        except Exception as e:
            self.di_error = f"Errore lettura attributi: {e}"
            self.di_available_columns = []

    
    @rx.event
    def di_set_map_field(self, key: str, col: str) -> None:
        # aggiorna la var UI corrispondente
        if key == "id": self.map_id = col
        elif key == "buildingUse": self.map_buildingUse = col
        elif key == "year": self.map_year = col
        elif key == "gfa": self.map_gfa = col
        elif key == "roof": self.map_roof = col
        elif key == "height": self.map_height = col
        elif key == "floors": self.map_floors = col



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
        # sync anche con la mappatura Planheat (campo id)
        self.map_id = self.di_selected_id_field
        # aggiorna in memoria planheat_map_by_project (non su file ancora)
        mp = self.planheat_map_by_project.get(slug, {})
        mp["id"] = self.map_id
        self.planheat_map_by_project[slug] = mp
        self.di_info = "Colonna ID salvata."

    @rx.event
    def di_save_planheat_mapping(self) -> None:
        """Salva la mappatura Planheat per il progetto (memoria + file JSON) e sincronizza id_field_by_project."""
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
        """Controlli base: esistenza colonne e 'numericità' ragionevole dove attesa."""
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

            # 2) numericità per alcuni campi (sample veloce)
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
                    bad.append(f"{dict(PLANHEAT_FIELDS)[key]} ({col}) ~{int(ratio*100)}% numerico")

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
    # --- PVGIS step-by-step ---
    pvgis_total_buildings: int = 0
    pvgis_current_idx: int = 0
    pvgis_gdf_path: str = ""
    pvgis_results: Dict[int, dict] = {}
    pvgis_progress: int = 0
    pvgis_running: bool = False
    pvgis_error: str = ""
    pvgis_plots: list[str] = []

    pvgis_horizon_map_html: str = ""

    @rx.event
    def start_pvgis_analysis(self) -> None:
        """Prepara lo stato e avvia l'analisi step-by-step PVGIS."""
        slug = self.active_project_slug
        if not slug:
            self.pvgis_error = "Nessun progetto selezionato."
            return
        shp = self._resolve_project_shp(slug)
        if not shp:
            self.pvgis_error = "Nessuno shapefile 'buildings' trovato."
            return
        try:
            import geopandas as gpd
            gdf = gpd.read_file(str(shp))
            if gdf.crs is None:
                gdf = gdf.set_crs(epsg=4326)
            # Salva il path temporaneo del GDF come pickle
            import tempfile, pickle
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pkl")
            pickle.dump(gdf, tmp)
            tmp.close()
            self.pvgis_gdf_path = tmp.name
            self.pvgis_total_buildings = len(gdf)
            self.pvgis_current_idx = 0
            self.pvgis_results = {}
            self.pvgis_progress = 0
            self.pvgis_running = True
            self.pvgis_error = ""
            self.step_pvgis_analysis()
        except Exception as e:
            self.pvgis_error = f"Errore inizializzazione PVGIS: {e}"
            self.pvgis_running = False

    @rx.event
    def step_pvgis_analysis(self) -> None:
        """Elabora un edificio e aggiorna la barra di avanzamento."""
        if not self.pvgis_running or not self.pvgis_gdf_path:
            return
        try:
            import pickle
            import numpy as np
            from importlib import import_module
            print(f"[PVGIS] Inizio step edificio {self.pvgis_current_idx+1}/{self.pvgis_total_buildings}")
            pvgis_analyzer = import_module("PVGIS.pvgis_analyzer")
            with open(self.pvgis_gdf_path, "rb") as f:
                gdf = pickle.load(f)
            idx = self.pvgis_current_idx
            utm_epsg = gdf.crs.to_epsg()
            print(f"[PVGIS] Chiamo process_building per idx={idx}")
            result = pvgis_analyzer.process_building(gdf, idx, utm_epsg=utm_epsg)
            print(f"[PVGIS] Risultato edificio {idx}: {result is not None}")
            def _to_serializable(obj):
                if isinstance(obj, dict):
                    return {str(k): _to_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [_to_serializable(v) for v in obj]
                elif isinstance(obj, np.generic):
                    return obj.item()
                else:
                    return obj
            self.pvgis_results[idx] = _to_serializable(result) if result else None
            self.pvgis_progress = int((idx+1)/self.pvgis_total_buildings*100)
            self.pvgis_current_idx += 1
            print(f"[PVGIS] Avanzamento: {self.pvgis_progress}%")
            if self.pvgis_current_idx < self.pvgis_total_buildings:
                self.step_pvgis_analysis()  # Chiamata diretta ricorsiva
            else:
                self.pvgis_running = False
                print("[PVGIS] Analisi completata!")
        except Exception as e:
            self.pvgis_error = f"Errore step PVGIS: {e}"
            self.pvgis_running = False