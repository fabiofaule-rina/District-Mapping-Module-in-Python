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
    pvgis_map_html_str: str = ""

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

    @rx.var
    def pvgis_map_iframe(self) -> str:
        """Restituisce l'URL della mappa interattiva FV se esiste."""
        map_path = Path("uploaded_files/maps/pv_potential_map.html")
        if map_path.exists():
            return "/uploaded_files/maps/pv_potential_map.html"
        return ""

    # Aggiungi queste computed vars nella classe MainState (dopo pvgis_horizon_map_html: str = "")
    # Aggiungi queste computed vars nella classe MainState (dopo pvgis_horizon_map_html: str = "")

    @rx.var
    def pvgis_building_ids(self) -> list[str]:
        """Lista degli ID edifici con risultati PVGIS."""
        if not self.pvgis_results:
            return []
        return [str(k) for k in sorted(self.pvgis_results.keys()) if self.pvgis_results[k] is not None]

    def get_building_energy(self, building_id: str) -> str:
        """Energia annua per un edificio (come stringa)."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                val = float(self.pvgis_results[idx]['annual_metrics']['energy_kwh'])
                return f"{val:.2f}"
        except (ValueError, KeyError, TypeError):
            pass
        return "0.00"

    def get_building_cf(self, building_id: str) -> str:
        """Capacity factor per un edificio (come numero, senza formatting)."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                val = float(self.pvgis_results[idx]['annual_metrics']['capacity_factor'])
                return str(val)
        except (ValueError, KeyError, TypeError):
            pass
        return "0.0"

    def get_building_cf_str(self, building_id: str) -> str:
        """Capacity factor per un edificio (formattato con 3 decimali)."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                val = float(self.pvgis_results[idx]['annual_metrics']['capacity_factor'])
                return f"{val:.3f}"
        except (ValueError, KeyError, TypeError):
            pass
        return "0.000"

    def get_building_yield(self, building_id: str) -> str:
        """Produttività specifica per un edificio (come stringa)."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                val = float(self.pvgis_results[idx]['annual_metrics']['specific_yield_kwh_kw'])
                return f"{val:.2f}"
        except (ValueError, KeyError, TypeError):
            pass
        return "0.00"

    def get_building_avg_power(self, building_id: str) -> str:
        """Potenza media per un edificio (come stringa)."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                val = float(self.pvgis_results[idx]['annual_metrics']['avg_power_w'])
                return f"{val:.2f}"
        except (ValueError, KeyError, TypeError):
            pass
        return "0.00"

    def get_building_max_power(self, building_id: str) -> str:
        """Potenza massima per un edificio (come stringa)."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                val = float(self.pvgis_results[idx]['annual_metrics']['max_power_w'])
                return f"{val:.2f}"
        except (ValueError, KeyError, TypeError):
            pass
        return "0.00"

    def get_building_peak_hours(self, building_id: str) -> str:
        """Ore equivalenti per un edificio (come stringa)."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                val = float(self.pvgis_results[idx]['annual_metrics']['peak_hours_h'])
                return f"{val:.2f}"
        except (ValueError, KeyError, TypeError):
            pass
        return "0.00"

    @rx.var
    def pvgis_building_ids(self) -> list[str]:
        """Lista degli ID edifici con risultati PVGIS."""
        if not self.pvgis_results:
            return []
        return [str(k) for k in sorted(self.pvgis_results.keys()) if self.pvgis_results[k] is not None]

    def get_building_energy(self, building_id: str) -> float:
        """Energia annua per un edificio."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['energy_kwh'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    def get_building_cf(self, building_id: str) -> float:
        """Capacity factor per un edificio."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['capacity_factor'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    def get_building_yield(self, building_id: str) -> float:
        """Produttività specifica per un edificio."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['specific_yield_kwh_kw'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    def get_building_avg_power(self, building_id: str) -> float:
        """Potenza media per un edificio."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['avg_power_w'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    def get_building_max_power(self, building_id: str) -> float:
        """Potenza massima per un edificio."""
        try:
            idx = int(building_id)
            if idx in self.pvgis_results and self.pvgis_results[idx]:
                return float(self.pvgis_results[idx]['annual_metrics']['max_power_w'])
        except (ValueError, KeyError, TypeError):
            pass
        return 0.0

    def get_building_peak_hours(self, building_id: str) -> float:
        """Ore equivalenti per un edificio."""
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
        # Converte {0: {...}, 1: {...}} in [("0", {...}), ("1", {...})]
        return [(str(k), v) for k, v in self.pvgis_results.items() if v is not None]

    @rx.event
    def start_pvgis_analysis(self) -> None:
        """Prepara lo stato e avvia l'analisi PVGIS su tutti gli edifici."""
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
            import tempfile, pickle
            from importlib import import_module
            import numpy as np
            gdf = gpd.read_file(str(shp))
            if gdf.crs is None:
                gdf = gdf.set_crs(epsg=4326)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pkl")
            pickle.dump(gdf, tmp)
            tmp.close()
            self.pvgis_gdf_path = tmp.name
            self.pvgis_total_buildings = len(gdf)
            self.pvgis_results = {}
            self.pvgis_progress = 0
            self.pvgis_running = True
            self.pvgis_error = ""
            pvgis_analyzer = import_module("PVGIS.pvgis_analyzer")
            utm_epsg = gdf.crs.to_epsg()
            for idx in range(self.pvgis_total_buildings):
                print(f"[PVGIS] Inizio edificio {idx+1}/{self.pvgis_total_buildings}")
                # --- Caching PVGIS ---
                cache_dir = PROJECTS_DIR / slug / "pvgis_cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file = cache_dir / f"building_{idx}.json"
                result = None
                if cache_file.exists():
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            result = json.load(f)
                        print(f"  [PVGIS] Cache trovata per edificio {idx}")
                    except Exception as e:
                        print(f"  [PVGIS] Errore lettura cache edificio {idx}: {e}")
                if result is None:
                    try:
                        result = pvgis_analyzer.process_building(gdf, idx, utm_epsg=utm_epsg)
                        # Serializza e salva su file
                        def _to_serializable(obj):
                            if isinstance(obj, dict):
                                # Rimuovi DataFrame e oggetti non serializzabili
                                return {str(k): _to_serializable(v) for k, v in obj.items() if not hasattr(v, 'to_dict') and not hasattr(v, 'to_json')}
                            elif isinstance(obj, list):
                                return [_to_serializable(v) for v in obj]
                            elif isinstance(obj, np.generic):
                                return obj.item()
                            elif isinstance(obj, (str, int, float, bool, type(None))):
                                return obj
                            else:
                                return None
                        serializable_result = _to_serializable(result) if result else None
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump(serializable_result, f, ensure_ascii=False, indent=2)
                        print(f"  [PVGIS] Risultato salvato in cache per edificio {idx}")
                        result = serializable_result
                    except Exception as e:
                        result = None
                        print(f"[PVGIS] Errore edificio {idx}: {e}")
                self.pvgis_results[idx] = result
                self.pvgis_progress = int((idx+1)/self.pvgis_total_buildings*100)
            self.pvgis_running = False
            print("[PVGIS] Analisi completata!")
            # --- Genera mappa Folium interattiva con potenziale FV come stringa HTML ---
            try:
                from PVGIS.plot_viewer_folium import plot_pv_potential_folium_file
                valid_results = {k: v for k, v in self.pvgis_results.items() if v is not None}
                map_path = Path("uploaded_files/maps/pv_potential_map.html")
                plot_pv_potential_folium_file(gdf, valid_results, output_html=str(map_path))
                self.pvgis_map_url = "/uploaded_files/maps/pv_potential_map.html"
            except Exception as e:
                print(f"[PVGIS] Errore generazione mappa Folium: {e}")
        except Exception as e:
            self.pvgis_error = f"Errore analisi PVGIS: {e}"
            self.pvgis_running = False

    auto_step_pvgis: bool = False

    @rx.event
    def toggle_auto_step_pvgis(self) -> None:
        self.auto_step_pvgis = not self.auto_step_pvgis

    @rx.var
    def pvgis_results_ui(self) -> list[dict]:
        """Restituisce i risultati PVGIS già formattati per la UI."""
        results = []
        for idx, res in self.pvgis_results.items():
            if res is not None:
                results.append({
                    "building_id": str(idx),
                    "energy": f"{res['annual_metrics']['energy_kwh']:.2f}",
                    "cf": f"{res['annual_metrics']['capacity_factor']:.3f}",
                    "yield": f"{res['annual_metrics']['specific_yield_kwh_kw']:.2f}",
                    "avg_power": f"{res['annual_metrics']['avg_power_w']:.2f}",
                    "max_power": f"{res['annual_metrics']['max_power_w']:.2f}",
                    "peak_hours": f"{res['annual_metrics']['peak_hours_h']:.2f}",
                })
        return results

    selected_building: str = ""

    @rx.event
    def set_selected_building(self, building_id: str) -> None:
        self.selected_building = building_id

    pvgis_map_url: str = ""

    @rx.var
    def pvgis_map_iframe(self) -> str:
        """Restituisce l'URL della mappa Folium per iframe."""
        return self.pvgis_map_url if self.pvgis_map_url else ""

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
            import geopandas as gpd
            gdf = gpd.read_file(str(shp))
            from PVGIS.plot_viewer_folium import plot_pv_potential_folium_file
            # Mappa base: layer edifici sempre presente
            # Aggiunta di log per debug
            print(f"[DEBUG] Generazione mappa base: {shp}")
            print(f"[DEBUG] Percorso output mappa base: uploaded_files/maps/pv_potential_map.html")
            plot_pv_potential_folium_file(gdf, {}, output_html="uploaded_files/maps/pv_potential_map.html")
            self.pvgis_map_url = "/uploaded_files/maps/pv_potential_map.html"
        except Exception as e:
            print(f"[PVGIS] Errore generazione mappa base: {e}")
            self.pvgis_map_url = ""