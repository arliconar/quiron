import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import os
import queue

# Importar la lógica de corrección
try:
    from corrector import corregir_reporte_pdf
except ImportError:
    messagebox.showerror("Error", "No se encontró el archivo corrector.py")
    sys.exit(1)

class StdoutRedirector:
    def __init__(self, text_widget, msg_queue):
        self.text_widget = text_widget
        self.msg_queue = msg_queue

    def write(self, string):
        self.msg_queue.put(string)

    def flush(self):
        pass

class QuironGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Quirón - Corrector de Reportes PDF")
        self.root.geometry("680x550")
        self.root.resizable(False, False)
        
        self.input_file = tk.StringVar()
        self.agents_var = tk.IntVar(value=10)
        self.overwrite_var = tk.BooleanVar(value=False)
        
        self.msg_queue = queue.Queue()
        
        self.create_widgets()
        self.root.after(100, self.process_queue)
        
        # Redirigir stdout y stderr
        sys.stdout = StdoutRedirector(self.console_text, self.msg_queue)
        sys.stderr = StdoutRedirector(self.console_text, self.msg_queue)

    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Sección 1: Selección de Archivo ---
        file_frame = ttk.LabelFrame(main_frame, text="1. Selección de Memoria (PDF)", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="Ruta del archivo:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.file_entry = ttk.Entry(file_frame, textvariable=self.input_file, state='readonly', width=55)
        self.file_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(file_frame, text="Buscar Archivo...", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)
        
        # --- Sección 2: Opciones de Corrección ---
        options_frame = ttk.LabelFrame(main_frame, text="2. Opciones de Ejecución", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        
        # Agentes
        ttk.Label(options_frame, text="Número de Agentes (Hilos paralelos):").grid(row=0, column=0, sticky=tk.W, pady=5)
        agents_spinbox = ttk.Spinbox(options_frame, from_=1, to=50, textvariable=self.agents_var, width=5)
        agents_spinbox.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        # Sobrescribir
        ttk.Checkbutton(options_frame, text="Sobrescribir archivo original", variable=self.overwrite_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # --- Sección 3: Acciones ---
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill=tk.X, pady=5)
        
        self.run_button = ttk.Button(action_frame, text="Iniciar Corrección", command=self.start_correction)
        self.run_button.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(action_frame, text="Terminal Antigravity (Opcional)", command=self.login_antigravity).pack(side=tk.RIGHT, padx=5)
        
        # --- Sección 4: Consola ---
        console_frame = ttk.LabelFrame(main_frame, text="Consola de Progreso", padding="10")
        console_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.console_text = tk.Text(console_frame, height=15, wrap=tk.WORD, state=tk.DISABLED, bg="black", fg="white", font=("Consolas", 9))
        self.console_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.console_text, command=self.console_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.console_text.config(yscrollcommand=scrollbar.set)

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar Memoria PDF",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if file_path:
            self.input_file.set(file_path)

    def login_antigravity(self):
        # Abre una consola para interactuar con agy si es necesario (ej: agy login)
        if os.name == 'nt':
            os.system('start cmd /k "agy --help"')
        else:
            self.msg_queue.put("Esta función abre la terminal solo en Windows.\n")

    def process_queue(self):
        while not self.msg_queue.empty():
            msg = self.msg_queue.get()
            self.console_text.config(state=tk.NORMAL)
            self.console_text.insert(tk.END, msg)
            self.console_text.see(tk.END)
            self.console_text.config(state=tk.DISABLED)
        self.root.after(100, self.process_queue)

    def run_correction_thread(self, input_path, output_path, num_agents):
        try:
            corregir_reporte_pdf(input_path, output_path, num_agents)
            self.msg_queue.put("\n>>> PROCESO FINALIZADO CON ÉXITO <<<\n")
            messagebox.showinfo("Completado", "El reporte ha sido corregido exitosamente.")
        except Exception as e:
            self.msg_queue.put(f"\n[ERROR CRÍTICO] {e}\n")
            messagebox.showerror("Error", f"Ocurrió un error inesperado:\n{e}")
        finally:
            self.run_button.config(state=tk.NORMAL)

    def start_correction(self):
        input_path = self.input_file.get()
        if not input_path or not os.path.exists(input_path):
            messagebox.showwarning("Atención", "Por favor, selecciona un archivo PDF válido.")
            return
            
        num_agents = self.agents_var.get()
        if num_agents < 1:
            messagebox.showwarning("Atención", "El número de agentes debe ser mayor a 0.")
            return
            
        # Determinar archivo de salida
        if self.overwrite_var.get():
            output_path = input_path
        else:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_corregido{ext}"
            
        self.console_text.config(state=tk.NORMAL)
        self.console_text.delete(1.0, tk.END)
        self.console_text.config(state=tk.DISABLED)
        
        self.run_button.config(state=tk.DISABLED)
        self.msg_queue.put(f"Iniciando proceso con {num_agents} agentes...\n")
        self.msg_queue.put(f"Archivo entrada: {input_path}\n")
        self.msg_queue.put(f"Archivo salida: {output_path}\n")
        
        # Lanzar el hilo
        thread = threading.Thread(target=self.run_correction_thread, args=(input_path, output_path, num_agents))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = QuironGUI(root)
    root.mainloop()
