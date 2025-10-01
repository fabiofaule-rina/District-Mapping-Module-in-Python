# app/db/init_db.py
from __future__ import annotations
from pathlib import Path
import sqlite3
from datetime import datetime

DB_PATH = Path("db/app.sqlite")

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS PROJECTS (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  country_code TEXT,
  created_at TEXT NOT NULL,
  db_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS LAYERS (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL,
  name TEXT NOT NULL,          -- es. "buildings"
  type TEXT NOT NULL,          -- es. "buildings"
  path TEXT NOT NULL,          -- es. ./data/layers/<slug>/buildings.geojson
  features_count INTEGER NOT NULL,
  bbox_minx REAL, bbox_miny REAL, bbox_maxx REAL, bbox_maxy REAL,
  imported_at TEXT NOT NULL,
  FOREIGN KEY(project_id) REFERENCES PROJECTS(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS BUILDINGS (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  layer_id INTEGER NOT NULL,
  ext_id TEXT,
  centroid_lon REAL, centroid_lat REAL,
  floors INTEGER,
  area_m2 REAL,
  volume_m3 REAL,
  year INTEGER,
  use TEXT,
  attrs_json TEXT,
  FOREIGN KEY(layer_id) REFERENCES LAYERS(id) ON DELETE CASCADE
);
"""

def ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        con.executescript(DDL)
        con.commit()
    finally:
        con.close()