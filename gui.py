import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import os
import queue
import json

# Importar la lógica de corrección
try:
    from corrector import corregir_reporte_pdf
except ImportError:
    messagebox.showerror("Error", "No se encontró el archivo corrector.py")
    sys.exit(1)

CONFIG_FILE = "config.json"

MODELS_JSON = {
    "ChatGPT": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
    "Gemini": ["gemini-3.5-flash", "gemini-3.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"],
    "Claude": ["claude-3-haiku-20240307", "claude-3-5-sonnet-20240620", "claude-3-sonnet-20240229", "claude-3-opus-20240229"],
    "Grok": ["grok-beta", "grok-2", "grok-2-mini"]
}

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
        self.root.geometry("680x680")
        self.root.resizable(False, False)
        
        self.input_file = tk.StringVar()
        self.report_file = tk.StringVar()
        self.guide_file = tk.StringVar()
        self.agents_var = tk.IntVar(value=10)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.do_spelling_var = tk.BooleanVar(value=True)
        self.do_dictamen_var = tk.BooleanVar(value=True)
        self.do_guide_var = tk.BooleanVar(value=True)
        self.do_crossref_var = tk.BooleanVar(value=True)
        self.mode_var = tk.StringVar(value="cli") # 'cli' o 'api'
        self.agent_var = tk.StringVar(value="Antigravity")
        
        self.api_llm_var = tk.StringVar(value="ChatGPT")
        self.api_model_var = tk.StringVar(value="gpt-4o-mini")
        self.api_key_var = tk.StringVar()
        
        self.config_data = self.load_config()
        
        self.msg_queue = queue.Queue()
        
        self.create_widgets()
        
        self.apply_config()
        
        self.root.after(100, self.process_queue)
        
        # Redirigir stdout y stderr
        sys.stdout = StdoutRedirector(self.console_text, self.msg_queue)
        sys.stderr = StdoutRedirector(self.console_text, self.msg_queue)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self):
        self.config_data["api_keys"] = self.config_data.get("api_keys", {})
        llm = self.api_llm_var.get()
        key = self.api_key_var.get()
        if key:
            self.config_data["api_keys"][llm] = key
            
        self.config_data["last_llm"] = llm
        self.config_data["last_model"] = self.api_model_var.get()
        self.config_data["mode"] = self.mode_var.get()
        
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            print(f"Error guardando configuración: {e}", file=sys.stderr)

    def apply_config(self):
        if "mode" in self.config_data:
            self.mode_var.set(self.config_data["mode"])
        if "last_llm" in self.config_data:
            self.api_llm_var.set(self.config_data["last_llm"])
        if "last_model" in self.config_data:
            self.api_model_var.set(self.config_data["last_model"])
        self.toggle_mode()

    def update_api_key_from_config(self, *args):
        llm = self.api_llm_var.get()
        keys = self.config_data.get("api_keys", {})
        self.api_key_var.set(keys.get(llm, ""))
        
        # Actualizar modelos disponibles
        models = MODELS_JSON.get(llm, [])
        self.api_model_combo['values'] = models
        if models and self.api_model_var.get() not in models:
            self.api_model_var.set(models[0])

    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Sección 1: Selección de Archivo ---
        file_frame = ttk.LabelFrame(main_frame, text="1. Selección de Archivos", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="Memoria (PDF):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.file_entry = ttk.Entry(file_frame, textvariable=self.input_file, state='readonly', width=55)
        self.file_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(file_frame, text="Buscar PDF...", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(file_frame, text="Dictamen Académico (opcional):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.report_entry = ttk.Entry(file_frame, textvariable=self.report_file, state='readonly', width=55)
        self.report_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(file_frame, text="Buscar Destino...", command=self.browse_report).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(file_frame, text="Guía / Manual (PDF, opcional):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.guide_entry = ttk.Entry(file_frame, textvariable=self.guide_file, state='readonly', width=55)
        self.guide_entry.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Button(file_frame, text="Buscar Guía...", command=self.browse_guide).grid(row=2, column=2, padx=5, pady=5)
        
        # --- Sección 2: Opciones de Corrección ---
        options_frame = ttk.LabelFrame(main_frame, text="2. Opciones de Ejecución", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        
        # Tareas
        ttk.Label(options_frame, text="Tareas:").grid(row=0, column=0, sticky=tk.W, pady=5)
        tasks_frame = ttk.Frame(options_frame)
        tasks_frame.grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Checkbutton(tasks_frame, text="Corrección Ortográfica", variable=self.do_spelling_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(tasks_frame, text="Dictamen Académico", variable=self.do_dictamen_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(tasks_frame, text="Verificación de Guía", variable=self.do_guide_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(tasks_frame, text="Ref. Cruzadas", variable=self.do_crossref_var).pack(side=tk.LEFT, padx=5)
        
        # Agentes y Modo
        ttk.Label(options_frame, text="Modo de Ejecución:").grid(row=1, column=0, sticky=tk.W, pady=5)
        mode_frame = ttk.Frame(options_frame)
        mode_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(mode_frame, text="CLI Local (agy, gh, claude)", variable=self.mode_var, value="cli", command=self.toggle_mode).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="API Directa (Tokens/Keys)", variable=self.mode_var, value="api", command=self.toggle_mode).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(options_frame, text="Hilos paralelos:").grid(row=2, column=0, sticky=tk.W, pady=5)
        agents_spinbox = ttk.Spinbox(options_frame, from_=1, to=50, textvariable=self.agents_var, width=5)
        agents_spinbox.grid(row=2, column=1, sticky=tk.W, padx=10)
        
        # CLI Frame
        self.cli_frame = ttk.Frame(options_frame)
        ttk.Label(self.cli_frame, text="Agente CLI:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.agent_combo = ttk.Combobox(self.cli_frame, textvariable=self.agent_var, state='readonly', width=15)
        self.agent_combo['values'] = ("Antigravity", "GitHub CLI", "Claude Code")
        self.agent_combo.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        # API Frame
        self.api_frame = ttk.Frame(options_frame)
        
        ttk.Label(self.api_frame, text="Proveedor LLM:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.api_llm_combo = ttk.Combobox(self.api_frame, textvariable=self.api_llm_var, state='readonly', width=15)
        self.api_llm_combo['values'] = list(MODELS_JSON.keys())
        self.api_llm_combo.grid(row=0, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(self.api_frame, text="Modelo:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.api_model_combo = ttk.Combobox(self.api_frame, textvariable=self.api_model_var, state='readonly', width=25)
        self.api_model_combo.grid(row=1, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(self.api_frame, text="API Key:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.api_key_entry = ttk.Entry(self.api_frame, textvariable=self.api_key_var, show="*", width=35)
        self.api_key_entry.grid(row=2, column=1, sticky=tk.W, padx=10)
        
        self.api_llm_var.trace_add('write', self.update_api_key_from_config)
        self.update_api_key_from_config()
        
        # Colocar frames dinámicos
        self.cli_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        self.api_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Sobrescribir
        ttk.Checkbutton(options_frame, text="Sobrescribir archivo original", variable=self.overwrite_var).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # --- Sección 3: Acciones ---
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(fill=tk.X, pady=5)
        
        self.run_button = ttk.Button(action_frame, text="Iniciar Corrección", command=self.start_correction)
        self.run_button.pack(side=tk.RIGHT, padx=5)
        
        self.terminal_button = ttk.Button(action_frame, text="Terminal Antigravity (Opcional)", command=self.login_antigravity)
        self.terminal_button.pack(side=tk.RIGHT, padx=5)

        self.prompts_button = ttk.Button(action_frame, text="Editar Perfiles (Prompts)", command=self.open_prompts_editor)
        self.prompts_button.pack(side=tk.LEFT, padx=5)
        
        # --- Sección 4: Consola ---
        console_frame = ttk.LabelFrame(main_frame, text="Consola de Progreso", padding="10")
        console_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.console_text = tk.Text(console_frame, height=15, wrap=tk.WORD, state=tk.DISABLED, bg="black", fg="white", font=("Consolas", 9))
        self.console_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(self.console_text, command=self.console_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.console_text.config(yscrollcommand=scrollbar.set)

    def toggle_mode(self):
        mode = self.mode_var.get()
        if mode == "cli":
            self.api_frame.grid_remove()
            self.cli_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
            self.terminal_button.pack(side=tk.RIGHT, padx=5)
        else:
            self.cli_frame.grid_remove()
            self.api_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
            self.terminal_button.pack_forget()

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar Memoria PDF",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if file_path:
            self.input_file.set(file_path)

    def browse_report(self):
        file_path = filedialog.asksaveasfilename(
            title="Guardar Dictamen Académico",
            defaultextension=".txt",
            filetypes=[("Archivos de Texto", "*.txt")]
        )
        if file_path:
            self.report_file.set(file_path)

    def browse_guide(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar Guía o Manual (PDF)",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if file_path:
            self.guide_file.set(file_path)

    def login_antigravity(self):
        if os.name == 'nt':
            os.system('start cmd /k "agy --help"')
        else:
            self.msg_queue.put("Esta función abre la terminal solo en Windows.\n")

    def open_prompts_editor(self):
        editor = tk.Toplevel(self.root)
        editor.title("Editar Perfiles (Prompts)")
        editor.geometry("700x650")
        editor.resizable(True, True)
        
        try:
            from corrector import load_prompts
            prompts = load_prompts()
            if len(prompts) == 3:
                system_personality, dictamen_prompt, guide_prompt = prompts
            else:
                system_personality, dictamen_prompt = prompts
                guide_prompt = ""
        except ImportError:
            system_personality, dictamen_prompt, guide_prompt = "", "", ""
            
        main_frame = ttk.Frame(editor, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        def load_txt_to_widget(text_widget):
            file_path = filedialog.askopenfilename(
                title="Seleccionar archivo de Prompt (TXT)",
                filetypes=[("Archivos de Texto", "*.txt")]
            )
            if file_path:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    text_widget.delete("1.0", tk.END)
                    text_widget.insert(tk.END, content)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")

        def save_widget_to_txt(text_widget):
            file_path = filedialog.asksaveasfilename(
                title="Guardar Prompt como (TXT)",
                defaultextension=".txt",
                filetypes=[("Archivos de Texto", "*.txt")]
            )
            if file_path:
                try:
                    content = text_widget.get("1.0", tk.END).strip()
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    messagebox.showinfo("Guardado", f"El prompt se guardó correctamente en:\n{file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{e}")
        
        # Corrector Prompt
        header_frame_1 = ttk.Frame(main_frame)
        header_frame_1.pack(fill=tk.X, pady=(0,2))
        ttk.Label(header_frame_1, text="Personalidad del Corrector Ortográfico:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        buttons_1 = ttk.Frame(header_frame_1)
        buttons_1.pack(side=tk.RIGHT)
        ttk.Button(buttons_1, text="Cargar TXT", command=lambda: load_txt_to_widget(system_text)).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(buttons_1, text="Guardar TXT", command=lambda: save_widget_to_txt(system_text)).pack(side=tk.LEFT)
        
        system_text = tk.Text(main_frame, height=8, wrap=tk.WORD, font=("Consolas", 10))
        system_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        system_text.insert(tk.END, system_personality)
        
        # Dictamen Prompt
        header_frame_2 = ttk.Frame(main_frame)
        header_frame_2.pack(fill=tk.X, pady=(0,2))
        ttk.Label(header_frame_2, text="Prompt del Dictamen Académico (Revisión de Contenido):", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        buttons_2 = ttk.Frame(header_frame_2)
        buttons_2.pack(side=tk.RIGHT)
        ttk.Button(buttons_2, text="Cargar TXT", command=lambda: load_txt_to_widget(dictamen_text)).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(buttons_2, text="Guardar TXT", command=lambda: save_widget_to_txt(dictamen_text)).pack(side=tk.LEFT)
        
        dictamen_text = tk.Text(main_frame, height=8, wrap=tk.WORD, font=("Consolas", 10))
        dictamen_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        dictamen_text.insert(tk.END, dictamen_prompt)
        
        # Guide Prompt
        header_frame_3 = ttk.Frame(main_frame)
        header_frame_3.pack(fill=tk.X, pady=(0,2))
        ttk.Label(header_frame_3, text="Prompt del Verificador de Guía/Manual:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        buttons_3 = ttk.Frame(header_frame_3)
        buttons_3.pack(side=tk.RIGHT)
        ttk.Button(buttons_3, text="Cargar TXT", command=lambda: load_txt_to_widget(guide_text)).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(buttons_3, text="Guardar TXT", command=lambda: save_widget_to_txt(guide_text)).pack(side=tk.LEFT)
        
        guide_text = tk.Text(main_frame, height=8, wrap=tk.WORD, font=("Consolas", 10))
        guide_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        guide_text.insert(tk.END, guide_prompt)
        
        def save_prompts():
            new_system = system_text.get("1.0", tk.END).strip()
            new_dictamen = dictamen_text.get("1.0", tk.END).strip()
            new_guide = guide_text.get("1.0", tk.END).strip()
            
            prompts_data = {
                "system_personality": new_system,
                "dictamen_prompt": new_dictamen,
                "guide_prompt": new_guide
            }
            
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                prompts_file = os.path.join(base_dir, "prompts.json")
                with open(prompts_file, "w", encoding="utf-8") as f:
                    json.dump(prompts_data, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Guardado", "Los perfiles han sido guardados exitosamente.", parent=editor)
                editor.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudieron guardar los perfiles:\n{e}", parent=editor)
                
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="Guardar", command=save_prompts).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=editor.destroy).pack(side=tk.RIGHT, padx=5)

    def process_queue(self):
        while not self.msg_queue.empty():
            msg = self.msg_queue.get()
            self.console_text.config(state=tk.NORMAL)
            self.console_text.insert(tk.END, msg)
            self.console_text.see(tk.END)
            self.console_text.config(state=tk.DISABLED)
        self.root.after(100, self.process_queue)

    def run_correction_thread(self, input_path, output_path, num_agents, agent_name, mode, api_llm, api_model, report_path, do_spelling, do_dictamen, do_guide, guide_path, do_crossref):
        try:
            corregir_reporte_pdf(input_path, output_path, num_agents, agent_name, mode, api_llm, api_model, report_path, do_spelling, do_dictamen, do_guide, guide_path, do_crossref)
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
            
        mode = self.mode_var.get()
        api_llm = ""
        api_model = ""
        agent_name = ""
        
        if mode == "api":
            api_llm = self.api_llm_var.get()
            api_model = self.api_model_var.get()
            api_key = self.api_key_var.get()
            
            if not api_key:
                messagebox.showwarning("Atención", "Por favor, ingresa la API Key para continuar.")
                return
                
            # Establecer variable de entorno
            if api_llm == "ChatGPT":
                os.environ["OPENAI_API_KEY"] = api_key
            elif api_llm == "Gemini":
                os.environ["GEMINI_API_KEY"] = api_key
            elif api_llm == "Claude":
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif api_llm == "Grok":
                os.environ["XAI_API_KEY"] = api_key
                
            self.save_config()
        else:
            agent_name = self.agent_var.get()
            
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
        if mode == "api":
            self.msg_queue.put(f"Iniciando proceso con {num_agents} hilos usando API de {api_llm} ({api_model})...\n")
        else:
            self.msg_queue.put(f"Iniciando proceso con {num_agents} agentes de {agent_name}...\n")
            
        self.msg_queue.put(f"Archivo entrada: {input_path}\n")
        self.msg_queue.put(f"Archivo salida: {output_path}\n")
        
        report_path = self.report_file.get()
        guide_path = self.guide_file.get()
        do_spelling = self.do_spelling_var.get()
        do_dictamen = self.do_dictamen_var.get()
        do_guide = self.do_guide_var.get()
        
        do_crossref = self.do_crossref_var.get()
        
        if not do_spelling and not do_dictamen and not do_guide and not do_crossref:
            self.msg_queue.put("No se seleccionó ninguna tarea a realizar.\n")
            self.run_button.config(state=tk.NORMAL)
            return
            
        if do_guide and not guide_path:
            self.msg_queue.put("AVISO: Tarea de Verificación de Guía ignorada por no seleccionar archivo de Guía.\n")
            do_guide = False
            
        # Lanzar el hilo
        thread = threading.Thread(target=self.run_correction_thread, args=(input_path, output_path, num_agents, agent_name, mode, api_llm, api_model, report_path, do_spelling, do_dictamen, do_guide, guide_path, do_crossref))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = QuironGUI(root)
    root.mainloop()
