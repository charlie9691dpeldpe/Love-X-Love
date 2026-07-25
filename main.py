"""
main.py
Punto de entrada de ChispaIA.
"""

import tkinter as tk

from gui import ChispaIAApp


def main():
    root = tk.Tk()
    app = ChispaIAApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
