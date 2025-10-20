# Owner: Dev 5
import customtkinter as ctk
import threading
import json
from typing import Callable, Dict, Any

# Importar la lógica del backend
from ..sim.runner import run_simulation, STRATEGIES
from ..sim.scenario_definitions import available_scenarios, get_config

class ScenarioView(ctk.CTkFrame):
    """
    Vista para configurar y lanzar una simulación.
    Utiliza threading para no bloquear la UI.
    """
    
    def __init__(self, master, on_run_complete: Callable[[Dict[str, Any]], None], **kwargs):
        super().__init__(master, **kwargs)
        self.on_run_complete = on_run_complete

        self.grid_columnconfigure(1, weight=1)

        # --- Fila 1: Estrategia ---
        self.strategy_label = ctk.CTkLabel(self, text="Estrategia:", anchor="w")
        self.strategy_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.strategy_var = ctk.StringVar(value="contiguous")
        self.strategy_menu = ctk.CTkOptionMenu(
            self,
            variable=self.strategy_var,
            values=list(STRATEGIES.keys()) + ["all"]
        )
        self.strategy_menu.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")

        # --- Fila 2: Escenario ---
        self.scenario_label = ctk.CTkLabel(self, text="Escenario Base:", anchor="w")
        self.scenario_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        
        # Cargar escenarios disponibles
        try:
            scenarios = available_scenarios("data/scenarios.json")
            scenario_keys = list(scenarios.keys())
            default_scenario = scenario_keys[0] if scenario_keys else ""
        except Exception as e:
            print(f"Error cargando scenarios.json: {e}")
            scenarios = {}
            scenario_keys = ["Error"]
            default_scenario = "Error"

        self.scenario_var = ctk.StringVar(value=default_scenario)
        self.scenario_menu = ctk.CTkOptionMenu(
            self,
            variable=self.scenario_var,
            values=scenario_keys
        )
        self.scenario_menu.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        # --- Fila 3: Botón de Ejecución ---
        self.run_button = ctk.CTkButton(self, text="Ejecutar Simulación", command=self._start_simulation)
        self.run_button.grid(row=3, column=0, columnspan=2, padx=20, pady=20)

        # --- Fila 4: Estado ---
        self.status_label = ctk.CTkLabel(self, text="", text_color="gray")
        self.status_label.grid(row=4, column=0, columnspan=2, padx=20, pady=10)

    def _start_simulation(self):
        """
        Llamado por el botón. Inicia el hilo de simulación.
        """
        self.run_button.configure(state="disabled", text="Ejecutando...")
        self.status_label.configure(text="Iniciando simulación...")

        strategy = self.strategy_var.get()
        scenario = self.scenario_var.get()

        # Ejecutar en un hilo separado para no congelar la UI
        thread = threading.Thread(
            target=self._run_simulation_thread,
            args=(strategy, scenario),
            daemon=True
        )
        thread.start()

    def _run_simulation_thread(self, strategy: str, scenario: str):
        """
        Función que se ejecuta en el hilo secundario.
        Llama al backend.
        """
        try:
            # Esta es la llamada al backend. Puede tardar.
            results = run_simulation(
                strategy_name=strategy,
                scenario=scenario,
                scenarios_path="data/scenarios.json",
                seed=None,
                overrides={},
                out=None # No guardamos a CSV/JSON desde la UI, solo mostramos
            )
            # Cuando termina, programamos la finalización en el hilo principal
            self.after(0, self._simulation_complete, results)
        
        except Exception as e:
            print(f"Error en el hilo de simulación: {e}")
            self.after(0, self._simulation_error, e)

    def _simulation_complete(self, results: Dict[str, Any]):
        """
        Callback en el hilo principal cuando la simulación fue exitosa.
        """
        self.status_label.configure(text=f"Simulación completada. Resultados para '{self.strategy_var.get()}'.")
        self.run_button.configure(state="normal", text="Ejecutar Simulación")
        
        # Llama al callback del MainView para mostrar resultados
        if self.on_run_complete:
            self.on_run_complete(results)

    def _simulation_error(self, error: Exception):
        """
        Callback en el hilo principal cuando la simulación falló.
        """
        self.status_label.configure(text=f"Error: {error}", text_color="red")
        self.run_button.configure(state="normal", text="Ejecutar Simulación")
        
        # Muestra el error en la vista de resultados
        if self.on_run_complete:
            self.on_run_complete({"error": str(error)})