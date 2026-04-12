import customtkinter as ctk
from PIL import Image, ImageTk, ImageSequence

root = ctk.CTk()
root.geometry("300x300")

# Load GIF
gif_image = Image.open(r"C:\Users\Bahaa\Desktop\ExoSystem\softdreamIDE\icons\animated_widgets\Circle Loader.gif")
frames = [ImageTk.PhotoImage(frame.copy().convert("RGBA")) for frame in ImageSequence.Iterator(gif_image)]

label = ctk.CTkLabel(root)
label.pack(pady=20)

# Animate GIF
def animate(counter=0):
    frame = frames[counter % len(frames)]
    label.configure(image=frame)
    root.after(100, lambda: animate(counter + 1))

animate()
root.mainloop()