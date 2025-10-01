# app/states/project_state.py
from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Optional

import reflex as rx
from app.services.files import save_upload, extract_shapefile, clean_dir

# --------------------------------------------------------------------
# Costanti per la mappatura Buildings (se servono nella pagina)
# --------------------------------------------------------------------
REQUIRED_BUILDING_FIELDS = ("id", "area_m2", "year", "use")
OPTIONAL_BUILDING_FIELDS = ("floors", "volume_m3")


def slugify(name: str) -> str:
    """Crea uno slug safe per nome progetto (cartelle)."""
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)        # rimuovi caratteri non alfanumerici/underscore/spazi/-
    s = re.sub(r"[\s]+", "-", s)          # spazi -> trattini
    s = s.replace("/", "-").replace("\\", "-")
    return s


class ProjectState(rx.State):
    """Stato della pagina 'Progetto'."""
    # --- Metadati progetto
    project_name: str = ""
    project_description: str = ""
    country_code: str = ""      # es. "IT"
    country: str = ""
    uploading: bool = False
    file_name: str = ""
    source_columns: list[str] = []
    column_mapping: dict[str, str] = {}
    preview_data: list[dict] = []
    is_project_creatable: bool = False
    # --- Derivati
    project_slug: str = ""

    # --- Upload & layer
    upload_file: Optional[bytes] = None   # contenuto ZIP caricato
    upload_ok: bool = False
    buildings_shp_path: str = ""          # path allo .shp estratto

    # ----------------------------------------------------------------
    # Setters espliciti (compatibili col deprecamento state_auto_setters)
    # ----------------------------------------------------------------
    
    @rx.event
    async def create_project(self):
        # TODO: implementa la logica di creazione progetto
        print("Creazione progetto avviata.")
        print("DEBUG: toast dovrebbe apparire ora")
        
        print("Creazione progetto avviata.")
        rx.toast.success("TOAST 1: Progetto creato con successo.")
        import time
        time.sleep(2)  # ⏳ Pausa per dare tempo al toast
        rx.toast.success("TOAST 2: Questo è un secondo messaggio.")

        rx.toast.success("Progetto creato con successo. Vai alla sezione 'Mappe' per visualizzare il layer caricato.")



    def set_project_name(self, v: str):
        self.project_name = v

    def set_project_description(self, v: str):
        self.project_description = v

    def set_country_code(self, v: str):
        self.country_code = v

    def set_upload_file(self, content: Optional[bytes]):
        """Setter diretto se ottieni già i bytes dal componente UI."""
        self.upload_file = content
        self.upload_ok = content is not None

    
    def update_mapping(self, field_key: str, selected_col: str):
        self.column_mapping[field_key] = selected_col


    # Opzionale: handler asincrono per rx.upload(..., on_drop=...)
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Legge il primo file caricato (ZIP) e lo mette in upload_file."""
        if not files:
            rx.toast.error("No file dropped.")
            return
        file0 = files[0]
        try:
            # UploadFile in Reflex/Starlette espone .read() asincrono
            content = await file0.read()
        except Exception as e:
            rx.toast.error(f"Upload read error: {e}")
            return

        if not content:
            rx.toast.error("Empty file.")
            return

        # opzionale: check estensione
        name = getattr(file0, "filename", "uploaded.zip")
        if not str(name).lower().endswith(".zip"):
            rx.toast.warning("Please upload a .zip containing the shapefile (.shp/.dbf/.shx/.prj).")

        self.upload_file = content
        self.upload_ok = True
        rx.toast.success("File received.")
        self.finalize_project()

    # ----------------------------------------------------------------
    # Azioni
    # ----------------------------------------------------------------
    def finalize_project(self):
        print("DEBUG: finalize_project started")
        if not self.project_name or not self.country_code:
            print("DEBUG: missing project_name or country_code")
            rx.toast.error("Project name and country are required.")
            return
        if not self.upload_ok or not self.upload_file:
            print("DEBUG: missing upload file")
            rx.toast.error("Please upload the shapefile .zip before finalizing.")
            return

        self.project_slug = slugify(self.project_name)
        proj_dir = Path(f"data/projects/{self.project_slug}")
        layers_dir = proj_dir / "layers" / "buildings"
        zip_path = layers_dir / "buildings.zip"
        shp_dir = layers_dir / "shp"

        try:
            print("DEBUG: saving ZIP")
            layers_dir.mkdir(parents=True, exist_ok=True)
            save_upload(self.upload_file, zip_path)

            print("DEBUG: extracting shapefile")
            clean_dir(shp_dir)
            shp_path = extract_shapefile(zip_path, shp_dir)
            self.buildings_shp_path = str(shp_path.resolve())

            print("DEBUG: writing project.json")
            proj_dir.mkdir(parents=True, exist_ok=True)
            meta = {
                "name": self.project_name,
                "description": self.project_description,
                "country": self.country_code,
                "layers": {
                    "buildings_shp": self.buildings_shp_path,
                },
            }
            (proj_dir / "project.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            print("DEBUG: project finalized")
            self.is_project_creatable = True
            rx.toast.success(f"Project '{self.project_name}' saved.")
        except Exception as e:
            print(f"DEBUG: finalize_project error: {e}")
            rx.toast.error(f"Finalize error: {e}")

    # Utility per resettare l’upload (se serve in UI)
    def reset_upload(self):
        self.upload_file = None
        self.upload_ok = False
        self.buildings_shp_path = ""