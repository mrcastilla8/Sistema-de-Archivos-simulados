# Owner: Dev 1
from __future__ import annotations
import csv, json, time
from pathlib import Path
from typing import Dict, Any, List
from ..core.disk import Disk
from ..core.free_space import FreeSpaceManager
from ..fs_strategies.contiguous import ContiguousFS
from ..fs_strategies.linked import LinkedFS
from ..fs_strategies.indexed import IndexedFS
from .scenario_definitions import DEFAULTS, load_from_json
from .workload_generators import generate_workload
from .metrics import summarize

STRATEGIES = {
    "contiguous": ContiguousFS,
    "linked": LinkedFS,
    "indexed": IndexedFS,
}

def build_config(scenario: str | None, scenarios_path: str | None, overrides: Dict[str, Any]) -> Dict[str, Any]:
    cfg = {}
    if scenario:
        cfgs = {**DEFAULTS, **load_from_json(scenarios_path) if scenarios_path else {}}
        if scenario not in cfgs:
            raise KeyError(f"Escenario '{scenario}' no existe")
        cfg.update(cfgs[scenario])
    cfg.update(overrides or {})
    return cfg

def run_simulation(strategy_name: str, scenario: str | None, scenarios_path: str | None, seed: int | None,
                   overrides: Dict[str, Any], out: str | None = None) -> Dict[str, Any]:
    if strategy_name not in STRATEGIES and strategy_name != "all":
        raise KeyError(f"Estrategia inválida: {strategy_name}")

    cfg = build_config(scenario, scenarios_path, overrides)
    disk = Disk(n_blocks=cfg.get("disk_size", 50000), block_size=cfg.get("block_size", 4096))
    fsm = FreeSpaceManager(disk.n_blocks)
    ops = generate_workload(cfg, seed=seed)

    strategies = STRATEGIES.keys() if strategy_name == "all" else [strategy_name]
    summaries = {}

    for s in strategies:
        results: List[Dict[str, Any]] = []
        fs_class = STRATEGIES[s]
        fs = fs_class(disk, fsm)
        start = time.perf_counter()
        for op in ops:
            try:
                if op["op"] == "create":
                    fs.create(op["name"], op["size_blocks"])
                elif op["op"] == "delete":
                    try:
                        fs.delete(op["name"])
                    except Exception:
                        pass  # si no existe, ignorar en stub
                elif op["op"] == "read":
                    fs.read(op["name"], op["offset"], op["n_blocks"], op["access_mode"])
                elif op["op"] == "write":
                    fs.write(op["name"], op["offset"], op["n_blocks"], None)
            except NotImplementedError:
                # Estrategia aún no implementada; registramos y continuamos.
                pass
        elapsed = (time.perf_counter() - start) * 1000.0  # ms
        results.append({"operation": "TOTAL", "elapsed_ms": elapsed})
        summary = summarize(results)
        summary["elapsed_ms_total"] = elapsed
        summaries[s] = summary

    if out:
        p = Path(out)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() == ".csv":
            with p.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = ["strategy"] + list(next(iter(summaries.values())).keys())
                writer.writerow(headers)
                for k, v in summaries.items():
                    writer.writerow([k] + [v[h] for h in headers[1:]])
        else:
            with p.open("w", encoding="utf-8") as f:
                json.dump(summaries, f, indent=2)
    return summaries
