# Owner: Dev 5
import customtkinter as ctk
from typing import Dict, Any, List, Optional
import time

# --- CONSTANTES DE DIBUJO ---
BLOCK_SIZE_PX = 4
BLOCK_PAD_PX = 1
COLS = 170

class DiskView(ctk.CTkFrame):
    """
    Vista para la visualización del bitmap del disco (En Vivo).
    Implementa "throttling", optimización de dibujo (run-length),
    y manejo extra-robusto de bitmaps inválidos/dimensiones cero.
    """
    def __init__(self, master, palette: Dict[str, str], **kwargs):
        super().__init__(master, **kwargs)
        self.palette = palette
        self.configure(fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.COLOR_FREE = self.palette["button_hover"]
        self.COLOR_USED = self.palette["app_bg"]

        self.info_label = ctk.CTkLabel(
            self, text="Ejecuta una simulación para ver el estado del disco.",
            font=ctk.CTkFont(size=16), text_color=self.palette["text_light"]
        )
        self.info_label.grid(row=0, column=0, padx=10, pady=(0, 5), sticky="w")

        self.legend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.legend_frame.grid(row=1, column=0, padx=15, pady=0, sticky="w")
        # ... (leyenda sin cambios) ...
        self.legend_used_color=ctk.CTkFrame(self.legend_frame, width=15, height=15, fg_color=self.COLOR_USED, border_width=1, border_color=self.palette["button_hover"]); self.legend_used_color.pack(side="left", padx=(0, 5))
        self.legend_used_label=ctk.CTkLabel(self.legend_frame, text="Ocupado", text_color=self.palette["text_light"]); self.legend_used_label.pack(side="left", padx=(0, 20))
        self.legend_free_color=ctk.CTkFrame(self.legend_frame, width=15, height=15, fg_color=self.COLOR_FREE, border_width=0); self.legend_free_color.pack(side="left", padx=(0, 5))
        self.legend_free_label=ctk.CTkLabel(self.legend_frame, text="Libre", text_color=self.palette["text_light"]); self.legend_free_label.pack(side="left", padx=(0, 20))

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=2, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self._current_scroll_row = 0
        self._live_canvas: Optional[ctk.CTkCanvas] = None
        self._live_canvas_strategy = ""
        self._last_live_update_time = 0.0
        self._live_update_throttle_ms = 50

    def _clear_bitmaps(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self._current_scroll_row = 0
        self._live_canvas = None
        self._live_canvas_strategy = ""

    def _draw_run(self, canvas: ctk.CTkCanvas, start_index: int, end_index: int, value: int):
        """Helper para dibujar un 'run' (rango) de bloques."""
        color = self.COLOR_FREE if value == 0 else self.COLOR_USED
        current_index = start_index
        while current_index <= end_index:
            row = current_index // COLS
            col_start = current_index % COLS
            blocks_in_this_row = min(COLS - col_start, (end_index - current_index) + 1)
            col_end = col_start + blocks_in_this_row - 1

            x1 = col_start * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
            y1 = row * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
            x2 = (col_end + 1) * (BLOCK_SIZE_PX + BLOCK_PAD_PX) - BLOCK_PAD_PX
            y2 = y1 + BLOCK_SIZE_PX

            # --- EXTRA ROBUSTEZ: Asegurar coordenadas válidas ---
            # Asegurar que x2 > x1 y y2 > y1 antes de dibujar
            safe_x1 = int(x1)
            safe_y1 = int(y1)
            safe_x2 = int(max(x1 + 1, x2)) # Al menos 1 pixel de ancho
            safe_y2 = int(max(y1 + 1, y2)) # Al menos 1 pixel de alto

            # Solo dibujar si las coordenadas son válidas
            if safe_x1 < safe_x2 and safe_y1 < safe_y2:
                 try:
                      canvas.create_rectangle(safe_x1, safe_y1, safe_x2, safe_y2, fill=color, outline="")
                 except Exception as draw_error:
                      print(f"Error drawing rectangle ({safe_x1},{safe_y1} -> {safe_x2},{safe_y2}): {draw_error}")
            # --- FIN EXTRA ROBUSTEZ ---

            current_index += blocks_in_this_row


    def _draw_bitmap(self,
                     bitmap: List[int],
                     strategy_name: str,
                     canvas_instance: Optional[ctk.CTkCanvas] = None
                     ) -> ctk.CTkCanvas:
        """Dibuja un bitmap en un canvas."""

        if not bitmap: # Si es None o lista vacía
            num_blocks = 0
            # --- EXTRA ROBUSTEZ: Usar tamaño mínimo 1 ---
            canvas_width = 1
            canvas_height = 1
        else:
            num_blocks = len(bitmap)
            num_rows = (num_blocks // COLS) + 1
            canvas_width = COLS * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
            canvas_height = num_rows * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
            # --- EXTRA ROBUSTEZ: Asegurar tamaño mínimo 1 ---
            canvas_width = max(1, canvas_width)
            canvas_height = max(1, canvas_height)

        canvas: ctk.CTkCanvas
        if canvas_instance:
            canvas = canvas_instance
            try:
                # Limpiar y reconfigurar asegurando tamaño > 0
                canvas.delete("all")
                canvas.configure(width=max(1, int(canvas_width)), height=max(1, int(canvas_height)))
            except Exception as e:
                print(f"Error reconfigurando canvas existente: {e}")
                canvas = self._create_new_canvas(strategy_name, int(canvas_width), int(canvas_height)) # Crear nuevo si falla
                self._live_canvas = canvas # Actualizar referencia
        else:
            canvas = self._create_new_canvas(strategy_name, int(canvas_width), int(canvas_height))

        # Dibujar (optimizado) solo si hay bloques
        if num_blocks > 0 and bitmap:
            try:
                current_run_val = bitmap[0]
                current_run_start = 0
                for i in range(1, num_blocks):
                    if bitmap[i] != current_run_val:
                        self._draw_run(canvas, current_run_start, i - 1, current_run_val)
                        current_run_val = bitmap[i]
                        current_run_start = i
                self._draw_run(canvas, current_run_start, num_blocks - 1, current_run_val)
            except IndexError as e:
                 print(f"Error dibujando runs (IndexError): {e}. Bitmap len={len(bitmap)}")
            except Exception as e:
                 print(f"Error inesperado dibujando runs: {e}")

        return canvas

    def _create_new_canvas(self, strategy_name: str, canvas_width: int, canvas_height: int) -> ctk.CTkCanvas:
        """Helper para crear el título y el canvas, asegurando tamaño > 0."""
        title_label = ctk.CTkLabel(
            self.scroll_frame, text=f"Estrategia: {strategy_name.upper()}",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=self.palette["text_light"]
        )
        title_label.grid(row=self._current_scroll_row, column=0, padx=10, pady=(15, 5), sticky="w")
        self._current_scroll_row += 1

        # --- EXTRA ROBUSTEZ: Asegurar tamaño > 0 al crear ---
        safe_width = max(1, int(canvas_width))
        safe_height = max(1, int(canvas_height))

        canvas = ctk.CTkCanvas(
            self.scroll_frame, bg=self.palette["frame_bg"], highlightthickness=0,
            width=safe_width, height=safe_height
        )
        canvas.grid(row=self._current_scroll_row, column=0, pady=10, padx=10)
        self._current_scroll_row += 1
        return canvas


    def live_update(self, strategy_name: str, bitmap: List[int]):
        """Punto de entrada llamado DESDE EL HILO DE SIMULACIÓN (vía runner)."""
        current_time_s = time.monotonic()
        elapsed_ms = (current_time_s - self._last_live_update_time) * 1000.0
        if elapsed_ms < self._live_update_throttle_ms:
            return
        self._last_live_update_time = current_time_s
        # Pasar una COPIA (o lista vacía si es None)
        self.after(0, self._safe_live_update, strategy_name, list(bitmap) if bitmap is not None else [])

    def _safe_live_update(self, strategy_name: str, bitmap: List[int]):
        """Esta función se ejecuta EN EL HILO PRINCIPAL de la UI."""
        try:
            if not self.winfo_exists(): return

            # Bitmap ya no debería ser None aquí
            # if bitmap is None: return

            self.info_label.configure(text=f"Simulando en vivo: {strategy_name.upper()}...")

            if strategy_name != self._live_canvas_strategy:
                self._clear_bitmaps()
                self._live_canvas_strategy = strategy_name
                self._live_canvas = self._draw_bitmap(bitmap, strategy_name, canvas_instance=None)
            elif self._live_canvas is not None:
                 # Reutilizar canvas existente, _draw_bitmap limpiará y redibujará
                self._draw_bitmap(bitmap, strategy_name, canvas_instance=self._live_canvas)
            else:
                 # Si canvas no existe (raro), crearlo
                self._live_canvas = self._draw_bitmap(bitmap, strategy_name, canvas_instance=None)

        except Exception as e:
            print(f"Error crítico en _safe_live_update: {e}")


    def show_final_snapshots(self, bitmaps: Optional[Dict[str, List[int]]]):
        """Punto de entrada para los resultados FINALES."""
        self._clear_bitmaps()
        if bitmaps is None:
            self.info_label.configure(text="La simulación falló. No hay bitmap para mostrar.")
            return
        if not bitmaps:
            self.info_label.configure(text="No se recibieron bitmaps de la simulación.")
            return
        self.info_label.configure(text=f"Mostrando {len(bitmaps)} bitmap(s) finales:")
        for strategy_name, bitmap_to_draw in bitmaps.items():
            # Robustez: Enviar lista vacía si es None
            safe_bitmap = bitmap_to_draw if bitmap_to_draw is not None else []
            display_name = strategy_name
            if bitmap_to_draw is None:
                print(f"Warning: Bitmap final para '{strategy_name}' es None.")
                display_name += " (Bitmap Inválido)"
            self._draw_bitmap(safe_bitmap, display_name, canvas_instance=None)