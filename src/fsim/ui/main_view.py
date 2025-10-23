# Owner: Dev 5
import customtkinter as ctk
from .scenario_view import ScenarioView
from .results_view import ResultsView
from .disk_view import DiskView
from .charts_view import ChartsView # <-- 1. IMPORT NEW VIEW
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
        # --- MODIFICADO: Ajustar fila de expansión ---
        self.sidebar_frame.grid_rowconfigure(5, weight=1) # Fila 5 es ahora la de expansión

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

        # --- MODIFICADO: Añadir botón Gráficos ---
        # 2. Add Charts Button
        self.charts_button = ctk.CTkButton(self.sidebar_frame, text="Gráficos", command=lambda: self.select_frame("charts"), **button_style)
        self.charts_button.grid(row=4, column=0, padx=20, pady=10) # Nueva Fila 4
        # --- FIN MODIFICACIÓN ---


        # 3. Vistas de Página (Contenedor)
        self.main_content_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=self.palette["frame_bg"])
        self.main_content_frame.grid(row=0, column=1, sticky="nsew")
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)

        # --- Instanciar las vistas ---
        self.results_view = ResultsView(self.main_content_frame, palette=self.palette, fg_color="transparent")
        self.disk_view = DiskView(self.main_content_frame, palette=self.palette, fg_color="transparent")

        # --- MODIFICADO: Instanciar ChartsView ---
        # 4. Instantiate ChartsView
        self.charts_view = ChartsView(self.main_content_frame, palette=self.palette, fg_color="transparent")
        # --- FIN MODIFICACIÓN ---

        # Conexión de ScenarioView (SIN on_live_update)
        self.scenario_view = ScenarioView(
            self.main_content_frame,
            on_run_start=lambda: self.select_frame("disk"), # Al empezar, ir a Disco
            on_run_complete=self.on_simulation_complete,     # Al terminar, llamar a esta función
            on_live_update=self.disk_view.live_update, # Mantenido COMENTADO como en tu archivo
            palette=self.palette,
            fg_color="transparent"
        )


        # --- MODIFICADO: Añadir charts_view al diccionario ---
        # 5. Add ChartsView to frames dictionary
        self.frames = {
            "scenario": self.scenario_view,
            "results": self.results_view,
            "disk": self.disk_view,
            "charts": self.charts_view, # Añadido
        }
        # --- FIN MODIFICACIÓN ---

        self.select_frame("scenario") # Iniciar en Escenario

    def select_frame(self, name: str):
        # ... (Sin cambios) ...
        for frame_name, frame in self.frames.items():
            if frame_name == name:
                frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            else:
                frame.grid_forget()

    # --- MODIFICADO: Añadir llamada a charts_view.update_charts ---
    def on_simulation_complete(self, results: dict, bitmaps: Optional[Dict[str, List[int]]]): # Mantenida firma original
        """
        Callback que se ejecuta cuando ScenarioView termina una simulación.
        """
        # 1. Enviar métricas a la vista de Resultados
        self.results_view.show_results(results)

        # 2. Enviar bitmaps FINALES a la vista de Disco
        self.disk_view.show_final_snapshots(bitmaps) # Usa bitmaps, no results

        # 6. Pass results (containing op_traces) to ChartsView
        self.charts_view.update_charts(results) # Pasar 'results' que contiene 'op_traces'
        # --- FIN MODIFICACIÓN ---

        # 7. Cambiar a la pestaña de Resultados (se mantiene igual)
        self.select_frame("results")