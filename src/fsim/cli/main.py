import sys
import os
import platform
import json
import csv
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional, Tuple

# Importamos las funciones clave de los compañeros
try:
    from ..sim.runner import run_simulation, STRATEGIES
    from ..sim.scenario_definitions import available_scenarios
except ImportError:
    print("Error: No se pudieron importar los módulos. Asegúrate de ejecutar como 'python -m src.fsim'")
    sys.exit(1)


# --- Constantes de configuración de la CLI ---
SCENARIOS_JSON_PATH = "data/scenarios.json"
RESULTS_DIR = Path("results")
MANIFEST_PREVIEW_COUNT = 15  # Número de archivos a mostrar en el resumen

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

def print_results(
    summaries: Dict[str, Any], 
    bitmaps: Dict[str, List[int]]
):
    """
    Imprime una tabla formateada con el resumen de métricas
    Y el nuevo manifiesto de archivos (SOLICITUD 2).
    """
    print("\n" + "---" * 20)
    print("    RESUMEN DE METRICAS DE LA SIMULACION")
    print("---" * 20)
    
    for strategy, metrics in summaries.items():
        spanish_name = STRATEGY_NAMES_ES.get(strategy, strategy)
        print(f"\n  Estrategia: {strategy.upper()} ({spanish_name})")
        
        # --- Métricas de rendimiento ---
        print(f"    - Tiempo Acceso Prom.: {metrics.get('avg_access_time_ms', 0):.3f} ms")
        print(f"    - Uso de Espacio:      {metrics.get('space_usage_pct', 0):.2f} %")
        print(f"    - Frag. Externa:       {metrics.get('fragmentation_external_pct', 0):.2f} %")
        print(f"    - Ops/Seg (Throughput): {metrics.get('throughput_ops_per_sec', 0):.2f}")
        print(f"    - Total Seeks (Est.):  {metrics.get('seeks_total_est', 0)}")
        print(f"    - Tiempo Total Sim.:   {metrics.get('elapsed_ms_total', 0):.2f} ms")
        
        bitmap_len = len(bitmaps.get(strategy, []))
        if bitmap_len > 0:
            print(f"    - (Bitmap final generado con {bitmap_len} bloques)")
            
        # --- SOLICITUD 2: Manifiesto de Archivos ---
        manifest = metrics.get("files_manifest", [])
        if manifest:
            total_files = len(manifest)
            alive_files = sum(1 for f in manifest if f.get("alive"))
            
            print(f"    {'-'*64}")
            print(f"    MANIFEST DE ARCHIVOS (Total: {total_files}, Vivos: {alive_files})")
            print(f"    {'-'*64}")
            
            # Encabezados de la tabla
            print(f"    {'Nombre':<20} {'Tam (Blq)':<10} {'Estado':<10} {'Lecturas':<8} {'Escrituras':<10}")
            
            # Imprimir las primeras N filas
            for f in manifest[:MANIFEST_PREVIEW_COUNT]:
                name = str(f.get("name", "?"))[:18]  # Truncar nombre
                size = f.get("size_blocks", 0)
                status = "Vivo" if f.get("alive") else "Borrado"
                reads = f.get("read_ops", 0)
                writes = f.get("write_ops", 0)
                
                print(f"    {name:<20} {size:<10} {status:<10} {reads:<8} {writes:<10}")
            
            if total_files > MANIFEST_PREVIEW_COUNT:
                print(f"    ... y {total_files - MANIFEST_PREVIEW_COUNT} archivos mas.")
            
    print("---" * 20)
    # Pausa para que el usuario pueda ver los resultados
    input("\n... Presiona Enter para continuar ...")


# =============================================================================
# 2. Helpers de Captura de Archivos (SOLICITUD 1)
# =============================================================================

def _capture_manual_files_interactive() -> Optional[List[Dict[str, Any]]]:
    """Captura interactiva de archivos manuales."""
    clear_screen()
    print_header("Ingreso Interactivo de Archivos")
    user_files = []
    
    while True:
        name = input(f"  Nombre del archivo (deja vacio para terminar): ").strip()
        if not name:
            break
            
        size_str = input(f"  Tamano en bloques para '{name}': ").strip()
        try:
            size_blocks = int(size_str)
            if size_blocks <= 0:
                print_error("El tamano debe ser un entero mayor a 0.")
                continue
            
            user_files.append({"name": name, "size_blocks": size_blocks})
            print_success(f"Archivo '{name}' (tam: {size_blocks}) agregado.")
            
        except ValueError:
            print_error("Entrada invalida. El tamano debe ser un numero.")
            
    return user_files if user_files else None

def _capture_manual_files_import() -> Optional[List[Dict[str, Any]]]:
    """Captura de archivos manuales desde un archivo CSV o JSON."""
    clear_screen()
    print_header("Importar Archivos desde CSV/JSON")
    path_str = input("  Ruta al archivo (ej: 'data/mis_archivos.json' o 'data/mis_archivos.csv'): ").strip()
    
    user_files = []
    
    try:
        path = Path(path_str)
        if not path.exists():
            print_error(f"El archivo no existe en: {path_str}")
            return None
            
        with path.open("r", encoding="utf-8") as f:
            if path_str.endswith(".json"):
                data = json.load(f)
                if not isinstance(data, list):
                    print_error("El JSON debe ser una *lista* de objetos.")
                    return None
                
                for i, item in enumerate(data):
                    name = item.get("name")
                    size = item.get("size_blocks")
                    if not isinstance(name, str) or not isinstance(size, int) or size <= 0:
                        print_error(f"Error en JSON (item {i}): debe tener 'name' (str) y 'size_blocks' (int > 0).")
                        return None
                    user_files.append({"name": name, "size_blocks": size})
                    
            elif path_str.endswith(".csv"):
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    name = row.get("name")
                    size_str = row.get("size_blocks")
                    if not name or not size_str:
                        print_error(f"Error en CSV (fila {i+1}): Faltan cabeceras 'name' o 'size_blocks'.")
                        return None
                    
                    try:
                        size = int(size_str)
                        if size <= 0:
                            raise ValueError()
                        user_files.append({"name": name, "size_blocks": size})
                    except ValueError:
                        print_error(f"Error en CSV (fila {i+1}): 'size_blocks' ('{size_str}') debe ser un int > 0.")
                        return None
            else:
                print_error("Formato no soportado. Use .json o .csv")
                return None
                
    except json.JSONDecodeError:
        print_error("Error al parsear el JSON. Verifica la sintaxis.")
        return None
    except FileNotFoundError:
        print_error(f"El archivo no existe en: {path_str}")
        return None
    except Exception as e:
        print_error(f"Ocurrio un error inesperado al leer el archivo: {e}")
        return None

    print_success(f"Se importaron {len(user_files)} archivos exitosamente desde {path_str}.")
    return user_files if user_files else None

def _configure_workload() -> Optional[Tuple[Optional[List[Dict[str, Any]]], bool, Optional[int]]]:
    """
    Paso interactivo para configurar la carga de trabajo (Aleatoria vs Manual).
    Devuelve: (user_files, respect_user_files_only, seed) o None si se aborta.
    """
    clear_screen()
    print_header("Configuracion de Carga de Trabajo")
    print("  1) Aleatorios")
    print("  2) Archivos Manuales")
    
    choice = input("Selecciona el tipo de carga de trabajo (1-2): ").strip()
    
    user_files: Optional[List[Dict[str, Any]]] = None
    respect_user_files_only: bool = False
    
    if choice == "1":
        # Modo Aleatorio
        pass # user_files se queda en None, respect_user_files_only en False
        
    elif choice == "2":
        # Modo Manual
        print("\n  Como deseas ingresar los archivos manuales?")
        print("    1) Interactivamente (uno por uno)")
        print("    2) Importar desde archivo (CSV o JSON)")
        
        sub_choice = input("  Selecciona una opcion (1-2): ").strip()
        if sub_choice == "1":
            user_files = _capture_manual_files_interactive()
        elif sub_choice == "2":
            user_files = _capture_manual_files_import()
        else:
            print_error("Opcion invalida.")
            return None # Abortar

        if not user_files:
            print_error("No se ingresaron archivos manuales. Abortando simulacion.")
            return None # Abortar
            
        print("\n  Como deben usarse estos archivos manuales?")
        print("    1) Solo usar manuales (ignorar aleatorios del escenario)")
        print("    2) Combinar (agregar manuales + aleatorios del escenario)")
        
        respect_choice = input("  Selecciona una opcion (1-2): ").strip()
        if respect_choice == "1":
            respect_user_files_only = True
        elif respect_choice == "2":
            respect_user_files_only = False
        else:
            print_error("Opcion invalida.")
            return None # Abortar
            
    else:
        print_error("Opcion invalida.")
        return None # Abortar

    # Pedir la SEED en ambos modos (para el generador de operaciones)
    seed_str = input("\nIntroduce una 'seed' (semilla) numerica (ej. 42, o deja vacio para aleatorio): ")
    seed = int(seed_str) if seed_str.isdigit() else None
    
    return user_files, respect_user_files_only, seed


# =============================================================================
# 3. Funciones del Menú Principal
# =============================================================================

def do_list_strategies():
    """Opción 1: Muestra las estrategias disponibles."""
    print_header("Estrategias Soportadas")
    print("Estas son las estrategias que el Runner puede ejecutar:")
    for key in STRATEGIES.keys():
        spanish_name = STRATEGY_NAMES_ES.get(key, key)
        print(f"  - {key} ({spanish_name})")

def do_list_scenarios():
    """Opción 2: Muestra los escenarios disponibles."""
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
    clear_screen()
    print_header("Ejecutar Simulacion Unica")
    
    # 1. Elegir Estrategia
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

    # 2. Elegir Escenario
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

    # 3. Configurar Carga de Trabajo (SOLICITUD 1)
    workload_config = _configure_workload()
    if workload_config is None:
        return # Usuario abortó la configuración
    user_files, respect_only, seed = workload_config
    
    # 4. Archivo de Salida
    out_path = None
    save_choice = input(f"\n¿Deseas guardar los resultados en un archivo? (s/n) [n]: ").lower().strip()
    if save_choice == 's':
        default_out = f"run_{strategy_name}_{scenario}.json"
        out_file_str = input(f"  Nombre del archivo (en 'results/'): [{default_out}] ")
        if not out_file_str:
            out_file_str = default_out
        out_path = RESULTS_DIR / out_file_str
    
    clear_screen()
    print(f"\nIniciando simulacion: {strategy_name} | {scenario} | seed={seed}...")
    
    try:
        # Llamada al Runner con los nuevos argumentos
        summaries, bitmaps = run_simulation(
            strategy_name=strategy_name,
            scenario=scenario,
            scenarios_path=SCENARIOS_JSON_PATH,
            seed=seed,
            overrides={},
            out=str(out_path) if out_path else None,
            user_files=user_files,                 # <-- NUEVO
            respect_user_files_only=respect_only   # <-- NUEVO
        )
        
        if out_path:
            print_success(f"Simulacion completada. Resultados guardados en {out_path}")
        else:
            print_success("Simulacion completada.")

        # Imprimir resultados y manifiesto (SOLICITUD 2)
        print_results(summaries, bitmaps)

    except Exception as e:
        print_error(f"La simulacion fallo: {e}")
        # Pausa para ver el error
        input("\n... Presiona Enter para continuar ...")

def do_run_sweep():
    """Opción 4: Ejecuta un barrido de TODAS las estrategias en UN escenario."""
    clear_screen()
    print_header("Ejecutar Barrido (Sweep)")
    print("Este modo ejecutara 'TODAS' las estrategias en un solo escenario.")

    # 1. Elegir Escenario
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
    
    # 2. Configurar Carga de Trabajo (SOLICITUD 1)
    workload_config = _configure_workload()
    if workload_config is None:
        return # Usuario abortó la configuración
    user_files, respect_only, seed = workload_config
    
    # 3. Archivo de Salida
    default_out = f"sweep_{scenario}.csv" 
    out_file_str = input(f"\nNombre del archivo de resultados (en 'results/'): [{default_out}] ")
    if not out_file_str:
        out_file_str = default_out
    out_path = RESULTS_DIR / out_file_str

    clear_screen()
    print(f"\nIniciando BARRIDO: 'all' estrategias | {scenario} | seed={seed}...")
    
    try:
        # Llamada al Runner con los nuevos argumentos
        summaries, bitmaps = run_simulation(
            strategy_name="all",
            scenario=scenario,
            scenarios_path=SCENARIOS_JSON_PATH,
            seed=seed,
            overrides={},
            out=str(out_path),
            user_files=user_files,                 # <-- NUEVO
            respect_user_files_only=respect_only   # <-- NUEVO
        )
        print_success(f"Barrido completado. Resultados guardados en {out_path}")
        
        # Imprimir resultados y manifiesto (SOLICITUD 2)
        print_results(summaries, bitmaps)

    except Exception as e:
        print_error(f"El barrido fallo: {e}")
        # Pausa para ver el error
        input("\n... Presiona Enter para continuar ...")

def do_exit():
    """Opción 5: Salir del programa."""
    clear_screen()
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
# 4. Función Principal (Entry Point)
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
        clear_screen()
        print_menu()
        choice = input("Selecciona una opcion (1-5): ")
        
        action = menu_options.get(choice)
        
        if action:
            clear_screen()
            action()
        else:
            print_error("Opcion no valida.")
            input("\n... Presiona Enter para continuar ...")
        
        # La pausa para las opciones 1 y 2
        if choice in ("1", "2"):
            input("\n... Presiona Enter para continuar ...")

if __name__ == "__main__":
    main()

