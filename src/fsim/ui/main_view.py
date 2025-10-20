# Owner: Dev 5
import customtkinter as ctk
from .scenario_view import ScenarioView
from .results_view import ResultsView
from .disk_view import DiskView
from typing import Dict, Any, List, Optional

class MainView(ctk.CTkFrame):
    """
    Vista principal que contiene la navegación (sidebar) y las vistas de página.
    """
    def __init__(self, master, palette: Dict[str, str], **kwargs):
        super().__init__(master, **kwargs)
        self.palette = palette
        
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar de Navegación
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=10, fg_color=self.palette["frame_bg"])
        self.sidebar_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, text="FSim", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.palette["text_light"]
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        button_style = {
            "fg_color": self.palette["button"],
            "hover_color": self.palette["button_hover"],
            "text_color": self.palette["text_on_button"]
        }
        self.scenario_button = ctk.CTkButton(self.sidebar_frame, text="Escenario", command=lambda: self.select_frame("scenario"), **button_style)
        self.scenario_button.grid(row=1, column=0, padx=20, pady=10)
        self.results_button = ctk.CTkButton(self.sidebar_frame, text="Resultados", command=lambda: self.select_frame("results"), **button_style)
        self.results_button.grid(row=2, column=0, padx=20, pady=10)
        self.disk_button = ctk.CTkButton(self.sidebar_frame, text="Disco", command=lambda: self.select_frame("disk"), **button_style)
        self.disk_button.grid(row=3, column=0, padx=20, pady=10)

        # 2. Vistas de Página (Contenedor)
        self.main_content_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=self.palette["frame_bg"])
        self.main_content_frame.grid(row=0, column=1, sticky="nsew")
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)

        # --- Instanciar las vistas ---
        self.results_view = ResultsView(self.main_content_frame, palette=self.palette, fg_color="transparent")
        self.disk_view = DiskView(self.main_content_frame, palette=self.palette, fg_color="transparent")
        
        # --- MODIFICACIÓN: Conectar los callbacks de live-update y start ---
        self.scenario_view = ScenarioView(
            self.main_content_frame, 
            on_run_start=lambda: self.select_frame("disk"), # Al empezar, cambiar a la vista de Disco
            on_run_complete=self.on_simulation_complete,     # Al terminar, llamar a esta función
            on_live_update=self.disk_view.live_update,       # Durante la simulación, llamar a disk_view.live_update
            palette=self.palette,
            fg_color="transparent"
        )
        # --- FIN MODIFICACIÓN ---

        self.frames = {
            "scenario": self.scenario_view,
            "results": self.results_view,
            "disk": self.disk_view,
        }

        self.select_frame("scenario")

    def select_frame(self, name: str):
        for frame in self.frames.values():
            frame.grid_forget()
        selected_frame = self.frames[name]
        selected_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10) 

    def on_simulation_complete(self, results: dict, bitmaps: Optional[Dict[str, List[int]]]):
        """
        Callback que se ejecuta cuando ScenarioView termina una simulación.
        """
        # 1. Enviar métricas a la vista de Resultados
        self.results_view.show_results(results)
        
        # 2. Enviar bitmaps FINALES a la vista de Disco
        #    (Esto reemplazará la vista "en vivo" por la(s) instantánea(s) final(es))
        # MODIFICADO: Renombrar la función llamada
        self.disk_view.show_final_snapshots(bitmaps)
        # --- FIN MODIFICACIÓN ---
        
        # 3. Cambiar a la pestaña de Resultados
        self.select_frame("results")