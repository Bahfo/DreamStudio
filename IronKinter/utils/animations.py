import customtkinter as ctk

class ScreenShakeAnimation:
    def __init__(
        self,
        widget,
        orig_x=None,
        orig_y=None,
        intensity_x=5,
        intensity_y=2,
        duration=50,
        cycles=6,
        anchor=None,
    ):
        self.widget = widget
        self.intensity_x = intensity_x
        self.intensity_y = intensity_y
        self.duration = duration
        self.cycles = cycles
        self.anchor = anchor

        widget.update_idletasks()
        self.orig_x = orig_x if orig_x is not None else widget.winfo_x()
        self.orig_y = orig_y if orig_y is not None else widget.winfo_y()

        self._animate(0)

    def _animate(self, count):
        if count < self.cycles:
            offset_x = self.intensity_x if count % 2 == 0 else -self.intensity_x
            offset_y = self.intensity_y if count % 2 == 0 else -self.intensity_y

            self.widget.place(
                x=int(self.orig_x + offset_x),
                y=int(self.orig_y + offset_y),
                anchor=self.anchor,
            )

            self.widget.after(self.duration, lambda: self._animate(count + 1))
        else:
            self.widget.place(
                x=int(self.orig_x), y=int(self.orig_y), anchor=self.anchor
            )

class SlidingAnimation:
    def __init__(
        self,
        master: ctk.CTkFrame,
        x_target: int,
        y_target: int,
        animation_time: int,
        animation_step: int,
        slide_x: bool = True,
        slide_y: bool = False):

        if slide_x == slide_y:
            raise ValueError("Animation can specify either X or Y, not both")

        self.master = master
        self.x_target = x_target
        self.y_target = y_target
        self.animation_time = animation_time
        self.animation_step = animation_step
        self.slide_x = slide_x
        self.slide_y = slide_y

    def animate_in(self):
        if self.slide_x:
            self._animate_x_in()
        else:
            self._animate_y_in()

    def animate_out(self):
        if self.slide_x:
            self._animate_x_out()
        else:
            self._animate_y_out()

    def _animate_x_in(self):
        start_x = self.master.winfo_width()
        self.master.place(x=start_x, y=self.y_target)

        x = start_x

        def step():
            nonlocal x
            x -= self.animation_step
            if x <= self.x_target:
                self.master.place(x=self.x_target, y=self.y_target)
                return

            self.master.place(x=x, y=self.y_target)
            self.master.after(self.animation_time, step)

        step()

    def _animate_x_out(self):
        x = self.master.winfo_x()
        end_x = self.master.winfo_width()

        def step():
            nonlocal x
            x += self.animation_step
            if x >= end_x:
                self.master.place(x=end_x, y=self.y_target)
                return

            self.master.place(x=x, y=self.y_target)
            self.master.after(self.animation_time, step)

        step()

    def _animate_y_in(self):
        start_y = self.master.winfo_height()
        self.master.place(x=self.x_target, y=start_y)

        y = start_y

        def step():
            nonlocal y
            y -= self.animation_step
            if y <= self.y_target:
                self.master.place(x=self.x_target, y=self.y_target)
                return

            self.master.place(x=self.x_target, y=y)
            self.master.after(self.animation_time, step)

        step()

    def _animate_y_out(self):
        y = self.master.winfo_y()
        end_y = self.master.winfo_height()

        def step():
            nonlocal y
            y += self.animation_step
            if y >= end_y:
                self.master.place(x=self.x_target, y=end_y)
                return

            self.master.place(x=self.x_target, y=y)
            self.master.after(self.animation_time, step)

        step()
