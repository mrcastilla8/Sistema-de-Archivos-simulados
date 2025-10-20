# Owner: Dev 3
import customtkinter as ctk
import json

class ResultsView(ctk.CTkFrame):
    """
    Vista para mostrar los resultados de la simulación (en JSON).
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(self)
        self.textbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.textbox.insert("0.0", "Ejecuta una simulación desde la pestaña 'Escenario' para ver los resultados aquí.")
        self.textbox.configure(state="disabled")

    def show_results(self, results_dict: dict):
        """
Imprime los resultados de la simulación en el cuadro de texto.
Esta función es llamada por MainView.
"""
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        
        try:
            formatted_json = json.dumps(results_dict, indent=2)
            self.textbox.insert("0.0", formatted_json)
        except Exception as e:
            self.textbox.insert("0.0", f"Error al formatear resultados: {e}\n\nDatos brutos:\n{results_dict}")
            
        self.textbox.configure(state="disabled")