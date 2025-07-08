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
        """
        Set up the main window and canvas for visualization.
        """
        self.root.title("Cutting Plan Visualizer")
        self.canvas = Canvas(self.root, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind mouse events for interaction
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        self.canvas.bind("<Leave>", self.on_canvas_leave)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.pan)
        self.canvas.bind("<ButtonRelease-1>", self.end_pan)

        # Add a scrollbar
        self.scrollbar = Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Initialize the drawing
        self.draw()

    def draw(self):
        """
        Generate the visual representation of the sheets and parts.
        """
        self.canvas.delete("all")  # Clear the canvas
        for sheet in self.sheets:
            self.generate_sheet_vector(sheet)

    def generate_sheet_vector(self, sheet: Sheet):
        """
        Create the vector representation of a sheet and its parts.
        """
        sheet_id = f"sheet_{sheet.id}"
        # Draw the sheet outline
        self.canvas.create_rectangle(
            sheet.x, sheet.y, sheet.x + sheet.width, sheet.y + sheet.height,
            outline="black", fill="lightblue", tags=sheet_id
        )
        # Draw each part in the sheet
        for part in sheet.parts:
            self.draw_part(part, sheet_id)

        # Draw waste areas
        self.draw_waste_areas(sheet)

        # Bind click event to sheets for selection
        self.canvas.tag_bind(sheet_id, "<Button-1>", lambda event, s=sheet: self.on_sheet_click(event, s))

    def draw_part(self, part, parent_id):
        """
        Draw a part rectangle on the canvas.
        """
        x, y, width, height = part.x, part.y, part.width, part.height
        part_id = f"part_{part.id}"
        # Draw the part rectangle
        self.canvas.create_rectangle(
            x, y, x + width, y + height,
            outline="black", fill="green", tags=(parent_id, part_id)
        )
        # Bind hover events for the part
        self.canvas.tag_bind(part_id, "<Enter>", lambda event, p=part: self.on_part_hover(event, p))
        self.canvas.tag_bind(part_id, "<Leave>", self.on_part_hover_leave)

    def draw_waste_areas(self, sheet: Sheet):
        """
        Highlight the waste areas on the sheet.
        """
        for waste_area in sheet.waste_areas:
            x, y, width, height = waste_area.x, waste_area.y, waste_area.width, waste_area.height
            # Draw the waste area rectangle
            self.canvas.create_rectangle(
                x, y, x + width, y + height,
                outline="red", fill="red", stipple="gray50", tags=f"waste_{sheet.id}"
            )

    def on_canvas_motion(self, event):
        """
        Handle mouse motion over the canvas.
        """
        x, y = event.x, event.y
        # Update the status bar or any other UI element with the current coordinates
        self.root.title(f"Cutting Plan Visualizer - X: {x}, Y: {y}")

    def on_canvas_leave(self, event):
        """
        Handle mouse leaving the canvas area.
        """
        # Reset the status bar or any other UI element
        self.root.title("Cutting Plan Visualizer")

    def zoom(self, event):
        """
        Zoom in or out of the canvas.
        """
        scale_factor = 1.1
        if event.delta > 0:
            self.zoom_level *= scale_factor
        else:
            self.zoom_level /= scale_factor
        self.canvas.scale("all", event.x, event.y, self.zoom_level, self.zoom_level)

    def reset_view(self):
        """
        Reset the view to the default state.
        """
        self.zoom_level = 1.0
        self.canvas.scale("all", 0, 0, 1, 1)
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def start_pan(self, event):
        """
        Begin panning the view.
        """
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.panning = True

    def pan(self, event):
        """
        Perform the panning motion.
        """
        if self.panning:
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            self.canvas.xview_scroll(-dx, "units")
            self.canvas.yview_scroll(-dy, "units")
            self.pan_start_x = event.x
            self.pan_start_y = event.y

    def end_pan(self, event):
        """
        End the panning motion.
        """
        self.panning = False

    def on_sheet_click(self, event, sheet: Sheet):
        """
        Handle sheet click events for selection.
        """
        # Deselect all sheets and parts
        self.canvas.itemconfig("sheet", outline="black", fill="lightblue")
        self.canvas.itemconfig("part", outline="black", fill="green")
        # Select the clicked sheet
        self.canvas.itemconfig(f"sheet_{sheet.id}", outline="red", fill="lightgreen")
        # Update sheet information display
        self.update_sheet_info(sheet)

    def on_part_hover(self, event, part):
        """
        Handle part hover events to highlight the part.
        """
        self.current_hover_part = part
        self.canvas.itemconfig(f"part_{part.id}", outline="yellow", width=2)

    def on_part_hover_leave(self, event):
        """
        Handle mouse leave events for parts.
        """
        if self.current_hover_part:
            self.canvas.itemconfig(f"part_{self.current_hover_part.id}", outline="black", width=1)
            self.current_hover_part = None

    def update_part_info(self, part):
        """
        Update the part information display.
        """
        # This method would update some UI elements with the part's data
        print(f"Part ID: {part.id}, Name: {part.name}, Quantity: {part.quantity}")

    def update_sheet_info(self, sheet):
        """
        Update the sheet information display.
        """
        # This method would update some UI elements with the sheet's data
        print(f"Sheet ID: {sheet.id}, Width: {sheet.width}, Height: {sheet.height}")

    def validate_placements(self):
        """
        Validate the placements of parts on the sheets.
        """
        for sheet in self.sheets:
            for part in sheet.parts:
                if not self.rect_overlap(part, sheet):
                    print(f"Warning: Part {part.id} is out of the sheet {sheet.id} bounds!")

    def rect_overlap(self, rect1, rect2):
        """
        Check if two rectangles overlap.
        """
        r1_x1, r1_y1, r1_x2, r1_y2 = rect1.x, rect1.y, rect1.x + rect1.width, rect1.y + rect1.height
        r2_x1, r2_y1, r2_x2, r2_y2 = rect2.x, rect2.y, rect2.x + rect2.width, rect2.y + rect2.height
        return not (r1_x2 < r2_x1 or r1_x1 > r2_x2 or r1_y2 < r2_y1 or r1_y1 > r2_y2)

# The module can be run standalone or imported
if __name__ == "__main__":
    root = tk.Tk()
    # For standalone run, create some dummy sheets data
    dummy_sheets = []  # ...populate with dummy data...
    visualizer = CuttingPlanVisualizer(root, dummy_sheets)
    root.mainloop()
