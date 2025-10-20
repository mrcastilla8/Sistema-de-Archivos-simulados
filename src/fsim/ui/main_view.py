# Owner: Dev 5
import customtkinter as ctk
from .scenario_view import ScenarioView
from .results_view import ResultsView
from .disk_view import DiskView

class MainView(ctk.CTkFrame):
    """
    Vista principal que contiene la navegación (sidebar) y las vistas de página.
    Actúa como el controlador que conecta 'ScenarioView' (entrada)
    con 'ResultsView' (salida).
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar de Navegación
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsw")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="FSim", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.scenario_button = ctk.CTkButton(self.sidebar_frame, text="Escenario", command=lambda: self.select_frame("scenario"))
        self.scenario_button.grid(row=1, column=0, padx=20, pady=10)

        self.results_button = ctk.CTkButton(self.sidebar_frame, text="Resultados", command=lambda: self.select_frame("results"))
        self.results_button.grid(row=2, column=0, padx=20, pady=10)
        
        self.disk_button = ctk.CTkButton(self.sidebar_frame, text="Disco (WIP)", command=lambda: self.select_frame("disk"))
        self.disk_button.grid(row=3, column=0, padx=20, pady=10)


        # 2. Vistas de Página
        self.main_content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=0)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)

        # Instanciar las vistas
        self.results_view = ResultsView(self.main_content_frame)
        self.disk_view = DiskView(self.main_content_frame)
        
        # Conectamos ScenarioView con ResultsView
        # Cuando 'scenario_view' termine, llamará a 'on_simulation_complete'
        self.scenario_view = ScenarioView(
            self.main_content_frame, 
            on_run_complete=self.on_simulation_complete
        )

        # Diccionario para gestionar las vistas
        self.frames = {
            "scenario": self.scenario_view,
            "results": self.results_view,
            "disk": self.disk_view,
        }

        # Mostrar la vista por defecto
        self.select_frame("scenario")

    def select_frame(self, name: str):
        """Muestra la vista seleccionada y oculta las demás."""
        for frame in self.frames.values():
            frame.grid_forget()
        
        selected_frame = self.frames[name]
        selected_frame.grid(row=0, column=0, sticky="nsew")

    def on_simulation_complete(self, results: dict):
        """
        Callback que se ejecuta cuando ScenarioView termina una simulación.
        Actualiza la vista de resultados y cambia a ella.
        """
        self.results_view.show_results(results)
        self.select_frame("results")