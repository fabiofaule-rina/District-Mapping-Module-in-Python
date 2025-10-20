# app/services/folium_map.py
from __future__ import annotations
from pathlib import Path
import folium
import json
import geopandas as gpd

# app/services/folium_map.py
from folium.features import GeoJsonTooltip, GeoJsonPopup

# ---------- helper ----------
def _to_wgs84_and_fix(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        raise ValueError("CRS mancante: shapefile senza .prj. Imposta il CRS per proseguire.")
    gdf = gdf.to_crs(4326)
    gdf = gdf[gdf.geometry.notnull()].copy()
    # ripara self-intersections
    gdf["geometry"] = gdf.buffer(0)
    return gdf


def _add_geojson_overlay(m, geojson_path: Path, name: str):
    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    folium.GeoJson(
        data,
        name=name,
        style_function=lambda feat: {
            "fillColor": feat["properties"].get("color", "#3388ff"),
            "color": "#333333",
            "weight": 1,
            "fillOpacity": 0.7,
        },
        tooltip=folium.GeoJsonTooltip(fields=["popup_text"], aliases=["Info"])
    ).add_to(m)

def build_map_from_shp(shp_path: Path, out_html: Path, id_field: str | None = None,
                       overlay_geojsons: list[Path] | None = None):
    # ... costruiamo base + edifici come già fai ...
    m = folium.Map(...)  # esistente

    # (qui rimane la logica esistente per i buildings)
    # ...

    # --- Nuovi overlay opzionali (PV) ---
    if overlay_geojsons:
        for gj in overlay_geojsons:
            name = gj.stem.replace("_", " ").title()
            _add_geojson_overlay(m, gj, name)

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(out_html)


def _guess_id_column(gdf: gpd.GeoDataFrame) -> str | None:
    """
    Prova a identificare la colonna ID più probabile.
    Ordine: building_id, b_id, id, ID, fid, FID, OBJECTID, OBJECTID_1, ecc.
    Se non trovata, usa la prima colonna non geometrica con valori univoci;
    in ultima istanza, crea una colonna 'building_id' dal range index.
    """
    candidates = [
        "building_id","b_id","id","ID","fid","FID","objectid","OBJECTID","OBJECTID_1","gid","GID"
    ]
    cols = [c for c in gdf.columns if c != "geometry"]
    lower_map = {c.lower(): c for c in cols}
    for c in candidates:
        if c in lower_map:
            return lower_map[c]
    # cerca una colonna con alta unicità
    for c in cols:
        try:
            if gdf[c].is_unique and gdf[c].notna().all():
                return c
        except Exception:
            pass
    # fallback: crea una colonna sintetica
    gdf["building_id"] = range(1, len(gdf) + 1)
    return "building_id"

def _add_buildings_layer(m: folium.Map, gdf: gpd.GeoDataFrame, id_field: str | None = None) -> None:
    gdf = _to_wgs84_and_fix(gdf)
    id_col = id_field or _guess_id_column(gdf)

    # bounding box & centro
    minx, miny, maxx, maxy = gdf.total_bounds
    center = [(miny + maxy) / 2, (minx + maxx) / 2]
    m.location = center

    # Stile base e highlight on hover
    style_fn = lambda feat: {
        "fillColor": "#ff7800",
        "color": "#444444",
        "weight": 1,
        "fillOpacity": 0.35,
    }
    highlight_fn = lambda feat: {
        "fillColor": "#ffff00",
        "color": "#000000",
        "weight": 3,
        "fillOpacity": 0.55,
    }

    # Tooltip (hover) + Popup (click) con Building ID
    tooltip = GeoJsonTooltip(
        fields=[id_col],
        aliases=["Building ID:"],
        sticky=True,          # segue il cursore
        labels=True,
        localize=True,
        style=(
            "background-color: white; color: #333333; "
            "border: 1px solid #999; border-radius: 3px; "
            "box-shadow: 2px 2px 3px rgba(0,0,0,0.2); padding: 4px;"
        ),
    )
    popup = GeoJsonPopup(
        fields=[id_col],
        aliases=["Building ID:"],
        localize=True,
        labels=True,
        max_width=300,
    )

    folium.GeoJson(
        data=gdf.__geo_interface__,
        name="buildings",
        style_function=style_fn,
        highlight_function=highlight_fn,     # evidenzia il poligono al passaggio
        tooltip=tooltip,                      # nota al passaggio del cursore
        popup=popup,                          # nota “fissabile” al click
        popup_keep_highlighted=True,          # mantiene l’highlight mentre il popup è aperto
        zoom_on_click=False,                  # opzionale: se True, zooma al click
        smooth_factor=0.0,                    # a piacere (semplificazione in render)
    ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    m.fit_bounds([[miny, minx], [maxy, maxx]])


# ---------- public API ----------
def build_map_from_shp(shp_path: Path, out_html: Path, id_field: str | None = None) -> None:
    gdf = gpd.read_file(str(shp_path))
    # mappa base
    m = folium.Map(location=[45, 9], zoom_start=14, tiles="OpenStreetMap", control_scale=True)
    _add_buildings_layer(m, gdf, id_field=id_field)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))

def build_map_from_geojson(geojson_path: Path, out_html: Path, id_field: str | None = None) -> None:
    gdf = gpd.read_file(str(geojson_path))
    m = folium.Map(location=[45, 9], zoom_start=14, tiles="OpenStreetMap", control_scale=True)
    _add_buildings_layer(m, gdf, id_field=id_field)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))

#def build_map_from_shp(shp_path: Path, out_html: Path) -> None:
    """Crea una mappa OSM con overlay dallo SHP (ri-proiettato al volo in EPSG:4326) e la salva in assets."""
    if not shp_path.exists():
        raise FileNotFoundError(f"Shapefile not found: {shp_path}")

    gdf = gpd.read_file(shp_path)
    if gdf.empty:
        raise ValueError("Shapefile has no features")

    # Leaflet/Folium si aspetta lon/lat in WGS84
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    minx, miny, maxx, maxy = gdf.total_bounds

    m = folium.Map(tiles="OpenStreetMap")  # base OSM
    # Passiamo l'overlay come GeoJSON "in memoria" (Nessun file .geojson su disco)
    folium.GeoJson(data=gdf.to_json(), name="Buildings").add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    m.fit_bounds([[miny, minx], [maxy, maxx]])

    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))

#def build_map_from_geojson(geojson_path: Path, out_html: Path) -> None:
    gdf = gpd.read_file(str(geojson_path))
    # converti a WGS84 (EPSG:4326) e ripara geometrie:
    if gdf.crs is None:
        raise ValueError("CRS mancante: aggiungi il .prj o imposta il CRS.")
    gdf = gdf.to_crs(4326)
    gdf = gdf[gdf.geometry.notnull()].copy()
    gdf["geometry"] = gdf.buffer(0)

    minx, miny, maxx, maxy = gdf.total_bounds
    center = [(miny + maxy)/2, (minx + maxx)/2]
    m = folium.Map(location=center, zoom_start=14, tiles="OpenStreetMap", control_scale=True)
    folium.GeoJson(
        gdf.__geo_interface__,
        name="buildings",
        style_function=lambda f: {"color": "#ff7800", "weight": 1, "fillOpacity": 0.35},
    ).add_to(m)
    folium.LayerControl().add_to(m)
    m.fit_bounds([[miny, minx], [maxy, maxx]])
    out_html.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_html))