"""
Visualization system for the sheet cutting app.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, Canvas, Frame, Scrollbar
from typing import List
from models.part import Sheet

class CuttingPlanVisualizer:
    def __init__(self, root, sheets: List[Sheet]):
        self.root = root
        self.sheets = sheets
        self.current_hover_part = None
        self.zoom_level = 1.0
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.panning = False
        self.create_window()

    def create_window(self):
        self.vis_window = tk.Toplevel(self.root)
        self.vis_window.title("Визуализация на Плана на Разрязване")
        self.vis_window.geometry("1300x900")
        main_frame = ttk.Frame(self.vis_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        notebook = ttk.Notebook(main_frame)
        notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_frame = ttk.LabelFrame(main_frame, text="Детайли за Частта", width=300)
        info_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.part_info_text = scrolledtext.ScrolledText(
            info_frame, wrap=tk.WORD, height=10, width=35)
        self.part_info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.part_info_text.config(state=tk.DISABLED)
        ttk.Label(info_frame, text="Информация за Листа:").pack(anchor=tk.W, padx=5, pady=(10, 5))
        self.sheet_info_text = scrolledtext.ScrolledText(
            info_frame, wrap=tk.WORD, height=8, width=35)
        self.sheet_info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.sheet_info_text.config(state=tk.DISABLED)
        for i, sheet in enumerate(self.sheets, 1):
            tab = ttk.Frame(notebook)
            utilization = sheet.utilization * 100
            waste_percent = sheet.efficiency['waste_percent'] * 100
            notebook.add(tab, text=f"Лист {i} - {utilization:.1f}% използване")
            canvas_container = Frame(tab)
            canvas_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            hscroll = Scrollbar(canvas_container, orient=tk.HORIZONTAL)
            vscroll = Scrollbar(canvas_container, orient=tk.VERTICAL)
            canvas = Canvas(
                canvas_container,
                bg="white",
                xscrollcommand=hscroll.set,
                yscrollcommand=vscroll.set
            )
            hscroll.config(command=canvas.xview)
            vscroll.config(command=canvas.yview)
            canvas.grid(row=0, column=0, sticky="nsew")
            vscroll.grid(row=0, column=1, sticky="ns")
            hscroll.grid(row=1, column=0, sticky="ew")
            canvas_container.grid_rowconfigure(0, weight=1)
            canvas_container.grid_columnconfigure(0, weight=1)
            tab.sheet = sheet
            tab.canvas = canvas
            self.generate_sheet_vector(canvas, sheet)
            zoom_frame = Frame(tab)
            zoom_frame.pack(fill=tk.X, padx=10, pady=5)
            ttk.Button(zoom_frame, text="Увеличи (1.2x)", 
                      command=lambda t=tab: self.zoom(t, 1.2)).pack(side=tk.LEFT, padx=5)
            ttk.Button(zoom_frame, text="Намали (0.8x)", 
                      command=lambda t=tab: self.zoom(t, 0.8)).pack(side=tk.LEFT, padx=5)
            ttk.Button(zoom_frame, text="Нулирай Изглед", 
                      command=lambda t=tab: self.reset_view(t)).pack(side=tk.LEFT, padx=5)
            status_bar = ttk.Label(tab, text="", relief=tk.SUNKEN, anchor=tk.W)
            status_bar.pack(side=tk.BOTTOM, fill=tk.X)
            overlap_status = self.validate_placements(sheet.placements)
            eff = sheet.efficiency
            status_text = (f"{overlap_status} | "
                           f"Алгоритъм: {sheet.algorithm} | "
                           f"Използване: {utilization:.1f}% | "
                           f"Отпадък: {waste_percent:.1f}% | "
                           f"Плътност: {eff['density']:.1f} части/m²")
            status_bar.config(text=status_text)
            tab.status_bar = status_bar
            tab.info_frame = self.part_info_text
            tab.sheet_info = self.sheet_info_text
            canvas.bind("<Motion>", lambda event, t=tab: self.on_canvas_motion(event, t))
            canvas.bind("<ButtonPress-1>", lambda event, c=canvas: self.start_pan(event, c))
            canvas.bind("<B1-Motion>", lambda event, c=canvas: self.pan(event, c))
            canvas.bind("<ButtonRelease-1>", lambda event: self.end_pan(event))
            canvas.bind("<Leave>", lambda event, t=tab: self.on_canvas_leave(t))

    def generate_sheet_vector(self, canvas, sheet, zoom_level=1.0):
        canvas.delete("all")
        sheet_w, sheet_h = sheet.size
        placements = sheet.placements
        base_scale = 0.25 * zoom_level
        canvas_scale = base_scale
        canvas.config(scrollregion=(0, 0, sheet_w * canvas_scale, sheet_h * canvas_scale))
        canvas.create_rectangle(
            0, 0, 
            sheet_w * canvas_scale, 
            sheet_h * canvas_scale, 
            outline="black", width=2
        )
        utilization = sheet.utilization * 100
        waste_percent = sheet.efficiency['waste_percent'] * 100
        density = sheet.efficiency['density']
        info_text = (f"Лист: {sheet_w}x{sheet_h} мм | "
                     f"Използване: {utilization:.1f}% | "
                     f"Отпадък: {waste_percent:.1f}%")
        canvas.create_text(
            sheet_w * canvas_scale / 2, 
            10 * canvas_scale, 
            text=info_text, 
            fill="black", 
            anchor="n", 
            font=("Arial", 10)
        )
        eff_ratio = utilization / 100
        eff_color = "#{:02x}{:02x}00".format(
            int(255 * (1 - eff_ratio)), 
            int(255 * eff_ratio)
        )
        canvas.create_rectangle(
            sheet_w * canvas_scale - 150 * canvas_scale, 
            5 * canvas_scale,
            sheet_w * canvas_scale - 5 * canvas_scale,
           25 * canvas_scale,
            outline="black",
            fill=eff_color
        )
        self.draw_waste_areas(canvas, sheet, canvas_scale)
        for placement in placements:
            x = placement.x * canvas_scale
            y = placement.y * canvas_scale
            w = placement.width * canvas_scale
            h = placement.height * canvas_scale
            sp = placement.spacing
            sp_x = sp.get('x', placement.x - 5) * canvas_scale
            sp_y = sp.get('y', placement.y - 5) * canvas_scale
            sp_w = sp.get('width', placement.width + 10) * canvas_scale
            sp_h = sp.get('height', placement.height + 10) * canvas_scale
            color = '#3498db' if not placement.rotated else '#e74c3c'
            canvas.create_rectangle(
                sp_x, sp_y, sp_x + sp_w, sp_y + sp_h,
                outline='#888', dash=(4, 2), width=1
            )
            part_rect = canvas.create_rectangle(
                x, y, x + w, y + h,
                outline="black", width=1, fill=color,
                tags=("part",)
            )
            canvas.create_text(
                x + w/2, y + h/2,
                text=placement.ref, fill="black", 
                font=("Arial", 8)
            )
        legend_text = "Синьо: Нормално | Червено: Завъртяно | Пунктирана линия: 5мм разстояние"
        canvas.create_text(
            sheet_w * canvas_scale / 2, 
            sheet_h * canvas_scale - 10 * canvas_scale,
            text=legend_text, 
            fill="black", 
            anchor="s", 
            font=("Arial", 9)
        )
        canvas.zoom_level = zoom_level

    def draw_waste_areas(self, canvas, sheet, canvas_scale):
        sheet_w, sheet_h = sheet.size
        placements = sheet.placements
        grid_size = 50
        grid = []
        for x in range(0, sheet_w, grid_size):
            for y in range(0, sheet_h, grid_size):
                grid.append({'x': x, 'y': y, 'covered': False})
        for placement in placements:
            px = placement.x
            py = placement.y
            pw = placement.width
            ph = placement.height
            for cell in grid:
                cx, cy = cell['x'], cell['y']
                if px <= cx < px + pw and py <= cy < py + ph:
                    cell['covered'] = True
        for cell in grid:
            if not cell['covered']:
                x1 = cell['x'] * canvas_scale
                y1 = cell['y'] * canvas_scale
                x2 = (cell['x'] + grid_size) * canvas_scale
                y2 = (cell['y'] + grid_size) * canvas_scale
                canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill='#ff0000', stipple="gray12", outline=""
                )

    def on_canvas_motion(self, event, tab):
        canvas = tab.canvas
        x, y = canvas.canvasx(event.x), canvas.canvasy(event.y)
        scale = getattr(canvas, "zoom_level", 1.0) * 0.25
        found_part = None
        for placement in tab.sheet.placements:
            px = placement.x * scale
            py = placement.y * scale
            pw = placement.width * scale
            ph = placement.height * scale
            if px <= x <= px + pw and py <= y <= py + ph:
                found_part = placement
                break
        if found_part:
            self.current_hover_part = found_part
            self.update_part_info(tab, found_part)
        else:
            self.current_hover_part = None
            self.update_sheet_info(tab)

    def on_canvas_leave(self, tab):
        self.current_hover_part = None
        self.update_sheet_info(tab)

    def update_part_info(self, tab, part):
        self.part_info_text.config(state=tk.NORMAL)
        self.part_info_text.delete(1.0, tk.END)
        self.part_info_text.insert(tk.END, 
            f"Означение: {part.ref}\n"
            f"Размери: {part.width} x {part.height} мм\n"
            f"Ориентация: {'Завъртяна' if part.rotated else 'Нормална'}\n"
            f"Позиция: ({part.x:.1f}, {part.y:.1f}) мм\n"
            f"Площ: {part.width * part.height / 10000:.2f} cm²\n")
        self.part_info_text.config(state=tk.DISABLED)
        self.update_sheet_info(tab)

    def update_sheet_info(self, tab):
        sheet = tab.sheet
        w, h = sheet.size
        eff = sheet.efficiency
        self.sheet_info_text.config(state=tk.NORMAL)
        self.sheet_info_text.delete(1.0, tk.END)
        self.sheet_info_text.insert(tk.END, 
            f"Размер на листа: {w} x {h} мм\n"
            f"Обща площ: {w * h / 1000000:.2f} m²\n"
            f"Използвана площ: {eff['used_area'] / 10000:.2f} cm²\n"
            f"Отпадък: {eff['waste_area'] / 10000:.2f} cm²\n"
            f"Ефективност: {eff['efficiency']:.1f}%\n"
            f"Брой части: {len(sheet.placements)}\n"
            f"Алгоритъм: {sheet.algorithm}\n"
            f"Метод на сортиране: {sheet.sort_method}")
        self.sheet_info_text.config(state=tk.DISABLED)

    def zoom(self, tab, factor):
        canvas = tab.canvas
        sheet = tab.sheet
        current_zoom = getattr(canvas, "zoom_level", 1.0)
        new_zoom = current_zoom * factor
        if new_zoom < 0.1:
            new_zoom = 0.1
        elif new_zoom > 5.0:
            new_zoom = 5.0
        self.generate_sheet_vector(canvas, sheet, new_zoom)

    def reset_view(self, tab):
        canvas = tab.canvas
        sheet = tab.sheet
        self.generate_sheet_vector(canvas, sheet, 1.0)

    def start_pan(self, event, canvas):
        canvas.scan_mark(event.x, event.y)
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.panning = True

    def pan(self, event, canvas):
        if self.panning:
            canvas.scan_dragto(event.x, event.y, gain=1)

    def end_pan(self, event):
        self.panning = False

    def validate_placements(self, placements):
        rectangles = []
        for placement in placements:
            sp = placement.spacing
            x = sp.get('x', placement.x - 5)
            y = sp.get('y', placement.y - 5)
            w = sp.get('width', placement.width + 10)
            h = sp.get('height', placement.height + 10)
            rectangles.append({
                'x1': x,
                'y1': y,
                'x2': x + w,
                'y2': y + h,
                'ref': placement.ref
            })
        overlaps = []
        for i in range(len(rectangles)):
            for j in range(i+1, len(rectangles)):
                if self.rect_overlap(rectangles[i], rectangles[j]):
                    overlaps.append((rectangles[i]['ref'], rectangles[j]['ref']))
        if overlaps:
            overlap_msg = "ПРЕДУПРЕЖДЕНИЕ: Открито застъпване! "
            for pair in set(overlaps):
                overlap_msg += f"{pair[0]} <-> {pair[1]}; "
            return overlap_msg
        else:
            return "Всички части са поставени с правилни разстояния - няма застъпвания"

    def rect_overlap(self, r1, r2):
        return not (r1['x2'] < r2['x1'] or 
                   r1['x1'] > r2['x2'] or 
                   r1['y2'] < r2['y1'] or 
                   r1['y1'] > r2['y2'])
