# Owner: Dev 1
from __future__ import annotations
import random
from typing import Dict, Any, List

def generate_workload(cfg: Dict[str, Any], seed: int | None = None) -> List[Dict[str, Any]]:
    """
    Genera una lista de operaciones: create/delete/read/write
    Este es un stub simple para que se reemplace con un generador más fiel.
    """
    rng = random.Random(seed)
    ops = []
    n = cfg.get("ops", 1000)
    for i in range(n):
        op = rng.choices(["create", "delete", "read", "write"], weights=[0.2, 0.2, 0.3, 0.3], k=1)[0]
        ops.append({
            "op": op,
            "name": f"file_{rng.randint(1, 300)}",
            "size_blocks": rng.randint(1, 32),
            "offset": 0,
            "n_blocks": rng.randint(1, 8),
            "access_mode": "seq" if rng.random() < cfg.get("access_pattern", {}).get("seq", 0.5) else "rand"
        })
    return ops
