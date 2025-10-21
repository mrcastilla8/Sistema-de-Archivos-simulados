# Owner: Dev 1
from __future__ import annotations
import csv, json, time
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional, Tuple

from ..core.disk import Disk
from ..core.free_space import FreeSpaceManager
from ..fs_strategies.contiguous import ContiguousFS
from ..fs_strategies.linked import LinkedFS
from ..fs_strategies.indexed import IndexedFS
from .scenario_definitions import DEFAULTS, load_from_json
from .workload_generators import generate_workload
from .metrics import summarize, full_metrics_summary

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
    def on_event(event_type: str, **payload: Any) -> None:
        collector["last_event"] = (event_type, payload)
        phys = payload.get("physical")
        if isinstance(phys, list) and phys:
            seeks = 0
            for i in range(len(phys) - 1):
                if phys[i + 1] != phys[i] + 1:
                    seeks += 1
            collector["seeks"] = collector.get("seeks", 0) + seeks
        nb = payload.get("n_blocks")
        if isinstance(nb, int) and nb > 0:
            collector["blocks_touched"] = collector.get("blocks_touched", 0) + nb
    return on_event


def _snapshot_state(fsm: FreeSpaceManager) -> Dict[str, float]:
    total = fsm.n_blocks
    used = fsm.used_count()
    usage_pct = (used / total) * 100 if total > 0 else 0.0
    ext_frag = fsm.external_fragmentation_ratio()
    return {
        "space_used": float(used),
        "space_total": float(total),
        "external_frag": float(ext_frag),
        "internal_frag": 0.0,
    }


def run_simulation(
    strategy_name: str,
    scenario: str | None,
    scenarios_path: str | None,
    seed: int | None,
    overrides: Dict[str, Any],
    out: str | None = None,
    on_bitmap_update: Optional[Callable[[str, List[int]], None]] = None,
    # --- MODIFICACIÓN: Añadir parámetro de freno ---
    ui_slowdown_ms: Optional[int] = None # Milisegundos de pausa por operación
    # --- FIN MODIFICACIÓN ---
) -> Tuple[Dict[str, Any], Dict[str, List[int]]]:
    """
    Ejecuta la simulación...
    """
    if strategy_name not in STRATEGIES and strategy_name != "all":
        raise KeyError(f"Estrategia inválida: {strategy_name}")

    cfg = build_config(scenario, scenarios_path, overrides)
    ops = generate_workload(cfg, seed=seed)

    strategies = list(STRATEGIES.keys()) if strategy_name == "all" else [strategy_name]
    summaries: Dict[str, Dict[str, Any]] = {}
    final_bitmaps: Dict[str, List[int]] = {}

    # --- MODIFICACIÓN: Convertir ms a segundos ---
    sleep_duration_s = 0.0
    if ui_slowdown_ms and ui_slowdown_ms > 0:
        sleep_duration_s = ui_slowdown_ms / 1000.0
    # --- FIN MODIFICACIÓN ---

    for s in strategies:
        disk_size = cfg.get("disk_size", 50000)
        block_size = cfg.get("block_size", 4096)
        
        max_blocks_for_ui = 50000 
        if disk_size > max_blocks_for_ui:
            disk_size = max_blocks_for_ui

        disk = Disk(
            n_blocks=disk_size,
            block_size=block_size,
            prefill=None,
        )

        fsm_callback = None
        if on_bitmap_update:
            def create_callback(strategy_key: str):
                return lambda bitmap: on_bitmap_update(strategy_key, bitmap)
            fsm_callback = create_callback(s)

        fsm = FreeSpaceManager(
            disk.n_blocks, 
            on_bitmap_update=fsm_callback
        )

        results: List[Dict[str, Any]] = []
        event_acc: Dict[str, Any] = {}
        on_event = _make_event_handler(event_acc)
        fs_class = STRATEGIES[s]
        fs = fs_class(disk, fsm, on_event=on_event)

        sim_start_wall = time.perf_counter()
        sim_start_cpu = time.process_time()

        for op in ops:
            event_acc.clear()
            op_name = op.get("op")
            t0_wall = time.perf_counter()
            t0_cpu = time.process_time()
            hit, miss = 1, 0

            try:
                if op_name == "create":
                    fs.create(op["name"], op["size_blocks"])
                elif op_name == "delete":
                    fs.delete(op["name"])
                elif op_name == "read":
                    fs.read(op["name"], op["offset"], op["n_blocks"], op.get("access_mode", "seq"))
                elif op_name == "write":
                    fs.write(op["name"], op["offset"], op["n_blocks"], None)
                else:
                    hit, miss = 0, 1
            except Exception:
                hit, miss = 0, 1

            op_elapsed_ms = (time.perf_counter() - t0_wall) * 1000.0
            op_cpu_s = (time.process_time() - t0_cpu)
            snap = _snapshot_state(fsm)

            # --- MODIFICACIÓN: Pausar el hilo de simulación ---
            if sleep_duration_s > 0:
                time.sleep(sleep_duration_s)
            # --- FIN MODIFICACIÓN ---

            result: Dict[str, Any] = {
                "strategy": s, "operation": op_name,
                "access_time_ms": float(op_elapsed_ms),
                "elapsed_time_s": float(op_elapsed_ms / 1000.0),
                "cpu_time": float(op_cpu_s), "hits": hit, "misses": miss,
                "seeks_est": int(event_acc.get("seeks", 0)),
                "blocks_touched": int(event_acc.get("blocks_touched", 0)),
                **snap,
            }
            results.append(result)

        # ... (resto del runner.py sin cambios) ...
        total_elapsed_s = time.perf_counter() - sim_start_wall
        total_cpu_s = time.process_time() - sim_start_cpu
        results.append({
            "strategy": s, "operation": "TOTAL",
            "access_time_ms": total_elapsed_s * 1000.0 / max(1, (len(results) or 1)),
            "elapsed_time_s": total_elapsed_s, "cpu_time": total_cpu_s,
            "hits": sum(r["hits"] for r in results if r.get("operation") != "TOTAL"),
            "misses": sum(r["misses"] for r in results if r.get("operation") != "TOTAL"),
            "seeks_est": sum(r["seeks_est"] for r in results if r.get("operation") != "TOTAL"),
            "blocks_touched": sum(r["blocks_touched"] for r in results if r.get("operation") != "TOTAL"),
            **_snapshot_state(fsm),
        })
        summary_ext = full_metrics_summary(results)
        summary_basic = summarize(results)
        summary_ext["elapsed_ms_total"] = round(total_elapsed_s * 1000.0, 3)
        summary_ext["cpu_time_total_s"] = round(total_cpu_s, 6)
        summary_ext["ops_count"] = sum(1 for r in results if r.get("operation") not in ("TOTAL", None))
        summary_ext["seeks_total_est"] = int(sum(r["seeks_est"] for r in results if r.get("operation") != "TOTAL"))
        summary_ext["_scenario"] = scenario or "overrides-only"
        summary_ext["_seed"] = seed
        summaries[s] = { **summary_ext, "_basic": summary_basic, }
        final_bitmaps[s] = fsm.snapshot_bitmap()

    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() == ".csv":
            key_order = [
                "avg_access_time_ms", "space_usage_pct", "fragmentation_internal_pct",
                "fragmentation_external_pct", "throughput_ops_per_sec", "hit_miss_ratio",
                "cpu_usage_pct", "fairness_index", "elapsed_ms_total",
                "cpu_time_total_s", "ops_count", "seeks_total_est",
            ]
            with p.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["strategy"] + key_order)
                for strat, vals in summaries.items():
                    row = [strat] + [vals.get(k, "") for k in key_order]
                    writer.writerow(row)
        else:
            with p.open("w", encoding="utf-8") as f:
                json.dump(summaries, f, indent=2)

    return summaries, final_bitmaps