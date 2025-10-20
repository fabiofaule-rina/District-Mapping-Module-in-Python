# app/services/planheat_lookup.py
"""
Modulo per interrogare planheat.db e recuperare:
- country_id da nome paese
- period_id da anno di costruzione
- building_use_id da nome uso
- U-values (roof, wall, window) da (country_id, period_id, residential)
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional
import unicodedata
import re

PLANHEAT_DB = Path("app/db/planheat.db")

# Lista ufficiale degli usi Planheat (case-sensitive per il DB)
PLANHEAT_USES = [
    "Residential",
    "Office", 
    "Health Care",
    "Education",
    "Sport",
    "Historical Heritage",
    "Commercial",
    "Restaurant",
    "Public Administration"
]


class PlanheatLookupError(Exception):
    """Eccezione base per errori di lookup in planheat.db"""
    pass


# ============================================================================
# UTILITY
# ============================================================================

def _normalize_string(s: str) -> str:
    """Normalizza stringa: lowercase, rimuove accenti, strip spazi."""
    if not s:
        return ""
    # Rimuovi accenti (es. "Città" → "citta")
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('ascii')
    # Lowercase e strip
    s = s.lower().strip()
    # Rimuovi spazi multipli
    s = re.sub(r'\s+', ' ', s)
    return s


def _get_connection() -> sqlite3.Connection:
    """Apre connessione a planheat.db."""
    if not PLANHEAT_DB.exists():
        raise PlanheatLookupError(f"Database non trovato: {PLANHEAT_DB}")
    return sqlite3.connect(str(PLANHEAT_DB))


# ============================================================================
# LOOKUP FUNCTIONS
# ============================================================================

def get_country_id(country_name: str) -> int:
    """
    Recupera country_id da nome paese (case/accent insensitive).
    
    Args:
        country_name: Nome del paese (es. "Italy", "germany", "Città del Vaticano")
    
    Returns:
        int: country_id
        
    Raises:
        PlanheatLookupError: Se il paese non viene trovato o non è attivo
    """
    if not country_name:
        raise PlanheatLookupError("Nome paese vuoto")
    
    normalized_input = _normalize_string(country_name)
    
    with _get_connection() as conn:
        cur = conn.cursor()
        # Recupera tutti i paesi attivi
        cur.execute("SELECT id, country FROM country WHERE active = 1")
        rows = cur.fetchall()
        
        if not rows:
            raise PlanheatLookupError("Nessun paese attivo trovato nel database")
        
        # Cerca match normalizzato
        for row_id, row_country in rows:
            if _normalize_string(row_country) == normalized_input:
                return row_id
        
        # Se non trovato, lista disponibili per messaggio errore
        available = [r[1] for r in rows]
        raise PlanheatLookupError(
            f"Paese '{country_name}' non trovato. "
            f"Paesi disponibili: {', '.join(available)}"
        )


def get_period_id(year: int) -> int:
    """
    Recupera period_id dall'anno di costruzione.
    
    Args:
        year: Anno di costruzione (es. 1985)
    
    Returns:
        int: period_id
        
    Raises:
        PlanheatLookupError: Se l'anno non rientra in nessun periodo attivo
    """
    if not isinstance(year, int) or year < 1000 or year > 3000:
        raise PlanheatLookupError(f"Anno non valido: {year}")
    
    with _get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, start_period, end_period, period_text 
            FROM period 
            WHERE active = 1 
              AND ? >= start_period 
              AND ? <= end_period
            LIMIT 1
        """, (year, year))
        
        row = cur.fetchone()
        if not row:
            raise PlanheatLookupError(
                f"Anno {year} non rientra in nessun periodo attivo"
            )
        
        return row[0]  # period_id


def get_building_use_id(use_name: str) -> Optional[int]:
    """
    Recupera building_use_id da nome uso (case/accent insensitive).
    
    Args:
        use_name: Nome uso (es. "residential", "Office", "health care")
    
    Returns:
        int | None: building_use_id o None se non trovato
    """
    if not use_name:
        return None
    
    normalized_input = _normalize_string(use_name)
    
    with _get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, use FROM building_use WHERE active = 1")
        rows = cur.fetchall()
        
        for row_id, row_use in rows:
            if _normalize_string(row_use) == normalized_input:
                return row_id
        
        return None


def is_residential_use(use_name: str) -> bool:
    """
    Determina se un uso è residenziale (euristica semplice).
    
    Args:
        use_name: Nome uso già mappato a Planheat (es. "Residential")
    
    Returns:
        bool: True se residenziale
    """
    normalized = _normalize_string(use_name)
    return "residential" in normalized


def get_u_values(
    country_id: int,
    period_id: int,
    is_residential: bool
) -> dict[str, float]:
    """
    Recupera U-values da (country_id, period_id, residential).
    
    Args:
        country_id: ID paese
        period_id: ID periodo
        is_residential: True se uso residenziale
    
    Returns:
        dict con chiavi: 'roof', 'wall', 'window' (valori float)
        
    Raises:
        PlanheatLookupError: Se non ci sono U-values per quella combinazione
    """
    residential_flag = 1 if is_residential else 0
    
    with _get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT roof_u_value, wall_u_value, window_u_value
            FROM u_values
            WHERE country_id = ?
              AND period_id = ?
              AND residential = ?
            LIMIT 1
        """, (country_id, period_id, residential_flag))
        
        row = cur.fetchone()
        if not row:
            raise PlanheatLookupError(
                f"Nessun U-value trovato per: "
                f"country_id={country_id}, period_id={period_id}, "
                f"residential={residential_flag}"
            )
        
        return {
            "roof": float(row[0]) if row[0] is not None else 0.0,
            "wall": float(row[1]) if row[1] is not None else 0.0,
            "window": float(row[2]) if row[2] is not None else 0.0,
        }


# ============================================================================
# FUNZIONE COMPLETA (per comodità)
# ============================================================================

def lookup_building_data(
    country_name: str,
    use_name: str,
    year: int,
    building_id: str = ""
) -> dict:
    """
    Funzione aggregata che esegue tutti i lookup e restituisce un dict completo.
    
    Args:
        country_name: Nome paese
        use_name: Nome uso (già mappato a Planheat)
        year: Anno di costruzione
        building_id: ID edificio (opzionale, per logging)
    
    Returns:
        dict con tutte le info calcolate + eventuali warnings
        
    Esempio output:
        {
            "building_id": "abc123",
            "country_id": 15,
            "period_id": 3,
            "building_use_id": 1,
            "use_name_planheat": "Residential",
            "is_residential": True,
            "u_values": {"roof": 0.45, "wall": 0.65, "window": 2.8},
            "warnings": []
        }
    """
    result = {
        "building_id": building_id,
        "country_id": None,
        "period_id": None,
        "building_use_id": None,
        "use_name_planheat": use_name,
        "is_residential": False,
        "u_values": {"roof": 0.0, "wall": 0.0, "window": 0.0},
        "warnings": []
    }
    
    # 1. Country ID
    try:
        result["country_id"] = get_country_id(country_name)
    except PlanheatLookupError as e:
        result["warnings"].append(f"Country lookup: {e}")
        return result  # Non possiamo proseguire senza country_id
    
    # 2. Period ID
    try:
        result["period_id"] = get_period_id(year)
    except PlanheatLookupError as e:
        result["warnings"].append(f"Period lookup: {e}")
        return result
    
    # 3. Building Use ID
    use_id = get_building_use_id(use_name)
    if use_id is None:
        result["warnings"].append(f"Use '{use_name}' non trovato in building_use")
        return result
    result["building_use_id"] = use_id
    
    # 4. Residential flag
    result["is_residential"] = is_residential_use(use_name)
    
    # 5. U-values
    try:
        result["u_values"] = get_u_values(
            result["country_id"],
            result["period_id"],
            result["is_residential"]
        )
    except PlanheatLookupError as e:
        result["warnings"].append(f"U-values lookup: {e}")
    
    return result


# ============================================================================
# FUNZIONI DI UTILITÀ PER L'UI
# ============================================================================

def get_available_countries() -> list[str]:
    """Restituisce lista nomi paesi attivi (per popolare select UI)."""
    with _get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT country FROM country WHERE active = 1 ORDER BY country")
        return [row[0] for row in cur.fetchall()]


def get_available_uses() -> list[str]:
    """Restituisce lista usi attivi (per popolare select UI)."""
    with _get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT use FROM building_use WHERE active = 1 ORDER BY use")
        return [row[0] for row in cur.fetchall()]