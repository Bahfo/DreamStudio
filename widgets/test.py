import customtkinter as ctk

root = ctk.CTk()
root.geometry("800x500")

# Example widget to attach the Toplevel to
button = ctk.CTkButton(root, text="Open Toplevel", width=150, height=30)
button.place(x=200, y=150)


def open_follow_toplevel():
    # Toplevel size
    top_width = 300
    top_height = 150

    # Create Toplevel
    top = ctk.CTkToplevel(root)
    top.title("Follow Widget Example")
    top.configure(fg_color="#1C1C1C")
    top.geometry(f"{top_width}x{top_height}")  # width & height
    top.attributes("-topmost", True)

    # Position relative to the widget
    def update_position():
        widget_x = button.winfo_rootx()
        widget_y = button.winfo_rooty()
        widget_height = button.winfo_height()

        # Place Toplevel just below the widget
        x = widget_x
        y = widget_y + widget_height + 5  # 5 pixels gap

        top.geometry(f"{top_width}x{top_height}+{x}+{y}")

        # Continue updating every 50ms
        top.after(50, update_position)

    update_position()


button.configure(command=open_follow_toplevel)

root.mainloop()
