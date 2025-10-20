# Owner: Axel Cueva
from __future__ import annotations
from typing import Dict, Any, List
import json
import csv

def summarize(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calcula métricas agregadas a partir de resultados de operaciones
    (por ejemplo, generadas por runner o simulador).

    Cada elemento de 'results' puede tener:
        {
            "access_time_ms": float,   # tiempo de acceso por operación
            "strategy": str,           # nombre de estrategia (opcional)
            "space_used": int,         # bloques usados
            "space_total": int,        # total de bloques
            "external_frag": float,    # 0..1 (de fsm)
        }
    """
    if not results:
        return {
            "avg_access_time_ms": 0.0,
            "space_usage_pct": 0.0,
            "fragmentation_internal_pct": 0.0,
            "fragmentation_external_pct": 0.0,
        }

    # Calcular promedios
    n = len(results)
    avg_access_time = sum(r.get("access_time_ms", 0) for r in results) / n
    avg_usage = sum((r.get("space_used", 0) / max(r.get("space_total", 1), 1)) * 100 for r in results) / n
    avg_external_frag = sum(r.get("external_frag", 0) * 100 for r in results) / n

    return {
        "avg_access_time_ms": round(avg_access_time, 3),
        "space_usage_pct": round(avg_usage, 2),
        "fragmentation_internal_pct": 0.0,  # No se simula fragmentación interna en contigua
        "fragmentation_external_pct": round(avg_external_frag, 2),
    }


# ======================================================
# Clase de Métricas (para usar directamente en simulaciones)
# ======================================================

class Metrics:
    def __init__(self, disk, fsm, fs):
        """
        disk: instancia de Disk
        fsm: instancia de FreeSpaceManager
        fs:  instancia de FilesystemBase (ej. ContiguousFS)
        """
        self.disk = disk
        self.fsm = fsm
        self.fs = fs

    def compute(self) -> Dict[str, float]:
        """Calcula métricas actuales del estado del sistema."""
        total_blocks = self.fsm.n_blocks
        used_blocks = self.fsm.used_count()
        free_blocks = self.fsm.free_count()

        external_frag = self.fsm.external_fragmentation_ratio() * 100

        return {
            "total_blocks": total_blocks,
            "used_blocks": used_blocks,
            "free_blocks": free_blocks,
            "space_usage_pct": round((used_blocks / total_blocks) * 100, 2),
            "fragmentation_external_pct": round(external_frag, 2),
            "fragmentation_internal_pct": 0.0,
            "files_stored": len(self.fs.file_table),
        }

    def print_summary(self):
        """Imprime las métricas en consola."""
        m = self.compute()
        print("\n===== MÉTRICAS DEL SISTEMA =====")
        for k, v in m.items():
            print(f"{k}: {v}")

    def export_json(self, path: str = "metrics.json"):
        """Exporta las métricas a un archivo JSON."""
        m = self.compute()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(m, f, indent=4)
        print(f"Métricas exportadas a {path}")

    def export_csv(self, path: str = "metrics.csv"):
        """Exporta las métricas a un archivo CSV."""
        m = self.compute()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Métrica", "Valor"])
            for k, v in m.items():
                writer.writerow([k, v])
        print(f"Métricas exportadas a {path}")


# ======================================================
# 🔧 PRUEBA RÁPIDA (solo se ejecuta si corres este archivo directamente)
# ======================================================
if __name__ == "__main__":
    from ..core.disk import Disk
    from ..core.free_space import FreeSpaceManager
    from ..fs_strategies.contiguous import ContiguousFS

    disk = Disk(n_blocks=10, block_size=8)
    fsm = FreeSpaceManager(n_blocks=10)
    fs = ContiguousFS(disk, fsm)

    fs.create("A.txt", 3)
    fs.create("B.txt", 2)
    fs.delete("A.txt")

    metrics = Metrics(disk, fsm, fs)
    metrics.print_summary()
    metrics.export_json()
    metrics.export_csv()
