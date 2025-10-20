# Owner: Dev 5
import customtkinter as ctk
import threading
import json
from typing import Callable, Dict, Any, List, Optional

# Importar la lógica del backend
from ..sim.runner import run_simulation, STRATEGIES
from ..sim.scenario_definitions import available_scenarios, get_config

# ... (Mapas de Traducción sin cambios) ...
STRATEGY_MAP_ES = {
    "contiguous": "Asignación Contigua",
    "linked": "Asignación Enlazada",
    "indexed": "Asignación Indexada",
    "all": "Todas las Estrategias"
}
STRATEGY_MAP_EN = {v: k for k, v in STRATEGY_MAP_ES.items()}
SCENARIO_MAP_ES: Dict[str, str] = {}
SCENARIO_MAP_EN: Dict[str, str] = {}


class ScenarioView(ctk.CTkFrame):
    """
    Vista para configurar y lanzar una simulación.
    Utiliza threading para no bloquear la UI.
    """
    
    def __init__(self, 
                 master, 
                 on_run_start: Callable[[], None],
                 on_run_complete: Callable[[Dict[str, Any], Optional[Dict[str, List[int]]]], None], 
                 on_live_update: Callable[[str, List[int]], None],
                 palette: Dict[str, str], 
                 **kwargs):
        super().__init__(master, **kwargs)
        self.on_run_start = on_run_start
        self.on_run_complete = on_run_complete
        self.on_live_update = on_live_update 
        self.palette = palette

        self.grid_columnconfigure(1, weight=1)

        # ... (Definición de Estilos sin cambios) ...
        label_style = {"text_color": self.palette["text_light"]}
        button_style = {
            "fg_color": self.palette["button"],
            "hover_color": self.palette["button_hover"],
            "text_color": self.palette["text_on_button"]
        }
        option_style = {
            "fg_color": self.palette["button"],
            "button_color": self.palette["button"],
            "button_hover_color": self.palette["button_hover"],
            "text_color": self.palette["text_on_button"],
            "dropdown_fg_color": self.palette["frame_bg"],
            "dropdown_hover_color": self.palette["button_hover"],
            "dropdown_text_color": self.palette["text_light"]
        }

        # --- Fila 1: Estrategia ---
        self.strategy_label = ctk.CTkLabel(self, text="Estrategia:", anchor="w", **label_style)
        self.strategy_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        strategy_display_names = list(STRATEGY_MAP_ES.values())
        default_strategy_display = STRATEGY_MAP_ES["contiguous"]
        self.strategy_var = ctk.StringVar(value=default_strategy_display)
        self.strategy_menu = ctk.CTkOptionMenu(
            self, variable=self.strategy_var, values=strategy_display_names, **option_style
        )
        self.strategy_menu.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")

        # --- Fila 2: Escenario ---
        self.scenario_label = ctk.CTkLabel(self, text="Escenario Base:", anchor="w", **label_style)
        self.scenario_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        
        global SCENARIO_MAP_ES, SCENARIO_MAP_EN
        try:
            scenarios = available_scenarios("data/scenarios.json")
            SCENARIO_MAP_ES.clear()
            SCENARIO_MAP_EN.clear()
            for key, description in scenarios.items():
                friendly_name = ""
                if key == "mix-small-large": friendly_name = "Mezcla Pequeños y Grandes"
                elif key == "seq-vs-rand": friendly_name = "Acceso Secuencial vs Aleatorio"
                elif key == "frag-intensive": friendly_name = "Fragmentación Intensiva"
                else: friendly_name = description.split(",")[0] 
                SCENARIO_MAP_ES[key] = friendly_name
                SCENARIO_MAP_EN[friendly_name] = key
            scenario_display_names = list(SCENARIO_MAP_ES.values())
            default_scenario_display = scenario_display_names[0] if scenario_display_names else "Sin Escenarios"
        except Exception as e:
            print(f"Error cargando scenarios.json: {e}")
            scenario_display_names = ["Error al Cargar"]
            default_scenario_display = "Error al Cargar"
        self.scenario_var = ctk.StringVar(value=default_scenario_display)
        self.scenario_menu = ctk.CTkOptionMenu(
            self, variable=self.scenario_var, values=scenario_display_names, **option_style
        )
        self.scenario_menu.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        # --- MODIFICACIÓN: Añadir Checkbox ---
        # --- Fila 3: Checkbox Modo Lento ---
        self.slow_mo_var = ctk.BooleanVar(value=True) # Activo por defecto
        self.slow_mo_check = ctk.CTkCheckBox(
            self,
            text="Activar visualización lenta (Modo Demo)",
            variable=self.slow_mo_var,
            text_color=self.palette["text_light"],
            border_color=self.palette["button"],
            hover_color=self.palette["button_hover"],
            fg_color=self.palette["button"]
        )
        self.slow_mo_check.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="w")
        # --- FIN MODIFICACIÓN ---

        # --- Fila 4: Botón de Ejecución (movido de fila 3 a 4) ---
        self.run_button = ctk.CTkButton(self, text="Ejecutar Simulación", command=self._start_simulation, **button_style)
        self.run_button.grid(row=4, column=0, columnspan=2, padx=20, pady=20)

        # --- Fila 5: Estado (movido de fila 4 a 5) ---
        self.status_label = ctk.CTkLabel(self, text="", text_color=self.palette["text_light"])
        self.status_label.grid(row=5, column=0, columnspan=2, padx=20, pady=10)

    def _start_simulation(self):
        self.run_button.configure(state="disabled", text="Ejecutando...")
        self.status_label.configure(text="Iniciando simulación...", text_color=self.palette["text_light"])

        if self.on_run_start:
            self.on_run_start()

        strategy_display = self.strategy_var.get()
        scenario_display = self.scenario_var.get()
        strategy_key = STRATEGY_MAP_EN.get(strategy_display)
        scenario_key = SCENARIO_MAP_EN.get(scenario_display)
        
        if strategy_key is None or scenario_key is None:
            err_msg = f"Error: No se pudo encontrar la clave interna para '{strategy_display}' o '{scenario_display}'"
            print(err_msg)
            self.after(0, self._simulation_error, Exception(err_msg))
            return
            
        # --- MODIFICACIÓN: Leer valor del checkbox ---
        # 5ms de pausa por operación si está activo, 0 si no.
        # Puedes ajustar este valor (ej. 10, 1, etc.)
        slowdown_val = 5 if self.slow_mo_var.get() else 0
        # --- FIN MODIFICACIÓN ---

        thread = threading.Thread(
            target=self._run_simulation_thread,
            args=(strategy_key, scenario_key, slowdown_val), # Pasar el valor
            daemon=True
        )
        thread.start()

    # --- MODIFICACIÓN: Aceptar 'slowdown_val' ---
    def _run_simulation_thread(self, strategy_key: str, scenario_key: str, slowdown_val: int):
    # --- FIN MODIFICACIÓN ---
        try:
            results, bitmaps = run_simulation(
                strategy_name=strategy_key,
                scenario=scenario_key,
                scenarios_path="data/scenarios.json",
                seed=None,
                overrides={},
                out=None,
                on_bitmap_update=self.on_live_update,
                ui_slowdown_ms=slowdown_val # <-- Pasarlo al runner
            )
            
            self.after(0, self._simulation_complete, results, bitmaps)
        
        except Exception as e:
            print(f"Error en el hilo de simulación: {e}")
            self.after(0, self._simulation_error, e)

    def _simulation_complete(self, results: Dict[str, Any], bitmaps: Optional[Dict[str, List[int]]]):
        strategy_display = self.strategy_var.get()
        self.status_label.configure(text=f"Simulación completada. Resultados para '{strategy_display}'.", text_color=self.palette["text_light"])
        self.run_button.configure(state="normal", text="Ejecutar Simulación")
        
        if self.on_run_complete:
            self.on_run_complete(results, bitmaps)

    def _simulation_error(self, error: Exception):
        self.status_label.configure(text=f"Error: {error}", text_color="#FF5555")
        self.run_button.configure(state="normal", text="Ejecutar Simulación")
        
        if self.on_run_complete:
            self.on_run_complete({"error": str(error)}, None)