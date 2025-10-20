# Owner: Dev 5
import customtkinter as ctk
from .main_view import MainView

def main():
    """
    Punto de entrada principal para la aplicación de UI (opcional).
    """
    try:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        app = ctk.CTk()
        app.title("FSim - Simulador de Sistemas de Archivos")
        app.geometry("1100x700")

        main_view = MainView(master=app)
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
    # Esto permite correr la UI directamente para pruebas
    # (asumiendo que estás en el directorio raíz y corres con python -m src.fsim.ui.app)
    # El método preferido es a través de un script de entrada
    main()