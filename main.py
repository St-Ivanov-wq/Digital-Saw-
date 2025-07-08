"""
Entry point for the sheet cutting optimization app.
"""

import tkinter as tk
from ui.app_ui import SheetCuttingApp

def main():
    root = tk.Tk()
    app = SheetCuttingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
