HELP = r"""
DREAMSTUDIO IDE — PROMPT-X INTERACTIVE SHELL                 
© EXcellent TechStacks

• Display help documentation:              help
• Exit terminal environment:               quit

NOTE:
All command inputs are processed sequentially by the terminal's core interpreter. Invalid or malformed syntax may
result in undefined behavior or ignored operations.

A DreamStudio commands shell powered by command-type language 'Prompt-X'.
Prompt-X is a one-line shell command language for executing various system level commands, and various input/output 
user commands.
"""

ALL_COMMANDS = """All Available Commands:
changedir       Changes the current working directory
clear           Clears the terminal screen
clearhistory    Clears the command history
clone           Copies a file from source to destination
copydir         Copies a directory recursively from source to destination
cpuinfo         Displays CPU information
date            Shows the current date and time
deletedir       Deletes the specified directory
diskinfo        Shows hard disk information
download        Downloads a file from a URL
echo            Prints text to the terminal output
env             Displays environment variables
erase           Deletes the specified file
find            Shows detailed information about a file
fileinfo        Shows metadata and properties of a file
head            Shows first N lines of a file
help            Displays documentation for commands and topics
here            Shows the current working directory
history         Displays command history
kill            Terminates a process by PID
makedir         Creates a new directory
me              Shows the current username
meminfo         Shows memory usage information
mybox           Shows the system hostname
newbie          Creates a new file with optional content
pacman          Universal package manager for development languages
peek            Lists the contents of a directory
ping            Tests network connectivity to a host
ps              Lists running processes
quit            Exits the terminal environment
rename          Renames a file or directory
shift           Replaces strings within a file
sysinfo         Shows system information
tail            Shows last N lines of a file
unzip           Extracts a zip archive
uptime          Shows system uptime
whoami          Displays the current user
zip             Creates a zip archive
"""

import os
import cmd
import sys
import socket
import signal
import psutil
import shutil
import getpass
import zipfile
import datetime
import platform
import subprocess
import urllib.request
import urllib.error
from itertools import islice
from collections import deque


class BridgeInterpreter:
    """
    Redirects the standard output of the command line interface into
    custom-tkinter's textbox. Works by writing the text into the
    textbox, and moving the cursor's position into the end of the line.
    The other method `flush` is an empty method for instantly flushing
    the textbox.
    """

    def __init__(self, engine):
        self.engine = engine  # CommandLine instance

    def __call__(self, source):
        result = self.engine.onecmd(source)
        return str(result) if result is not None else ""


# ---------------- Command Line Logic ----------------
class CommandLine(cmd.Cmd):
    """
    Command-Line class inherited from `cmd` library.
    Inside, it has the backend and logic structure for generating
    responses of commands. It makes usage of the `cmd` library by
    generating a `do_command` function for each typed function on
    the user's screen. The text enters from the `GUIStdout` class
    and leaves towards.
    """

    def __init__(self, currentDir, stdout=None):
        super().__init__(stdout=stdout)
        self.currentDir = currentDir
        self.prompt = f"{self.currentDir}>>> "
        self._history = []
        self._history_index = None

    def parse_args(self, arg):
        """
        Prases arguments passed from `GUIStdout` class by splitting from the
        two -must written- characters (-) and (=). It splits each argument
        from the assign character (=). Then strips any dashes, or quotations
        found to store all parameters in one list.

        :param self: self parameter for class.
        :param arg: arguments to be parsed in.
        :return: dictionary of each parameter and its value assigned.
        """
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
        """
        oneCMD: Interpret the argument as though it had been typed in response
        to the prompt.
        The return value is a flag indicating whether interpretation of
        commands by the interpreter should stop.

        :param self: self parameter for class
        :param line: command-line typed by the user
        :return: flag indicating whether interpretation should stop or not.
        """
        line = line.strip()
        if line:
            self._history.append(line)
            self._history_index = len(self._history)
        return super().onecmd(line)

    def get_previous_command(self):
        """
        Scans the history of commands to get the previous commmand, which is
        a normal behavior in command-line tools after clicking the top-arrow
        on the keyboard.

        :param self: self parameter for class
        :return: previous command.
        :rtype: Any | Literal['']
        """
        if self._history and self._history_index > 0:
            self._history_index -= 1
            return self._history[self._history_index]
        return ""

    def get_next_command(self):
        """
        Scans the history of commands to get the next command, which is obtained
        if the user is checking the history. Works fine with `get_previous_command`
        method.

        :param self: self parameter for class
        :return: previous command.
        :rtype: Any | Literal ['']
        """
        if self._history and self._history_index < len(self._history) - 1:
            self._history_index += 1
            return self._history[self._history_index]
        self._history_index = len(self._history)
        return ""

    def run_command(self, cmd_list):
        """
        Runs a command as a list and returns its output.
        If the command prints to stdout or stderr, it will be captured and returned.
        """
        try:
            result = subprocess.run(
                cmd_list, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            output = result.stdout.strip()
            return output if output else "Command executed, no output."
        except Exception as e:
            return f"Execution Error no.300: {e}"

    def internet_exists(self):
        try:
            socket.create_connection(("pypi.org", 443), timeout=3)
            return True
        except OSError:
            return False

    # -------------------- Help --------------------
    def do_help(self, arg):
        """
        Help: help    Provides detailed guidance about available commands and topics
        Usage:
            help <command_or_topic>
        Parameters:
            <command_or_topic>   The name of the command, function, or topic you want help about.
                                 Example: 'changedir', 'pacman', 'fileinfo', 'syntax'
        Description:
            The 'help' command is designed to give you a complete overview and usage instructions
            for any command available in this terminal environment. It includes:
              - Purpose and functionality of the command
              - Syntax and usage patterns
              - Parameters and their explanations
              - Optional parameters and default values
              - Examples showing practical use
              - Possible output and return values
              - Error codes and explanations
              - Related or hot-topic commands
        Features:
            1. **Command-level documentation**:
               - Displays all details about the specified command including usage and parameters.
            2. **Error guidance**:
               - Shows the specific error codes associated with the command and their explanations.
            3. **Examples**:
               - Provides one or more working examples showing how to execute the command correctly.
            4. **Cross-references**:
               - Suggests related commands or topics to explore further for more advanced tasks.
        Output:
            - A formatted text block detailing all aspects of the requested command.
            - If no command is specified, lists all available commands with short descriptions.
        Examples:
            help changedir
        """
        if arg != "":
            import io

            buf = io.StringIO()
            old_stdout = self.stdout
            self.stdout = buf
            try:
                super().do_help(arg)
            finally:
                self.stdout = old_stdout
            result = buf.getvalue()
            return result if result else f"No help available for '{arg}'."
        else:
            return HELP

    # -------------------- All Commands --------------------
    def do_commands(self, arg):
        """
        Help: allcommands -- display all PromptX commands
        """
        if arg != 0:
            return "Error 0: Usage: commands"
        return ALL_COMMANDS

    # -------------------- Changedir --------------------
    def do_changedir(self, arg):
        """
        Help: changedir   -- changes the current working directory
        Usage:
            changedir     --path=direcotry_path
        Parameters:
            --path        path to the new directory
        Output:
            If the path to the new directory exists, the screen prompt of the user will be
            changed to match the new directory's path
        Errors:
            Error 1: Exception occured
            Error 2: No path provided
        Hot-topic commands:
            clearhistory, help
        """
        args = self.parse_args(arg)
        path = args.get("path", None)
        if not path:
            return "Error 2: You must provide a path."
        try:
            os.chdir(path)
            self.currentDir = os.getcwd()
            self.prompt = f"{self.currentDir}>>> "
            return f"Changed directory to {self.currentDir}"
        except Exception as e:
            return f"Error 1: {e}"

    # -------------------- Clear History --------------------
    def do_clearhistory(self, arg=None):
        """
        Help: clearhistory   -- clears previously used commands history
        Usage:
            clearhistory
        Output:
            - The commands history dictionary will be cleaned, so up and down arrows
              to access previously used commands will not function
            - A message (Command history cleared) will be shown after successful cleaning
        Hot-topic commands:
            help
        """
        self._history.clear()
        self._history_index = None
        return "Command history cleared."

    # -------------------- Clone --------------------
    def do_clone(self, arg):
        """
        Help: clone   -- clones the specifed file (copy) from src to dst
        Usage:
            clone --source=<source_file> --destination=<destination_file_or_dir>
        Parameters:
            --source        file source-path
            --destination   file destination-path
        Output:
            - File will be copied from source to destination
            - An end message will be displayed
        Errors:
            Error 3: No source or destination are provided
            Error 4: Destination directory does not exist
            Error 5: Source directory does not exist
            Error 6: Exception error
        Hot-topic commands:
            clearhistory, help
        """
        args = self.parse_args(arg)
        source = args.get("source", None)
        destination = args.get("destination", None)
        if not source or not destination:
            return "Error 3: You must provide --source=<source_file> and --destination=<destination_file_or_dir>"
        try:
            if not os.path.isfile(source):
                return f"Error 5: Source file '{source}' does not exist."
            if os.path.isdir(destination):
                file_name = os.path.basename(source)
                destination = os.path.join(destination, file_name)
            dest_dir = os.path.dirname(destination)
            if dest_dir and not os.path.exists(dest_dir):
                return f"Error 4: Destination directory '{dest_dir}' does not exist."
            with open(source, "rb") as src:
                data = src.read()
            with open(destination, "wb") as dst:
                dst.write(data)
            return f"File cloned from '{source}' to '{destination}'."
        except Exception as e:
            return f"Error 6: {e}"

    # -------------------- Copydir --------------------
    def do_copydir(self, arg):
        """
        Help: copydir   copies a certain directory from source to destination
        Usage:
            copydir --source=<source_workspace> --destination=<destination_path>
        Parameters:
            --source        directory source-path
            --destination   directory destination-path
        Output:
            - Directory will be copied from source to destination
            - An end message will be displayed
        Errors:
            Error 7: File existing error
            Error 8: File not found error
            Error 9: Permission error
            Error 10: Exception error
        Hot-topic commands:
            clearhistory, help
        """
        args = self.parse_args(arg)
        source = os.path.abspath(args.get("source"))
        destination = os.path.abspath(args.get("destination"))
        try:
            shutil.copytree(src=source, dst=destination)
            return (
                f"{source} copied to {destination} successfully!"
                f"\nCheck 'peek' to see {destination} content or 'changedir' to move to {destination}"
            )
        except FileExistsError:
            return f"Error 7: Destination '{destination}' already exists. Copy aborted."
        except FileNotFoundError:
            return f"Error 8: Source '{source}' does not exist."
        except PermissionError:
            return f"Error 9: Permission denied while accessing source or destination."
        except Exception as e:
            return f"Error 10: {e}"

    # -------------------- Cpuinfo --------------------
    def do_cpuinfo(self, arg=None):
        """
        Help: cpuinfo   Returns the underlying hardware processor's information
        Usage:
            cpuinfo
        Output:
            - CPU information will be displayed on terminal's screen
        Hot-topic commands:
            clearhistory, help
        """
        return f"CPU: {platform.processor()}"

    # -------------------- Date ---------------------
    def do_date(self, arg=None):
        """
        Help: date:
        Usage:
            date
        Output:
            - Current date and time is displayed
        Hot-topic commands:
            clearhistory, help
        """
        current_date = datetime.datetime.now()
        return (
            f"Current date: {current_date.date()}\n"
            f"Current time: {current_date.time()}\n"
            f"{current_date}"
        )

    # -------------------- Deletedir -------------------
    def do_deletedir(self, arg):
        """
        Help: deletedir    Deletes the current directory specified by a user
        If no path is given, it simply removes the current directory the terminal
        is represented at.

        Usage: deletedir --path=<path>     %% removes directory in <path>
               deletedir                   %% removes current working directory

        Output:
            - Removing a directory of files and folders
        Errors:
            - Privilage Error (42): Mixed exceptions provided by the operating system

        Hot-Topic Commands:
            erase, help
        """
        if not arg:
            path = os.getcwd()
        else:
            path = arg
        try:
            if not os.path.isdir(path):
                return f"Error 42: Path '{path}' is not a directory or does not exist."
            os.rmdir(path=path)
            return f"Directory '{path}' removed."
        except Exception as e:
            return f"Error 42: {e}"

    # -------------------- Diskinfo --------------------
    def do_diskinfo(self, arg):
        """
        Help: diskinfo: Returns the hard disk drive (HDD) information
        Usage:
            diskinfo [--path=<path>]
        Parameters:
            --path      Optional. Path to check disk usage for. Default is current directory
        Output:
            - Disk info (HDD) is displayed
        Errors:
            Error 43: Path does not exist
        Hot-topic commands:
            cpuinfo, meminfo, sysinfo, help
        """
        try:
            args = self.parse_args(arg) if arg else {}
            path = args.get("path", os.getcwd())
            if not os.path.exists(path):
                return f"Error 43: Path does not exist: {path}"
            usage = shutil.disk_usage(path)
            total = usage.total // (1024**3)
            used = usage.used // (1024**3)
            free = usage.free // (1024**3)
            percent = round((used / total) * 100, 2)
            return f"Disk info for {path}:\nTotal: {total} GB\nUsed: {used} GB\nFree: {free} GB\nUsage: {percent}%"
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Erase --------------------
    def do_erase(self, arg):
        """
        Help: erase   Deletes the specified file by location
        Usage:
            erase --file=<filename_or_path>
        Parameters:
            --file    file name or file path (if in another directory)
            default directory to be taken if only the name is provided
        Output:
            - File will be deleted
            - An end message will be displayed
        Errors:
            Error 11: File parameter not provided
            Error 12: File not found error
            Error 13: Exception error
        Hot-topic commands:
            clearhistory, help
        """
        args = self.parse_args(arg)
        filename = args.get("file", None)
        if not filename:
            return "Error 11: You must provide --file=<filename_or_path>"
        try:
            if not os.path.isfile(filename):
                return f"Error 12: File '{filename}' does not exist."
            os.remove(filename)
            return f"File '{filename}' has been deleted."
        except Exception as e:
            return f"Error 13: {e}"

    # -------------------- Find --------------------
    def do_find(self, arg):
        """
        Help: find    Searches for files matching patterns in destination
        Usage:
            find --file=<file_path>
        Parameters:
            --file       Path to the file to inspect. Must exist
        Output:
            File: <path>
            Size: <bytes>
            Created: <datetime>
            Modified: <datetime>
            Absolute Path: <full_path>
            Type: <file or directory>
            Readable: <True/False>
            Writable: <True/False>
        Errors:
            Error 14: File path is not provided
            Error 15: File path does not exist
            Error 16: Exception error
        Hot-topic commands:
            clearhistory, help
        """
        args = self.parse_args(arg)
        file_path = args.get("file")
        if not file_path:
            return "Error 14: You must provide --file=<file_path>"
        if not os.path.exists(file_path):
            return f"Error 15: File '{file_path}' does not exist."
        try:
            stats = os.stat(file_path)
            size = stats.st_size
            created = datetime.datetime.fromtimestamp(stats.st_ctime)
            modified = datetime.datetime.fromtimestamp(stats.st_mtime)
            abs_path = os.path.abspath(file_path)
            file_type = "Directory" if os.path.isdir(file_path) else "File"
            readable = os.access(file_path, os.R_OK)
            writable = os.access(file_path, os.W_OK)
            return (
                f"File: {file_path}\n"
                f"Absolute Path: {abs_path}\n"
                f"Type: {file_type}\n"
                f"Size: {size} bytes\n"
                f"Created: {created}\n"
                f"Modified: {modified}\n"
                f"Readable: {readable}\n"
                f"Writable: {writable}"
            )
        except Exception as e:
            return f"Error 16: {e}"

    # -------------------- File Info --------------------
    def do_fileinfo(self, arg):
        """
        Help: fileinfo   Shows metadata of the specified file
        Usage:
            fileinfo --file=<file>
        Parameters:
            --file
        Output:
            - Searches for specified patterns, returns them if any
        Errors:
            Error 14: Path not provided
            Error 15: Pattern not specified
            Error 16: Exception error
        Hot-topic commands:
            clearhistory, help
        """
        args = self.parse_args(arg)
        file_path = args.get("file", os.getcwd())
        if not file_path:
            return "Error: You must provide --file=<file_path>"
        if not os.path.isfile(file_path):
            if os.path.exists(file_path):
                return f"Error: '{file_path}' is a directory, not a file."
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

    # -------------------- Head --------------------
    def do_head(self, arg):
        """
        Help: head    Displays the first n lines of a specified file
        Usage:
            head --file=<file_path> [--lines=<n>]
        Parameters:
            --file       Path to the file to display
            --lines      Optional. Number of lines to show from the top of the file. Default is 10
        Output:
            Shows the first n lines of the file, line by line
        Errors:
            Error 17: File path not provided
            Error 18: File does not exist
            Error 19: Lines number must be integers only
            Error 20: Exception error
        Hot-topic commands:
            clearhistory, help
        """
        args = self.parse_args(arg)
        file_path = args.get("file", None)
        if not file_path:
            return "Error 17: You must provide --file=<file_path>"
        if not os.path.isfile(file_path):
            return f"Error 18: File '{file_path}' does not exist."
        try:
            lines = int(args.get("lines", 10))
        except ValueError:
            return "Error 19: --lines must be an integer."
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = [line.rstrip("\n") for line in islice(f, lines)]
            return "\n".join(content)
        except Exception as e:
            return f"Error 20: {e}"

    # -------------------- Here --------------------
    def do_here(self, arg=None):
        """
        Help: here    Displays the current working directory
        Usage:
            here
        Output:
            Shows the current working directory
        Hot-topic commands:
            clearhistory, help
        """
        return f"\ncurrent working directory: {os.getcwd()}"

    # -------------------- Makedir -----------------
    def do_makedir(self, arg):
        """
        Help: makedir    Creates a new directory with the specified path
        If no path specified, it creates an 'untitiled' directory at the given path
        Usage:
            makedir [--path=<path>] [--name=<name>]    %% Directory at the specified <path>
            makedir                                    %% Directory at current path with name 'untitled'
            makedir [--name=<name>]                    %% A Directory at the current path with <name>
            makedir [--path=<path>]                    %% Could be a directory with a path containing a name
                                                       %% or a directory with no name ('untitled' by default)
        Parameters:
            --path       Path to create the directory at
            --name       Name of the directory
        Output:
            Creates the directory at the specified location with the given content. Returns a success message including the full file path
        Errors:
            Error 44: Exception error
        Hot-topic commands:
            peek, head, tail, deletedir, help
        """
        args = self.parse_args(arg)
        path = args.get("path", os.getcwd())
        name = args.get("name", "untitled")
        target = os.path.join(path, name)
        try:
            if not os.path.exists(path):
                return f"Error 44: Path '{path}' does not exist."
            os.mkdir(target)
            return f"Directory '{target}' created."
        except Exception as e:
            return f"Error 44: {e}"

    # -------------------- Me --------------------
    def do_me(self, arg=None):
        """
        Help: me    Displays username
        Usage:
            me
        Output:
            Shows the user's name
        Hot-topic commands:
            clearhistory, help
        """
        return f"Username: {getpass.getuser()}"

    # -------------------- Meminfo --------------------
    def do_meminfo(self, arg=None):
        """
        Help: meminfo    Displays main memory information
        Usage:
            meminfo
        Output:
            Total usage
            Used
            Available
            Usage Percentage
        Hot-topic commands:
            clearhistory, help
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

    # -------------------- Mybox --------------------
    def do_mybox(self, arg=None):
        """
        Help: mybox    Displays the current hostname
        Usage:
            mybox
        Output:
            Shows the machine's host name
        Hot-topic commands:
            clearhistory, help
        """
        return f"Hostname: {socket.gethostname()}"

    # -------------------- Newbie --------------------
    def do_newbie(self, arg):
        """
        Help: newbie    Creates a new file with specified name, path, extension, and content
        Usage:
            newbie --name=<file_name> [--path=<directory_path>] [--ext=<file_extension>] [--content="<file_content>"]
        Parameters:
            --name       Name of the new file (without extension)
            --path       Optional. Directory path to create the file in. Default is the current working directory
            --ext        Optional. File extension. Default is ".txt"
            --content    Optional. Initial content to write into the file. Default is empty
        Output:
            Creates the file at the specified location with the given content. Returns a success message including the full file path
        Errors:
            Error 21: File name not provided
            Error 22: Invalid path or directory does not exist
            Error 23: Exception error
        Hot-topic commands:
            peek, head, tail
        """
        args = self.parse_args(arg)
        if "name" not in args:
            return "Error 21: You must provide --name=<file_name>"
        file_name = args["name"]
        file_path = args.get("path", os.getcwd())
        extension = args.get("ext", ".txt")
        content = args.get("content", "")
        try:
            if not os.path.exists(file_path):
                return f"Error 22: Path '{file_path}' does not exist."
            full_path = os.path.join(file_path, file_name + extension)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"File '{full_path}' has been created."
        except Exception as e:
            return f"Error 23: {e}"

    def do_pacman(self, arg):
        pass

    # -------------------- Peek --------------------
    def do_peek(self, arg):
        """
        Help: peek    Lists the contents of a specified directory
        Usage:
            peek [--number=<n>] [--path=<directory_path>]
        Parameters:
            --number    Optional. Number of items to list from the directory. Default is all items
                        (You can type -all to display all files in the directory "Optional")
            --path      Optional. Path to the directory to inspect. Default is the current working directory
        Output:
            Displays the names of files and folders in the specified directory, line by line.
            If --number is provided, only the first n items are shown.
        Errors:
            Error 31: Invalid directory path
        Examples:
            peek
            peek --number=5
            peek --number=10 --path="C:/Users/Username/Documents"
        Hot-topic commands:
            changedir, fileinfo, head, tail
        """
        args = self.parse_args(arg)
        number = args.get("number", None)
        custom_path = args.get("path", None)
        if number and os.path.isdir(number):
            custom_path = number
            number = None
        try:
            path_to_use = custom_path if custom_path else os.getcwd()
            if number in (None, "", "--all"):
                items = []
                with os.scandir(path_to_use) as it:
                    for entry in it:
                        items.append(entry.name)
                return f"Directory ({path_to_use}):\n" + "\n".join(items)
            n = int(number)
            items = []
            with os.scandir(path_to_use) as it:
                for i, entry in enumerate(it):
                    if i >= n:
                        break
                    items.append(entry.name)
            return f"Directory ({path_to_use}) - first {n} items:\n" + "\n".join(items)
        except Exception as e:
            return f"Error 31: {e}"

    # -------------------- Shift --------------------
    def do_shift(self, arg):
        """
        Help: shift    Moves a file from src to dst
        Usage:
            shift --old=<old_string> --new=<new_string> --path=<file_path>
        Parameters:
            --old       The string to be replaced in the file
            --new       The string to replace it with
            --path      Path to the file in which to perform the replacement
        Output:
            Modifies the file in-place, replacing all occurrences of --old with --new.
            Returns a success message indicating the file was updated.
        Errors:
            Error 32: File path not provided
            Error 33: File does not exist
            Error 34: File not found
            Error 35: Exception error
        Examples:
            shift --old="foo" --new="bar" --path="C:/path/to/file.txt"
            shift --old="temp" --new="permanent" --path="./data.txt"
        Hot-topic commands:
            peek, head, tail, fileinfo
        """
        args = self.parse_args(arg)
        old_string = args.get("old", None)
        new_string = args.get("new", None)
        file_path = args.get("path", None)
        if not old_string or not new_string or not file_path:
            return "Error 32: You must provide --old=<old_string> --new=<new_string> --path=<file_path>"
        try:
            if not os.path.isfile(file_path):
                return f"Error 33: File '{file_path}' does not exist."
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if old_string not in content:
                return f"Error 34: '{old_string}' was not found in '{file_path}'."
            updated_content = content.replace(old_string, new_string)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            return f"Shifted '{old_string}' → '{new_string}' in '{file_path}'."
        except Exception as e:
            return f"Error 35: {e}"

    # -------------------- Systeminfo --------------------
    def do_sysinfo(self, arg=None):
        """
        Help: sysinfo    Displays the currnet system information
        Usage:
            sysinfo
        Output:
            System info
            Release
            Version
            Architecture
        Hot-topic commands:
            cpuinfo, meminfo, diskinfo
        """
        try:
            system = platform.system()
            release = platform.release()
            version = platform.version()
            arch = platform.machine()
            return f"System: {system}\nRelease: {release}\nVersion: {version}\nArchitecture: {arch}"
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Tail --------------------
    def do_tail(self, arg):
        """
        Help: tail    Displays the last n lines of a specified file
        Usage:
            tail --file=<file_path> [--lines=<n>]
        Parameters:
            --file       Path to the file to display
            --lines      Optional. Number of lines to show from the end of the file. Default is 10
        Output:
            Shows the last n lines of the file, line by line
        Errors:
            Error 36: File path not provided
            Error 37: File does not exist
            Error 38: Lines number must be an integer
            Error 39: Exception errors
        Examples:
            tail --file=example.txt
            tail --file=example.txt --lines=5
        Hot-topic commands:
            head, peek, fileinfo
        """

        args = self.parse_args(arg)
        file_path = args.get("file", None)
        if not file_path:
            return "Error 36: You must provide --file=<file_path>"
        if not os.path.isfile(file_path):
            return f"Error 37: File '{file_path}' does not exist."
        try:
            lines = int(args.get("lines", 10))
        except ValueError:
            return "Error 38: Lines must be an integer"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                last_lines = deque(f, maxlen=lines)
            return "".join(last_lines)
        except Exception as e:
            return f"Error 39: {e}"

    def do_zip(self, arg):
        """
        Help: zip    Creates a zip archive from a file or directory
        Usage:
            zip --source=<file_or_directory> --destination=<zipfile>
        Parameters:
            --source       Path to the file or directory to archive
            --destination  Path to the output zip file
        Output:
            Creates a zip archive at the specified destination containing the source content
            Returns a success message with the archive path
        Errors:
            Error 40: Source or destination not provided
            Error 41: Source path does not exist
            Error 42: Exception occurred during zipping
        Examples:
            zip --source=./project --destination=project.zip
            zip --source=example.txt --destination=example.zip
        Hot-topic commands:
            unzip, peek, fileinfo
        """
        args = self.parse_args(arg)
        source = args.get("source")
        destination = args.get("destination")
        if not source or not destination:
            return "Error 40: You must provide --source=<file_or_dir> --destination=<zipfile>"
        if not os.path.exists(source):
            return f"Error 41: Source '{source}' does not exist."
        try:
            with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as z:
                if os.path.isdir(source):
                    for root, _, files in os.walk(source):
                        for f in files:
                            abs_path = os.path.join(root, f)
                            arcname = os.path.relpath(
                                abs_path, start=os.path.dirname(source)
                            )
                            z.write(abs_path, arcname)
                else:
                    z.write(source, os.path.basename(source))
            return f"Archive '{destination}' created from '{source}'."
        except Exception as e:
            return f"Error 42: {e}"

    # -------------------- Clear --------------------
    def do_clear(self, arg=None):
        """
        Help: clear    Clears the terminal screen
        Usage:
            clear
        Output:
            - All previous output is cleared from the terminal display
        Hot-topic commands:
            help
        """
        return None

    # -------------------- Download --------------------
    def do_download(self, arg):
        """
        Help: download    Downloads a file from a URL to the local filesystem
        Usage:
            download --url=<url> [--path=<destination_path>]
        Parameters:
            --url       URL of the file to download
            --path      Optional. Destination path to save the file. Default is current directory
        Output:
            Downloads the file from the specified URL and saves it to the destination path.
            Returns a success message with the file location.
        Errors:
            Error 50: URL not provided
            Error 51: Download failed - network or server error
        Hot-topic commands:
            ping, pacman, help
        """
        args = self.parse_args(arg)
        url = args.get("url")
        if not url:
            return "Error 50: You must provide --url=<url>"
        dest = args.get("path", os.getcwd())
        try:
            if os.path.isdir(dest):
                filename = url.split("/")[-1].split("?")[0]
                dest = os.path.join(dest, filename)
            urllib.request.urlretrieve(url, dest)
            return f"Downloaded '{url}' to '{dest}'."
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            return f"Error 51: Download failed: {e}"

    # -------------------- Echo --------------------
    def do_echo(self, arg):
        """
        Help: echo    Prints the given text to the terminal output
        Usage:
            echo <text>
        Parameters:
            <text>      The text to display. Enclose in quotes if it contains spaces
        Output:
            Repeats the provided text back to the terminal
        Hot-topic commands:
            help
        """
        return arg if arg else ""

    # -------------------- Env --------------------
    def do_env(self, arg=None):
        """
        Help: env    Displays all environment variables
        Usage:
            env
        Output:
            Lists all environment variables and their values, one per line
        Hot-topic commands:
            sysinfo, me, help
        """
        try:
            lines = [f"{k}={v}" for k, v in sorted(os.environ.items())]
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    # -------------------- History --------------------
    def do_history(self, arg=None):
        """
        Help: history    Displays the recently executed commands history
        Usage:
            history
        Output:
            Shows all previously executed commands in order, each prefixed by its index
        Hot-topic commands:
            clearhistory, help
        """
        if not self._history:
            return "No commands in history."
        lines = [f"{i:4d}  {cmd}" for i, cmd in enumerate(self._history, 1)]
        return "\n".join(lines)

    # -------------------- Kill --------------------
    def do_kill(self, arg):
        """
        Help: kill    Terminates a running process by its PID
        Usage:
            kill --pid=<process_id> [--force]
        Parameters:
            --pid       Process ID of the process to terminate
            --force     Optional. Force kill the process (SIGKILL on Unix)
        Output:
            Sends a termination signal to the specified process.
            Returns a success or error message.
        Errors:
            Error 52: PID not provided
            Error 53: Process does not exist
            Error 54: Permission denied
        Hot-topic commands:
            ps, help
        """
        args = self.parse_args(arg)
        pid = args.get("pid")
        if not pid:
            return "Error 52: You must provide --pid=<process_id>"
        try:
            pid = int(pid)
            sig = signal.SIGKILL if "force" in args else signal.SIGTERM
            os.kill(pid, sig)
            return f"Process {pid} terminated."
        except ValueError:
            return "Error 52: PID must be a valid integer."
        except ProcessLookupError:
            return f"Error 53: Process '{pid}' does not exist."
        except PermissionError:
            return f"Error 54: Permission denied to kill process '{pid}'."
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Ping --------------------
    def do_ping(self, arg):
        """
        Help: ping    Tests network connectivity to a remote host
        Usage:
            ping --host=<hostname_or_ip> [--count=<n>]
        Parameters:
            --host      Hostname or IP address to ping
            --count     Optional. Number of ping requests to send. Default is 4
        Output:
            Sends ICMP echo requests to the specified host and returns the results.
        Errors:
            Error 55: Host not provided
            Error 56: Ping command failed
        Hot-topic commands:
            download, help
        """
        args = self.parse_args(arg)
        host = args.get("host")
        if not host:
            return "Error 55: You must provide --host=<hostname_or_ip>"
        count = args.get("count", "4")
        try:
            param = "-n" if sys.platform == "win32" else "-c"
            result = subprocess.run(
                ["ping", param, str(count), host],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
            )
            output = result.stdout.strip()
            return output if output else f"Ping to '{host}' completed."
        except subprocess.TimeoutExpired:
            return f"Error 56: Ping to '{host}' timed out."
        except FileNotFoundError:
            return "Error 56: Ping command not found on this system."
        except Exception as e:
            return f"Error 56: {e}"

    # -------------------- Ps --------------------
    def do_ps(self, arg=None):
        """
        Help: ps    Lists currently running processes on the system
        Usage:
            ps
        Output:
            Displays a table of running processes with PID, name, and status
        Hot-topic commands:
            kill, sysinfo, help
        """
        try:
            processes = []
            for proc in psutil.process_iter(["pid", "name", "status"]):
                try:
                    pinfo = proc.info
                    processes.append(
                        f"{pinfo['pid']:>8d}  {pinfo['name']:<30s}  {pinfo['status'] or 'running'}"
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            header = f"{'PID':>8s}  {'NAME':<30s}  {'STATUS'}"
            lines = [header, "-" * 60] + sorted(
                processes, key=lambda x: int(x.split()[0])
            )
            return "\n".join(lines[:100])
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Quit --------------------
    def do_quit(self, arg=None):
        """
        Help: quit    Exits the terminal environment
        Usage:
            quit
        Output:
            Prompts the user to close the terminal panel
        Hot-topic commands:
            help
        """
        return "Type 'close' or use the close button to close the terminal panel."

    # -------------------- Rename --------------------
    def do_rename(self, arg):
        """
        Help: rename    Renames a file or directory
        Usage:
            rename --source=<current_name> --destination=<new_name>
        Parameters:
            --source       Current name or path of the file/directory
            --destination  New name or path for the file/directory
        Output:
            Renames the specified file or directory from source to destination.
            Returns a success message with both old and new names.
        Errors:
            Error 57: Source or destination not provided
            Error 58: Source does not exist
            Error 59: Destination already exists
            Error 60: Permission denied
        Hot-topic commands:
            shift, clone, help
        """
        args = self.parse_args(arg)
        source = args.get("source")
        destination = args.get("destination")
        if not source or not destination:
            return "Error 57: You must provide --source=<current_name> --destination=<new_name>"
        try:
            if not os.path.exists(source):
                return f"Error 58: Source '{source}' does not exist."
            if os.path.exists(destination):
                return f"Error 59: Destination '{destination}' already exists."
            os.rename(source, destination)
            return f"Renamed '{source}' to '{destination}'."
        except PermissionError:
            return f"Error 60: Permission denied."
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Unzip --------------------
    def do_unzip(self, arg):
        """
        Help: unzip    Extracts a zip archive to a specified directory
        Usage:
            unzip --source=<zipfile> [--destination=<output_dir>]
        Parameters:
            --source       Path to the zip file to extract
            --destination  Optional. Directory to extract contents into.
                           Default is the current working directory
        Output:
            Extracts all files from the zip archive into the destination directory.
            Returns a success message with the extraction location.
        Errors:
            Error 61: Source not provided
            Error 62: Source file does not exist
            Error 63: Not a valid zip file
            Error 64: Exception during extraction
        Examples:
            unzip --source=archive.zip
            unzip --source=archive.zip --destination=./extracted
        Hot-topic commands:
            zip, peek, help
        """
        args = self.parse_args(arg)
        source = args.get("source")
        if not source:
            return "Error 61: You must provide --source=<zipfile>"
        if not os.path.isfile(source):
            return f"Error 62: File '{source}' does not exist."
        destination = args.get("destination", os.getcwd())
        try:
            if not os.path.exists(destination):
                os.makedirs(destination, exist_ok=True)
            with zipfile.ZipFile(source, "r") as z:
                z.extractall(destination)
            return f"Extracted '{source}' to '{destination}'."
        except zipfile.BadZipFile:
            return f"Error 63: '{source}' is not a valid zip file."
        except Exception as e:
            return f"Error 64: {e}"

    # -------------------- Uptime --------------------
    def do_uptime(self, arg=None):
        """
        Help: uptime    Displays how long the system has been running
        Usage:
            uptime
        Output:
            Shows the system uptime in days, hours, minutes, and seconds
        Hot-topic commands:
            sysinfo, date, help
        """
        try:
            uptime_seconds = datetime.datetime.now().timestamp() - psutil.boot_time()
            days, remainder = divmod(int(uptime_seconds), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
            if minutes > 0:
                parts.append(f"{minutes}m")
            parts.append(f"{seconds}s")
            return f"Uptime: {' '.join(parts)}"
        except Exception as e:
            return f"Error: {e}"

    # -------------------- Whoami --------------------
    def do_whoami(self, arg=None):
        """
        Help: whoami    Displays the current username
        Usage:
            whoami
        Output:
            Shows the username of the currently logged-in user
        Hot-topic commands:
            me, mybox, help
        """
        return getpass.getuser()
