import customtkinter as ctk
import re
import jedi

class PythonIntellisense:
    def __init__(self, widget, text_box, path=None):
        self.widget = widget
        self.text_box = text_box
        self.path = path
        self.suggestions_frame = None
        self.buttons = []
        self.selected_index = 0
        self.completions = []

    def on_key_release(self, event):
        if self.suggestions_frame:
            self.suggestions_frame.destroy()
            self.buttons = []
            self.selected_index = 0

        cursor_index = self.text_box.index("insert")
        line, column = map(int, cursor_index.split('.'))
        text = self.text_box.get("1.0", "end-1c")
        before_cursor = self.text_box.get("1.0", "insert")

        if re.search(r"\s$", before_cursor) or not text.strip():
            return

        try:
            script = jedi.Script(code=text, path=self.path)
            self.completions = script.complete(line=line, column=column, fuzzy=True)
        except Exception:
            return

        if not self.completions:
            return

        match = re.search(r"[\w_]+$", before_cursor)
        prefix = match.group(0) if match else ""

        def sort_key(comp):
            name = comp.name
            if name.startswith(prefix):
                return (0, len(name))
            elif prefix in name:
                return (1, len(name))
            else:
                return (2, name.lower())

        self.completions = sorted(self.completions, key=sort_key)[:7]

        self.show_suggestions()

    def show_suggestions(self):
        if not self.completions:
            return re

        try:
            x, y, width, height = self.text_box.bbox("insert")
        except Exception:
            x, y, height = 0, 0, 20

        self.suggestions_frame = ctk.CTkFrame(self.text_box, corner_radius=0, fg_color="#1D1D1D", width=300,
                                              border_color="#5F5F5F", border_width=1)
        self.suggestions_frame.place(x=x, y=y+height)

        for comp in self.completions:
            btn = ctk.CTkButton(
                self.suggestions_frame,
                text=comp.name,
                font=("Consolas", 11),
                corner_radius=0,
                fg_color="#1D1D1D",
                hover_color="#004073",
                anchor="w",
                width=296,
                height=20,
                command=lambda c=comp: self.insert_completion(c.name))
            btn.pack(fill="x", pady=2,padx=2)
            self.buttons.append(btn)

    def insert_completion(self, text):
        prefix = self._current_prefix()
        self.text_box.insert("insert", text[len(prefix):])
        if self.suggestions_frame:
            self.suggestions_frame.destroy()
            self.suggestions_frame = None

    def _current_prefix(self):
        before = self.text_box.get("1.0", "insert")
        match = re.search(r"[\w_]+$", before)
        return match.group(0) if match else ""
    
    def onEscKey(self):
        if self.suggestions_frame:
            self.suggestions_frame.destroy()
            self.suggestions_frame = None
        return "break"
    
    def on_ctrl_space(self, event):
        self.on_key_release(event)
        return "break"

    def bindings(self):
        self.text_box.bind("<KeyRelease>", self.on_key_release)
        self.text_box.bind("<Escape>", self.onEscKey)
        self.text_box.bind("<Control-space>", self.on_ctrl_space)