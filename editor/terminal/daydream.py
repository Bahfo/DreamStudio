"""
(C) COPYRIGHT 2026 - EXcellent TechStacks : All Rights Reserved

A Tkinter CLI Tool that comes with DreamStudio IDE: The main purpose of the
tool is to interact directly with the build_utils (Build Utilities) that are
responsible for building the project.

DayDream Builder is also available as an embedded tool inside DreamStudio IDE
itself, but it can also come as a standalone system that helps developers write
building commands and scripts faster with autocompletion, syntax highlighting,
and a very responsive system.

Developed and Maintained by DreamStudio Team - EXcellent TechStacks. 2026
"""

# Written by Bahaa Nofal - 5/2026

import tkinter as tk

from editor import *
import psutil

help_tool = """
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved

DayDream Terminal
Building Manager for DreamStudio Projects. It uses .dst files written and 
compiles them to produce building outputs for the studio.

Topmost commands:

showcommands        shows all commands and parameters
clear               clears terminal
exit                exits terminal

For full help, please read provided documentation
EX Technologies
"""

all_commands = """
AVAILABLE COMMANDS:
copyfile          file_name   source_path   destination_path
movefile          file_name   source_path   destination_path
compile           file_name   file_path     language
addfile           file_name   file_path
deletefile        file_name   file_path
makeworkspace     make_name   make_path
deleteworkspace   make_name   make_path
list              make_name   make_path
isactive          file_name
typemessage       message
help
showcommands
clear
exit
"""

error_0 = (
    "bad command, perhaps you could check 'ShowCommands' for completed commands list."
)
error_1 = """\nBad Command Structure. Please Check:
1. Correct path
2. Extension included
3. Language specified correctly
"""


def main_terminal():
    def center_window(window):
        window.update_idletasks()
        w = window.winfo_width()
        h = window.winfo_height()
        x = (window.winfo_screenwidth() - w) // 2
        y = (window.winfo_screenheight() - h) // 2
        window.geometry(f"{w}x{h}+{x}+{y}")

    window = tk.Tk()
    window.title("DayDream Terminal")
    window.geometry("900x550")
    center_window(window)

    terminal_textbox = tk.Text(
        window,
        bg="#2e2e2e",
        fg="#ffffff",
        insertbackground="#ffffff",
        wrap="word",
        font=("JetBrains Mono", 11),
        relief="flat",
        bd=0,
    )

    terminal_textbox.pack(fill="both", expand=True)

    terminal_textbox.insert("1.0", "Daydream Console\nCOPYRIGHT 2026 EX Technologies\n")

    terminal_textbox.configure(state="normal")

    editable_index = "end-1c"

    def insert_prompt():
        nonlocal editable_index
        terminal_textbox.insert(tk.END, "\n>>> ")
        editable_index = terminal_textbox.index("end-1c")
        terminal_textbox.mark_set("insert", tk.END)

    def command_execution(user_input):
        parts = user_input.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()

        try:
            if len(parts) == 4:
                name, path, arg = parts[1], parts[2], parts[3]
                full_path = os.path.join(path, name)

                if cmd == "copyfile":
                    if not os.path.exists(full_path):
                        terminal_textbox.insert(tk.END, f"\nNot found {error_1}")
                    else:
                        shutil.copyfile(full_path, os.path.join(arg, name))
                        terminal_textbox.insert(tk.END, "\nCopied")

                elif cmd == "movefile":
                    if not os.path.exists(full_path):
                        terminal_textbox.insert(tk.END, f"\nNot found {error_1}")
                    else:
                        shutil.move(full_path, os.path.join(arg, name))
                        terminal_textbox.insert(tk.END, "\nMoved")

                elif cmd == "compile":
                    if not os.path.exists(full_path):
                        terminal_textbox.insert(tk.END, f"\nNot found {error_1}")
                        return

                    compilers = {
                        "c": ["gcc", full_path, "-o", full_path[:-2]],
                        "cpp": ["g++", full_path, "-o", full_path[:-4]],
                        "py": ["python", "-m", "py_compile", full_path],
                        "java": ["javac", full_path],
                    }

                    if arg not in compilers:
                        terminal_textbox.insert(tk.END, "\nUnsupported language")
                        return

                    result = subprocess.run(
                        compilers[arg], capture_output=True, text=True
                    )

                    terminal_textbox.insert(
                        tk.END, "\n" + result.stdout + result.stderr
                    )

            elif len(parts) == 3:
                name, path = parts[1], parts[2]
                full_path = os.path.join(path, name)

                if cmd == "addfile":
                    os.makedirs(path, exist_ok=True)
                    open(full_path, "w").close()
                    terminal_textbox.insert(tk.END, "\nFile created")

                elif cmd == "deletefile":
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        terminal_textbox.insert(tk.END, "\nDeleted")
                    else:
                        terminal_textbox.insert(tk.END, "\nNot found")

                elif cmd == "makeworkspace":
                    os.makedirs(full_path, exist_ok=True)
                    terminal_textbox.insert(tk.END, "\nWorkspace created")

                elif cmd == "deleteworkspace":
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                        terminal_textbox.insert(tk.END, "\nWorkspace deleted")
                    else:
                        terminal_textbox.insert(tk.END, "\nNot found")

                elif cmd == "list":
                    if not os.path.exists(full_path):
                        terminal_textbox.insert(tk.END, "\nNot found")
                        return

                    for root, dirs, files in os.walk(full_path):
                        level = root.replace(full_path, "").count(os.sep)
                        indent = " " * 4 * level
                        terminal_textbox.insert(
                            tk.END, f"\n{indent}{os.path.basename(root)}/"
                        )
                        for f in files:
                            terminal_textbox.insert(tk.END, f"\n{indent}    {f}")

                else:
                    terminal_textbox.insert(tk.END, f"\n{error_0}")

            elif len(parts) == 2:
                arg = parts[1]

                if cmd == "isactive":
                    found = False
                    for p in psutil.process_iter(["name"]):
                        if arg.lower() in p.info["name"].lower():
                            found = True
                            break
                    terminal_textbox.insert(
                        tk.END, "\nActive" if found else "\nNot active"
                    )

                elif cmd == "typemessage":
                    terminal_textbox.insert(tk.END, "\n" + arg)

                else:
                    terminal_textbox.insert(tk.END, f"\n{error_0}")

            elif len(parts) == 1:
                if cmd == "help":
                    terminal_textbox.insert(tk.END, "\n" + help_tool)

                elif cmd == "showcommands":
                    terminal_textbox.insert(tk.END, "\n" + all_commands)

                elif cmd == "clear":
                    terminal_textbox.delete("1.0", tk.END)

                elif cmd == "exit":
                    window.destroy()

                else:
                    terminal_textbox.insert(tk.END, f"\n{error_0}")

        except Exception as e:
            terminal_textbox.insert(tk.END, f"\nError: {e}")

    def on_enter(event=None):
        nonlocal editable_index
        command = terminal_textbox.get(editable_index, "end-1c")
        terminal_textbox.insert(tk.END, "\n")

        threading.Thread(
            target=lambda: [command_execution(command), insert_prompt()], daemon=True
        ).start()

        return "break"

    def on_key(event):
        if terminal_textbox.compare("insert", "<", editable_index):
            return "break"

    terminal_textbox.bind("<Return>", on_enter)
    terminal_textbox.bind("<Key>", on_key)

    insert_prompt()
    window.mainloop()


if __name__ == "__main__":
    main_terminal()
