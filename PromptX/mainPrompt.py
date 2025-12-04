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

class mainAppWindow:
    def __init__(self):
        ctk.set_appearance_mode('dark')
        self.mainWindow = ctk.CTk()
        self.mainWindow.geometry("1300x750")
        self.mainWindow.title("Power PromptX")

        self.leftFrame = ctk.CTkFrame(self.mainWindow, width=400, height=750, fg_color="#1E1E1E",
                                      corner_radius=0, border_color="#5F5F5F", border_width=1)
        self.leftFrame.pack(fill='y', side='left')

        self.topRightFrame = ctk.CTkFrame(self.mainWindow, width=900, height=120, fg_color="#373737",
                                          corner_radius=0, border_color="#5F5F5F", border_width=1)
        self.topRightFrame.pack(fill='x', side='top')

        self.commandLabel = ctk.CTkLabel(self.mainWindow, text="Command Prompt", font=("Segoe UI", 18),
                                         justify='left', anchor='w', width=800)
        self.commandLabel.pack(side="top", padx=50, pady=(40, 0), fill='x')

        self.commandBox = ctk.CTkEntry(self.mainWindow, width=800, height=50, fg_color="#1E1E1E",
                                       corner_radius=5, border_color="#5F5F5F", border_width=1,
                                       font=("Consolas", 14),
                                       placeholder_text=">>> Type 'help' to see all commands, or start typing to dismiss")
        self.commandBox.pack(side="top", fill="x", padx=50, pady=(10, 0))

        self.commandLabel = ctk.CTkLabel(self.mainWindow, text="Terminal", font=("Segoe UI", 18),
                                         justify='left', anchor='w', width=800)
        self.commandLabel.pack(side="top", padx=50, pady=(40, 0), fill='x')

        self.terminalBox = ctk.CTkTextbox(self.mainWindow, font=("Consolas", 14), width=1000,
                                          height=400, border_color="#5F5F5F", border_width=1,
                                          state=ctk.DISABLED)
        self.terminalBox.pack(side="top", padx=50, pady=(10, 0), fill='x')

        self.bottomFrame = ctk.CTkFrame(self.mainWindow, fg_color="#373737", border_color="#5F5F5F",
                                        border_width=1, corner_radius=0, width=900, height=30)
        self.bottomFrame.pack(side="bottom", fill='x')

        self.cmd_shell = CommandLine(stdout=GUIStdout(self.terminalBox))
        self.commandBox.bind("<Return>", self.onEnter)

    def execute_command(self, line: str):
        import time
        if not line.strip():
            return 
        
        if line.strip() == "clear":
            self.terminalBox.configure(state=ctk.NORMAL)
            self.terminalBox.delete("1.0","end")
            return
        
        try:
            if line.startswith("quit"):
                self.print_output("\nExiting ...\n")
                time.sleep(3)
                self.mainWindow.destroy()
                return

            result = self.cmd_shell.onecmd(line)
            
            if result is True:
                self.print_output("\nStopping Shell\n")
                time.sleep(3)
                self.mainWindow.destroy()
            elif isinstance(result, str):
                result:str
                if result.lower().startswith("error"):
                    self.print_output("\n" + result + "\n")
                else:
                    self.print_output("\n" + result + "\n")

        except Exception as e:
            self.print_output("\nError: " + str(e) + "\n")

    def onEnter(self, event=None):
        user_input = self.commandBox.get().strip()
        self.execute_command(user_input)

    def print_output(self, message):
        self.terminalBox.configure(state=ctk.NORMAL)
        self.terminalBox.insert(ctk.END, message)
        self.terminalBox.see(ctk.END)
        self.terminalBox.configure(state=ctk.DISABLED)

    def show(self):
        self.mainWindow.mainloop()

# ---------------- Redirect stdout to GUI ----------------
class GUIStdout:
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, text):
        if text.strip():
            self.textbox.configure(state=ctk.NORMAL)
            self.textbox.insert("end", text + "\n")
            self.textbox.see("end")
            self.textbox.configure(state=ctk.DISABLED)

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


    # -------------------- Help --------------------
    def do_help(self, arg):
        """
Help: help: 
Provides help for functions.
Type in the function name or topic after typing 'help'.
Example: help changedir.
        """
        if arg:
            return super().do_help(arg)
        else:
            return logo_ascii

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

if __name__ == '__main__':
    app = mainAppWindow()
    app.show()