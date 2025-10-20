# src/fsim/cli/main.py
# Propietario: Dev 4
# Implementación de la interfaz de usuario interactiva en consola.

import sys
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

# --- Mapeos para Traducción (SOLICITUD 1 y 2) ---
STRATEGY_NAMES_ES = {
    "contiguous": "Asignación Contigua",
    "linked": "Asignación Enlazada",
    "indexed": "Asignación Indexada",
}

# (Este mapeo es para las claves de los escenarios)
SCENARIO_NAMES_ES = {
    "mix-small-large": "Mezcla Pequeños/Grandes",
    "seq-vs-rand": "Secuencial vs Aleatorio",
    "frag-intensive": "Fragmentación Intensiva",
}


# =============================================================================
# 1. Helpers de Visualización
# =============================================================================

def print_header(title: str):
    """Imprime un encabezado visualmente atractivo."""
    print("\n" + "=" * 60)
    print(f"    🚀 {title.upper()} 🚀")
    print("=" * 60)

def print_error(message: str):
    """Imprime un mensaje de error estandarizado."""
    print(f"\n[ERROR] ❌: {message}")

def print_success(message: str):
    """Imprime un mensaje de éxito estandarizado."""
    print(f"\n[ÉXITO] ✅: {message}")

def print_results(summaries: Dict[str, Any], bitmaps: Dict[str, List[int]]):
    """
    Imprime una tabla formateada con el resumen de métricas.
    El runner.py modificado ahora devuelve (summaries, bitmaps).
    """
    print("\n" + "---" * 15)
    print("    📊 RESUMEN DE MÉTRICAS DE LA SIMULACIÓN 📊")
    print("---" * 15)
    
    for strategy, metrics in summaries.items():
        # Usamos el mapeo para mostrar el nombre en español aquí también
        spanish_name = STRATEGY_NAMES_ES.get(strategy, strategy)
        print(f"\n  Estrategia: {strategy.upper()} ({spanish_name})")
        
        print(f"    - Tiempo Acceso Prom.: {metrics.get('avg_access_time_ms', 0):.3f} ms")
        print(f"    - Uso de Espacio:      {metrics.get('space_usage_pct', 0):.2f} %")
        print(f"    - Frag. Externa:       {metrics.get('fragmentation_external_pct', 0):.2f} %")
        print(f"    - Ops/Seg (Throughput): {metrics.get('throughput_ops_per_sec', 0):.2f}")
        print(f"    - Total Seeks (Est.):  {metrics.get('seeks_total_est', 0)}")
        print(f"    - Tiempo Total Sim.:   {metrics.get('elapsed_ms_total', 0):.2f} ms")
        
        # Mencionamos el bitmap generado para la UI (Dev 5)
        bitmap_len = len(bitmaps.get(strategy, []))
        if bitmap_len > 0:
            print(f"    - (Bitmap final generado con {bitmap_len} bloques)")
            
    print("---" * 15)


# =============================================================================
# 2. Funciones del Menú
# =============================================================================

def do_list_strategies():
    """Opción 1: Muestra las estrategias disponibles desde runner.py."""
    print_header("Estrategias Soportadas")
    print("Estas son las estrategias que el Runner puede ejecutar:")
    
    # Leemos el diccionario STRATEGIES del Dev 1
    for key in STRATEGIES.keys():
        # SOLICITUD 1: Añadir nombre en español
        spanish_name = STRATEGY_NAMES_ES.get(key, key)
        print(f"  - {key} ({spanish_name})")

def do_list_scenarios():
    """Opción 2: Muestra los escenarios desde scenario_definitions.py."""
    print_header("Escenarios Disponibles")
    print(f"Cargando escenarios desde {SCENARIOS_JSON_PATH}...")
    try:
        # Usamos la API del Dev 1 para listar escenarios
        scens = available_scenarios(SCENARIOS_JSON_PATH)
        
        if not scens:
            print("  No se encontraron escenarios en DEFAULTS ni en el archivo JSON.")
            return
            
        for name, desc in scens.items():
            # SOLICITUD 2: Añadir nombre en español
            spanish_name = SCENARIO_NAMES_ES.get(name, name)
            print(f"\n  - {name} ({spanish_name}):")
            
            # La descripción (desc) ya viene en español desde el archivo .py
            # (Ej: "60% secuencial, 40% aleatorio")
            print(f"      {desc}") 
                        
    except Exception as e:
        print_error(f"No se pudo cargar o leer '{SCENARIOS_JSON_PATH}': {e}")

def do_run_simulation():
    """Opción 3: Guía al usuario para ejecutar una simulación única."""
    print_header("Ejecutar Simulación Única")
    
    # 1. Elegir Estrategia
    print("Estrategias disponibles:")
    strat_list = list(STRATEGIES.keys()) #
    for i, s in enumerate(strat_list):
        spanish_name = STRATEGY_NAMES_ES.get(s, s)
        print(f"  {i+1}) {s} ({spanish_name})")
    try:
        choice = int(input("Elige una estrategia (número): ")) - 1
        strategy_name = strat_list[choice]
    except (ValueError, IndexError):
        print_error("Selección inválida.")
        return

    # 2. Elegir Escenario
    print("\nEscenarios disponibles:")
    try:
        scen_map = available_scenarios(SCENARIOS_JSON_PATH) #
    except Exception as e:
        print_error(f"No se pudieron cargar escenarios: {e}")
        return
        
    scen_list = list(scen_map.keys())
    for i, s in enumerate(scen_list):
        spanish_name = SCENARIO_NAMES_ES.get(s, s)
        print(f"  {i+1}) {s} ({spanish_name})")
    try:
        choice = int(input("Elige un escenario (número): ")) - 1
        scenario = scen_list[choice]
    except (ValueError, IndexError):
        print_error("Selección inválida.")
        return

    # 3. Seed (Semilla)
    seed_str = input("\nIntroduce una 'seed' (semilla) numérica (ej. 42, o deja vacío para aleatorio): ")
    seed = int(seed_str) if seed_str.isdigit() else None
    
    # 4. Archivo de Salida (MODIFICADO - SOLICITUD 3)
    out_path = None # Por defecto, no se guarda
    save_choice = input(f"\n¿Deseas guardar los resultados en un archivo? (s/n) [n]: ").lower().strip()
    
    if save_choice == 's':
        default_out = f"run_{strategy_name}_{scenario}.json"
        out_file_str = input(f"  Nombre del archivo (en 'results/'): [{default_out}] ")
        if not out_file_str:
            out_file_str = default_out
        out_path = RESULTS_DIR / out_file_str
    
    print(f"\nIniciando simulación: {strategy_name} | {scenario} | seed={seed}...")
    
    try:
        # Llamada principal al Runner del Dev 1
        summaries, bitmaps = run_simulation(
            strategy_name=strategy_name,
            scenario=scenario,
            scenarios_path=SCENARIOS_JSON_PATH,
            seed=seed,
            overrides={}, # No usamos overrides en modo interactivo simple
            out=str(out_path) if out_path else None # Pasa el path o None
        )
        
        # SOLICITUD 3: Imprimimos el resumen (al igual que en el barrido)
        print_results(summaries, bitmaps) 
        
        if out_path:
            print_success(f"Simulación completada. Resultados guardados en {out_path}")
        else:
            print_success("Simulación completada.")

    except Exception as e:
        print_error(f"La simulación falló: {e}")
        if "KeyError" in str(e):
            print_error(f"Detalle: El escenario '{scenario}' no se encontró. Verifica el JSON.")

def do_run_sweep():
    """Opción 4: Ejecuta un barrido de TODAS las estrategias en UN escenario."""
    print_header("Ejecutar Barrido (Sweep)")
    print("Este modo ejecutará 'TODAS' las estrategias en un solo escenario.")

    # 1. Elegir Escenario
    print("\nEscenarios disponibles:")
    try:
        scen_map = available_scenarios(SCENARIOS_JSON_PATH) #
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
        print_error("Selección inválida.")
        return
    
    # 2. Seed (Semilla)
    seed_str = input("\nIntroduce una 'seed' (semilla) numérica (ej. 42, o deja vacío para aleatorio): ")
    seed = int(seed_str) if seed_str.isdigit() else None
    
    # 3. Archivo de Salida
    # Los barridos (sweeps) se guardan mejor como CSV
    default_out = f"sweep_{scenario}.csv" 
    out_file_str = input(f"\nNombre del archivo de resultados (en 'results/'): [{default_out}] ")
    if not out_file_str:
        out_file_str = default_out
    out_path = RESULTS_DIR / out_file_str

    print(f"\nIniciando BARRIDO: 'all' estrategias | {scenario} | seed={seed}...")
    
    try:
        # Llamada principal al Runner, pidiendo "all" estrategias
        summaries, bitmaps = run_simulation(
            strategy_name="all", # <-- Clave para el barrido
            scenario=scenario,
            scenarios_path=SCENARIOS_JSON_PATH,
            seed=seed,
            overrides={},
            out=str(out_path) 
        )
        print_success(f"Barrido completado. Resultados guardados en {out_path}")
        # El barrido (sweep) ya imprimía los resultados, lo cual era correcto
        print_results(summaries, bitmaps)

    except Exception as e:
        print_error(f"El barrido falló: {e}")

def do_exit():
    """Opción 5: Salir del programa."""
    print("\nPrograma finalizado\n")
    sys.exit()

def print_menu():
    """Muestra el menú principal."""
    print_header("Simulador de Sistema de Archivos")
    print("  1. Listar estrategias disponibles")
    print("  2. Listar escenarios de prueba")
    print("  3. Ejecutar una simulación única")
    print("  4. Ejecutar un barrido (todas las estrategias en 1 escenario)")
    print("  5. Salir")
    print("-" * 60)


# =============================================================================
# 3. Función Principal (Entry Point)
# =============================================================================

def main():
    """
    Función principal que ejecuta el bucle del menú interactivo.
    Esta función es llamada por src/fsim/__main__.py.
    """
    
    # Asegurarse de que el directorio de resultados exista
    try:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print_error(f"No se pudo crear el directorio 'results': {e}")
        sys.exit(1)
    
    # Mapeo de opciones a funciones
    menu_options: Dict[str, Callable[[], None]] = {
        "1": do_list_strategies,
        "2": do_list_scenarios,
        "3": do_run_simulation,
        "4": do_run_sweep,
        "5": do_exit,
    }

    # Bucle principal del programa
    while True:
        print_menu()
        choice = input("Selecciona una opción (1-5): ")
        
        action = menu_options.get(choice)
        
        if action:
            action()
        else:
            print_error("Opción no válida. Por favor, intenta de nuevo.")
        
        if choice != "5":
            input("\n... Presiona Enter para continuar ...")

# Esta guarda es necesaria para que __main__.py funcione correctamente
if __name__ == "__main__":
    main()