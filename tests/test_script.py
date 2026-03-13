import customtkinter as ctk
import tkinter as tk

class Tooltip(ctk.CTkFrame):
    def __init__(self, master, text, width=150, height=40, triangle_height=10, **kwargs):
        super().__init__(master, **kwargs)
        self.width = width
        self.height = height
        self.triangle_height = triangle_height

        # Canvas for drawing the triangle
        self.canvas = tk.Canvas(self, width=width, height=triangle_height, bg=self["bg"], highlightthickness=0)
        self.canvas.pack(side="bottom", fill="x")

        # Draw the downward-pointing triangle
        mid = width // 2
        points = [mid - 10, 0, mid + 10, 0, mid, triangle_height]
        self.canvas.create_polygon(points, fill="#6B5BFF", outline="#6B5BFF")

        # Tooltip label
        self.label = ctk.CTkLabel(self, text=text, width=width, height=height, fg_color="#6B5BFF", corner_radius=8)
        self.label.pack(side="top", fill="both")

# Example usage
root = ctk.CTk()
root.geometry("300x200")

tooltip = Tooltip(root, text="Tooltip design")
tooltip.place(x=80, y=50)

root.mainloop()
