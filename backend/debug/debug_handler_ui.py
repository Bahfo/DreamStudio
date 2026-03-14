import tkinter as tk
from editor.texteditor import Editor

class ShowErrorLogMessage(tk.Frame):
    def __init__(self, error_message, error_line, editor:Editor, is_error:bool, **kwargs):
        super().__init__(editor, bg="#880000", **kwargs)
        self.error_message = error_message
        self.error_line = error_line
        self.editor = editor
        self.is_error = is_error

        self.text_area = tk.Text(
            self,
            font=("Consolas", 11),
            bg="#880000",
            fg="#FFFFFF",
            border=0,
            state=tk.DISABLED,
            height=self.error_message.count("\n") + 2,
            wrap="word"
        )
        self.text_area.pack(padx=2, pady=2, fill="x")

    def _fill_error_message(self):
        self.text_area.configure(state=tk.NORMAL)
        self.text_area.insert("1.0", f"Runtime Failure Occurred in Line {self.error_line}\n")
        self.text_area.insert("end", self.error_message)
        self.text_area.see("end")
        self.text_area.configure(state=tk.DISABLED)

    def _label_with_red(self):
        self.editor.show_error_in_current_line(self.error_line)

    def _remove_labeling(self):
        self.editor.end_debugging()

    def _place_error(self):
        self.grid(sticky="ew")

    def _remove(self):
        self.grid_forget()

    def show_error(self):
        self._fill_error_message()
        self._label_with_red()
        self._place_error()

    def remove_error(self):
        self._remove()