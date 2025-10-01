import reflex as rx
from datetime import datetime

class MapState(rx.State):
    building: bool = False
    last_build_ts: str = ""

    def build_map(self):
        """Costruisce/aggiorna la mappa ed aggiorna lo stato UI."""
        self.building = True
        # TODO: qui dentro richiama la tua logica di build della mappa
        # (lettura shapefile/geojson, generazione tiles, caching, ecc.)
        # Puoi estrarla in una funzione pura da importare e chiamare qui.
        self.last_build_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.building = False