"""
gui.py
Interfaz gráfica de ChispaIA en Tkinter, con estética dark mode.
Tres pestañas: Analizar, Historial/Favoritos, Configuración.
"""

import json
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import ai_engine
import config_manager
import ocr_engine

# --- Paleta dark mode ---
BG = "#1e1e1e"
BG_PANEL = "#262626"
BG_INPUT = "#2d2d2d"
FG = "#e8e8e8"
FG_MUTED = "#9a9a9a"
ACCENT = "#d97757"  # tono "Claude-inspired"
ACCENT_HOVER = "#c9663f"
BORDER = "#3a3a3a"

HISTORY_FILE = Path(config_manager.APP_DIR) / "historial.json"

TONE_LABELS = {
    "coqueto": "😏 Coqueto",
    "nerd": "🤓 Nerd / Divertido",
    "directo": "💪 Directo",
    "misterioso": "🌙 Misterioso",
    "tierno": "🥰 Tierno",
    "sarcastico": "😏 Sarcástico",
}


def load_history() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history(history: list):
    config_manager.APP_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


class ChispaIAApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ChispaIA — Asistente de chat con IA")
        self.root.geometry("880x680")
        self.root.configure(bg=BG)
        self.root.minsize(720, 560)

        self.image_path = None
        self.config = config_manager.load_config()

        self._setup_style()
        self._build_ui()

    # ---------- estilo ----------
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_PANEL, foreground=FG_MUTED,
                         padding=(16, 8), font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", BG)],
                  foreground=[("selected", ACCENT)])

        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=BG_PANEL)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=BG, foreground=FG_MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI", 14, "bold"))

        style.configure("TButton", background=ACCENT, foreground="white",
                         font=("Segoe UI", 10, "bold"), padding=(14, 8), borderwidth=0)
        style.map("TButton", background=[("active", ACCENT_HOVER)])

        style.configure("Secondary.TButton", background=BG_INPUT, foreground=FG,
                         font=("Segoe UI", 9), padding=(10, 6), borderwidth=1)
        style.map("Secondary.TButton", background=[("active", BORDER)])

        style.configure("TCombobox", fieldbackground=BG_INPUT, background=BG_INPUT, foreground=FG)
        style.configure("TRadiobutton", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("TCheckbutton", background=BG, foreground=FG)

    # ---------- construcción de UI ----------
    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_analizar = ttk.Frame(notebook)
        self.tab_historial = ttk.Frame(notebook)
        self.tab_config = ttk.Frame(notebook)

        notebook.add(self.tab_analizar, text="  💬 Analizar chat  ")
        notebook.add(self.tab_historial, text="  ⭐ Historial  ")
        notebook.add(self.tab_config, text="  ⚙ Configuración  ")

        self._build_tab_analizar()
        self._build_tab_historial()
        self._build_tab_config()

    # ---------- pestaña: analizar ----------
    def _build_tab_analizar(self):
        frame = self.tab_analizar

        ttk.Label(frame, text="Pegá el chat o cargá una captura de pantalla",
                  style="Title.TLabel").pack(anchor="w", pady=(10, 4), padx=4)

        input_row = ttk.Frame(frame)
        input_row.pack(fill="x", padx=4, pady=(0, 8))

        self.text_input = tk.Text(frame, height=8, bg=BG_INPUT, fg=FG, insertbackground=FG,
                                   font=("Segoe UI", 10), relief="flat", wrap="word",
                                   highlightthickness=1, highlightbackground=BORDER)
        self.text_input.pack(fill="x", padx=4, pady=(0, 8))

        img_row = ttk.Frame(frame)
        img_row.pack(fill="x", padx=4, pady=(0, 10))
        ttk.Button(img_row, text="📷 Cargar captura de pantalla", style="Secondary.TButton",
                   command=self._select_image).pack(side="left")
        self.img_label = ttk.Label(img_row, text="Ninguna imagen cargada", style="Muted.TLabel")
        self.img_label.pack(side="left", padx=10)
        ttk.Button(img_row, text="✕ Quitar", style="Secondary.TButton",
                   command=self._clear_image).pack(side="left")

        tone_row = ttk.Frame(frame)
        tone_row.pack(fill="x", padx=4, pady=(0, 10))
        ttk.Label(tone_row, text="Tono de respuesta:").pack(side="left", padx=(0, 8))
        self.tone_var = tk.StringVar(value=self.config.get("default_tone", "coqueto"))
        tone_combo = ttk.Combobox(tone_row, textvariable=self.tone_var, state="readonly",
                                   values=list(TONE_LABELS.keys()), width=14)
        tone_combo.pack(side="left")
        self.tone_display = ttk.Label(tone_row, text=TONE_LABELS.get(self.tone_var.get(), ""),
                                       style="Muted.TLabel")
        self.tone_display.pack(side="left", padx=10)
        tone_combo.bind("<<ComboboxSelected>>",
                         lambda e: self.tone_display.config(text=TONE_LABELS.get(self.tone_var.get(), "")))

        mode_row = ttk.Frame(frame)
        mode_row.pack(fill="x", padx=4, pady=(0, 10))
        ttk.Label(mode_row, text="Modo:").pack(side="left", padx=(0, 8))
        self.mode_label = ttk.Label(mode_row, text=self._mode_display_text(), style="Muted.TLabel")
        self.mode_label.pack(side="left")

        self.generate_btn = ttk.Button(frame, text="✨ Generar sugerencias", command=self._on_generate)
        self.generate_btn.pack(anchor="w", padx=4, pady=(0, 12))

        self.status_label = ttk.Label(frame, text="", style="Muted.TLabel")
        self.status_label.pack(anchor="w", padx=4)

        # resultados
        results_panel = ttk.Frame(frame, style="Panel.TFrame")
        results_panel.pack(fill="both", expand=True, padx=4, pady=(6, 4))
        self.results_container = ttk.Frame(results_panel, style="Panel.TFrame")
        self.results_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.result_widgets = []

    def _mode_display_text(self):
        mode = self.config.get("mode", "online")
        return "🌐 Online (Claude)" if mode == "online" else "💻 Offline (Ollama, local)"

    def _select_image(self):
        path = filedialog.askopenfilename(
            title="Seleccionar captura de pantalla",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp"), ("Todos los archivos", "*.*")]
        )
        if path:
            self.image_path = path
            self.img_label.config(text=Path(path).name)

    def _clear_image(self):
        self.image_path = None
        self.img_label.config(text="Ninguna imagen cargada")

    def _on_generate(self):
        chat_text = self.text_input.get("1.0", "end").strip()
        tone = self.tone_var.get()

        if not chat_text and not self.image_path:
            messagebox.showwarning("Falta información",
                                    "Pegá texto del chat o cargá una captura de pantalla.")
            return

        self.config = config_manager.load_config()
        mode = self.config.get("mode", "online")

        if mode == "online" and not config_manager.has_api_key():
            messagebox.showwarning("Falta API key",
                                    "Configurá tu API key de Anthropic en la pestaña Configuración.")
            return

        self.generate_btn.config(state="disabled", text="Generando...")
        self.status_label.config(text="Pensando en las mejores respuestas...")
        self._clear_results()

        threading.Thread(target=self._generate_worker, args=(chat_text, tone, mode), daemon=True).start()

    def _generate_worker(self, chat_text, tone, mode):
        try:
            working_text = chat_text
            image_to_send = self.image_path if mode == "online" else None

            # En modo offline, si hay imagen, la pasamos por OCR primero
            if mode == "offline" and self.image_path:
                try:
                    ocr_text = ocr_engine.extract_text_from_image(self.image_path)
                    working_text = (working_text + "\n" + ocr_text).strip()
                except ocr_engine.OCRError as e:
                    self.root.after(0, lambda: self._on_error(str(e)))
                    return

            suggestions = ai_engine.generate_suggestions(working_text, tone, image_to_send)
            self.root.after(0, lambda: self._on_success(suggestions, working_text, tone))
        except ai_engine.AIEngineError as e:
            self.root.after(0, lambda: self._on_error(str(e)))
        except Exception as e:
            self.root.after(0, lambda: self._on_error(f"Error inesperado: {e}"))

    def _on_error(self, message):
        self.generate_btn.config(state="normal", text="✨ Generar sugerencias")
        self.status_label.config(text="")
        messagebox.showerror("Error", message)

    def _on_success(self, suggestions, chat_text, tone):
        self.generate_btn.config(state="normal", text="✨ Generar sugerencias")
        self.status_label.config(text=f"{len(suggestions)} sugerencias generadas.")
        self._render_results(suggestions)

        history = load_history()
        history.insert(0, {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tono": tone,
            "chat": chat_text[:500],
            "sugerencias": suggestions,
            "favorito": False,
        })
        save_history(history[:200])
        self._refresh_history_list()

    def _clear_results(self):
        for w in self.result_widgets:
            w.destroy()
        self.result_widgets = []

    def _render_results(self, suggestions):
        self._clear_results()
        for i, suggestion in enumerate(suggestions, 1):
            row = ttk.Frame(self.results_container, style="Panel.TFrame")
            row.pack(fill="x", pady=6)

            text_widget = tk.Text(row, height=2, bg=BG_INPUT, fg=FG, wrap="word",
                                   font=("Segoe UI", 10), relief="flat", padx=8, pady=6)
            text_widget.insert("1.0", suggestion)
            text_widget.config(state="disabled")
            text_widget.pack(side="left", fill="x", expand=True)

            copy_btn = ttk.Button(row, text="📋 Copiar", style="Secondary.TButton",
                                   command=lambda s=suggestion: self._copy_to_clipboard(s))
            copy_btn.pack(side="right", padx=(8, 0))

            self.result_widgets.append(row)

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_label.config(text="Copiado al portapapeles ✓")

    # ---------- pestaña: historial ----------
    def _build_tab_historial(self):
        frame = self.tab_historial
        ttk.Label(frame, text="Historial de conversaciones analizadas", style="Title.TLabel").pack(
            anchor="w", pady=(10, 8), padx=4)

        list_frame = ttk.Frame(frame, style="Panel.TFrame")
        list_frame.pack(fill="both", expand=True, padx=4, pady=4)

        canvas = tk.Canvas(list_frame, bg=BG_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.history_inner = ttk.Frame(canvas, style="Panel.TFrame")

        self.history_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.history_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y")

        self._refresh_history_list()

    def _refresh_history_list(self):
        for widget in self.history_inner.winfo_children():
            widget.destroy()

        history = load_history()
        if not history:
            ttk.Label(self.history_inner, text="Todavía no hay conversaciones analizadas.",
                      style="Muted.TLabel").pack(padx=10, pady=10)
            return

        for entry in history[:50]:
            card = ttk.Frame(self.history_inner, style="Panel.TFrame")
            card.pack(fill="x", padx=6, pady=4)

            header = f"{entry['fecha']}  ·  {TONE_LABELS.get(entry['tono'], entry['tono'])}"
            ttk.Label(card, text=header, style="Muted.TLabel").pack(anchor="w")

            preview = (entry.get("chat", "")[:120] + "…") if len(entry.get("chat", "")) > 120 else entry.get("chat", "")
            ttk.Label(card, text=preview or "(imagen sin texto)", wraplength=760).pack(anchor="w", pady=(2, 4))

            for s in entry.get("sugerencias", [])[:4]:
                ttk.Label(card, text=f"• {s}", wraplength=760, style="Muted.TLabel").pack(anchor="w")

            ttk.Separator(self.history_inner, orient="horizontal").pack(fill="x", padx=6, pady=6)

    # ---------- pestaña: configuración ----------
    def _build_tab_config(self):
        frame = self.tab_config
        ttk.Label(frame, text="Configuración", style="Title.TLabel").pack(anchor="w", pady=(10, 12), padx=4)

        # Modo
        mode_panel = ttk.Frame(frame, style="Panel.TFrame")
        mode_panel.pack(fill="x", padx=4, pady=(0, 14))
        ttk.Label(mode_panel, text="Modo de trabajo", style="Title.TLabel").pack(anchor="w", padx=12, pady=(10, 4))

        self.mode_radio_var = tk.StringVar(value=self.config.get("mode", "online"))
        ttk.Radiobutton(mode_panel, text="🌐 Online — usa la API de Claude (mejor calidad, requiere API key)",
                        variable=self.mode_radio_var, value="online",
                        command=self._on_mode_change).pack(anchor="w", padx=12, pady=2)
        ttk.Radiobutton(mode_panel, text="💻 Offline — usa Ollama local (sin internet, requiere tenerlo instalado)",
                        variable=self.mode_radio_var, value="offline",
                        command=self._on_mode_change).pack(anchor="w", padx=12, pady=(2, 10))

        # API key
        api_panel = ttk.Frame(frame, style="Panel.TFrame")
        api_panel.pack(fill="x", padx=4, pady=(0, 14))
        ttk.Label(api_panel, text="API key de Anthropic (Claude)", style="Title.TLabel").pack(
            anchor="w", padx=12, pady=(10, 4))
        ttk.Label(api_panel, text="Se guarda cifrada localmente en tu PC. Conseguila en console.anthropic.com",
                  style="Muted.TLabel").pack(anchor="w", padx=12)

        key_row = ttk.Frame(api_panel, style="Panel.TFrame")
        key_row.pack(fill="x", padx=12, pady=8)
        self.api_key_var = tk.StringVar(value="•" * 20 if config_manager.has_api_key() else "")
        self.api_key_entry = tk.Entry(key_row, textvariable=self.api_key_var, show="•",
                                       bg=BG_INPUT, fg=FG, insertbackground=FG, relief="flat", width=50)
        self.api_key_entry.pack(side="left", ipady=4, padx=(0, 8))
        ttk.Button(key_row, text="Guardar", style="Secondary.TButton",
                   command=self._save_api_key).pack(side="left", padx=4)
        ttk.Button(key_row, text="Probar conexión", style="Secondary.TButton",
                   command=self._test_claude).pack(side="left", padx=4)

        # Ollama
        ollama_panel = ttk.Frame(frame, style="Panel.TFrame")
        ollama_panel.pack(fill="x", padx=4, pady=(0, 14))
        ttk.Label(ollama_panel, text="Configuración de Ollama (modo offline)", style="Title.TLabel").pack(
            anchor="w", padx=12, pady=(10, 4))

        ollama_row = ttk.Frame(ollama_panel, style="Panel.TFrame")
        ollama_row.pack(fill="x", padx=12, pady=8)
        ttk.Label(ollama_row, text="Modelo:").pack(side="left")
        self.ollama_model_var = tk.StringVar(value=self.config.get("ollama_model", "llama3.2"))
        tk.Entry(ollama_row, textvariable=self.ollama_model_var, bg=BG_INPUT, fg=FG,
                 insertbackground=FG, relief="flat", width=20).pack(side="left", ipady=4, padx=(6, 16))
        ttk.Button(ollama_row, text="Probar conexión", style="Secondary.TButton",
                   command=self._test_ollama).pack(side="left")

        ttk.Label(ollama_panel,
                  text="Requiere tener Ollama instalado (ollama.com) y corriendo con:  ollama run llama3.2",
                  style="Muted.TLabel").pack(anchor="w", padx=12, pady=(0, 10))

        self.config_status = ttk.Label(frame, text="", style="Muted.TLabel")
        self.config_status.pack(anchor="w", padx=8, pady=6)

        ttk.Button(frame, text="💾 Guardar toda la configuración", command=self._save_all_config).pack(
            anchor="w", padx=8, pady=6)

    def _on_mode_change(self):
        self.config["mode"] = self.mode_radio_var.get()
        config_manager.save_config(self.config)
        self.mode_label.config(text=self._mode_display_text())

    def _save_api_key(self):
        key = self.api_key_var.get().strip()
        if not key or key.startswith("•"):
            messagebox.showinfo("API key", "Ingresá una API key válida.")
            return
        config_manager.set_api_key(key)
        self.api_key_var.set("•" * 20)
        self.config_status.config(text="API key guardada correctamente ✓")

    def _test_claude(self):
        self.config_status.config(text="Probando conexión con Claude...")
        self.root.update_idletasks()
        ok, msg = ai_engine.test_claude_connection()
        self.config_status.config(text=("✓ " if ok else "✗ ") + msg)

    def _test_ollama(self):
        self.config["ollama_model"] = self.ollama_model_var.get().strip()
        config_manager.save_config(self.config)
        self.config_status.config(text="Probando conexión con Ollama...")
        self.root.update_idletasks()
        ok, msg = ai_engine.test_ollama_connection()
        self.config_status.config(text=("✓ " if ok else "✗ ") + msg)

    def _save_all_config(self):
        self.config["mode"] = self.mode_radio_var.get()
        self.config["ollama_model"] = self.ollama_model_var.get().strip()
        self.config["default_tone"] = self.tone_var.get()
        config_manager.save_config(self.config)
        self.mode_label.config(text=self._mode_display_text())
        self.config_status.config(text="Configuración guardada ✓")
