# Owner: Dev 5
import customtkinter as ctk
import threading
import json
from typing import Callable, Dict, Any, List, Optional # <- Añadir List, Optional

# Importar la lógica del backend
from ..sim.runner import run_simulation, STRATEGIES
from ..sim.scenario_definitions import available_scenarios, get_config

# --- Mapas de Traducción Español ---

STRATEGY_MAP_ES = {
    "contiguous": "Asignación Contigua",
    "linked": "Asignación Enlazada",
    "indexed": "Asignación Indexada",
    "all": "Todas las Estrategias"
}
# Mapa inverso para buscar la clave interna
STRATEGY_MAP_EN = {v: k for k, v in STRATEGY_MAP_ES.items()}

# Mapa para escenarios (se carga dinámicamente)
SCENARIO_MAP_ES: Dict[str, str] = {}
SCENARIO_MAP_EN: Dict[str, str] = {}


class ScenarioView(ctk.CTkFrame):
    """
    Vista para configurar y lanzar una simulación.
    Utiliza threading para no bloquear la UI.
    """
    
    # --- MODIFICACIÓN: Actualizar firma del callback ---
    def __init__(self, master, 
                 on_run_complete: Callable[[Dict[str, Any], Optional[Dict[str, List[int]]]], None], 
                 palette: Dict[str, str], **kwargs):
    # --- FIN MODIFICACIÓN ---
        super().__init__(master, **kwargs)
        self.on_run_complete = on_run_complete
        self.palette = palette

        self.grid_columnconfigure(1, weight=1)

        # --- Estilos de widgets ---
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
            self,
            variable=self.strategy_var,
            values=strategy_display_names,
            **option_style
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
                if key == "mix-small-large":
                    friendly_name = "Mezcla Pequeños y Grandes"
                elif key == "seq-vs-rand":
                    friendly_name = "Acceso Secuencial vs Aleatorio"
                elif key == "frag-intensive":
                    friendly_name = "Fragmentación Intensiva"
                else:
                    friendly_name = description.split(",")[0] 

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
            self,
            variable=self.scenario_var,
            values=scenario_display_names,
            **option_style
        )
        self.scenario_menu.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        # --- Fila 3: Botón de Ejecución ---
        self.run_button = ctk.CTkButton(self, text="Ejecutar Simulación", command=self._start_simulation, **button_style)
        self.run_button.grid(row=3, column=0, columnspan=2, padx=20, pady=20)

        # --- Fila 4: Estado ---
        self.status_label = ctk.CTkLabel(self, text="", text_color=self.palette["text_light"])
        self.status_label.grid(row=4, column=0, columnspan=2, padx=20, pady=10)

    def _start_simulation(self):
        self.run_button.configure(state="disabled", text="Ejecutando...")
        self.status_label.configure(text="Iniciando simulación...", text_color=self.palette["text_light"])

        strategy_display = self.strategy_var.get()
        scenario_display = self.scenario_var.get()

        strategy_key = STRATEGY_MAP_EN.get(strategy_display)
        scenario_key = SCENARIO_MAP_EN.get(scenario_display)
        
        if strategy_key is None or scenario_key is None:
            err_msg = f"Error: No se pudo encontrar la clave interna para '{strategy_display}' o '{scenario_display}'"
            print(err_msg)
            # --- MODIFICACIÓN: Enviar None para el bitmap en caso de error ---
            self.after(0, self._simulation_error, Exception(err_msg))
            # --- FIN MODIFICACIÓN ---
            return

        thread = threading.Thread(
            target=self._run_simulation_thread,
            args=(strategy_key, scenario_key), 
            daemon=True
        )
        thread.start()

    def _run_simulation_thread(self, strategy_key: str, scenario_key: str):
        try:
            # --- MODIFICACIÓN: Recibir 'results' y 'bitmaps' ---
            results, bitmaps = run_simulation(
                strategy_name=strategy_key,
                scenario=scenario_key,
                scenarios_path="data/scenarios.json",
                seed=None,
                overrides={},
                out=None
            )
            # --- FIN MODIFICACIÓN ---
            
            # --- MODIFICACIÓN: Pasar ambos al callback ---
            self.after(0, self._simulation_complete, results, bitmaps)
            # --- FIN MODIFICACIÓN ---
        
        except Exception as e:
            print(f"Error en el hilo de simulación: {e}")
            self.after(0, self._simulation_error, e)

    # --- MODIFICACIÓN: Actualizar firma ---
    def _simulation_complete(self, results: Dict[str, Any], bitmaps: Dict[str, List[int]]):
    # --- FIN MODIFICACIÓN ---
        strategy_display = self.strategy_var.get()
        self.status_label.configure(text=f"Simulación completada. Resultados para '{strategy_display}'.", text_color=self.palette["text_light"])
        self.run_button.configure(state="normal", text="Ejecutar Simulación")
        
        if self.on_run_complete:
            # --- MODIFICACIÓN: Pasar ambos ---
            self.on_run_complete(results, bitmaps)
            # --- FIN MODIFICACIÓN ---

    def _simulation_error(self, error: Exception):
        self.status_label.configure(text=f"Error: {error}", text_color="#FF5555")
        self.run_button.configure(state="normal", text="Ejecutar Simulación")
        
        if self.on_run_complete:
            # --- MODIFICACIÓN: Pasar el error y None para el bitmap ---
            self.on_run_complete({"error": str(error)}, None)
            # --- FIN MODIFICACIÓN ---