# app/services/files.py
from __future__ import annotations
from pathlib import Path
import zipfile
import shutil

def save_upload(content: bytes, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

def extract_shapefile(zip_path: Path, out_dir: Path) -> Path:
    """Estrae lo shapefile .zip e ritorna il path al file .shp principale."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(out_dir)
    # cerca lo .shp
    shp_list = list(out_dir.rglob("*.shp"))
    if not shp_list:
        raise FileNotFoundError("No .shp found inside ZIP")
    return shp_list[0]

def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)