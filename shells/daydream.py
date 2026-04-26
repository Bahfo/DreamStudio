import customtkinter as ctk
import os
import threading
import shutil
import subprocess
import psutil

help_tool = """
(C) COPYRIGHT - 2026 Excellent Technologies Cooperation - All Rights Reserved

DayDream Terminal
A special terminal designed for file management and code files execution
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

error_0 = "bad command, perhaps you check list of commands? type showcommands"
error_1 = """\nCheck:\n 1.The correct path\n 2.Add the extension if missing \n 
3. Perhaps you didn't specify the language correctly?\n
Check the documentation or type (help) for help"""


def main_terminal():

    ctk.set_appearance_mode("dark")

    def center_window(window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

    window = ctk.CTk()
    window.title("daydream terminal")
    window.eval("tk::PlaceWindow . center")
    center_window(window)
    window.geometry("700x450")

    ###########################################################################################
    # TEXTBOX
    ###########################################################################################
    terminal_textbox = ctk.CTkTextbox(
        window, bg_color="#2e2e2e", corner_radius=0, wrap="word", font=("Consolas", 16)
    )
    terminal_textbox.insert(
        "0.0", "Daydream Console \nCOPYRIGHT 2026 EX Technologies" + "\n"
    )
    terminal_textbox.pack(
        padx=(5, 5), pady=(5, 5), fill="both", side="left", expand=True
    )
    terminal_textbox.configure(state="normal")

    def insert_prompt():
        global editable_index
        terminal_textbox.insert(ctk.END, ">>> ")  # prompt
        editable_index = terminal_textbox.index("end-1c")  # start of editable region
        terminal_textbox.see(ctk.END)

    insert_prompt()

    def command_execution(user_input, screen_widget):
        user_input = user_input.lower()
        parts = user_input.split(" ")
        command_identifier = parts[0]

        if len(parts) == 4:
            parameter_1 = parts[1]  # Name
            parameter_2 = parts[2]  # Path
            parameter_3 = parts[3].lower()  # Source Language / Or Destination Path

            # COPYFILE   copyfile file_name source_path destination_path
            if command_identifier == "copyfile":
                full_path = os.path.join(parameter_2, parameter_1)

                if not os.path.exists(full_path):
                    screen_widget.insert(
                        ctk.END,
                        f"File '{parameter_1}' not found in '{parameter_2}' {error_1}\n",
                    )
                else:
                    try:
                        destination_file = os.path.join(parameter_3, parameter_1)
                        shutil.copyfile(full_path, destination_file)
                        screen_widget.insert(
                            ctk.END,
                            f"Copied '{parameter_1}' to '{parameter_3}' successfully\n",
                        )
                    except Exception as e:
                        screen_widget.insert(ctk.END, f"Error copying file: {e}\n")

            # MOVEFILE   movefile file_name source_path destination_path
            if command_identifier == "movefile":
                full_path = os.path.join(parameter_2, parameter_1)

                if not os.path.exists(full_path):
                    screen_widget.insert(
                        ctk.END,
                        f"File '{parameter_1}' not found in '{parameter_2}' {error_1}\n",
                    )
                else:
                    try:
                        destination_file = os.path.join(parameter_3, parameter_1)
                        shutil.move(full_path, destination_file)
                        screen_widget.insert(
                            ctk.END,
                            f"Moved '{parameter_1}' to '{parameter_3}' successfully\n",
                        )
                    except Exception as e:
                        screen_widget.insert(ctk.END, f"Error moving file: {e}\n")

            # COMPILATION
            if command_identifier == "compile":
                full_path_compile = os.path.join(parameter_2, parameter_1)
                if not os.path.exists(full_path_compile):
                    screen_widget.insert(
                        ctk.END, f"File {parameter_1} not found {error_1}\n"
                    )
                    pass
                else:
                    try:
                        compiler_commands = {
                            # C / C++
                            "c": [
                                "gcc",
                                full_path_compile,
                                "-o",
                                os.path.splitext(full_path_compile)[0],
                            ],
                            "cpp": [
                                "g++",
                                full_path_compile,
                                "-o",
                                os.path.splitext(full_path_compile)[0],
                            ],
                            "c++": [
                                "g++",
                                full_path_compile,
                                "-o",
                                os.path.splitext(full_path_compile)[0],
                            ],
                            "csharp": ["csc", full_path_compile],
                            "cs": ["csc", full_path_compile],
                            # Java
                            "java": ["javac", full_path_compile],
                            # Python
                            "python": ["python", "-m", "py_compile", full_path_compile],
                            "py": ["python", "-m", "py_compile", full_path_compile],
                            # Go
                            "go": ["go", "build", full_path_compile],
                            # Rust
                            "rust": ["rustc", full_path_compile],
                            "rs": ["rustc", full_path_compile],
                            # Kotlin
                            "kotlin": ["kotlinc", full_path_compile],
                            # Swift
                            "swift": ["swiftc", full_path_compile],
                            # TypeScript (compile to JavaScript)
                            "typescript": ["tsc", full_path_compile],
                            "ts": ["tsc", full_path_compile],
                            # JavaScript (optional: check syntax or transpile)
                            "javascript": ["node", "--check", full_path_compile],
                            "js": ["node", "--check", full_path_compile],
                            # Pascal
                            "pascal": ["fpc", full_path_compile],
                            "p": ["fpc", full_path_compile],
                            # Ruby (syntax check)
                            "ruby": ["ruby", "-c", full_path_compile],
                            "rb": ["ruby", "-c", full_path_compile],
                            # PHP (syntax check)
                            "php": ["php", "-l", full_path_compile],
                            # Scala
                            "scala": ["scalac", full_path_compile],
                            # Haskell
                            "haskell": ["ghc", full_path_compile],
                            "hs": ["ghc", full_path_compile],
                            # Dart
                            "dart": ["dart", "compile", "exe", full_path_compile],
                        }
                        if parameter_3 not in compiler_commands:
                            screen_widget.insert(
                                ctk.END, f"Unsupported language: {parameter_3}\n"
                            )
                            pass
                        else:
                            try:
                                result = subprocess.run(
                                    compiler_commands[parameter_3],
                                    capture_output=True,
                                    text=True,
                                )

                                # Show both stdout and stderr on the screen
                                if result.stdout:
                                    screen_widget.insert(ctk.END, f"{result.stdout}\n")
                                if result.stderr:
                                    screen_widget.insert(ctk.END, f"{result.stderr}\n")

                                # Check return code
                                if result.returncode == 0:
                                    screen_widget.insert(
                                        ctk.END,
                                        f"{parameter_3.capitalize()} compilation successful.\n",
                                    )
                                else:
                                    screen_widget.insert(
                                        ctk.END,
                                        f"{parameter_3.capitalize()} compilation failed.\n",
                                    )

                            except FileNotFoundError:
                                screen_widget.insert(
                                    ctk.END,
                                    f"Compiler for {parameter_3} not found on this system.\n",
                                )
                            except Exception as e:
                                screen_widget.insert(
                                    ctk.END, f"Error during compilation: {e}\n"
                                )

                    except Exception as e:
                        screen_widget.insert(ctk.END, f"Error: {e}\n")

        if len(parts) == 3:
            parameter_1 = parts[1]  # Name
            parameter_2 = parts[2]  # Path

            # ADD FILE
            if command_identifier == "addfile":
                try:
                    full_path_add = os.path.join(parameter_2, parameter_1)
                    os.makedirs(parameter_2, exist_ok=True)  # ensure directory exists
                    with open(full_path_add, "w") as f:
                        pass
                    screen_widget.insert(
                        ctk.END, f"File created successfully: {full_path_add}\n"
                    )

                except Exception as e:
                    screen_widget.insert(ctk.END, f"Error: {e}\n")

            # DELETE FILE
            elif command_identifier == "deletefile":
                try:
                    full_path_delete = os.path.join(parameter_2, parameter_1)
                    if os.path.exists(full_path_delete):
                        os.remove(full_path_delete)
                        screen_widget.insert(
                            ctk.END, f"File deleted successfully: {full_path_delete}\n"
                        )
                    else:
                        screen_widget.insert(ctk.END, "File not found\n")

                except Exception as e:
                    screen_widget.insert(ctk.END, f"Error: {e}\n")

            # MAKE WORKSPACE
            elif command_identifier == "makeworkspace":
                try:
                    full_path_workspace = os.path.join(parameter_2, parameter_1)
                    if os.path.exists(full_path_workspace):
                        screen_widget.insert(
                            ctk.END, f"Workspace '{parameter_1}' already exists.\n"
                        )
                    else:
                        os.makedirs(full_path_workspace, exist_ok=True)
                        screen_widget.insert(
                            ctk.END,
                            f"Workspace '{parameter_1}' created successfully.\n",
                        )

                except Exception as e:
                    screen_widget.insert(ctk.END, f"Error: {e}\n")

            # DELETE WORKSPACE
            elif command_identifier == "deleteworkspace":
                try:
                    full_path_delete_ws = os.path.join(parameter_2, parameter_1)
                    if not os.path.exists(full_path_delete_ws):
                        screen_widget.insert(ctk.END, "Workspace not found.\n")

                    elif os.path.isdir(full_path_delete_ws):
                        if not os.listdir(full_path_delete_ws):  # folder is empty
                            os.rmdir(full_path_delete_ws)
                            screen_widget.insert(
                                ctk.END, "Empty workspace removed successfully.\n"
                            )
                        else:
                            screen_widget.insert(
                                ctk.END,
                                "Workspace not empty. Confirm deletion [Y/n]:\n",
                            )

                            user_input = (
                                terminal_textbox.get("end-2c linestart", "end-1c")
                                .strip()
                                .lower()
                            )
                            if user_input == "y":
                                shutil.rmtree(full_path_delete_ws)
                                screen_widget.insert(
                                    ctk.END,
                                    f"Workspace and contents deleted: {full_path_delete_ws}\n",
                                )
                            else:
                                screen_widget.insert(
                                    ctk.END, "Deletion canceled by user.\n"
                                )

                except Exception as e:
                    screen_widget.insert(ctk.END, f"Error: {e}\n")

            elif command_identifier == "list":
                full_path = os.path.join(parameter_2, parameter_1)
                if not os.path.exists(full_path):
                    screen_widget.insert(ctk.END, "Workspace not found\n")
                else:
                    # Define a version of print_tree that writes to the GUI
                    def gui_print_tree(path, widget, indent=""):
                        widget.insert(ctk.END, f"{indent}{os.path.basename(path)}/\n")
                        try:
                            for item in os.listdir(path):
                                full_item_path = os.path.join(path, item)
                                if os.path.isdir(full_item_path):
                                    gui_print_tree(
                                        full_item_path, widget, indent + "    "
                                    )
                                else:
                                    widget.insert(ctk.END, f"{indent}    {item}\n")
                        except PermissionError:
                            widget.insert(ctk.END, f"{indent}    [Permission Denied]\n")

                    gui_print_tree(full_path, screen_widget)

            else:
                screen_widget.insert(ctk.END, f"{error_0}\n")
                pass

        if len(parts) == 2:
            parameter = parts[1]

            # CHECKING IF A PROCESS IS ACTIVE
            if command_identifier == "isactive":
                try:
                    for proc in psutil.process_iter(["name"]):
                        if parameter.lower() in proc.info["name"].lower():
                            screen_widget.insert(
                                ctk.END, f"process {parameter} is active\n"
                            )
                    return screen_widget.insert(
                        ctk.END, f"process {parameter} is not active\n"
                    )
                except Exception as e:
                    screen_widget.insert(ctk.END, f"Error: {e}\n")

            # TYPE MESSAGE
            elif command_identifier == "typemessage":
                screen_widget.insert(ctk.END, f"{parameter}")

            else:
                screen_widget.insert(ctk.END, f"{error_0}\n")
                pass

        if len(parts) == 1:
            # HELP
            if command_identifier == "help":
                screen_widget.insert(ctk.END, help_tool + "\n")

            # SHOWCOMMANDS
            elif command_identifier == "showcommands":
                screen_widget.insert(ctk.END, all_commands + "\n")

            # EXIT TERMINAL
            elif command_identifier == "exit":
                window.destroy()

            # CLEAR SCREEN
            elif command_identifier == "clear":
                screen_widget.delete("0.0", "end")
                screen_widget.insert(
                    "0.0", "Daydream Console \nCOPYRIGHT 2026 EX Technologies" + "\n"
                )

            else:
                screen_widget.insert(ctk.END, f"{error_0}\n")
                pass

        insert_prompt()
        screen_widget.see(ctk.END)

    def on_enter(event=None):
        global editable_index
        text = terminal_textbox.get(editable_index, "end-1c")
        terminal_textbox.insert(ctk.END, "\n")

        threading.Thread(
            target=command_execution, args=(text, terminal_textbox), daemon=True
        ).start()
        return "break"

    def on_key(event=None):
        cursor_index = terminal_textbox.index("insert")
        if terminal_textbox.compare(cursor_index, "<", editable_index):
            return "break"

    terminal_textbox.bind("<Return>", on_enter)
    terminal_textbox.bind("<Key>", on_key)

    window.mainloop()


if __name__ == "__main__":
    main_terminal()
