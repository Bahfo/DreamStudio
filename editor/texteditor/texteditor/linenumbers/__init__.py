import tkinter as tk
from .breakpoint import Breakpoint
from ...utils import Canvas, Menubutton


class LineNumbers(Canvas):
    def __init__(self, master, text=None, font=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.font = font
        self.fg = self.base.theme.linenumbers["foreground"]
        self.hfg = self.base.theme.linenumbers["activeforeground"]
        self.config(
            width=65,
            bd=0,
            highlightthickness=0,
            bg=self.base.theme.linenumbers["background"],
        )
        self.text = text

    def attach(self, text):
        self.text = text

    def mark_line(self, line):
        dline = self.text.dlineinfo(line)
        if not dline:
            return
        y = dline[1]
        btn = Menubutton(
            self,
            text=">",
            font=self.font,
            cursor="hand2",
            borderwidth=0,
            width=2,
            height=1,
            pady=0,
            padx=0,
            relief=tk.FLAT,
            **self.base.theme.linenumbers,
        )
        self.create_window(70, y - 2, anchor=tk.NE, window=btn)

    def set_bar_width(self, width):
        self.configure(width=width)

    def get_indentation_level(self, line):
        return len(line) - len(line.lstrip())

    def redraw(self, *_):
        """Redraw line numbers for VISIBLE lines only — O(visible) not O(total)."""
        self.delete(tk.ALL)

        # Current line y-position for active-line highlight
        curline = self.text.dlineinfo(tk.INSERT)
        cur_y = curline[1] if curline else None

        prev_indent = 0

        # Start at the first visible line
        i = self.text.index("@0,0")

        while True:
            dline = self.text.dlineinfo(i)
            # dlineinfo returns None once we're past the visible area
            if dline is None:
                break

            x, y, width, height, baseline = dline
            linenum = i.split(".")[0]

            # Only fetch line content when we need indent info (cheap for
            # visible lines; the real win is not calling dlineinfo on every
            # off-screen line like before)
            line_content = self.text.get(f"{linenum}.0", f"{linenum}.end")
            current_indent = self.get_indentation_level(line_content)

            color = self.hfg if (cur_y is not None and y == cur_y) else self.fg

            self.create_text(
                40,
                y,
                anchor=tk.NE,
                text=linenum,
                font=self.font,
                fill=color,
                tag=i,
            )
            self.tag_bind(i, "<Button-1>", lambda _, idx=i: self.text.select_line(idx))

            if current_indent > prev_indent:
                fold_tag = f"f{i}"
                self.create_text(
                    50,
                    y,
                    anchor=tk.NW,
                    text="+",
                    font=self.font,
                    fill=self.fg,
                    tag=fold_tag,
                )
                self.tag_bind(
                    fold_tag, "<Button-1>", lambda _, idx=i: print(f"Fold from {idx}")
                )

            prev_indent = current_indent

            # Advance to the next line
            next_i = self.text.index(f"{i}+1line")
            # Guard: if the index didn't advance we've hit the end
            if next_i == i:
                break
            i = next_i

    def draw_breakpoint(self, y):
        bp = Breakpoint(self)
        self.create_window(21, y - 2, anchor=tk.NE, window=bp)
