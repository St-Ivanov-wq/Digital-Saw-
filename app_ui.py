"""
Tkinter UI logic for the sheet cutting app.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Canvas, Frame, Scrollbar
from models.part import Part, Placement, Sheet
from packing.engine import PackingEngine
from visualization.visualizer import CuttingPlanVisualizer
from export.google_sheets import GoogleSheetsExporter
from config import DEFAULT_SHEET_SIZES
import threading
import queue
import time

class SheetCuttingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Дигитален Трион")
        self.root.geometry("1000x800")

        # Configure the grid layout
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Create a frame for the sheet size selection
        self.sheet_size_frame = ttk.LabelFrame(self.root, text="Размер на листа")
        self.sheet_size_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # Create a combobox for sheet size selection
        self.sheet_size_var = tk.StringVar()
        self.sheet_size_combobox = ttk.Combobox(self.sheet_size_frame, textvariable=self.sheet_size_var)
        self.sheet_size_combobox["values"] = list(DEFAULT_SHEET_SIZES.keys())
        self.sheet_size_combobox.grid(row=0, column=0, padx=5, pady=5)
        self.sheet_size_combobox.bind("<<ComboboxSelected>>", self.on_sheet_size_selected)

        # Create a button to add a new custom sheet size
        self.add_sheet_size_button = ttk.Button(self.sheet_size_frame, text="Добави размер", command=self.add_sheet_size)
        self.add_sheet_size_button.grid(row=0, column=1, padx=5, pady=5)

        # Create a frame for the parts list
        self.parts_frame = ttk.LabelFrame(self.root, text="Части")
        self.parts_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Configure the parts frame grid
        self.parts_frame.columnconfigure(0, weight=1)
        self.parts_frame.rowconfigure(0, weight=1)

        # Create a treeview for displaying parts
        self.parts_treeview = ttk.Treeview(self.parts_frame, columns=("width", "height", "quantity"), show="headings")
        self.parts_treeview.heading("width", text="Ширина")
        self.parts_treeview.heading("height", text="Височина")
        self.parts_treeview.heading("quantity", text="Количество")
        self.parts_treeview.grid(row=0, column=0, sticky="nsew")

        # Create a scrollbar for the parts treeview
        self.parts_scrollbar = ttk.Scrollbar(self.parts_frame, orient="vertical", command=self.parts_treeview.yview)
        self.parts_scrollbar.grid(row=0, column=1, sticky="ns")
        self.parts_treeview.configure(yscrollcommand=self.parts_scrollbar.set)

        # Create a frame for the part details
        self.part_details_frame = ttk.LabelFrame(self.root, text="Детайли за част")
        self.part_details_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        # Create labels and entries for part details
        ttk.Label(self.part_details_frame, text="Ширина:").grid(row=0, column=0, padx=5, pady=5)
        self.part_width_var = tk.StringVar()
        self.part_width_entry = ttk.Entry(self.part_details_frame, textvariable=self.part_width_var)
        self.part_width_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.part_details_frame, text="Височина:").grid(row=1, column=0, padx=5, pady=5)
        self.part_height_var = tk.StringVar()
        self.part_height_entry = ttk.Entry(self.part_details_frame, textvariable=self.part_height_var)
        self.part_height_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(self.part_details_frame, text="Количество:").grid(row=2, column=0, padx=5, pady=5)
        self.part_quantity_var = tk.StringVar()
        self.part_quantity_entry = ttk.Entry(self.part_details_frame, textvariable=self.part_quantity_var)
        self.part_quantity_entry.grid(row=2, column=1, padx=5, pady=5)

        # Create buttons for part operations
        self.add_part_button = ttk.Button(self.part_details_frame, text="Добави част", command=self.add_part)
        self.add_part_button.grid(row=3, column=0, padx=5, pady=5)

        self.remove_part_button = ttk.Button(self.part_details_frame, text="Премахни част", command=self.remove_part)
        self.remove_part_button.grid(row=3, column=1, padx=5, pady=5)

        # Create a frame for the cutting plan visualization
        self.visualization_frame = ttk.LabelFrame(self.root, text="Визуализация на рязането")
        self.visualization_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=10, pady=10)

        # Configure the visualization frame grid
        self.visualization_frame.columnconfigure(0, weight=1)
        self.visualization_frame.rowconfigure(0, weight=1)

        # Create a canvas for the cutting plan visualization
        self.visualization_canvas = Canvas(self.visualization_frame)
        self.visualization_canvas.grid(row=0, column=0, sticky="nsew")

        # Create a scrollbar for the visualization canvas
        self.visualization_scrollbar = Scrollbar(self.visualization_frame, orient="vertical", command=self.visualization_canvas.yview)
        self.visualization_scrollbar.grid(row=0, column=1, sticky="ns")
        self.visualization_canvas.configure(yscrollcommand=self.visualization_scrollbar.set)

        # Create a frame for the Google Sheets export
        self.export_frame = ttk.LabelFrame(self.root, text="Експорт в Google Sheets")
        self.export_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        # Create a button to export the cutting plan to Google Sheets
        self.export_button = ttk.Button(self.export_frame, text="Експортиране", command=self.export_to_google_sheets)
        self.export_button.grid(row=0, column=0, padx=5, pady=5)

        # Create a status bar
        self.status_bar = ttk.Label(self.root, text="Добре дошли в приложението за рязане на листове!", relief=tk.SUNKEN, anchor="w")
        self.status_bar.grid(row=4, column=0, columnspan=2, sticky="ew")

        # Initialize the packing engine and visualizer
        self.packing_engine = PackingEngine()
        self.visualizer = CuttingPlanVisualizer(self.visualization_canvas)

        # Initialize the parts and sheet variables
        self.parts = []
        self.sheet = None

        # Bind the treeview selection event
        self.parts_treeview.bind("<<TreeviewSelect>>", self.on_part_selected)

        # Update the UI elements
        self.update_sheet_size_combobox()
        self.update_parts_treeview()
        self.update_status_bar()

    def on_sheet_size_selected(self, event):
        """
        Event handler for sheet size selection.
        """
        selected_size = self.sheet_size_var.get()
        if selected_size in DEFAULT_SHEET_SIZES:
            width, height = DEFAULT_SHEET_SIZES[selected_size]
            self.sheet = Sheet(width, height)
            self.visualizer.set_sheet(self.sheet)
            self.update_status_bar()

    def add_sheet_size(self):
        """
        Add a new custom sheet size.
        """
        # Open a dialog to get the custom sheet size from the user
        dialog = CustomSheetSizeDialog(self.root)
        self.root.wait_window(dialog.top)

        # If the user provided a valid size, add it to the combobox and select it
        if dialog.result:
            size_name, (width, height) = dialog.result
            DEFAULT_SHEET_SIZES[size_name] = (width, height)
            self.sheet_size_combobox["values"] = list(DEFAULT_SHEET_SIZES.keys())
            self.sheet_size_var.set(size_name)
            self.on_sheet_size_selected(None)

    def add_part(self):
        """
        Add a new part to the cutting plan.
        """
        try:
            width = float(self.part_width_var.get())
            height = float(self.part_height_var.get())
            quantity = int(self.part_quantity_var.get())
            part = Part(width, height, quantity)
            self.parts.append(part)
            self.update_parts_treeview()
            self.update_status_bar()
        except ValueError:
            messagebox.showerror("Грешка", "Моля, въведете валидни стойности за частите.")

    def remove_part(self):
        """
        Remove the selected part from the cutting plan.
        """
        selected_item = self.parts_treeview.selection()
        if selected_item:
            part_index = self.parts_treeview.index(selected_item)
            del self.parts[part_index]
            self.update_parts_treeview()
            self.update_status_bar()

    def on_part_selected(self, event):
        """
        Event handler for part selection in the treeview.
        """
        selected_item = self.parts_treeview.selection()
        if selected_item:
            part_index = self.parts_treeview.index(selected_item)
            part = self.parts[part_index]
            self.part_width_var.set(part.width)
            self.part_height_var.set(part.height)
            self.part_quantity_var.set(part.quantity)

    def export_to_google_sheets(self):
        """
        Export the cutting plan to Google Sheets.
        """
        if not self.sheet or not self.parts:
            messagebox.showwarning("Предупреждение", "Моля, добавете лист и части преди експортиране.")
            return

        # Create a new thread for the export process
        export_thread = threading.Thread(target=self.run_export_to_google_sheets)
        export_thread.start()

    def run_export_to_google_sheets(self):
        """
        Run the export process in a separate thread.
        """
        try:
            exporter = GoogleSheetsExporter()
            exporter.export_cutting_plan(self.sheet, self.parts)
            self.show_export_success_message()
        except Exception as e:
            self.show_export_error_message(str(e))

    def show_export_success_message(self):
        """
        Show a success message after exporting to Google Sheets.
        """
        self.root.after(0, messagebox.showinfo, "Успех", "Планът за рязане беше експортиран успешно в Google Sheets.")

    def show_export_error_message(self, error_message):
        """
        Show an error message after a failed export to Google Sheets.
        """
        self.root.after(0, messagebox.showerror, "Грешка при експортиране", error_message)

    def update_sheet_size_combobox(self):
        """
        Update the sheet size combobox values.
        """
        self.sheet_size_combobox["values"] = list(DEFAULT_SHEET_SIZES.keys())
        if self.sheet:
            size_name = next((name for name, dims in DEFAULT_SHEET_SIZES.items() if dims == (self.sheet.width, self.sheet.height)), None)
            self.sheet_size_var.set(size_name)

    def update_parts_treeview(self):
        """
        Update the parts treeview with the current parts list.
        """
        self.parts_treeview.delete(*self.parts_treeview.get_children())
        for part in self.parts:
            self.parts_treeview.insert("", "end", values=(part.width, part.height, part.quantity))

    def update_status_bar(self):
        """
        Update the status bar text.
        """
        if self.sheet:
            self.status_bar.config(text=f"Лист: {self.sheet.width}x{self.sheet.height} мм")
        else:
            self.status_bar.config(text="Добре дошли в приложението за рязане на листове!")

# Custom dialog class for adding a new sheet size
class CustomSheetSizeDialog:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("Добавяне на нов размер на листа")
        self.top.geometry("300x200")

        self.result = None

        # Create labels and entries for sheet size
        ttk.Label(self.top, text="Име на размера:").grid(row=0, column=0, padx=5, pady=5)
        self.size_name_var = tk.StringVar()
        self.size_name_entry = ttk.Entry(self.top, textvariable=self.size_name_var)
        self.size_name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.top, text="Ширина:").grid(row=1, column=0, padx=5, pady=5)
        self.width_var = tk.StringVar()
        self.width_entry = ttk.Entry(self.top, textvariable=self.width_var)
        self.width_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(self.top, text="Височина:").grid(row=2, column=0, padx=5, pady=5)
        self.height_var = tk.StringVar()
        self.height_entry = ttk.Entry(self.top, textvariable=self.height_var)
        self.height_entry.grid(row=2, column=1, padx=5, pady=5)

        # Create buttons for dialog actions
        self.ok_button = ttk.Button(self.top, text="OK", command=self.on_ok)
        self.ok_button.grid(row=3, column=0, padx=5, pady=5)

        self.cancel_button = ttk.Button(self.top, text="Отказ", command=self.on_cancel)
        self.cancel_button.grid(row=3, column=1, padx=5, pady=5)

        # Center the dialog on the parent window
        self.top.transient(parent)
        self.top.grab_set()
        parent.wait_window(self.top)

    def on_ok(self):
        """
        Handle the OK button click.
        """
        size_name = self.size_name_var.get().strip()
        width = self.width_var.get().strip()
        height = self.height_var.get().strip()

        if size_name and width and height:
            try:
                width = float(width)
                height = float(height)
                self.result = (size_name, (width, height))
                self.top.destroy()
            except ValueError:
                messagebox.showerror("Грешка", "Моля, въведете валидни числови стойности за ширина и височина.")
        else:
            messagebox.showerror("Грешка", "Моля, попълнете всички полета.")

    def on_cancel(self):
        """
        Handle the Cancel button click.
        """
        self.top.destroy()
