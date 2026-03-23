import tkinter as tk

# Functions for drag operations
def on_drag_start(event):
    widget = event.widget
    widget.start_x = event.x
    widget.start_y = event.y

def on_drag_motion(event):
    widget = event.widget
    x = widget.winfo_x() - widget.start_x + event.x
    y = widget.winfo_y() - widget.start_y + event.y
    widget.place(x=x, y=y)

root = tk.Tk()
frame = tk.Frame(root, width=100, height=100, bg="blue")
frame.place(x=10, y=10)

# Bind events to frame
frame.bind("<Button-1>", on_drag_start)
frame.bind("<B1-Motion>", on_drag_motion)
root.mainloop()
