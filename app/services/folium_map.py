# app/services/folium_map.py
from __future__ import annotations
from pathlib import Path
import folium
import geopandas as gpd

def build_map_from_shp(shp_path: Path, out_html: Path) -> None:
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

def build_map_from_geojson(geojson_path: Path, out_html: Path) -> None:
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