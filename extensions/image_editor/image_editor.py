ROTATE_DEFAULT = 0
ZOOM_DEFAULT = 0
FLIP_OPTIONS = ['None','X','Y','BOTH']
BLUR_DEFAULT = 0
CONTRAST_DEFAULT = 0
EFFECT_OPTIONS = ['None','Emboss','Find Edges',
                  'Contour','Edge enhance']
BRIGHTNESS_DEFAULT = 1
VIBRANCE_DEFAULT = 1
GRAYSCALE_DEFAULT = False
INVERT_DEFAULT = False

WHITE     = "#FFFFFF"
GREY      = "#B1B1B1"
BLUE      = "#004073"
DARK_GREY = "#4A4A4A"
CLOSE_RED = "#8A0606"

SLIDER_BG = "#64686B"

import customtkinter as ctk
import pywinstyles

from PIL import Image

class ImageEditor(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)

        self.geometry("700x450")
        self.resizable(False, False)
        self.title("Photo Editor")
        pywinstyles.change_header_color(self, BLUE)

        self.leftFrame = ctk.CTkFrame(self, width=50, corner_radius=0, border_width=0,
                                      bg_color="transparent", fg_color=["#F5F5F5","#1E1E1E"])
        self.leftFrame.pack(side="left", fill="y", anchor="w")

        # BUTTONS INSIDE THE LEFT FRAME
        self.rotateBtn  = ctk.CTkButton(self.leftFrame, width=46, height=46, text="").pack(padx=2,pady=(4,0))
        self.zoomInBtn  = ctk.CTkButton(self.leftFrame, width=46, height=46, text="").pack(padx=2,pady=2)
        self.zoomoutBtn = ctk.CTkButton(self.leftFrame, width=46, height=46, text="").pack(padx=2,pady=2)
        self.invertXBtn = ctk.CTkButton(self.leftFrame, width=46, height=46, text="").pack(padx=2,pady=2)
        self.invertYBtn = ctk.CTkButton(self.leftFrame, width=46, height=46, text="").pack(padx=2,pady=2)
        self.brightnessBar = ctk.CTkSlider(self.leftFrame, orientation='vertical').pack(padx=5,pady=5)

    def run(self):
        self.mainloop()

image_editor = ImageEditor(None)
image_editor.run()