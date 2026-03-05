import customtkinter as ctk
import subprocess
import os
import re
import platform

def open_path(path):
    """Open file/folder path based on OS"""
    path = path.strip()
    if not os.path.exists(path):
        print(f"Path not found: {path}")
        return
    
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":  # macOS
        subprocess.run(["open", path])
    else:  # Linux
        subprocess.run(["xdg-open", path])

def setup_clickable_paths(textbox):
    """
    Make file paths in a CTkTextbox ctrl+clickable.
    Call this after inserting text.
    """
    widget = textbox._textbox  # Access underlying tk.Text widget

    # Tag styling for links
    widget.tag_config("path_link",
        foreground="#4FC3F7",
        underline=True
    )
    widget.tag_config("path_hover",
        foreground="#81D4FA",
        underline=True
    )

    def highlight_paths():
        # Remove old tags
        widget.tag_remove("path_link", "1.0", "end")

        content = widget.get("1.0", "end")

        # Regex for Unix and Windows paths
        path_pattern = re.compile(
            r'(?<!\w)'
            r'('
            r'(?:[A-Za-z]:\\[\w\\.\- ]+)'   # Windows: C:\Users\...
            r'|'
            r'(?:/[\w/.\-]+)'                # Unix: /home/user/...
            r')',
            re.MULTILINE
        )

        for match in path_pattern.finditer(content):
            start_idx = f"1.0 + {match.start()} chars"
            end_idx   = f"1.0 + {match.end()} chars"
            widget.tag_add("path_link", start_idx, end_idx)

    def on_ctrl_click(event):
        # Get the index under cursor
        index = widget.index(f"@{event.x},{event.y}")
        # Check if it's inside a path_link tag
        tags = widget.tag_names(index)
        if "path_link" in tags:
            # Extract the tagged range
            ranges = widget.tag_prevrange("path_link", index + "+1c")
            if ranges:
                path = widget.get(*ranges)
                open_path(path)

    def on_mouse_move(event):
        index = widget.index(f"@{event.x},{event.y}")
        tags = widget.tag_names(index)
        if "path_link" in tags:
            widget.config(cursor="hand2")
            widget.tag_remove("path_hover", "1.0", "end")
            ranges = widget.tag_prevrange("path_link", index + "+1c")
            if ranges:
                widget.tag_add("path_hover", *ranges)
        else:
            widget.config(cursor="")
            widget.tag_remove("path_hover", "1.0", "end")

    widget.bind("<Control-Button-1>", on_ctrl_click)
    widget.bind("<Motion>", on_mouse_move)

    highlight_paths()


# ── Demo app ──────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.title("Clickable Paths Demo")
app.geometry("620x340")

textbox = ctk.CTkTextbox(app, width=580, height=280, font=("Courier New", 13))
textbox.pack(pady=20, padx=20)

sample_text = """Build finished successfully.

Output written to:  /home/user/projects/myapp/dist/output.bin
Config loaded from: /etc/myapp/config.yaml
Log file:           /var/log/myapp/run.log

On Windows you might see paths like:
  C:\\Users\\Alice\\Documents\\report.pdf
  C:\\Program Files\\MyApp\\app.exe

Ctrl+Click any highlighted path to open it.
"""

textbox.insert("end", sample_text)
setup_clickable_paths(textbox)   # Call AFTER inserting text

app.mainloop()