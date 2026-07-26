"""
main.py
Punto de entrada de ChispaIA.
"""

import tkinter as tk

import ollama_manager
from gui import ChispaIAApp


def main():
    root = tk.Tk()
    app = ChispaIAApp(root)

    def on_close():
        ollama_manager.stop_ollama_server()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
