# Owner: Dev 5
import customtkinter as ctk
from typing import Dict, Any, List, Optional

# --- CONSTANTES DE DIBUJO ---
BLOCK_SIZE_PX = 4  # MODIFICADO: Punto medio (4x4 px)
BLOCK_PAD_PX = 1   # MODIFICADO: Añadimos 1px de padding
COLS = 170         # MODIFICADO: 170 columnas (se ajusta bien al ancho)

class DiskView(ctk.CTkFrame):
    """
    Vista para la visualización del bitmap del disco (instantánea final).
    Dibuja un canvas separado por cada estrategia.
    """
    def __init__(self, master, palette: Dict[str, str], **kwargs):
        super().__init__(master, **kwargs)
        self.palette = palette
        
        self.configure(fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Fila 2 (scroll) es la que expande
        
        # --- Colores del Bitmap ---
        self.COLOR_FREE = self.palette["button_hover"] # Azul claro (#78B9B5)
        self.COLOR_USED = self.palette["app_bg"]       # Azul oscuro (#320A6B)
        
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
        
        # Contador de filas para la grilla del scroll_frame
        self._current_scroll_row = 0

    def _clear_bitmaps(self):
        """Limpia todos los widgets (títulos, canvas) del scroll_frame."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self._current_scroll_row = 0

    def _draw_bitmap(self, bitmap: List[int], strategy_name: str):
        """
        MODIFICADO: Dibuja un nuevo título y un nuevo canvas
        dentro del scroll_frame.
        """
        
        # 1. Añadir Título de la Estrategia
        title_label = ctk.CTkLabel(
            self.scroll_frame, 
            text=f"Estrategia: {strategy_name.upper()}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.palette["text_light"]
        )
        title_label.grid(row=self._current_scroll_row, column=0, padx=10, pady=(15, 5), sticky="w")
        self._current_scroll_row += 1

        # 2. Crear un Nuevo Canvas para este bitmap
        num_blocks = len(bitmap)
        num_rows = (num_blocks // COLS) + 1
        
        canvas_width = COLS * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
        canvas_height = num_rows * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
        
        canvas = ctk.CTkCanvas(
            self.scroll_frame,
            bg=self.palette["frame_bg"],
            highlightthickness=0,
            width=canvas_width,
            height=canvas_height
        )
        canvas.grid(row=self._current_scroll_row, column=0, pady=10, padx=10)
        self._current_scroll_row += 1
        
        # 3. Dibujar los bloques en este canvas específico
        for i, bit in enumerate(bitmap):
            row = i // COLS
            col = i % COLS
            
            x1 = col * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
            y1 = row * (BLOCK_SIZE_PX + BLOCK_PAD_PX)
            x2 = x1 + BLOCK_SIZE_PX
            y2 = y1 + BLOCK_SIZE_PX
            
            color = self.COLOR_FREE if bit == 0 else self.COLOR_USED
            
            canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

    def update_display(self, bitmaps: Optional[Dict[str, List[int]]]):
        """
        MODIFICADO: Itera sobre TODOS los bitmaps recibidos
        y llama a _draw_bitmap para cada uno.
        """
        self._clear_bitmaps()
        
        if bitmaps is None:
            self.info_label.configure(text="La simulación falló. No hay bitmap para mostrar.")
            return
            
        if not bitmaps:
            self.info_label.configure(text="No se recibieron bitmaps de la simulación.")
            return
        
        # Actualizar etiqueta de información
        self.info_label.configure(text=f"Mostrando {len(bitmaps)} bitmap(s) finales:")

        # --- MODIFICACIÓN CLAVE ---
        # Iterar sobre todos los bitmaps y dibujar cada uno
        for strategy_name, bitmap_to_draw in bitmaps.items():
            self._draw_bitmap(bitmap_to_draw, strategy_name)
        # --- FIN MODIFICACIÓN ---