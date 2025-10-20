# Owner: Dev 5
import customtkinter as ctk
from typing import Dict, Any, List, Optional
import time 

# --- CONSTANTES DE DIBUJO ---
BLOCK_SIZE_PX = 4  # Punto medio (4x4 px)
BLOCK_PAD_PX = 1   # 1px de padding
COLS = 170         # 170 columnas

class DiskView(ctk.CTkFrame):
    """
    Vista para la visualización del bitmap del disco.
    Implementa "throttling" y optimización de dibujo (run-length)
    para una actualización en vivo fluida.
    """
    def __init__(self, master, palette: Dict[str, str], **kwargs):
        super().__init__(master, **kwargs)
        self.palette = palette
        
        self.configure(fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) 
        
        self.COLOR_FREE = self.palette["button_hover"]
        self.COLOR_USED = self.palette["app_bg"]       
        
        # 1. Etiqueta de información
        self.info_label = ctk.CTkLabel(
            self,
            text="Ejecuta una simulación para ver el estado final del disco.",
            font=ctk.CTkFont(size=16),
            text_color=self.palette["text_light"]
        )
        self.info_label.grid(row=0, column=0, padx=10, pady=(0, 5), sticky="w")

        # 2. Leyenda
        self.legend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.legend_frame.grid(row=1, column=0, padx=15, pady=0, sticky="w")
        # ... (código de la leyenda sin cambios) ...
        self.legend_used_color = ctk.CTkFrame(
            self.legend_frame, width=15, height=15, 
            fg_color=self.COLOR_USED, border_width=1, 
            border_color=self.palette["button_hover"]
        )
        self.legend_used_color.pack(side="left", padx=(0, 5))
        self.legend_used_label = ctk.CTkLabel(
            self.legend_frame, text="Ocupado", text_color=self.palette["text_light"]
        )
        self.legend_used_label.pack(side="left", padx=(0, 20))
        self.legend_free_color = ctk.CTkFrame(
            self.legend_frame, width=15, height=15, 
            fg_color=self.COLOR_FREE, border_width=0
        )
        self.legend_free_color.pack(side="left", padx=(0, 5))
        self.legend_free_label = ctk.CTkLabel(
            self.legend_frame, text="Libre", text_color=self.palette["text_light"]
        )
        self.legend_free_label.pack(side="left", padx=(0, 20))

        # 3. Frame con Scroll para los Canvas
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=2, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1) 
        
        self._current_scroll_row = 0
        self._live_canvas: Optional[ctk.CTkCanvas] = None
        self._live_canvas_strategy = ""
        
        # Variables para limitar FPS (throttling)
        self._last_live_update_time = 0.0
        self._live_update_throttle_ms = 50 # 50ms = max 20 FPS

    def _clear_bitmaps(self):
        """Limpia todos los widgets (títulos, canvas) del scroll_frame."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self._current_scroll_row = 0
        self._live_canvas = None 
        self._live_canvas_strategy = ""


    # --- MODIFICACIÓN CLAVE (Inicio) ---
    # Esta función es llamada por _draw_bitmap
    def _draw_run(self, canvas: ctk.CTkCanvas, start_index: int, end_index: int, value: int):
        """
        Helper para dibujar un 'run' (rango) de bloques del mismo valor.
        Puede abarcar múltiples filas del canvas.
        """
        color = self.COLOR_FREE if value == 0 else self.COLOR_USED
        
        current_index = start_index
        while current_index <= end_index:
            # Calcular fila y columna del bloque actual
            row = current_index // COLS
            col_start = current_index % COLS
            
            # Calcular cuántos bloques de este 'run' caben en esta fila
            blocks_in_this_row = min(COLS - col_start, (end_index - current_index) + 1)
            col_end = col_start + blocks_in_this_row - 1
            
            # Calcular coordenadas de píxeles
            x1 = col_start * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
            y1 = row * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
            # x2 es el borde DERECHO del último bloque
            x2 = (col_end + 1) * (BLOCK_SIZE_PX + BLOCK_PAD_PX) - BLOCK_PAD_PX
            # y2 es el borde INFERIOR de esta fila
            y2 = y1 + BLOCK_SIZE_PX
            
            canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            
            # Avanzar al siguiente bloque a dibujar
            current_index += blocks_in_this_row

    def _draw_bitmap(self, 
                     bitmap: List[int], 
                     strategy_name: str, 
                     canvas_instance: Optional[ctk.CTkCanvas] = None
                     ) -> ctk.CTkCanvas:
        """
        Dibuja un bitmap en un canvas.
        OPTIMIZADO: Usa run-length encoding para dibujar franjas, no bloques.
        """
        
        num_blocks = len(bitmap)
        if num_blocks == 0:
             # Manejar bitmap vacío
            if canvas_instance:
                canvas_instance.delete("all")
                return canvas_instance
            else:
                # Crear un canvas vacío si no existe
                canvas = ctk.CTkCanvas(self.scroll_frame, bg=self.palette["frame_bg"], highlightthickness=0, width=1, height=1)
                canvas.grid(row=self._current_scroll_row, column=0)
                self._current_scroll_row += 1
                return canvas

        num_rows = (num_blocks // COLS) + 1
        canvas_width = COLS * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
        canvas_height = num_rows * (BLOCK_SIZE_PX + BLOCK_PAD_PX)

        canvas: ctk.CTkCanvas
        if canvas_instance:
            canvas = canvas_instance
            canvas.delete("all") 
            canvas.configure(width=canvas_width, height=canvas_height)
        else:
            title_label = ctk.CTkLabel(
                self.scroll_frame, 
                text=f"Estrategia: {strategy_name.upper()}",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.palette["text_light"]
            )
            title_label.grid(row=self._current_scroll_row, column=0, padx=10, pady=(15, 5), sticky="w")
            self._current_scroll_row += 1

            canvas = ctk.CTkCanvas(
                self.scroll_frame,
                bg=self.palette["frame_bg"],
                highlightthickness=0,
                width=canvas_width,
                height=canvas_height
            )
            canvas.grid(row=self._current_scroll_row, column=0, pady=10, padx=10)
            self._current_scroll_row += 1

        # --- OPTIMIZACIÓN DE DIBUJO ---
        
        current_run_val = bitmap[0]
        current_run_start = 0

        for i in range(1, num_blocks):
            if bitmap[i] != current_run_val:
                # Fin de un 'run'. Dibujarlo.
                self._draw_run(canvas, current_run_start, i - 1, current_run_val)
                
                # Empezar nuevo 'run'
                current_run_val = bitmap[i]
                current_run_start = i

        # Dibujar el último 'run' (que llega hasta el final)
        self._draw_run(canvas, current_run_start, num_blocks - 1, current_run_val)
        
        return canvas

    # --- FIN MODIFICACIÓN ---


    def live_update(self, strategy_name: str, bitmap: List[int]):
        """
        Punto de entrada llamado DESDE EL HILO DE SIMULACIÓN.
        Limita la tasa de refresco (throttling).
        """
        current_time_s = time.monotonic()
        elapsed_ms = (current_time_s - self._last_live_update_time) * 1000.0
        
        if elapsed_ms < self._live_update_throttle_ms:
            return # Ignorar este evento, es demasiado pronto
        
        self._last_live_update_time = current_time_s
        self.after(0, self._safe_live_update, strategy_name, bitmap)

    def _safe_live_update(self, strategy_name: str, bitmap: List[int]):
        """
        Esta función se ejecuta EN EL HILO PRINCIPAL de la UI.
        Es seguro tocar los widgets aquí.
        """
        try:
            if not self.winfo_exists():
                return

            self.info_label.configure(text=f"Simulando en vivo: {strategy_name.upper()}...")
            
            if strategy_name != self._live_canvas_strategy:
                self._clear_bitmaps()
                self._live_canvas_strategy = strategy_name
                self._live_canvas = self._draw_bitmap(bitmap, strategy_name, canvas_instance=None)
            else:
                # Reutilizar el canvas existente para esta estrategia
                self._draw_bitmap(bitmap, strategy_name, canvas_instance=self._live_canvas)
        
        except Exception as e:
            print(f"Error en _safe_live_update: {e}")

    def show_final_snapshots(self, bitmaps: Optional[Dict[str, List[int]]]):
        """
        Punto de entrada para los resultados FINALES.
        """
        self._clear_bitmaps() 
        
        if bitmaps is None:
            self.info_label.configure(text="La simulación falló. No hay bitmap para mostrar.")
            return
            
        if not bitmaps:
            self.info_label.configure(text="No se recibieron bitmaps de la simulación.")
            return
        
        self.info_label.configure(text=f"Mostrando {len(bitmaps)} bitmap(s) finales:")

        for strategy_name, bitmap_to_draw in bitmaps.items():
            self._draw_bitmap(bitmap_to_draw, strategy_name, canvas_instance=None)