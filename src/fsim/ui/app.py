# Owner: Dev 5
# UI opcional (customtkinter). No es requerida para la CLI.
try:
    import customtkinter as ctk
except Exception as e:
    ctk = None

def main():
    if ctk is None:
        print("customtkinter no instalado. Ejecuta la CLI con: python -m fsim ...")
        return
    app = ctk.CTk()
    app.title("Filesystem Simulator")
    app.geometry("900x600")
    label = ctk.CTkLabel(app, text="UI en construcción. Usa la CLI por ahora.", font=("Arial", 16))
    label.pack(pady=20)
    app.mainloop()

if __name__ == "__main__":
    main()
