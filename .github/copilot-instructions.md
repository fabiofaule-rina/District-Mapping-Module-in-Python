# Copilot Instructions for District-Mapping-Module-in-Python

## Project Overview
This project is a modular Python application for district mapping and energy analysis, built with [Reflex](https://reflex.dev/) for the UI and [GeoPandas](https://geopandas.org/) for geospatial data. It supports project-based workflows, shapefile/GeoJSON import, attribute mapping, and stepwise PVGIS analysis for buildings.

## Architecture & Key Components
- **app/**: Main application logic and UI. Entry point is `app/app.py`.
  - `states/main_state.py`: Central state management, project selection, attribute mapping, and PVGIS analysis logic. All UI and workflow state is managed here.
  - `components/sidebar.py`: Sidebar navigation.
  - `pages/`: Each page (project, data import, map, parameters, kpi, pvgis) is a separate module. Pages use state from `main_state.py`.
  - `services/folium_map.py`: Map rendering using Folium, called from map page and state.
  - `db/init_db.py`: SQLite DB initialization for projects, layers, and buildings. Run at startup from `app.py`.
- **data/projects/**: Project folders with `project.json`, mapping files, and building layers (shp/geojson).
- **assets/**: Static files (favicon, map.html, etc.).
- **uploaded_files/maps/**: Runtime-generated map HTML files.
- **PVGIS/**: PVGIS analysis scripts, imported dynamically for building analysis.

## Developer Workflows
- **Run the app**: Use Reflex (`reflex run`) to start the development server. Ensure dependencies from `requirements.txt` are installed.
- **Database**: On startup, `ensure_db()` initializes the SQLite DB (`db/app.sqlite`). No manual migration needed.
- **Map Generation**: Maps are built via Folium and saved to `uploaded_files/maps/`. The map page triggers map builds and attribute table display.
- **PVGIS Analysis**: Triggered from the UI, runs stepwise per building. Results are stored in state and serialized for UI.

## Patterns & Conventions
- **State Management**: All UI and workflow state is managed in `MainState` (and page-specific states). Use `@rx.event` for event handlers and `@rx.var` for computed properties.
- **Project Selection**: Projects are discovered from `data/projects/` if they contain a valid `project.json`.
- **Attribute Mapping**: Column mapping for buildings is handled in state and persisted to `planheat_mapping.json` per project.
- **Error Handling**: Errors are stored in state variables (e.g., `di_error`, `pvgis_error`) and surfaced in the UI.
- **Dynamic Imports**: PVGIS analysis uses `importlib.import_module` to load scripts at runtime.
- **Map Output**: Always write map HTML to `uploaded_files/maps/` and update state for UI display.

## External Dependencies
- **Reflex**: UI framework, event-driven state.
- **GeoPandas, pandas, rtree, pyogrio**: Geospatial and data processing.
- **Folium**: Map rendering.
- **SQLite**: Local DB for project/layer/building metadata.
- **PVGIS**: External analysis scripts (in `PVGIS/`).

## Examples
- To add a new page, create a module in `app/pages/` and register it in `app/app.py`.
- To add a new project, create a folder in `data/projects/` with a `project.json` and building layers.
- To extend PVGIS analysis, update scripts in `PVGIS/` and ensure they expose required functions (e.g., `process_building`).

---

If any section is unclear or missing, please provide feedback or specify which workflows or patterns need more detail.
