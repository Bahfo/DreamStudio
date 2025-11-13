import customtkinter as ctk
from PIL import Image
import jedi
import re

ctk.set_default_color_theme(r'themes\midnight.json')

class PythonIntellisense:
    def __init__(self, widget, text_box, path=None):
        self.widget = widget
        self.text_box = text_box
        self.path = path
        self.suggestions_frame = None
        self.buttons = []
        self.selected_index = 0

    def on_key_release(self, event):
        # Clear previous suggestions
        if self.suggestions_frame:
            self.suggestions_frame.destroy()
            self.buttons = []
            self.selected_index = 0

        # Get full text and cursor info
        cursor_index = self.text_box.index("insert")
        line, column = map(int, cursor_index.split('.'))
        text = self.text_box.get("1.0", "end-1c")
        before_cursor = self.text_box.get("1.0", "insert")

        cursor_x, cursor_y, cursor_width, cursor_height = self.text_box.bbox("insert")
        self.abs_x = cursor_x
        self.abs_y = cursor_y + cursor_height

        # Do not suggest if previous char is space or text is empty
        if re.search(r"\s$", before_cursor) or not text.strip():
            return

        try:
            script = jedi.Script(code=text, path=self.path)
            self.completions = script.complete(line=line, column=column, fuzzy=True)
        except Exception:
            return

        if not self.completions:
            return

        # Get the current word being typed
        match = re.search(r"[\w_]+$", before_cursor)
        prefix = match.group(0) if match else ""

        # Sort completions by how well they match the prefix
        def sort_key(comp):
            name = comp.name
            if name.startswith(prefix):
                # Prioritize completions that start with the prefix
                return (0, len(name))
            elif prefix in name:
                # Then completions that contain the prefix
                return (1, len(name))
            else:
                # Then others alphabetically
                return (2, name.lower())

        self.completions = sorted(self.completions, key=sort_key)[:7]

        self.type_keys = {
            "function":ctk.CTkImage(light_image=Image.open(r"icons\instances and methods\function.ico"), size=(12, 12)),
            "class":ctk.CTkImage(light_image=Image.open(r"icons\instances and methods\class.ico"), size=(12, 12)),
            "method":ctk.CTkImage(light_image=Image.open(r"icons\instances and methods\method.ico"), size=(12, 12)),
            "module":ctk.CTkImage(light_image=Image.open(r"icons\instances and methods\module.ico"), size=(12, 12)),
            "instance":ctk.CTkImage(light_image=Image.open(r"icons\instances and methods\instance.ico"), size=(12, 12)),
            "param":ctk.CTkImage(light_image=Image.open(r"icons\instances and methods\param.ico"), size=(12, 12)),
            "statement":ctk.CTkImage(light_image=Image.open(r"icons\instances and methods\statement.ico"), size=(12, 12)),
            "keyword":ctk.CTkImage(light_image=Image.open(r"icons\instances and methods\keyword.ico"), size=(12, 12)),
            "path":ctk.CTkImage(light_image=Image.open(r"icons\instances and methods\path.ico"), size=(12, 12))
        }

        # Show the suggestions frame
        self.show_suggestions()

    def show_suggestions(self):
        """Creates a small suggestion box below the text box."""
        if not self.completions:
            return

        else:
            self.suggestions_frame = ctk.CTkFrame(self.text_box, corner_radius=5,fg_color='transparent',
                                                bg_color='transparent')
            self.suggestions_frame.place(x=self.abs_x, y=self.abs_y)

            for comp in self.completions:
                c_type = comp.type
                icon = self.type_keys.get(c_type, self.type_keys.get("class"))
                btn = ctk.CTkButton(
                    self.suggestions_frame,
                    text=comp.name,
                    font=("Consolas",14),
                    corner_radius=4,
                    command=lambda c=comp: self.insert_completion(c.name),
                    image=icon,
                    anchor="w"
                )
                btn.pack(fill="x", pady=1)
                self.buttons.append(btn)

    def insert_completion(self, text):
        """Inserts selected completion into the text box."""
        self.text_box.insert("insert", text[len(self._current_prefix()):])
        if self.suggestions_frame:
            self.suggestions_frame.destroy()
            self.suggestions_frame = None

    def _current_prefix(self):
        """Get the current word before cursor (used to remove duplicate insertions)."""
        before = self.text_box.get("1.0", "insert")
        match = re.search(r"[\w_]+$", before)
        return match.group(0) if match else ""