import os
import time
import pygame.mixer
import tkinter as tk
from PIL import Image, ImageTk


class mainApp(tk.Toplevel):
    def __init__(
        self, mode: str, icon: str | None = None, master=None, music_path=None
    ):
        super().__init__(master)
        pygame.mixer.init()

        self.geometry("300x230")
        self.resizable(False, False)
        self.title("DreamStudio's MP3 Player")

        self.mode = mode
        self.icon = icon
        self.music_path = music_path
        colors_scheme = self.getColor()
        self.paused = False

        if icon and isinstance(icon, str):
            pil_icon = Image.open(icon).resize((128, 128))
        else:
            pil_icon = Image.open(r"Extensions\music_player\music.png").resize(
                (128, 128)
            )

        self.tk_icon = ImageTk.PhotoImage(pil_icon)
        self.iconphoto(True, self.tk_icon)

        ### Frame 1
        self.status = tk.Frame(self, border=1, height=30, background=colors_scheme[0])
        self.status.pack(side="top", expand=True, fill="both")
        self.status.pack_propagate(False)

        self.label1 = tk.Label(
            self.status,
            border=0,
            text="Now Playing: ",
            height=24,
            background=colors_scheme[0],
            justify="left",
            anchor="w",
            font=("inter", 9),
            foreground=colors_scheme[3],
        )
        self.label1.pack(side="left", padx=5, pady=3)

        self.pathLabel = tk.Label(
            self.status,
            border=0,
            text=f"{self.music_path}",
            height=24,
            background=colors_scheme[0],
            justify="left",
            anchor="w",
            font=("inter", 9),
            foreground=colors_scheme[3],
        )
        self.pathLabel.pack(side="left", padx=5, pady=3)

        self.playStopBtn = tk.Button(
            self.status,
            overrelief="flat",
            border=1,
            text="▶",
            background=colors_scheme[1],
            foreground=colors_scheme[3],
            font=("inter", 12),
            command=self.toggle_play,
        )
        self.playStopBtn.pack(side="right", padx=2, pady=2)

        if self.music_path:
            self.load_sound()

        ### Frame 2
        self.gadgets = tk.Frame(self, border=1, height=200, background=colors_scheme[1])
        self.gadgets.pack(expand=True, fill="both")
        self.gadgets.pack_propagate(False)

        self.icon_label = tk.Label(
            self.gadgets,
            border=0,
            background=colors_scheme[1],
            image=self.tk_icon,
            text="",
            justify="center",
            anchor="center",
        )
        self.icon_label.pack(expand=True, fill="both", padx=10, pady=10)

        time.sleep(2)
        self.load_sound()

    def getColor(self):
        if self.mode == "dark":
            return ["#1E1E1E", "#2D2D2D", "#202020", "#FFFFFF"]
        else:
            return ["#F1F1F1", "#FFFFFF", "#F5F5F5", "#1E1E1E"]

    def load_sound(self):
        pygame.mixer.music.load(self.music_path)
        name = os.path.splitext(os.path.basename(self.music_path))
        self.pathLabel.configure(text=name)

    def toggle_play(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.paused = True
            self.playStopBtn.configure(text="▶")
        elif self.paused:
            pygame.mixer.music.unpause()
            self.paused = False
            self.playStopBtn.configure(text="■")
        else:
            pygame.mixer.music.play()
            self.paused = False
            self.playStopBtn.configure(text="■")

    def show(self):
        self.mainloop()


app = tk.Tk()

main = mainApp("dark", None, master=app, music_path=r"C:\Users\Bahaa\Music\2.ogg")
main.show()
