import tkinter as tk
from tkinter import INSERT, NE, Canvas, Menubutton
from tkinter.font import Font
import platform


class LineNumbers(Canvas):
    def __init__(self, master, text=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.config(width=50, bd=0, highlightthickness=0)
        self.text = text
        self.text.config(bd=0, highlightthickness=0)
        self.text.tag_config("sel", background="#48484f", foreground="#e1e1e6")
        self.text.bind("<Configure>", self.redraw)
        self.text.bind("<<Change>>", self.redraw)

        if platform.system() == "Linux":
            self.text.bind("<Button-4>", self.redraw)
            self.text.bind("<Button-5>", self.redraw)
        elif platform.system() == "Windows" or platform.system() == "Darwin":
            self.text.bind("<MouseWheel>", self.redraw)
        else:
            pass

    def attach(self, text):
        self.text = text

    def set_bar_width(self, width):
        self.configure(width=width)

    def get_indentation_level(self, line):
        """Get the indentation level of a given line."""
        return len(line) - len(line.lstrip())

    def redraw(self, *_):
        self.delete(tk.ALL)

        prev_indent = 0
        i = self.text.index("@0,0")

        curline = self.text.dlineinfo(tk.INSERT)
        cur_y = curline[1] if curline else None

        while True:
            dline = self.text.dlineinfo(i)
            if dline is None:
                break

            y = dline[1]
            linenum = str(i).split(".")[0]

            line_content = self.text.get(f"{linenum}.0", f"{linenum}.end")
            current_indent = self.get_indentation_level(line_content)

            if current_indent > prev_indent:
                line_num_with_indent = f"+ {linenum}"
            elif current_indent < prev_indent:
                line_num_with_indent = f"- {linenum}"
            else:
                line_num_with_indent = linenum

            color = "#83838f" if (cur_y is not None and y == cur_y) else "#525259"

            self.create_text(
                40,
                y,
                anchor=tk.NE,
                text=line_num_with_indent,
                font=("Consolas", 14),
                fill=color,
            )

            prev_indent = current_indent
            i = self.text.index(f"{i}+1line")


class Text(tk.Text):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.mark_set("input", "insert")
        self.mark_gravity("input", "left")

        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, *args):
        if (
            args[0] == "get"
            and (args[1] == tk.SEL_FIRST and args[2] == tk.SEL_LAST)
            and not self.tag_ranges(tk.SEL)
        ):
            return
        if (
            args[0] == "delete"
            and (args[1] == tk.SEL_FIRST and args[2] == tk.SEL_LAST)
            and not self.tag_ranges(tk.SEL)
        ):
            return

        cmd = (self._orig,) + args
        result = self.tk.call(cmd)

        if (
            args[0] in ("insert", "replace", "delete")
            or args[0:3] == ("mark", "set", "insert")
            or args[0:2] == ("xview", "moveto")
            or args[0:2] == ("yview", "moveto")
            or args[0:2] == ("xview", "scroll")
            or args[0:2] == ("yview", "scroll")
        ):
            self.event_generate("<<Change>>", when="tail")

        return result
