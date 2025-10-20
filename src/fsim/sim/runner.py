# Owner: Dev 1
from __future__ import annotations
import csv, json, time
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional

from ..core.disk import Disk
from ..core.free_space import FreeSpaceManager
from ..fs_strategies.contiguous import ContiguousFS
from ..fs_strategies.linked import LinkedFS
from ..fs_strategies.indexed import IndexedFS
from .scenario_definitions import DEFAULTS, load_from_json
from .workload_generators import generate_workload
from .metrics import summarize, full_metrics_summary  # usamos ambas

STRATEGIES = {
    "contiguous": ContiguousFS,
    "linked": LinkedFS,
    "indexed": IndexedFS,
}


def build_config(
    scenario: str | None,
    scenarios_path: str | None,
    overrides: Dict[str, Any],
) -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}
    if scenario:
        cfgs = {**DEFAULTS, **(load_from_json(scenarios_path) if scenarios_path else {})}
        if scenario not in cfgs:
            raise KeyError(f"Escenario '{scenario}' no existe")
        cfg.update(cfgs[scenario])
    cfg.update(overrides or {})
    return cfg


def _make_event_handler(collector: Dict[str, Any]) -> Callable[..., None]:
    """
    Devuelve un callback on_event(event_type, **payload) que acumula información
    útil para métricas por operación (e.g., estimación de seeks).
    - Se asume que las estrategias emiten eventos con claves como:
      physical: List[int], name, offset, n_blocks, access_mode, etc.
    """
    def on_event(event_type: str, **payload: Any) -> None:
        # Guardar último evento bruto si hiciera falta depurar
        collector["last_event"] = (event_type, payload)

        # Contar "seeks" estimados a partir de la secuencia física
        phys = payload.get("physical")
        if isinstance(phys, list) and phys:
            seeks = 0
            for i in range(len(phys) - 1):
                if phys[i + 1] != phys[i] + 1:
                    seeks += 1
            collector["seeks"] = collector.get("seeks", 0) + seeks

        # Llevar conteo de bloques tocados (útil para razones por bloque)
        nb = payload.get("n_blocks")
        if isinstance(nb, int) and nb > 0:
            collector["blocks_touched"] = collector.get("blocks_touched", 0) + nb

    return on_event


def _snapshot_state(fsm: FreeSpaceManager) -> Dict[str, float]:
    """Snapshot del estado de espacio para adjuntar a cada resultado."""
    total = fsm.n_blocks
    used = fsm.used_count()
    usage_pct = (used / total) * 100 if total > 0 else 0.0
    ext_frag = fsm.external_fragmentation_ratio()  # 0..1
    return {
        "space_used": float(used),
        "space_total": float(total),
        "external_frag": float(ext_frag),
        # internal_frag: si en el futuro modelan bytes útiles, agréguenlo aquí [0..1]
        "internal_frag": 0.0,
    }


def run_simulation(
    strategy_name: str,
    scenario: str | None,
    scenarios_path: str | None,
    seed: int | None,
    overrides: Dict[str, Any],
    out: str | None = None,
) -> Dict[str, Any]:
    """
    Ejecuta la simulación para una o todas las estrategias.
    - Genera el workload una única vez (reproducible con 'seed').
    - Para cada estrategia, usa un Disk/FSM NUEVOS para no contaminar resultados.
    - Mide tiempos por operación (ms), CPU y elapse total, y recolecta snapshots
      de uso de espacio y fragmentación tras cada operación.
    - Devuelve un resumen extendido (full_metrics_summary) por estrategia.
    """
    if strategy_name not in STRATEGIES and strategy_name != "all":
        raise KeyError(f"Estrategia inválida: {strategy_name}")

    cfg = build_config(scenario, scenarios_path, overrides)
    # Generamos el workload una sola vez para todas las estrategias
    ops = generate_workload(cfg, seed=seed)

    strategies = list(STRATEGIES.keys()) if strategy_name == "all" else [strategy_name]
    summaries: Dict[str, Dict[str, Any]] = {}

    for s in strategies:
        # Instancias limpias por estrategia (independencia total)
        disk = Disk(
            n_blocks=cfg.get("disk_size", 50000),
            block_size=cfg.get("block_size", 4096),
            prefill=None,  # evitar costo extra; cambiar a "zeros" si quieren baseline distinto
        )
        fsm = FreeSpaceManager(disk.n_blocks)

        # Colección de resultados por operación
        results: List[Dict[str, Any]] = []

        # Handler de eventos para métricas finas (seeks, bloques tocados, etc.)
        event_acc: Dict[str, Any] = {}
        on_event = _make_event_handler(event_acc)

        fs_class = STRATEGIES[s]
        fs = fs_class(disk, fsm, on_event=on_event)  # todas las estrategias aceptan on_event

        # Medición global (para throughput/CPU si hace falta)
        sim_start_wall = time.perf_counter()
        sim_start_cpu = time.process_time()

        for op in ops:
            event_acc.clear()  # limpiar acumuladores por cada operación
            op_name = op.get("op")

            # cronómetro por operación
            t0_wall = time.perf_counter()
            t0_cpu = time.process_time()

            hit = 1  # asumimos éxito; si hay excepción se marcará miss
            miss = 0

            try:
                if op_name == "create":
                    fs.create(op["name"], op["size_blocks"])
                elif op_name == "delete":
                    fs.delete(op["name"])
                elif op_name == "read":
                    # data no se usa aquí; solo tiempo y efectos
                    fs.read(op["name"], op["offset"], op["n_blocks"], op.get("access_mode", "seq"))
                elif op_name == "write":
                    fs.write(op["name"], op["offset"], op["n_blocks"], None)
                else:
                    # operación desconocida: se considera miss lógico
                    hit, miss = 0, 1
            except Exception:
                # cualquier excepción operativa cuenta como miss
                hit, miss = 0, 1

            # tiempos por operación
            op_elapsed_ms = (time.perf_counter() - t0_wall) * 1000.0
            op_cpu_s = (time.process_time() - t0_cpu)

            # snapshot de espacio y fragmentación tras la operación
            snap = _snapshot_state(fsm)

            # registro de resultado por operación
            result: Dict[str, Any] = {
                "strategy": s,
                "operation": op_name,
                "access_time_ms": float(op_elapsed_ms),
                "elapsed_time_s": float(op_elapsed_ms / 1000.0),  # útil para throughput por suma
                "cpu_time": float(op_cpu_s),  # tiempo de CPU por operación
                "hits": hit,
                "misses": miss,
                # auxiliares desde eventos
                "seeks_est": int(event_acc.get("seeks", 0)),
                "blocks_touched": int(event_acc.get("blocks_touched", 0)),
                # snapshots de estado
                **snap,
            }
            results.append(result)

        # métricas agregadas (extendidas y básicas)
        total_elapsed_s = time.perf_counter() - sim_start_wall
        total_cpu_s = time.process_time() - sim_start_cpu

        # Añadimos una fila "TOTAL" opcional (no interfiere con cálculos; sirve para trazabilidad)
        results.append({
            "strategy": s,
            "operation": "TOTAL",
            "access_time_ms": total_elapsed_s * 1000.0 / max(1, (len(results) or 1)),
            "elapsed_time_s": total_elapsed_s,
            "cpu_time": total_cpu_s,
            "hits": sum(r["hits"] for r in results if r.get("operation") != "TOTAL"),
            "misses": sum(r["misses"] for r in results if r.get("operation") != "TOTAL"),
            "seeks_est": sum(r["seeks_est"] for r in results if r.get("operation") != "TOTAL"),
            "blocks_touched": sum(r["blocks_touched"] for r in results if r.get("operation") != "TOTAL"),
            # snapshots del final (estado final del FSM)
            **_snapshot_state(fsm),
        })

        # resumen extendido oficial
        summary_ext = full_metrics_summary(results)
        # también dejamos el básico por compatibilidad
        summary_basic = summarize(results)

        # anexamos algunos campos útiles adicionales
        summary_ext["elapsed_ms_total"] = round(total_elapsed_s * 1000.0, 3)
        summary_ext["cpu_time_total_s"] = round(total_cpu_s, 6)
        summary_ext["ops_count"] = sum(1 for r in results if r.get("operation") not in ("TOTAL", None))
        summary_ext["seeks_total_est"] = int(sum(r["seeks_est"] for r in results if r.get("operation") != "TOTAL"))

        # elegimos devolver el extendido, e incluir el básico anidado para referencia
        summaries[s] = {
            **summary_ext,
            "_basic": summary_basic,
        }

    # Persistencia opcional
    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() == ".csv":
            # Aplanar y escribir columnas principales (evitar el campo "_basic")
            # Encabezados estables
            key_order = [
                "avg_access_time_ms",
                "space_usage_pct",
                "fragmentation_internal_pct",
                "fragmentation_external_pct",
                "throughput_ops_per_sec",
                "hit_miss_ratio",
                "cpu_usage_pct",
                "fairness_index",
                "elapsed_ms_total",
                "cpu_time_total_s",
                "ops_count",
                "seeks_total_est",
            ]
            with p.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["strategy"] + key_order)
                for strat, vals in summaries.items():
                    row = [strat] + [vals.get(k, "") for k in key_order]
                    writer.writerow(row)
        else:
            # JSON completo (incluye "_basic")
            with p.open("w", encoding="utf-8") as f:
                json.dump(summaries, f, indent=2)

    return summaries
