# Owner: Dev 3
import customtkinter as ctk
import json
from typing import Dict, Any

# Diccionario de traducción para las métricas
METRIC_NAMES_ES = {
    "avg_access_time_ms": "Tiempo Promedio de Acceso (ms)",
    "space_usage_pct": "Uso de Espacio (%)",
    "fragmentation_internal_pct": "Fragmentación Interna (%)",
    "fragmentation_external_pct": "Fragmentación Externa (%)",
    "throughput_ops_per_sec": "Operaciones por Segundo (OPS)",
    "hit_miss_ratio": "Tasa de Aciertos (%)",
    "cpu_usage_pct": "Uso de CPU (%)",
    "fairness_index": "Índice de Equidad (Desv. Tiempos)",
    "elapsed_ms_total": "Tiempo Total de Simulación (ms)",
    "ops_count": "Total de Operaciones Ejecutadas",
    "seeks_total_est": "Total de Saltos de Cabezal (Est.)"
}

# Orden preferido para mostrar las métricas
METRIC_ORDER = [
    "avg_access_time_ms",
    "throughput_ops_per_sec",
    "seeks_total_est",
    "space_usage_pct",
    "fragmentation_external_pct",
    "fragmentation_internal_pct",
    "hit_miss_ratio",
    "fairness_index",
    "cpu_usage_pct",
    "elapsed_ms_total",
    "ops_count",
]


class ResultsView(ctk.CTkFrame):
    """
    Vista para mostrar los resultados de la simulación de forma estilizada.
    """
    def __init__(self, master, palette: Dict[str, str], **kwargs):
        super().__init__(master, **kwargs)
        self.palette = palette

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(
            self, 
            text="Resultados de la Simulación", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.palette["text_light"]
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(0, 10), sticky="w") # Ajustado padding

        # Frame con scroll, fondo transparente para heredar del main_content_frame
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        self.current_row = 0 # Para llevar la cuenta de dónde insertar en el grid

        self._show_placeholder()

    def _clear_results(self):
        """Limpia todos los widgets de resultados anteriores."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.current_row = 0
        
    def _show_placeholder(self):
        """Muestra el mensaje inicial."""
        self._clear_results()
        label = ctk.CTkLabel(
            self.scroll_frame, 
            text="Ejecuta una simulación desde la pestaña 'Escenario' para ver los resultados aquí.", 
            text_color=self.palette["text_light"]
        )
        label.grid(row=self.current_row, column=0, padx=20, pady=20)
        self.current_row += 1

    def _show_error(self, error_msg: str):
        """Muestra un mensaje de error estilizado."""
        self._clear_results()
        label = ctk.CTkLabel(self.scroll_frame, text="Error en la Simulación:", text_color="#FF5555", font=ctk.CTkFont(size=16, weight="bold"))
        label.grid(row=self.current_row, column=0, padx=20, pady=(10, 5), sticky="w")
        self.current_row += 1
        
        error_text = ctk.CTkTextbox(self.scroll_frame, activate_scrollbars=False, text_color=self.palette["text_light"])
        error_text.insert("0.0", error_msg)
        error_text.configure(state="disabled", fg_color="transparent", font=ctk.CTkFont(family="monospace"))
        # Ajustar altura al contenido
        error_text.configure(height=len(error_msg.split('\n')) * 20 + 20)
        error_text.grid(row=self.current_row, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.current_row += 1

    def _add_metric_row(self, master_frame, key: str, value: Any):
        """Añade una fila de métrica (Nombre: Valor) al frame."""
        
        # Traducir el nombre de la métrica
        display_name = METRIC_NAMES_ES.get(key, key)
        
        # Formatear el valor
        if isinstance(value, float):
            display_value = f"{value:.3f}"
        else:
            display_value = str(value)

        # Crear un frame para la fila
        row_frame = ctk.CTkFrame(master_frame, fg_color="transparent")
        row_frame.pack(fill="x", padx=10, pady=1) # Usar pack dentro de la tarjeta
        
        row_frame.grid_columnconfigure(0, weight=1)
        row_frame.grid_columnconfigure(1, weight=1)
        
        name_label = ctk.CTkLabel(
            row_frame, 
            text=f"{display_name}:", 
            anchor="w", 
            text_color=self.palette["text_light"]
        )
        name_label.grid(row=0, column=0, sticky="w")
        
        value_label = ctk.CTkLabel(
            row_frame, 
            text=display_value, 
            anchor="e", 
            text_color=self.palette["text_light"], 
            font=ctk.CTkFont(weight="bold")
        )
        value_label.grid(row=0, column=1, sticky="e")

    def _add_strategy_card(self, strategy_name: str, metrics: Dict[str, Any]):
        """Añade una "tarjeta" completa para una estrategia."""
        
        # Título de la estrategia (en mayúsculas)
        title_label = ctk.CTkLabel(
            self.scroll_frame, 
            text=f"Estrategia: {strategy_name.upper()}", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.palette["text_light"]
        )
        title_label.grid(row=self.current_row, column=0, padx=5, pady=(20, 10), sticky="w")
        self.current_row += 1
        
        # Frame contenedor para las métricas de esta tarjeta
        # Usamos el color de fondo más oscuro para la tarjeta
        card_frame = ctk.CTkFrame(
            self.scroll_frame, 
            border_width=1, 
            border_color=self.palette["button_hover"], # Borde con color de acento
            fg_color=self.palette["app_bg"] # Fondo más oscuro
        )
        card_frame.grid(row=self.current_row, column=0, sticky="ew", padx=5, pady=5)
        self.current_row += 1
        
        # --- Añadir filas de métricas en el orden preferido ---
        for key in METRIC_ORDER:
            if key in metrics:
                self._add_metric_row(card_frame, key, metrics[key])
        
        # --- Añadir cualquier métrica extra que no estuviera en el orden preferido ---
        for key, value in metrics.items():
            if key not in METRIC_ORDER and not key.startswith("_"):
                self._add_metric_row(card_frame, key, value)
        
        # Añadir un separador/espaciador
        ctk.CTkFrame(card_frame, height=10, fg_color="transparent").pack()


    def show_results(self, results_dict: dict):
        """
        Imprime los resultados de la simulación de forma estilizada.
        Esta función es llamada por MainView.
        """
        self._clear_results()

        if not results_dict:
            self._show_placeholder()
            return

        if "error" in results_dict:
            self._show_error(results_dict["error"])
            return
            
        # Iterar por cada estrategia en los resultados (ej. "contiguous", "linked")
        for strategy_name, metrics in results_dict.items():
            if strategy_name.startswith("_"): # Ignorar campos privados como "_basic"
                continue
            
            self._add_strategy_card(strategy_name, metrics)