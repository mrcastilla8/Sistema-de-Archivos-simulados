# Owner: Dev 4
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Dict, Any
from ..sim.runner import run_simulation, STRATEGIES
from ..sim.scenario_definitions import DEFAULTS, load_from_json

def _parse_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    if args.disk_size: overrides["disk_size"] = args.disk_size
    if args.block_size: overrides["block_size"] = args.block_size
    return overrides

def cmd_list_strategies(_args: argparse.Namespace) -> int:
    print("\n".join(sorted(STRATEGIES.keys())))
    return 0

def cmd_list_scenarios(args: argparse.Namespace) -> int:
    merged = {**DEFAULTS, **load_from_json(args.scenarios) if args.scenarios else {}}
    for k, v in merged.items():
        print(f"{k}: {v.get('description', '')}")
    return 0

def cmd_run(args: argparse.Namespace) -> int:
    overrides = _parse_overrides(args)
    summaries = run_simulation(
        strategy_name=args.strategy,
        scenario=args.scenario,
        scenarios_path=args.scenarios,
        seed=args.seed,
        overrides=overrides,
        out=args.out
    )
    print(json.dumps(summaries, indent=2))
    return 0

def cmd_sweep(args: argparse.Namespace) -> int:
    # Sweep muy simple: variar block_size (ejemplo)
    keys_vals = [kv.split("=") for kv in args.vary.split(",")]
    matrix = {}
    for key, csv_vals in keys_vals:
        vals = [int(v) if v.isdigit() else v for v in csv_vals.split("|") if v]
        matrix[key] = vals

    results = {}
    for bs in matrix.get("block-size", [4096]):
        overrides = {"block_size": bs}
        out = args.out and str(Path(args.out).with_name(f"sweep_bs_{bs}").with_suffix(Path(args.out).suffix))
        res = run_simulation(
            strategy_name=args.strategy,
            scenario=args.scenario,
            scenarios_path=args.scenarios,
            seed=args.seed,
            overrides=overrides,
            out=out
        )
        results[str(bs)] = res
    print(json.dumps(results, indent=2))
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fsim", description="Filesystem Simulator (CLI)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list-strategies", help="Lista estrategias disponibles")
    sp.set_defaults(func=cmd_list_strategies)

    sp = sub.add_parser("list-scenarios", help="Lista escenarios disponibles")
    sp.add_argument("--scenarios", type=str, help="Ruta a data/scenarios.json")
    sp.set_defaults(func=cmd_list_scenarios)

    sp = sub.add_parser("run", help="Ejecuta una simulación")
    sp.add_argument("--strategy", type=str, choices=list(STRATEGIES.keys()) + ["all"], required=True)
    sp.add_argument("--scenario", type=str, help="Nombre del escenario predefinido")
    sp.add_argument("--scenarios", type=str, help="Ruta a data/scenarios.json")
    sp.add_argument("--disk-size", type=int, help="Bloques del disco")
    sp.add_argument("--block-size", type=int, help="Tamaño del bloque (bytes)")
    sp.add_argument("--seed", type=int, default=None, help="Semilla RNG")
    sp.add_argument("--out", type=str, help="Ruta de salida (CSV o JSON)")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("sweep", help="Barrido simple de parámetros")
    sp.add_argument("--strategy", type=str, choices=list(STRATEGIES.keys()) + ["all"], required=True)
    sp.add_argument("--scenario", type=str, required=True, help="Escenario base")
    sp.add_argument("--scenarios", type=str, help="Ruta a data/scenarios.json")
    sp.add_argument("--seed", type=int, default=None, help="Semilla RNG")
    sp.add_argument("--vary", type=str, required=True, help="Ej: block-size=1024|2048|4096")
    sp.add_argument("--out", type=str, help="Prefijo de archivo de salida (CSV o JSON)")
    sp.set_defaults(func=cmd_sweep)

    return p

def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
