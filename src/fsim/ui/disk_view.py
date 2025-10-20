# Owner: Dev 5
import customtkinter as ctk

class DiskView(ctk.CTkFrame):
    """
    Vista de marcador de posición para la visualización del disco.
    (Trabajo Futuro)
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.label = ctk.CTkLabel(
            self,
            text="Visualización del Disco (En Construcción)\n\n"
                 "Esta vista podría conectarse al 'on_event' del runner\n"
                 "para mostrar una visualización en vivo del bitmap del FSM.",
            font=ctk.CTkFont(size=16)
        )
        self.label.pack(pady=40, padx=40, expand=True)