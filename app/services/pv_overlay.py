# app/services/pv_overlay.py
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, Point
import reflex as rx  # per get_upload_dir()

# ---- helpers presi da plot_viewer.py (semplificati) ----
def compute_quintiles(values):
    vals = sorted([v for v in values if v is not None and v > 0])
    if not vals:
        return [0, 1], ["0-1"]
    q0, q20, q40, q60, q80, q100 = vals[0], *np.percentile(vals, [20,40,60,80]), vals[-1]
    return [q0, q20, q40, q60, q80, q100], [
        f"{q0:.0f}-{q20:.0f}", f"{q20:.0f}-{q40:.0f}", f"{q40:.0f}-{q60:.0f}",
        f"{q60:.0f}-{q80:.0f}", f"{q80:.0f}-{q100:.0f}",
    ]

def value_to_quintile(v, bounds):
    if v is None or v <= 0: return 0
    for i in range(len(bounds)-1):
        if bounds[i] <= v < bounds[i+1]:
            return i
    return len(bounds) - 2

def quintile_colors():
    # palette a 5 livelli (puoi cambiarla se vuoi)
    return ["#d73027","#fc8d59","#fee08b","#91bfdb","#1a9850"]

def create_panel_rectangle(centroid: Point, p1, p2):
    import numpy as np
    c = np.array([centroid.x, centroid.y], dtype=float)
    p1 = np.array(p1, dtype=float); p2 = np.array(p2, dtype=float)
    vec = p2 - p1; L = np.linalg.norm(vec)
    if L < 1e-6: return None
    perp = np.array([-vec[1], vec[0]], dtype=float); perp /= np.linalg.norm(perp)
    mid = (p1 + p2)/2.0
    if np.dot(perp, (c - mid)) < 0: perp = -perp
    t = np.dot(c - p1, vec) / (L**2); t = np.clip(t, 0, 1)
    proj = p1 + t*vec
    h = np.linalg.norm(c - proj)
    if h < 1e-6: h = 0.1*L
    p3 = p2 + h*perp; p4 = p1 + h*perp
    return Polygon([tuple(p1), tuple(p2), tuple(p3), tuple(p4)])

# ---- API principale ----
def build_pv_geojson_layers(gdf_utm: gpd.GeoDataFrame, results: dict,
                            project_slug: str) -> dict[str, str]:
    """
    Ritorna i path relativi (rispetto a upload dir) dei GeoJSON creati:
    - buildings_cf: poligoni edifici colorati per capacity factor
    - panels_quintiles: rettangoli pannelli colorati per energia (quintili)
    """
    # 1) Directory di output pubblica a runtime
    out_root = rx.get_upload_dir()
    layers_dir = out_root / "layers" / project_slug
    layers_dir.mkdir(parents=True, exist_ok=True)

    # --- Always ensure WGS84 for Leaflet ---
    gdf_ll = gdf_utm.to_crs(epsg=4326)

    # 2) Buildings CF (poligoni)
    features_b = []
    for idx in gdf_ll.index:
        if idx not in results or results[idx] is None:
            continue
        geom = gdf_ll.loc[idx, "geometry"]
        metrics = results[idx]["annual_metrics"]
        cf = metrics["capacity_factor"]
        energy = metrics["energy_kwh"]
        if cf >= 0.20:
            color, category = "#2ECC71", "high"
        elif cf >= 0.15:
            color, category = "#F1C40F", "medium"
        elif cf >= 0.10:
            color, category = "#E67E22", "low"
        else:
            color, category = "#E74C3C", "very_low"
        features_b.append({
            "type": "Feature",
            "geometry": json.loads(gdf_ll.loc[[idx]].to_json())["features"][0]["geometry"],
            "properties": {
                "building_id": int(idx),
                "energy_kwh": round(energy, 2),
                "capacity_factor": round(cf, 4),
                "cf_category": category,
                "color": color,
                "popup_text": f"Building {idx}: {energy:.0f} kWh/yr, CF {cf*100:.1f}%",
            }
        })
    geojson_b = {"type":"FeatureCollection","features":features_b}
    path_b = layers_dir / "buildings_pv_cf.geojson"
    path_b.write_text(json.dumps(geojson_b, indent=2), encoding="utf-8")

    # 3) Panels (rettangoli) colorati per quintili di energia
    #    -> costruiamo le geometrie in UTM e poi riproiettiamo a 4326
    energies = []
    for idx, r in results.items():
        if r and "annual_metrics" in r:
            energies.append(r["annual_metrics"]["energy_kwh"])
    bounds, labels = compute_quintiles(energies)
    colors = quintile_colors()

    rect_rows = []
    for idx, row in gdf_utm.iterrows():
        r = results.get(idx)
        if not r: continue
        long_side = (r.get("building_props", {}) or {}).get("long_side_endpoints")
        if not long_side or len(long_side) != 2:  # serve per creare il rettangolo
            continue
        centroid = row.geometry.centroid
        rect = create_panel_rectangle(centroid, long_side[0], long_side[1])
        if rect is None or rect.is_empty: continue
        energy = r["annual_metrics"]["energy_kwh"]
        q_idx = value_to_quintile(energy, bounds)
        rect_rows.append({
            "geometry": rect, "building_id": int(idx),
            "energy_kwh": round(energy, 2),
            "quintile": int(q_idx), "color": colors[q_idx],
            "label": labels[min(q_idx, len(labels)-1)]
        })
    if rect_rows:
        gdf_rect = gpd.GeoDataFrame(rect_rows, geometry="geometry", crs=gdf_utm.crs)
        gdf_rect_ll = gdf_rect.to_crs(epsg=4326)

        features_r = []
        gj_rect = json.loads(gdf_rect_ll.to_json())
        for f in gj_rect["features"]:
            props = f["properties"]
            props["popup_text"] = (f"Building {props['building_id']} – "
                                   f"{props['energy_kwh']:.0f} kWh/yr – Q{props['quintile']+1} ({props['label']})")
            features_r.append({
                "type":"Feature",
                "geometry": f["geometry"],
                "properties": props
            })
        geojson_r = {"type":"FeatureCollection","features":features_r}
    else:
        geojson_r = {"type":"FeatureCollection","features":[]}

    path_r = layers_dir / "panels_quintiles.geojson"
    path_r.write_text(json.dumps(geojson_r, indent=2), encoding="utf-8")

    # 4) Ritorna percorsi RELATIVI rispetto alla upload dir (per rx.get_upload_url)
    rel_b = f"layers/{project_slug}/{path_b.name}"
    rel_r = f"layers/{project_slug}/{path_r.name}"
    return {"buildings_cf": rel_b, "panels_quintiles": rel_r}