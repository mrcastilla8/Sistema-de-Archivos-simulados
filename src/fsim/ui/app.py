# Owner: Dev 5
import customtkinter as ctk
from .main_view import MainView

# Paleta de colores definida por el usuario
PALETTE = {
    "app_bg": "#320A6B",        # Fondo más oscuro
    "frame_bg": "#065084",      # Fondo de frames/sidebar
    "button": "#0F828C",        # Color de botones
    "button_hover": "#78B9B5",  # Hover y acentos
    "text_light": "#78B9B5",    # Texto principal
    "text_on_button": "#FFFFFF" # Texto sobre botones
}

def main():
    """
    Punto de entrada principal para la aplicación de UI (opcional).
    """
    try:
        ctk.set_appearance_mode("dark") # Mantiene el cromo oscuro (close, min, max)
        
        app = ctk.CTk()
        app.title("FSim - Simulador de Sistemas de Archivos")
        app.geometry("1100x700")
        
        # Aplicar color de fondo a la ventana principal
        app.configure(fg_color=PALETTE["app_bg"])

        # Pasamos la paleta a la vista principal
        main_view = MainView(master=app, palette=PALETTE)
        main_view.pack(fill="both", expand=True, padx=10, pady=10)

        app.mainloop()

    except ImportError:
        print("Error: 'customtkinter' no está instalado.")
        print("Ejecuta 'pip install customtkinter' para usar la UI.")
        print("Como alternativa, usa la CLI: python -m fsim ...")
    except Exception as e:
        print(f"No se pudo iniciar la UI: {e}")
        print("Asegúrate de tener un entorno gráfico (DISPLAY) disponible.")
        print("Como alternativa, usa la CLI: python -m fsim ...")


if __name__ == "__main__":
    main()