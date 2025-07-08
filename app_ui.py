"""
Tkinter UI logic for the sheet cutting app.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Canvas, Frame, Scrollbar
from typing import List
from models.part import Part, Placement, Sheet
from packing.engine import PackingEngine
from visualization.visualizer import CuttingPlanVisualizer
from export.google_sheets import GoogleSheetsExporter

class SheetCuttingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Дигитален Трион")
        self.root.geometry("1000x800")

        # Data storage
        self.parts = []
        self.sheets = []

        # Configuration
        from config import DEFAULT_SHEET_SIZES
        self.selected_sheet_sizes = DEFAULT_SHEET_SIZES.copy()

        # Create packing engine
        self.packing_engine = PackingEngine(self.selected_sheet_sizes)

        # UI setup
        self.setup_ui()

        # State variables
        self.editing_part_id = None
        self.calc_in_progress = False

    def setup_ui(self):
        input_frame = ttk.LabelFrame(self.root, text="Детайли на Части")
        input_frame.pack(padx=10, pady=10, fill=tk.X)

        fields = ["Означение", "Име", "Материал", "Дебелина", "Ширина", "Височина", "Количество"]
        self.entries = {}
        for i, field in enumerate(fields):
            ttk.Label(input_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)
            entry = ttk.Entry(input_frame, width=20)
            entry.grid(row=i, column=1, padx=5, pady=2)
            self.entries[field] = entry

        button_row = len(fields)
        self.add_button = ttk.Button(input_frame, text="Добави Част", command=self.add_part)
        self.add_button.grid(row=button_row, column=0, pady=5, sticky=tk.W+tk.E)

        self.update_button = ttk.Button(input_frame, text="Актуализирай", command=self.update_part, state=tk.DISABLED)
        self.update_button.grid(row=button_row, column=1, pady=5, sticky=tk.W+tk.E)

        self.cancel_edit_button = ttk.Button(input_frame, text="Отказ", command=self.cancel_edit, state=tk.DISABLED)
        self.cancel_edit_button.grid(row=button_row+1, column=0, columnspan=2, pady=5)

        ttk.Button(input_frame, text="Избери Размери на Листове", 
                  command=self.show_sheet_size_dialog).grid(
                  row=button_row+2, column=0, columnspan=2, pady=5)

        table_frame = ttk.LabelFrame(self.root, text="Списък на Части")
        table_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        columns = ("ID", "Означение", "Име", "Ширина", "Височина", "Количество")
        self.parts_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.parts_tree.heading(col, text=col)
        self.parts_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.parts_tree.bind("<<TreeviewSelect>>", self.on_part_select)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.parts_tree.yview)
        self.parts_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(padx=10, pady=10, fill=tk.X)
        ttk.Button(self.button_frame, text="Експорт към Google Sheets",
          command=self.export_to_s).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Изчисли План на Разрязване", 
                  command=self.start_calculation_thread).pack(side=tk.LEFT, padx=5)
        self.restart_button = ttk.Button(self.button_frame, text="Рестартирай Изчислението",
                  command=self.restart_calculation, state=tk.DISABLED)
        self.restart_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Изтрий Избраната Част", 
                  command=self.delete_selected_part).pack(side=tk.LEFT, padx=5)
        self.edit_button = ttk.Button(self.button_frame, text="Редактирай Избраната Част", 
                  command=self.edit_selected_part)
        self.edit_button.pack(side=tk.LEFT, padx=5)
        self.edit_button.config(state=tk.DISABLED)
        ttk.Button(self.button_frame, text="Изчисти Всичко", 
                  command=self.clear_all).pack(side=tk.LEFT, padx=5)
        self.show_plan_button = ttk.Button(self.button_frame, text="Покажи План на Разрязване",
                  command=self.show_cutting_plan, state=tk.DISABLED)
        self.show_plan_button.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.button_frame, text="Алгоритъм:").pack(side=tk.LEFT, padx=5)
        self.algo_var = tk.StringVar()
        self.algo_var.set("AUTO")

    def add_part(self):
        # Gather part data from entries
        try:
            part_data = {field: self.entries[field].get() for field in self.entries}
            part_data["Дебелина"] = float(part_data["Дебелина"])
            part_data["Ширина"] = float(part_data["Ширина"])
            part_data["Височина"] = float(part_data["Височина"])
            part_data["Количество"] = int(part_data["Количество"])
        except ValueError as e:
            messagebox.showerror("Грешка", f"Невалидни данни: {e}")
            return

        # Create and add part
        part = Part(**part_data)
        self.parts.append(part)
        self.update_parts_tree()
        self.clear_entries()

    def update_part(self):
        if self.editing_part_id is None:
            return

        # Gather updated part data from entries
        try:
            part_data = {field: self.entries[field].get() for field in self.entries}
            part_data["Дебелина"] = float(part_data["Дебелина"])
            part_data["Ширина"] = float(part_data["Ширина"])
            part_data["Височина"] = float(part_data["Височина"])
            part_data["Количество"] = int(part_data["Количество"])
        except ValueError as e:
            messagebox.showerror("Грешка", f"Невалидни данни: {e}")
            return

        # Update part
        part = self.parts[self.editing_part_id]
        part.update(**part_data)
        self.update_parts_tree()
        self.clear_entries()
        self.editing_part_id = None
        self.update_button.config(state=tk.DISABLED)
        self.cancel_edit_button.config(state=tk.DISABLED)

    def cancel_edit(self):
        self.clear_entries()
        self.editing_part_id = None
        self.update_button.config(state=tk.DISABLED)
        self.cancel_edit_button.config(state=tk.DISABLED)

    def show_sheet_size_dialog(self):
        from config import AVAILABLE_SHEET_SIZES

        dialog = tk.Toplevel(self.root)
        dialog.title("Избор на Размери на Листове")
        dialog.geometry("400x300")

        label = tk.Label(dialog, text="Изберете размери на листове:")
        label.pack(pady=10)

        sheet_size_listbox = tk.Listbox(dialog, selectmode=tk.MULTIPLE)
        for size in AVAILABLE_SHEET_SIZES:
            sheet_size_listbox.insert(tk.END, f"{size[0]}x{size[1]}")
        sheet_size_listbox.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        def on_ok():
            selected_indices = sheet_size_listbox.curselection()
            self.selected_sheet_sizes = [AVAILABLE_SHEET_SIZES[i] for i in selected_indices]
            self.packing_engine = PackingEngine(self.selected_sheet_sizes)  # Recreate engine with new sizes
            dialog.destroy()

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        ok_button = tk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side=tk.LEFT, padx=5)
        cancel_button = tk.Button(button_frame, text="Отказ", command=dialog.destroy)
        cancel_button.pack(side=tk.LEFT, padx=5)

        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def on_part_select(self, event):
        selected_item = self.parts_tree.selection()
        if not selected_item:
            return

        # Get selected part ID
        part_id = self.parts_tree.item(selected_item, "values")[0]
        self.editing_part_id = int(part_id) - 1  # Convert to 0-based index

        # Fill entries with part data
        part = self.parts[self.editing_part_id]
        for field in self.entries:
            self.entries[field].delete(0, tk.END)
            self.entries[field].insert(0, str(getattr(part, field)))

        self.update_button.config(state=tk.NORMAL)
        self.cancel_edit_button.config(state=tk.NORMAL)

    def delete_selected_part(self):
        selected_item = self.parts_tree.selection()
        if not selected_item:
            return

        part_id = int(self.parts_tree.item(selected_item, "values")[0]) - 1
        del self.parts[part_id]
        self.update_parts_tree()

    def edit_selected_part(self):
        selected_item = self.parts_tree.selection()
        if not selected_item:
            return

        part_id = int(self.parts_tree.item(selected_item, "values")[0]) - 1
        part = self.parts[part_id]
        self.editing_part_id = part_id

        # Fill entries with part data
        for field in self.entries:
            self.entries[field].delete(0, tk.END)
            self.entries[field].insert(0, str(getattr(part, field)))

        self.update_button.config(state=tk.NORMAL)
        self.cancel_edit_button.config(state=tk.NORMAL)

    def clear_all(self):
        self.parts = []
        self.sheets = []
        self.update_parts_tree()
        self.clear_entries()

    def show_cutting_plan(self):
        if not self.sheets:
            messagebox.showinfo("Информация", "Няма налични листове за показване на плана.")
            return

        visualizer = CuttingPlanVisualizer(self.sheets)
        visualizer.visualize()

    def export_to_s(self):
        if not self.parts:
            messagebox.showinfo("Информация", "Няма налични части за експортиране.")
            return

        exporter = GoogleSheetsExporter(self.parts)
        exporter.export()

    def start_calculation_thread(self):
        if self.calc_in_progress:
            return

        self.calc_in_progress = True
        self.restart_button.config(state=tk.NORMAL)
        self.show_plan_button.config(state=tk.DISABLED)

        # Run calculation in a separate thread
        import threading
        thread = threading.Thread(target=self.calculate_packing)
        thread.start()

    def calculate_packing(self):
        try:
            # Perform packing calculation
            self.packing_engine.pack(self.parts)

            # Update sheets and visualize plan
            self.sheets = self.packing_engine.sheets
            self.show_cutting_plan()
        except Exception as e:
            messagebox.showerror("Грешка при изчисление", str(e))
        finally:
            self.calc_in_progress = False
            self.restart_button.config(state=tk.DISABLED)
            self.show_plan_button.config(state=tk.NORMAL)

    def restart_calculation(self):
        if self.calc_in_progress:
            return

        self.calc_in_progress = True
        self.restart_button.config(state=tk.DISABLED)
        self.show_plan_button.config(state=tk.DISABLED)

        # Clear previous sheets
        self.sheets = []
        self.update_parts_tree()

        # Re-run packing calculation
        self.start_calculation_thread()

    def update_parts_tree(self):
        # Clear treeview
        for item in self.parts_tree.get_children():
            self.parts_tree.delete(item)

        # Insert updated parts
        for i, part in enumerate(self.parts):
            self.parts_tree.insert("", tk.END, values=(i+1, part.означение, part.име, part.ширина, part.височина, part.количество))

    def clear_entries(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.editing_part_id = None
        self.update_button.config(state=tk.DISABLED)
        self.cancel_edit_button.config(state=tk.DISABLED)
