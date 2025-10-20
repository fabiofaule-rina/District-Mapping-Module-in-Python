import folium
import geopandas as gpd
from branca.colormap import linear
from pathlib import Path

def plot_pv_potential_folium_html(gdf, results):
    """
    Crea una mappa Folium con due layer e restituisce l'HTML come stringa.
    - Layer base: edifici originali (grigio, trasparente)
    - Layer FV: edifici colorati per potenziale FV
    Args:
        gdf: GeoDataFrame degli edifici
        results: dict di risultati da process_all_buildings()
    Returns:
        html: stringa HTML della mappa
    """
    gdf = gdf.copy()
    gdf['energy_kwh'] = gdf.index.map(lambda idx: results.get(idx, {}).get('annual_metrics', {}).get('energy_kwh', 0))
    min_e = gdf['energy_kwh'].min()
    max_e = gdf['energy_kwh'].max()
    colormap = linear.YlOrRd_09.scale(min_e, max_e)
    colormap.caption = 'Potenziale FV (kWh/anno)'
    centroid = gdf.geometry.centroid
    m = folium.Map(location=[centroid.y.mean(), centroid.x.mean()], zoom_start=15, tiles='OpenStreetMap')
    folium.GeoJson(
        gdf,
        name='Edifici (base)',
        style_function=lambda feature: {
            'fillColor': '#cccccc',
            'color': '#666666',
            'weight': 0.5,
            'fillOpacity': 0.2,
        },
        tooltip=folium.GeoJsonTooltip(fields=[])
    ).add_to(m)
    folium.GeoJson(
        gdf,
        name='Potenziale FV',
        style_function=lambda feature: {
            'fillColor': colormap(feature['properties']['energy_kwh']),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7,
        },
        tooltip=folium.GeoJsonTooltip(fields=['energy_kwh'], aliases=['Potenziale FV (kWh/anno)'])
    ).add_to(m)
    colormap.add_to(m)
    folium.LayerControl().add_to(m)
    # Restituisci HTML come stringa
    return m.get_root().render()

def plot_pv_potential_folium_file(gdf, results, output_html):
    """
    Crea una mappa Folium con due layer e salva su file HTML.
    - Layer base: edifici originali (grigio, trasparente)
    - Layer FV: edifici colorati per potenziale FV
    Args:
        gdf: GeoDataFrame degli edifici
        results: dict di risultati da process_all_buildings()
        output_html: percorso file HTML
    """
    gdf = gdf.copy()
    gdf['energy_kwh'] = gdf.index.map(lambda idx: results.get(idx, {}).get('annual_metrics', {}).get('energy_kwh', 0))
    min_e = gdf['energy_kwh'].min()
    max_e = gdf['energy_kwh'].max()
    colormap = linear.YlOrRd_09.scale(min_e, max_e)
    colormap.caption = 'Potenziale FV (kWh/anno)'
    centroid = gdf.geometry.centroid
    m = folium.Map(location=[centroid.y.mean(), centroid.x.mean()], zoom_start=15, tiles='OpenStreetMap')
    folium.GeoJson(
        gdf,
        name='Edifici (base)',
        style_function=lambda feature: {
            'fillColor': '#cccccc',
            'color': '#666666',
            'weight': 0.5,
            'fillOpacity': 0.2,
        },
        tooltip=folium.GeoJsonTooltip(fields=[])
    ).add_to(m)
    folium.GeoJson(
        gdf,
        name='Potenziale FV',
        style_function=lambda feature: {
            'fillColor': colormap(feature['properties']['energy_kwh']),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7,
        },
        tooltip=folium.GeoJsonTooltip(fields=['energy_kwh'], aliases=['Potenziale FV (kWh/anno)'])
    ).add_to(m)
    colormap.add_to(m)
    folium.LayerControl().add_to(m)
    Path(output_html).parent.mkdir(parents=True, exist_ok=True)
    m.save(output_html)
    # Aggiunta di log per debug
    print(f"✓ Folium PV map saved: {output_html}")
    print(f"[DEBUG] Generazione mappa Folium: {output_html}")
    print(f"[DEBUG] Min energia: {min_e}, Max energia: {max_e}")
