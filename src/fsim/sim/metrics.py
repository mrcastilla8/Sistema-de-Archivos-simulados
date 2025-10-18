# Owner: Dev 3
from __future__ import annotations
from typing import Dict, Any, List

def summarize(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Stub de métricas: devuelve ceros hasta que se implemente.
    results: lista de dicts con tiempos/espacios por operación (llenar en runner).
    """
    return {
        "avg_access_time_ms": 0.0,
        "space_usage_pct": 0.0,
        "fragmentation_internal_pct": 0.0,
        "fragmentation_external_pct": 0.0,
    }
