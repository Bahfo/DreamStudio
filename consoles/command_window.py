logo_ascii = r"""
 /$$$$$$$                                               /$$     /$$   /$$
| $$__  $$                                             | $$    | $$  / $$
| $$  \ $$ /$$$$$$   /$$$$$$  /$$$$$$/$$$$   /$$$$$$  /$$$$$$  |  $$/ $$/
| $$$$$$$//$$__  $$ /$$__  $$| $$_  $$_  $$ /$$__  $$|_  $$_/   \  $$$$/ 
| $$____/| $$  \__/| $$  \ $$| $$ \ $$ \ $$| $$  \ $$  | $$      >$$  $$ 
| $$     | $$      | $$  | $$| $$ | $$ | $$| $$  | $$  | $$ /$$ /$$/\  $$
| $$     | $$      |  $$$$$$/| $$ | $$ | $$| $$$$$$$/  |  $$$$/| $$  \ $$
|__/     |__/       \______/ |__/ |__/ |__/| $$____/    \___/  |__/  |__/
                                           | $$                          
                                           | $$                          
                                           |__/

COPYRIGHT 2026 EX-TECHNOLOGIES. ALL RIGHTS RESERVED                                           
Welcome to PromptX Shell!
Type 'help' to see available commands.
"""

import re
import os
import cmd
import glob
import socket
import psutil
import shutil
import getpass
import zipfile
import datetime
import platform
import customtkinter as ctk

# ---------------- Redirect stdout to GUI ----------------
class GUIStdout:
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, text):
        if text.strip():
            self.textbox.insert("end", "\n" + text, "output")
            self.textbox.see("end")

    def flush(self):
        pass

# ---------------- Command Line Logic ----------------
class CommandLine(cmd.Cmd):
    def __init__(self, stdout=None):
        super().__init__(stdout=stdout)
        self.currentDir = os.getcwd()
        self.prompt = f"{self.currentDir}>>> "
        self._history = []
        self._history_index = None
        self.commands_list = [
            "here", "peek", "clear", "cpuinfo", "meminfo",
            "diskinfo", "sysinfo", "help", "quit", "fileinfo", "zip",
            "changedir", "me", "mybox", "newbie", "clone",
            "shift", "erase", "head", "tail", "find",]

    def parse_args(self, arg):
        parts = arg.split()
        args = {}
        for p in parts:
            if "=" in p:
                key, value = p.split("=", 1)
                key = key.lstrip("-")
                value = value.strip('"')
                args[key] = value
            else:
                args[p] = True
        return args
    
    def onecmd(self, line):
        line = line.strip()
        if line:
            self._history.append(line)
            self._history_index = len(self._history)
        return super().onecmd(line)

    def get_previous_command(self):
        if self._history and self._history_index > 0:
            self._history_index -= 1
            return self._history[self._history_index]
        return ""

    def get_next_command(self):
        if self._history and self._history_index < len(self._history) - 1:
            self._history_index += 1
            return self._history[self._history_index]
        self._history_index = len(self._history)
        return ""
    
    # -------------------- Logo --------------------
    def do_logo(self, arg=None):
        return f"\n{logo_ascii}\n"

    # -------------------- Help --------------------
    def do_help(self, arg):
        """
Help: help: 
Provides help for functions.
Type in the function name or topic after typing 'help'.
Example: help changedir.
        """
        return super().do_help(arg)

    # -------------------- Quit --------------------
    def do_quit(self, arg=None):
        """
Help: quit: 
Exits the command shell.
        """
        return True

    # -------------------- Changedir --------------------
    def do_changedir(self, arg):
        """
Help: changedir --path=<directory_path>:
Changes the current working directory to the specified path.
Example: changedir --path="C:/Users/Username/Documents"
        """
        args = self.parse_args(arg)
        path = args.get("path", None)
        if not path:
            return "Error: You must provide a path."
        try:
            os.chdir(path)
            self.currentDir = os.getcwd()
            self.prompt = f"{self.currentDir}>>> "
            return f"Changed directory to {self.currentDir}"
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Here --------------------
    def do_here(self, arg=None):
        """
Help: here:
Displays the current working directory.
Example: here
        """
        return f"\ncurrent working directory: {os.getcwd()}"

    # -------------------- Me --------------------
    def do_me(self, arg=None):
        """
Help: me:
Displays the current username.
Example: me
        """
        return f"Username: {getpass.getuser()}"

    # -------------------- Mybox --------------------
    def do_mybox(self, arg=None):
        """
Help: mybox:
Displays the hostname of the machine.
Example: mybox
        """
        return f"Hostname: {socket.gethostname()}"

    # -------------------- Newbie --------------------
    def do_newbie(self, arg):
        """
Help: newbie --name=<file_name> [--path=<directory_path>] [--ext=<file_extension>] [--content="<file_content>"]:
Creates a new file with the specified name, path, extension, and content.
Example: newbie --name="example" --path="C:/Users/Username/Documents" --ext=".txt" --content="Hello, World!"
        """
        args = self.parse_args(arg)
        if "name" not in args:
            return "Error: You must provide --name=<file_name>"
        file_name = args["name"]
        file_path = args.get("path", os.getcwd())
        extension = args.get("ext", ".txt")
        content = args.get("content", "")
        try:
            if not os.path.exists(file_path):
                return f"Error: Path '{file_path}' does not exist."
            full_path = os.path.join(file_path, file_name + extension)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"File '{full_path}' has been created."
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Clone --------------------
    def do_clone(self, arg):
        """
Help: clone --source=<source_file> --destination=<destination_file_or_dir>:
Clones a file from the source path to the destination path or directory.
Example: clone --source="C:/path/to/source.txt" --destination="C:/path/to/destination.txt"
        """
        args = self.parse_args(arg)
        source = args.get("source", None)
        destination = args.get("destination", None)
        if not source or not destination:
            return "Error: You must provide --source=<source_file> and --destination=<destination_file_or_dir>"
        try:
            if not os.path.isfile(source):
                return f"Error: Source file '{source}' does not exist."
            if os.path.isdir(destination):
                file_name = os.path.basename(source)
                destination = os.path.join(destination, file_name)
            dest_dir = os.path.dirname(destination)
            if dest_dir and not os.path.exists(dest_dir):
                return f"Error: Destination directory '{dest_dir}' does not exist."
            with open(source, "rb") as src:
                data = src.read()
            with open(destination, "wb") as dst:
                dst.write(data)
            return f"File cloned from '{source}' to '{destination}'."
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Shift --------------------
    def do_shift(self, arg):
        """
Help: shift --old=<old_string> --new=<new_string> --path=<file_path>:
Replaces all occurrences of old_string with new_string in the specified file.
Example: shift --old="foo" --new="bar" --path="C:/path/to/file.txt"
        """
        args = self.parse_args(arg)
        old_string = args.get("old", None)
        new_string = args.get("new", None)
        file_path = args.get("path", None)
        if not old_string or not new_string or not file_path:
            return "Error: You must provide --old=<old_string> --new=<new_string> --path=<file_path>"
        try:
            if not os.path.isfile(file_path):
                return f"Error: File '{file_path}' does not exist."
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if old_string not in content:
                return f"Error: '{old_string}' was not found in '{file_path}'."
            updated_content = content.replace(old_string, new_string)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            return f"Shifted '{old_string}' → '{new_string}' in '{file_path}'."
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Peek --------------------
    def do_peek(self, arg):
        """
Help: peek [--number=<n>] [--path=<directory_path>]:
Lists the contents of the specified directory. If --number is provided, lists only the first n items.
Example: peek --number=5 --path="C:/Users/Username/Documents"
        """
        args = self.parse_args(arg)
        number = args.get("number", None)
        custom_path = args.get("path", None)
        if number and os.path.isdir(number):
            custom_path = number
            number = None
        try:
            path_to_use = custom_path if custom_path else os.getcwd()
            all_items = os.listdir(path_to_use)
            if number in (None, "", "--all"):
                return f"Directory ({path_to_use}):\n" + "\n".join(all_items)
            n = int(number)
            return f"Directory ({path_to_use}) - first {n} items:\n" + "\n".join(all_items[:n])
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Erase --------------------
    def do_erase(self, arg):
        """
Help: erase --file=<filename_or_path>:
Deletes the specified file.
Example: erase --file="C:/path/to/file.txt"
        """
        args = self.parse_args(arg)
        filename = args.get("file", None)
        if not filename:
            return "Error: You must provide --file=<filename_or_path>"
        try:
            if not os.path.isfile(filename):
                return f"Error: File '{filename}' does not exist."
            os.remove(filename)
            return f"File '{filename}' has been deleted."
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Head --------------------
    def do_head(self, arg):
        """
Help: head --file=<file> --lines=<n>: Shows the first n lines of a file (default 10).
        """
        args = self.parse_args(arg)
        file_path = args.get("file", None)
        lines = int(args.get("lines", 10))
        if not file_path:
            return "Error: You must provide --file=<file_path>"
        if not os.path.isfile(file_path):
            return f"Error: File '{file_path}' does not exist."
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = [next(f).rstrip("\n") for _ in range(lines)]
            return "\n".join(content)
        except StopIteration:
            return "\n".join(content)
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Tail --------------------
    def do_tail(self, arg):
        """
Help: tail --file=<file> --lines=<n>: Shows the last n lines of a file (default 10).
        """
        args = self.parse_args(arg)
        file_path = args.get("file", None)
        lines = int(args.get("lines", 10))
        if not file_path:
            return "Error: You must provide --file=<file_path>"
        if not os.path.isfile(file_path):
            return f"Error: File '{file_path}' does not exist."
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.readlines()
            return "".join(content[-lines:])
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Find --------------------
    def do_find(self, arg):
        """Help: find --pattern=<pattern> --path=<path>: Search files matching pattern in path."""
        args = self.parse_args(arg)
        pattern = args.get("pattern", None)
        search_path = args.get("path", os.getcwd())
        if not pattern:
            return "Error: You must provide --pattern=<pattern>"
        try:
            files = glob.glob(os.path.join(search_path, pattern))
            if not files:
                return f"No files found matching pattern '{pattern}' in '{search_path}'"
            return "\n".join(files)
        except Exception as e:
            return f"Error: {e}"

    # -------------------- File Info --------------------
    def do_fileinfo(self, arg):
        """Help: fileinfo --file=<file>: Shows metadata of the specified file."""
        args = self.parse_args(arg)
        file_path = args.get("file", None)
        if not file_path:
            return "Error: You must provide --file=<file_path>"
        if not os.path.isfile(file_path):
            return f"Error: File '{file_path}' does not exist."
        try:
            stats = os.stat(file_path)
            size = stats.st_size
            created = datetime.datetime.fromtimestamp(stats.st_ctime)
            modified = datetime.datetime.fromtimestamp(stats.st_mtime)
            return (
                f"File: {file_path}\n"
                f"Size: {size} bytes\n"
                f"Created: {created}\n"
                f"Modified: {modified}"
            )
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Zip --------------------
    def do_zip(self, arg):
        """Help: zip --source=<source> --destination=<zipfile>: Create a zip archive."""
        args = self.parse_args(arg)
        source = args.get("source", None)
        destination = args.get("destination", None)
        if not source or not destination:
            return "Error: You must provide --source=<file_or_dir> --destination=<zipfile>"
        try:
            with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as z:
                if os.path.isdir(source):
                    for root, _, files in os.walk(source):
                        for f in files:
                            abs_path = os.path.join(root, f)
                            arcname = os.path.relpath(abs_path, start=os.path.dirname(source))
                            z.write(abs_path, arcname)
                elif os.path.isfile(source):
                    z.write(source, os.path.basename(source))
                else:
                    return f"Error: Source '{source}' does not exist."
            return f"Archive '{destination}' created from '{source}'."
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Cpuinfo --------------------
    def do_cpuinfo(self, arg=None):
        """
Help: cpuinfo: Returns the underlying hardware processor's information.
        """
        return f"CPU: {platform.processor()}"
    
    # -------------------- Meminfo --------------------
    def do_meminfo(self, arg=None):
        """
Help: meminfo: Returns the main memory system information.
        """
        try:
            mem = psutil.virtual_memory()
            total = round(mem.total / (1024**2), 2)
            available = round(mem.available / (1024**2), 2)
            used = round(mem.used / (1024**2), 2)
            percent = mem.percent
            return f"Memory Usage:\nTotal: {total} MB\nUsed: {used} MB\nAvailable: {available} MB\nUsage: {percent}%"
        except Exception as e:
            return f"Error: {e}"
        
    # -------------------- Diskinfo --------------------
    def do_diskinfo(self, path):
        """
Help: diskinfo: Returns the hard disk drive (HDD) information.
        """
        try:
            if not path:
                path = os.getcwd()
            if os.path.exists(path):
                usage = shutil.disk_usage(path)
                total = usage.total // (1024**3)
                used = usage.used // (1024**3)
                free = usage.free // (1024**3)
                percent = round((used / total) * 100, 2)
                return f"Disk info for {path}:\nTotal: {total} GB\nUsed: {used} GB\nFree: {free} GB\nUsage: {percent}%"
            else:
                return f"Error: Path does not exist: {path}"
        except Exception as e:
            return f"Error: {e}"
        
    # -------------------- Diskinfo --------------------
    def do_sysinfo(self, arg=None):
        """
Help: sysinfo: Returns the operating system and architecture information
        """
        try:
            system = platform.system()
            release = platform.release()
            version = platform.version()
            arch = platform.machine()
            return f"System: {system}\nRelease: {release}\nVersion: {version}\nArchitecture: {arch}"
        except Exception as e:
            return f"Error: {e}"

    def do_clearhistory(self, arg=None):
        """Help: clearhistory: Deletes all command history."""
        self._history.clear()
        self._history_index = None
        return "Command history cleared."

# ---------------- GUI Shell ----------------
class PromptXShell(ctk.CTkToplevel):
    def __init__(self, master=None, **kwargs):
        super().__init__(master=master, **kwargs)
        self.title("PromptX Shell")
        self.geometry("800x500")

        # ---------------- Textbox ----------------
        self.textbox = ctk.CTkTextbox(
            self, width=760, height=460, corner_radius=0,
            font=("Consolas", 15), fg_color="#0F0F0F"
        )
        self.textbox.pack(padx=5, pady=5, fill="both", expand=True)

        # ---------------- Tags ----------------
        self.textbox.tag_config("output", foreground="#EAEAEA")
        self.textbox.tag_config("error", foreground="#FF5555")
        self.textbox.tag_config("command", foreground="#FFFC56")
        self.textbox.tag_config("prompt", foreground="#767676")
        self.textbox.tag_config("number", foreground="#79FFA5")
        self.textbox.tag_config("string", foreground="#6770B9")
        self.textbox.tag_config("filename", foreground="#FFA500")
        self.textbox.tag_config("path", foreground="#9E57AD")

        # ---------------- Internal state ----------------
        self.multiline_buffer = ""
        self.readonly_index = "1.0"

        # ---------------- Command shell ----------------
        self.cmd_shell = CommandLine(stdout=GUIStdout(self.textbox))

        # ---------------- Event bindings ----------------
        self.textbox.bind("<Return>", self.onEnter)
        self.textbox.bind("<Shift-Return>", self.onShiftEnter)
        self.textbox.bind("<Key>", self.onKeyPress)
        self.textbox.bind("<KeyRelease>", lambda e: self.highlight_syntax())
        self.textbox.bind("<Button-1>", self.onClick)
        self.textbox.bind("<Control-a>", self.limit_select_all)
        self.textbox.bind("<Control-v>", self.onPaste)

        self.textbox.bind("<Up>", self.on_history_up)
        self.textbox.bind("<Down>", self.on_history_down)

        self.insert_prompt()

    # ---------------- Prompt ----------------
    def insert_prompt(self):
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.insert("end", f"{self.cmd_shell.currentDir}>>> ", "prompt")
        self.readonly_index = self.textbox.index("end-1c")
        self.textbox.mark_set("insert", self.readonly_index)
        self.textbox.see("end")
        self.textbox.configure(state=ctk.NORMAL)

    # ---------------- Key & Selection Control ----------------
    def onKeyPress(self, event):
        if self.textbox.compare("insert", "<", self.readonly_index):
            self.textbox.mark_set("insert", self.readonly_index)
        if event.keysym in ("BackSpace", "Delete"):
            if self.textbox.compare("insert", "<=", self.readonly_index):
                return "break"

    def onClick(self, event):
        self.after(1, self.fix_cursor)

    def fix_cursor(self):
        if self.textbox.compare("insert", "<", self.readonly_index):
            self.textbox.mark_set("insert", self.readonly_index)

    def limit_select_all(self, event):
        self.textbox.tag_remove("sel", "1.0", self.readonly_index)
        return "break"

    def onPaste(self, event=None):
        try:
            self.textbox.delete("sel.first", "sel.last")
        except:
            pass
        return "break"

    # ---------------- Command execution ----------------
    def execute_command(self, line):
        if not line.strip():
            return

        # Clear command
        if line.strip() == "clear":
            self.textbox.configure(state=ctk.NORMAL)
            self.textbox.delete("1.0", "end")
            self.insert_prompt()
            return

        try:
            if line.startswith("quit"):
                self.print_output("\nExiting shell...\n", "output")
                self.destroy()
                return

            result = self.cmd_shell.onecmd(line)

            if result is True:
                self.print_output("\nShell stopped.\n", "output")
                self.destroy()
            elif isinstance(result, str):
                if result.lower().startswith("error"):
                    self.print_output("\n" + result + "\n", "error")
                else:
                    self.print_output("\n" + result + "\n", "output")

        except Exception as e:
            self.print_output("\nError: " + str(e) + "\n", "error")

    # ---------------- Events ----------------
    def onEnter(self, event):
        user_input = self.textbox.get(self.readonly_index, "end-1c").strip()
        if self.multiline_buffer:
            self.multiline_buffer += "\n" + user_input
            self.execute_command(self.multiline_buffer)
            self.multiline_buffer = ""
        else:
            self.execute_command(user_input)
        self.textbox.insert("end", "\n")
        self.insert_prompt()
        return "break"

    def onShiftEnter(self, event):
        self.textbox.insert("insert", "\n")
        self.multiline_buffer += self.textbox.get(self.readonly_index, "end-1c") + "\n"
        return "break"

    # ---------------- Output ----------------
    def print_output(self, message, tag=None):
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.insert("end", message, tag)
        self.textbox.see("end")
        self.textbox.configure(state=ctk.NORMAL)

    # ---------------- Syntax highlighting ----------------
    def highlight_syntax(self):
        self.textbox.tag_remove("command", self.readonly_index, "end")
        self.textbox.tag_remove("number", self.readonly_index, "end")
        self.textbox.tag_remove("string", self.readonly_index, "end")
        self.textbox.tag_remove("filename", self.readonly_index, "end")
        self.textbox.tag_remove("path", self.readonly_index, "end")

        user_input = self.textbox.get(self.readonly_index, "end-1c")
        if not user_input.strip():
            return

        # Highlight first word as command
        first_word = user_input.strip().split(" ")[0]
        if first_word in self.cmd_shell.commands_list:
            start_index = self.readonly_index
            end_index = f"{self.readonly_index} + {len(first_word)}c"
            self.textbox.tag_add("command", start_index, end_index)

        # Numbers
        for match in re.finditer(r"\b\d+(\.\d+)?\b", user_input):
            start_index = f"{self.readonly_index} + {match.start()}c"
            end_index = f"{self.readonly_index} + {match.end()}c"
            self.textbox.tag_add("number", start_index, end_index)

        # Strings
        for match in re.finditer(r'(["\']).*?\1', user_input):
            start_index = f"{self.readonly_index} + {match.start()}c"
            end_index = f"{self.readonly_index} + {match.end()}c"
            self.textbox.tag_add("string", start_index, end_index)

        # Filenames
        for match in re.finditer(r'\b[\w\-]+\.(txt|py|log|csv|cpp|csharp|css|html|pyc|c|h|docx|ppt|pptx)\b', user_input):
            start_index = f"{self.readonly_index} + {match.start()}c"
            end_index = f"{self.readonly_index} + {match.end()}c"
            self.textbox.tag_add("filename", start_index, end_index)

        # Paths
        for match in re.finditer(r'([A-Za-z]:\\|/)[\w/\\.-]+', user_input):
            start_index = f"{self.readonly_index} + {match.start()}c"
            end_index = f"{self.readonly_index} + {match.end()}c"
            self.textbox.tag_add("path", start_index, end_index)

    # ---------------- Command history ----------------
    def on_history_up(self, event):
        prev = self.cmd_shell.get_previous_command()
        self.replace_current_input(prev)
        return "break"

    def on_history_down(self, event):
        next_cmd = self.cmd_shell.get_next_command()
        self.replace_current_input(next_cmd)
        return "break"

    def replace_current_input(self, text):
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.delete(self.readonly_index, "end-1c")
        self.textbox.insert("end", text)
        self.textbox.mark_set("insert", "end")
        self.textbox.see("end")

# ---------------- Run GUI ----------------
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = PromptXShell()
    app.mainloop()