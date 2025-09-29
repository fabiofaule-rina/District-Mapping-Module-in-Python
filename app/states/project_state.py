import reflex as rx
import geopandas as gpd
import logging
from typing import Union

REQUIRED_BUILDING_FIELDS = {
    "id_source": "Source Feature ID",
    "year_of_construction": "Year of Construction",
    "type_of_use": "Type of Use",
}


class ProjectState(rx.State):
    project_name: str = ""
    project_description: str = ""
    country: str = "IT"
    uploading: bool = False
    progress: int = 0
    file_name: str | None = None
    source_columns: list[str] = []
    preview_data: list[dict[str, str | int | float | bool | None]] = []
    column_mapping: dict[str, str] = {field: "" for field in REQUIRED_BUILDING_FIELDS}

    @rx.var
    def is_project_creatable(self) -> bool:
        return (
            bool(self.project_name)
            and bool(self.country)
            and bool(self.file_name)
            and all(self.column_mapping.values())
        )

    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile]):
        if not files:
            yield rx.toast.error("Nessun file selezionato.")
            return
        self.uploading = True
        yield
        try:
            uploaded_file = files[0]
            file_path = rx.get_upload_dir() / uploaded_file.name
            with file_path.open("wb") as f:
                f.write(await uploaded_file.read())
            gdf = gpd.read_file(file_path, engine="pyogrio", rows=20)
            self.file_name = uploaded_file.name
            self.source_columns = gdf.columns.tolist()
            self.preview_data = gdf.head(20).to_dict("records")
            self.column_mapping = {field: "" for field in REQUIRED_BUILDING_FIELDS}
            yield rx.toast.success(
                f"File '{uploaded_file.name}' caricato e analizzato."
            )
        except Exception as e:
            logging.exception(f"Error processing file: {e}")
            yield rx.toast.error(f"Errore durante l'elaborazione del file: {e}")
        finally:
            self.uploading = False
            self.progress = 0
            yield

    @rx.event
    def update_mapping(self, field: str, selected_column: str):
        self.column_mapping[field] = selected_column

    @rx.event
    def create_project(self):
        yield rx.toast.info(
            f"Creazione del progetto '{self.project_name}' con il layer '{self.file_name}'... (logica non implementata)"
        )
        print(
            "Project Metadata:",
            self.project_name,
            self.project_description,
            self.country,
        )
        print("File:", self.file_name)
        print("Column Mapping:", self.column_mapping)