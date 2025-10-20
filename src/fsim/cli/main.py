# src/fsim/cli/main.py
# Propietario: Dev 4
# Implementación de la interfaz de usuario interactiva en consola.

import sys
import os
import platform
from pathlib import Path
from typing import Dict, Any, List, Callable

# Importamos las funciones clave de los compañeros
try:
    from ..sim.runner import run_simulation, STRATEGIES
    from ..sim.scenario_definitions import available_scenarios
except ImportError:
    # Fallback para correr el script directamente si __main__ falla (menos común)
    print("Error: No se pudieron importar los módulos. Asegúrate de ejecutar como 'python -m src.fsim'")
    sys.exit(1)


# --- Constantes de configuración de la CLI ---

# Ruta donde buscamos escenarios (definida en la especificación)
SCENARIOS_JSON_PATH = "data/scenarios.json"
# Directorio donde guardamos los resultados
RESULTS_DIR = Path("results")

# --- Mapeos para Traducción ---
STRATEGY_NAMES_ES = {
    "contiguous": "Asignación Contigua",
    "linked": "Asignación Enlazada",
    "indexed": "Asignación Indexada",
}

SCENARIO_NAMES_ES = {
    "mix-small-large": "Mezcla Pequeños/Grandes",
    "seq-vs-rand": "Secuencial vs Aleatorio",
    "frag-intensive": "Fragmentación Intensiva",
}


# =============================================================================
# 1. Helpers de Visualización
# =============================================================================

def clear_screen():
    """Limpia la pantalla de la terminal (multiplataforma)."""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def print_header(title: str):
    """Imprime un encabezado visualmente atractivo."""
    print("\n" + "=" * 60)
    print(f"    {title.upper()}")
    print("=" * 60)

def print_error(message: str):
    """Imprime un mensaje de error estandarizado."""
    print(f"\n[ERROR]: {message}")

def print_success(message: str):
    """Imprime un mensaje de éxito estandarizado."""
    print(f"\n[EXITO]: {message}")

def print_results(summaries: Dict[str, Any], bitmaps: Dict[str, List[int]]):
    """
    Imprime una tabla formateada con el resumen de métricas.
    """
    print("\n" + "---" * 15)
    print("    RESUMEN DE METRICAS DE LA SIMULACION")
    print("---" * 15)
    
    for strategy, metrics in summaries.items():
        spanish_name = STRATEGY_NAMES_ES.get(strategy, strategy)
        print(f"\n  Estrategia: {strategy.upper()} ({spanish_name})")
        
        print(f"    - Tiempo Acceso Prom.: {metrics.get('avg_access_time_ms', 0):.3f} ms")
        print(f"    - Uso de Espacio:      {metrics.get('space_usage_pct', 0):.2f} %")
        print(f"    - Frag. Externa:       {metrics.get('fragmentation_external_pct', 0):.2f} %")
        print(f"    - Ops/Seg (Throughput): {metrics.get('throughput_ops_per_sec', 0):.2f}")
        print(f"    - Total Seeks (Est.):  {metrics.get('seeks_total_est', 0)}")
        print(f"    - Tiempo Total Sim.:   {metrics.get('elapsed_ms_total', 0):.2f} ms")
        
        bitmap_len = len(bitmaps.get(strategy, []))
        if bitmap_len > 0:
            print(f"    - (Bitmap final generado con {bitmap_len} bloques)")
            
    print("---" * 15)
    # SOLICITUD 2: Pausa para que el usuario pueda ver los resultados
    input("\n... Presiona Enter para continuar ...")


# =============================================================================
# 2. Funciones del Menú
# =============================================================================

def do_list_strategies():
    """Opción 1: Muestra las estrategias disponibles desde runner.py."""
    print_header("Estrategias Soportadas")
    print("Estas son las estrategias que el Runner puede ejecutar:")
    
    for key in STRATEGIES.keys():
        spanish_name = STRATEGY_NAMES_ES.get(key, key)
        print(f"  - {key} ({spanish_name})")

def do_list_scenarios():
    """Opción 2: Muestra los escenarios desde scenario_definitions.py."""
    print_header("Escenarios Disponibles")
    print(f"Cargando escenarios desde {SCENARIOS_JSON_PATH}...")
    try:
        scens = available_scenarios(SCENARIOS_JSON_PATH)
        
        if not scens:
            print("  No se encontraron escenarios en DEFAULTS ni en el archivo JSON.")
            return
            
        for name, desc in scens.items():
            spanish_name = SCENARIO_NAMES_ES.get(name, name)
            print(f"\n  - {name} ({spanish_name}):")
            print(f"      {desc}") 
                        
    except Exception as e:
        print_error(f"No se pudo cargar o leer '{SCENARIOS_JSON_PATH}': {e}")

def do_run_simulation():
    """Opción 3: Guía al usuario para ejecutar una simulación única."""
    print_header("Ejecutar Simulacion Unica")
    
    # ... (lógica para elegir estrategia, escenario, etc.)
    print("Estrategias disponibles:")
    strat_list = list(STRATEGIES.keys())
    for i, s in enumerate(strat_list):
        spanish_name = STRATEGY_NAMES_ES.get(s, s)
        print(f"  {i+1}) {s} ({spanish_name})")
    try:
        choice = int(input("Elige una estrategia (numero): ")) - 1
        strategy_name = strat_list[choice]
    except (ValueError, IndexError):
        print_error("Seleccion invalida.")
        return

    print("\nEscenarios disponibles:")
    try:
        scen_map = available_scenarios(SCENARIOS_JSON_PATH)
    except Exception as e:
        print_error(f"No se pudieron cargar escenarios: {e}")
        return
        
    scen_list = list(scen_map.keys())
    for i, s in enumerate(scen_list):
        spanish_name = SCENARIO_NAMES_ES.get(s, s)
        print(f"  {i+1}) {s} ({spanish_name})")
    try:
        choice = int(input("Elige un escenario (numero): ")) - 1
        scenario = scen_list[choice]
    except (ValueError, IndexError):
        print_error("Seleccion invalida.")
        return

    seed_str = input("\nIntroduce una 'seed' (semilla) numerica (ej. 42, o deja vacio para aleatorio): ")
    seed = int(seed_str) if seed_str.isdigit() else None
    
    out_path = None
    save_choice = input(f"\nDeseas guardar los resultados en un archivo? (s/n) [n]: ").lower().strip()
    
    if save_choice == 's':
        default_out = f"run_{strategy_name}_{scenario}.json"
        out_file_str = input(f"  Nombre del archivo (en 'results/'): [{default_out}] ")
        if not out_file_str:
            out_file_str = default_out
        out_path = RESULTS_DIR / out_file_str
    
    print(f"\nIniciando simulacion: {strategy_name} | {scenario} | seed={seed}...")
    
    try:
        summaries, bitmaps = run_simulation(
            strategy_name=strategy_name,
            scenario=scenario,
            scenarios_path=SCENARIOS_JSON_PATH,
            seed=seed,
            overrides={},
            out=str(out_path) if out_path else None
        )
        
        if out_path:
            print_success(f"Simulacion completada. Resultados guardados en {out_path}")
        else:
            print_success("Simulacion completada.")

        print_results(summaries, bitmaps)

    except Exception as e:
        print_error(f"La simulacion fallo: {e}")

def do_run_sweep():
    """Opción 4: Ejecuta un barrido de TODAS las estrategias en UN escenario."""
    print_header("Ejecutar Barrido (Sweep)")
    print("Este modo ejecutara 'TODAS' las estrategias en un solo escenario.")

    # ... (lógica para elegir escenario, etc.)
    print("\nEscenarios disponibles:")
    try:
        scen_map = available_scenarios(SCENARIOS_JSON_PATH)
    except Exception as e:
        print_error(f"No se pudieron cargar escenarios: {e}")
        return
        
    scen_list = list(scen_map.keys())
    for i, s in enumerate(scen_list):
        spanish_name = SCENARIO_NAMES_ES.get(s, s)
        print(f"  {i+1}) {s} ({spanish_name})")
    try:
        choice = int(input("Elige un escenario para el barrido: ")) - 1
        scenario = scen_list[choice]
    except (ValueError, IndexError):
        print_error("Seleccion invalida.")
        return
    
    seed_str = input("\nIntroduce una 'seed' (semilla) numerica (ej. 42, o deja vacio para aleatorio): ")
    seed = int(seed_str) if seed_str.isdigit() else None
    
    default_out = f"sweep_{scenario}.csv" 
    out_file_str = input(f"\nNombre del archivo de resultados (en 'results/'): [{default_out}] ")
    if not out_file_str:
        out_file_str = default_out
    out_path = RESULTS_DIR / out_file_str

    print(f"\nIniciando BARRIDO: 'all' estrategias | {scenario} | seed={seed}...")
    
    try:
        summaries, bitmaps = run_simulation(
            strategy_name="all",
            scenario=scenario,
            scenarios_path=SCENARIOS_JSON_PATH,
            seed=seed,
            overrides={},
            out=str(out_path) 
        )
        print_success(f"Barrido completado. Resultados guardados en {out_path}")
        print_results(summaries, bitmaps)

    except Exception as e:
        print_error(f"El barrido fallo: {e}")

def do_exit():
    """Opción 5: Salir del programa."""
    print("\nPrograma Finalizado\n")
    sys.exit()

def print_menu():
    """Muestra el menú principal."""
    print_header("Simulador de Sistema de Archivos")
    print("  1. Listar estrategias disponibles")
    print("  2. Listar escenarios de prueba")
    print("  3. Ejecutar una simulacion unica")
    print("  4. Ejecutar un barrido (todas las estrategias en 1 escenario)")
    print("  5. Salir")
    print("-" * 60)


# =============================================================================
# 3. Función Principal (Entry Point)
# =============================================================================

def main():
    """
    Función principal que ejecuta el bucle del menú interactivo.
    """
    try:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print_error(f"No se pudo crear el directorio 'results': {e}")
        sys.exit(1)
    
    menu_options: Dict[str, Callable[[], None]] = {
        "1": do_list_strategies,
        "2": do_list_scenarios,
        "3": do_run_simulation,
        "4": do_run_sweep,
        "5": do_exit,
    }

    while True:
        # SOLICITUD 1: Limpiar la pantalla antes de mostrar el menú
        clear_screen()
        print_menu()
        choice = input("Selecciona una opcion (1-5): ")
        
        action = menu_options.get(choice)
        
        if action:
            # Limpiar pantalla antes de ejecutar la acción para una vista más limpia
            clear_screen()
            action()
        else:
            print_error("Opcion no valida. Por favor, intenta de nuevo.")
        
        # Pausa genérica para acciones que no la tienen (como listar)
        if choice not in ("3", "4", "5"): # Las simulaciones ya tienen su propia pausa
            input("\n... Presiona Enter para continuar ...")

if __name__ == "__main__":
    main()
