# Owner: Dev 1
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

DEFAULTS = {
    "mix-small-large": {
        "description": "Mezcla de archivos pequeños y grandes, 60% secuencial, 40% aleatorio",
        "disk_size": 50000,
        "block_size": 4096,
        "n_files_small": 200,
        "file_small_range": [1, 16],
        "n_files_large": 30,
        "file_large_range": [256, 2048],
        "access_pattern": {"seq": 0.6, "rand": 0.4},
        "delete_rate": 0.1,
        "ops": 1000
    },
    "seq-vs-rand": {
        "description": "Comparativa de acceso 90% secuencial vs 90% aleatorio",
        "disk_size": 40000,
        "block_size": 4096,
        "n_files_small": 150,
        "file_small_range": [1, 32],
        "n_files_large": 20,
        "file_large_range": [128, 1024],
        "access_pattern": {"seq": 0.9, "rand": 0.1},
        "delete_rate": 0.05,
        "ops": 800
    },
    "frag-intensive": {
        "description": "Creación/borrado intensivo para inducir fragmentación",
        "disk_size": 60000,
        "block_size": 4096,
        "n_files_small": 250,
        "file_small_range": [1, 8],
        "n_files_large": 10,
        "file_large_range": [512, 1024],
        "access_pattern": {"seq": 0.5, "rand": 0.5},
        "delete_rate": 0.4,
        "ops": 1500
    }
}

def load_from_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
