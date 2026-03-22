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

────────────────────────────────────────────────────────────────────────────────────────────────
                        DREAMSTUDIO IDE — PROMPT-X INTERACTIVE SHELL                 
                                    © EX Technologies
────────────────────────────────────────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────────────────────────────────────────
COMMAND INDEX:
• Display help documentation:              help
• Exit terminal environment:               quit

────────────────────────────────────────────────────────────────────────────────────────────────
NOTE:
All command inputs are processed sequentially by the terminal's
core interpreter. Invalid or malformed syntax may result in
undefined behavior or ignored operations.
────────────────────────────────────────────────────────────────────────────────────────────────

A DreamStudio commands shell powered by command-type language 'Prompt-X'
Prompt-X is a one-line shell command language for executing various
system level commands, and various input/output user commands.

Below is a detailed list of available documented commands:

changedir       Changes current workspace directoy
clear           Clears terminal screen
clearhistory    Clears the commands history (with errors commands)
clone           Clones (Copies) a file from source to destination
copydir         Copies files inside a directory recursively
cpuinfo         Shows CPU related info
date            Shows current date and time
deletedir       Deletes the specified directory by path
diskinfo        Shows HDD related info
download
echo
env
erase           Deletes the specified file
find            Searches file matching patterns in destination
fileinfo        Shows files info
head            Shows first few lines of a file
help            Documentation Help of a specific command or topic
here            Shows current working directory
history
kill
makedir         Creates a new directory at the specified location
me              Shows info about the system
meminfo         Shows memory related info
mybox           Shows host name
newbie          Creates a new file
pacman          Universal language package manager (ULPM)
peek            Lists the content of a specific directory
ping
ps
rename
shift           Moves a file from source to destination
sysinfo         Shows system related info
tail            Shows last few lines of a file
unzip
uptime
whoami
zip             Packages a file into a .zip format

────────────────────────────────────────────────────────────────────────────────────────────────
                                    END OF DOCUMENTATION
────────────────────────────────────────────────────────────────────────────────────────────────
"""

pacman_real_commands = {
    "python": {
        "install": "pip install",
        "uninstall": "pip uninstall",
        "update": "pip install --upgrade",
        "upgrade": "pip install --upgrade",
        "remove": "pip uninstall",
        "search": "pip search",
        "info": "pip show",
        "list": "pip list",
        "clean": "pip cache purge",
        "repair": "pip check",
    },
    "javascript": {
        "install": "npm install",
        "uninstall": "npm uninstall",
        "update": "npm update",
        "upgrade": "npm update",
        "remove": "npm uninstall",
        "search": "npm search",
        "info": "npm info",
        "list": "npm list",
        "clean": "npm cache clean --force",
        "repair": "npm audit fix",
    },
    "java": {
        "install": "mvn install",
        "uninstall": "mvn dependency:purge-local-repository",
        "update": "mvn versions:use-latest-versions",
        "upgrade": "mvn versions:use-latest-releases",
        "remove": "mvn dependency:purge-local-repository",
        "search": "mvn dependency:resolve",
        "info": "mvn dependency:tree",
        "list": "mvn dependency:list",
        "clean": "mvn clean",
        "repair": "mvn dependency:analyze",
    },
    "c": {
        "install": "vcpkg install",
        "uninstall": "vcpkg remove",
        "update": "vcpkg update",
        "upgrade": "vcpkg upgrade",
        "remove": "vcpkg remove",
        "search": "vcpkg search",
        "info": "vcpkg info",
        "list": "vcpkg list",
        "clean": "vcpkg remove --outdated",
        "repair": "vcpkg regenerate",
    },
    "cpp": {
        "install": "vcpkg install",
        "uninstall": "vcpkg remove",
        "update": "vcpkg update",
        "upgrade": "vcpkg upgrade",
        "remove": "vcpkg remove",
        "search": "vcpkg search",
        "info": "vcpkg info",
        "list": "vcpkg list",
        "clean": "vcpkg remove --outdated",
        "repair": "vcpkg regenerate",
    },
    "csharp": {
        "install": "dotnet add package",
        "uninstall": "dotnet remove package",
        "update": "dotnet list package --outdated",
        "upgrade": "dotnet add package --version latest",
        "remove": "dotnet remove package",
        "search": "nuget search",
        "info": "nuget list",
        "list": "dotnet list package",
        "clean": "nuget locals all -clear",
        "repair": "nuget restore",
    },
    "ruby": {
        "install": "gem install",
        "uninstall": "gem uninstall",
        "update": "gem update",
        "upgrade": "gem update",
        "remove": "gem uninstall",
        "search": "gem search",
        "info": "gem info",
        "list": "gem list",
        "clean": "gem cleanup",
        "repair": "gem check",
    },
    "go": {
        "install": "go install",
        "uninstall": "go clean -i",
        "update": "go get -u",
        "upgrade": "go get -u",
        "remove": "go clean -i",
        "search": "go list -m all",
        "info": "go list -m <package>",
        "list": "go list -m all",
        "clean": "go clean -modcache",
        "repair": "go mod tidy",
    },
    "php": {
        "install": "composer require",
        "uninstall": "composer remove",
        "update": "composer update",
        "upgrade": "composer update",
        "remove": "composer remove",
        "search": "composer search",
        "info": "composer show <package>",
        "list": "composer show",
        "clean": "composer clear-cache",
        "repair": "composer validate",
    },
    "rust": {
        "install": "cargo install",
        "uninstall": "cargo uninstall",
        "update": "cargo update",
        "upgrade": "cargo install --force",
        "remove": "cargo uninstall",
        "search": "cargo search",
        "info": "cargo info <package>",
        "list": "cargo install --list",
        "clean": "cargo clean",
        "repair": "cargo check",
    },
    "kotlin": {
        "install": "gradle build",
        "uninstall": "gradle clean",
        "update": "gradle --refresh-dependencies",
        "upgrade": "gradle --refresh-dependencies",
        "remove": "gradle clean",
        "search": "gradle dependencies",
        "info": "gradle dependencies",
        "list": "gradle tasks",
        "clean": "gradle clean",
        "repair": "gradle build --refresh-dependencies",
    },
    "swift": {
        "install": "swift package update",
        "uninstall": "swift package clean",
        "update": "swift package update",
        "upgrade": "swift package update",
        "remove": "swift package clean",
        "search": "swift package show-dependencies",
        "info": "swift package show-dependencies",
        "list": "swift package show-dependencies",
        "clean": "swift package clean",
        "repair": "swift build",
    },
    "r": {
        "install": "install.packages",
        "uninstall": "remove.packages",
        "update": "update.packages",
        "upgrade": "update.packages",
        "remove": "remove.packages",
        "search": "available.packages",
        "info": "packageDescription",
        "list": "installed.packages",
        "clean": "remove.packages(older_versions)",
        "repair": "check.packages",
    },
    "dart": {
        "install": "dart pub add",
        "uninstall": "dart pub remove",
        "update": "dart pub upgrade",
        "upgrade": "dart pub upgrade",
        "remove": "dart pub remove",
        "search": "dart pub search",
        "info": "dart pub info <package>",
        "list": "dart pub list",
        "clean": "dart pub cache repair",
        "repair": "dart pub get",
    },
    "haskell": {
        "install": "cabal install",
        "uninstall": "cabal uninstall",
        "update": "cabal update",
        "upgrade": "cabal install --upgrade-dependencies",
        "remove": "cabal uninstall",
        "search": "cabal list",
        "info": "cabal info <package>",
        "list": "cabal list --installed",
        "clean": "cabal clean",
        "repair": "cabal check",
    },
    "perl": {
        "install": "cpan install",
        "uninstall": "cpan uninstall",
        "update": "cpan upgrade",
        "upgrade": "cpan upgrade",
        "remove": "cpan uninstall",
        "search": "cpan search",
        "info": "cpan info <package>",
        "list": "cpan list",
        "clean": "cpan clean",
        "repair": "cpan test",
    },
}

import re
import os
import cmd
import sys
import socket
import psutil
import shutil
import getpass
import zipfile
import datetime
import platform
import subprocess
import tkinter as tk
import customtkinter as ctk
from itertools import islice
from collections import deque


# ---------------- Redirect stdout to GUI ----------------
class GUIStdout:
    """
    Redirects the standard output of the command line interface into
    custom-tkinter's textbox. Works by writing the text into the
    textbox, and moving the cursor's position into the end of the line.
    The other method `flush` is an empty method for instantly flushing
    the textbox.
    """

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
    """
    Command-Line class inherited from `cmd` library.
    Inside, it has the backend and logic structure for generating
    responses of commands. It makes usage of the `cmd` library by
    generating a `do_command` function for each typed function on
    the user's screen. The text enters from the `GUIStdout` class
    and leaves towards.
    """

    def __init__(self, stdout=None):
        super().__init__(stdout=stdout)
        self.currentDir = os.getcwd()
        self.prompt = f"{self.currentDir}>>> "
        self._history = []
        self._history_index = None
        self.commands_list = [
            "changedir",
            "clearhistory",
            "clear",
            "clone",
            "copydir",
            "cpuinfo",
            "date",
            "diskinfo",
            "erase",
            "find",
            "fileinfo",
            "head",
            "here",
            "help",
            "me",
            "meminfo",
            "mybox",
            "newbie",
            "pacman",
            "peek",
            "quit",
            "shift",
            "sysinfo",
            "tail",
            "zip",
        ]

        self.internet_required_commands = [
            "install",
            "update",
            "upgrade",
            "search",
            "info",
        ]

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
            return super().do_help(arg)
        else:
            return logo_ascii

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
        try:
            if os.path.isdir(arg):
                os.rmdir(path=arg)
            else:
                os.rmdir(path=path)
        except Exception as e:
            return f"Error 42: {e}"

    # -------------------- Diskinfo --------------------
    def do_diskinfo(self, path):
        """
        Help: diskinfo: Returns the hard disk drive (HDD) information
        Usage:
            diskinfo
        Output:
            - Disk info (HDD) is displayed
        Hot-topic commands:
            clearhistory, help
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
                return f"""Disk info for {path}:
                Total: {total} GB
                Used: {used} GB
                Free: {free} GB
                Usage: {percent}%"""
            else:
                return f"Error: Path does not exist: {path}"
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
        Help: fileinfo    Displays detailed information about a specific file
        Usage:
            fileinfo --file=<file_path>
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
        file_path = args.get("file", os.getcwd(), None)
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
        if arg:
            pass

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
        """
        Help: pacman    A universal package manager for programming languages
        Usage:
            pacman --language=<language> --command=<command> [--package=<package_name>] [--parameters=<parameters>]
        Parameters:
            --language     Name of the programming language. Use 'help pacman_languages' to see available languages
            --command      Action to perform. Valid options:
                           install, uninstall, update, upgrade, remove, search, info, list, clean, repair
            --package      Optional. Name of the package to operate on (required for certain commands)
            --parameters   Optional. Special parameters:
                           'yes'  - automatically confirm prompts if required
                           'all'  - include all related package files
        Output:
            Performs the requested operation on the specified language/package and returns success or error messages
        Errors:
            Error 24: Language not specified or invalid
            Error 25: Command not specified or invalid
            Error 26: Package not specified when required
            Error 27: Unsupported language
            Error 28: Unsupported command
            Error 29: No internet connection or connection not stable
            Error 30: Exception error
        Hot-topic commands:
            pacman_languages, download
        """
        args = self.parse_args(arg)
        language = args.get("language")
        command = args.get("command")
        package = args.get("package")
        parameters = args.get("parameters", "").lower()

        if not language:
            return "Error 24: --language is required"
        if language not in pacman_real_commands:
            return f"Error 27: Unsupported language: {language}"
        if not command:
            return "Error 25: --command is required"
        if command not in pacman_real_commands[language]:
            return (
                f"Error 28: Unsupported command '{command}' for language '{language}'"
            )

        commands_require_package = [
            "install",
            "uninstall",
            "update",
            "upgrade",
            "remove",
            "info",
            "search",
        ]
        if command in commands_require_package and not package:
            return "Error 26: --package is required for this command"
        real_cmd = pacman_real_commands[language][command]
        if language == "python":
            cmd_list = [sys.executable, "-m", "pip"]
            cmd_list.extend(real_cmd.split()[1:])
            if package:
                cmd_list.append(package)
            if parameters == "yes" and command in [
                "install",
                "uninstall",
                "upgrade",
                "remove",
            ]:
                cmd_list.append("-y")
        else:
            cmd_list = real_cmd.split()
            if package:
                cmd_list.append(package)
            if parameters == "yes":
                cmd_list.append("-y")
            elif parameters == "all":
                cmd_list.append("--all")
        if command in self.internet_required_commands and not self.internet_exists():
            return "Error 29: No internet connection"
        try:
            output = self.run_command(cmd_list)
            return output
        except Exception as e:
            return f"Error 30: {e}"

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
            all_items = os.listdir(path_to_use)
            if number in (None, "", "--all"):
                return f"Directory ({path_to_use}):\n" + "\n".join(all_items)
            n = int(number)
            return f"Directory ({path_to_use}) - first {n} items:\n" + "\n".join(
                all_items[:n]
            )
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


# ---------------- GUI Shell ----------------
class PromptXShell(ctk.CTkFrame):
    """
    The GUI class housing a custom-tkinter's frame with a textbox inside.
    It hosts the area where the user should type-in commands. Behaves like a
    normal TUI tool that can be used inside DreamStudio's main terminal window.
    """

    def __init__(self, main_app=None, status_button=None):
        super().__init__(main_app)

        # Platform specific scaling:
        if platform.system() == "Windows":
            pass
        elif platform.system() == "Linux":
            ctk.set_window_scaling(1.25)
        else: # Empty for now for XOS
            pass


        self.main_app = main_app
        self.status_button = status_button
        self._corner_radius = 0
        self._border_color = "#5E5E5E"
        self._border_width = 1

        self.mode = ctk.get_appearance_mode()
        self.configure(fg_color="#1C1C1C" if self.mode == "Dark" else "#D4D4D4")

        if self.status_button:
            self.status_button.configure(text="Terminal Opened")

        self.place(x=0, y=0, relwidth=1, relheight=1)

        self.textbox = ctk.CTkTextbox(
            self,
            corner_radius=0,
            font=("Consolas", 13),
            text_color=["#1E1E1E", "#D4D4D4"],
            bg_color=["#606060", "#BABABA"],
            fg_color=["#F5F5F5", "#1E1E1E"],
            border_color="#5E5E5E",
            border_width=1,
        )
        self.textbox.place(x=0, y=0, relwidth=1, relheight=1)

        # ---------------- Tags ----------------
        self.textbox.tag_config("error", foreground="#FF5555")
        self.textbox.tag_config("command", foreground="#FFFC56")
        self.textbox.tag_config("prompt", foreground="#CECECE")
        self.textbox.tag_config("number", foreground="#79FFA5")
        self.textbox.tag_config("string", foreground="#6770B9")
        self.textbox.tag_config("filename", foreground="#FFA500")
        self.textbox.tag_config("path", foreground="#9E57AD")
        self.textbox.tag_config("subcommand", foreground="#FF8FD8")
        self.textbox.tag_config("language", foreground="#80936A")

        # ---------------- Internal state ----------------
        self.multiline_buffer = ""
        self.readonly_index = "1.0"

        # ---------------- Command shell ----------------
        self.cmd_shell = CommandLine(stdout=GUIStdout(self.textbox))

        # ---------------- Event bindings ----------------
        self.textbox.bind("<Return>", self.onEnter)
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
        """
        Inserts a prompt at the current cursor's location, a prompt consisting
        of the current working directory. It disables writing on the textbox
        accept last line where the current last prompt is inserted at.

        :param self: self parameter for class
        """
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.insert("end", f"{self.cmd_shell.currentDir}>>> ", "prompt")
        self.readonly_index = self.textbox.index("end-1c")
        self.textbox.mark_set("insert", self.readonly_index)
        self.textbox.see("end")

    # ---------------- Key & Selection Control ----------------
    def onKeyPress(self, event):
        """
        Checks what is the key press currently typed by the user. If it is `delete`
        or `backspace` it does nothing, disabling users from editing previous text.
        """
        if self.textbox.compare("insert", "<", self.readonly_index):
            self.textbox.mark_set("insert", self.readonly_index)
        if event.keysym in ("BackSpace", "Delete"):
            if self.textbox.compare("insert", "<=", self.readonly_index):
                return "break"

    def onClick(self, event):
        """ """
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
        highlight_dict = {
            "Usage:": "#2900F7",
            "Parameters:": "#2900F7",
            "Description:": "#2900F7",
            "Features:": "#2900F7",
            "Output:": "#00F736",
            "Examples:": "#00F736",
            "Hot-topic commands:": "#F3F700",
            "Errors:": "#F70000",
            "COMMAND INDEX:": "#2900F7",
            "NOTE:": "#2900F7",
            "END OF DOCUMENTATION": "#2900F7",
            "© EX Technologies": "#2900F7",
            "DREAMSTUDIO IDE — PROMPT-X INTERACTIVE SHELL": "#2900F7",
            "*** No help on": "#FF8C00",
            "*** Unknown syntax:": "#FF0000",
            "Requirement already satisfied:": "#00F736",
            "WARNING": "#FF8C00",
            "[notice]": "#F3F700",
            "ERROR": "red",
            "error:": "red",
            "Warning:": "#FF8C00",
            "[INFO]": "blue",
            "BUILD SUCCESS": "#00F736",
            "Compiling": "#00F736",
            "added": "#00F736",
            "[WinError 2]": "red",
            "(venv)": "#00F736",
        }

        if not line.strip():
            return False

        if line.strip().lower() == "clear":
            self.textbox.configure(state=ctk.NORMAL)
            self.textbox.delete("1.0", "end")
            self.insert_prompt()
            return True

        try:
            result = self.cmd_shell.onecmd(line.lower())

            if result is True:
                self.print_output("\nShell stopped.\n", "output")
                self.after(2000)
                self.destroy()
            elif isinstance(result, str):
                if result.lower().startswith("error"):
                    self.print_output(
                        f"\n{result}\n",
                        "dark_mode" if self.mode == "dark" else "light_mode",
                    )
                else:
                    self.print_output(
                        f"\n{result}\n",
                        "dark_mode" if self.mode == "dark" else "light_mode",
                    )
            for word, color in highlight_dict.items():
                self.highlight_word(word, color=color)

        except Exception as e:
            self.print_output("\nError: " + str(e) + "\n", "error")

    # ---------------- Events ----------------
    def onEnter(self, event):
        user_input = self.textbox.get(self.readonly_index, "end-1c").strip()

        if self.multiline_buffer:
            self.multiline_buffer += "\n" + user_input
            prompt_inserted = self.execute_command(self.multiline_buffer)
            self.multiline_buffer = ""
        else:
            prompt_inserted = self.execute_command(user_input)

        if not prompt_inserted:
            self.textbox.insert("end", "\n")
            self.insert_prompt()
        return "break"

    # ---------------- Output ----------------
    def print_output(self, text, tag=None):
        self.textbox.configure(state=ctk.NORMAL)
        self.textbox.insert("end", text, tag)
        self.textbox.see("end")
        self.textbox.configure(state=ctk.DISABLED)

    def highlight_syntax(self):
        # Remove previous tags
        for tag in [
            "command",
            "number",
            "string",
            "filename",
            "path",
            "subcommand",
            "language",
        ]:

            self.textbox.tag_remove(tag, self.readonly_index, "end")

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
        for match in re.finditer(r'(["\'])(?:\\.|(?!\1).)*\1', user_input):
            start_index = f"{self.readonly_index} + {match.start()}c"
            end_index = f"{self.readonly_index} + {match.end()}c"
            self.textbox.tag_add("string", start_index, end_index)

        # Filenames
        for match in re.finditer(
            r"\b[\w\-]+\.(txt|py|log|csv|cpp|cs|css|html|pyc|c|h|docx|ppt|pptx)\b",
            user_input,
        ):
            start_index = f"{self.readonly_index} + {match.start()}c"
            end_index = f"{self.readonly_index} + {match.end()}c"
            self.textbox.tag_add("filename", start_index, end_index)

        # Paths
        for match in re.finditer(r"([A-Za-z]:\\|/)[\w\s/\\.-]+", user_input):
            start_index = f"{self.readonly_index} + {match.start()}c"
            end_index = f"{self.readonly_index} + {match.end()}c"
            self.textbox.tag_add("path", start_index, end_index)

        # Subcommands
        for match in re.finditer(
            r"\b(install|uninstall|update|upgrade|remove|search|info|list|clean|repair)\b",
            user_input,
        ):
            start_index = f"{self.readonly_index} + {match.start()}c"
            end_index = f"{self.readonly_index} + {match.end()}c"
            self.textbox.tag_add("subcommand", start_index, end_index)

        # Languages
        for match in re.finditer(
            r"\b(" + "|".join(pacman_real_commands.keys()) + r")\b", user_input
        ):
            start_index = f"{self.readonly_index} + {match.start()}c"
            end_index = f"{self.readonly_index} + {match.end()}c"
            self.textbox.tag_add("language", start_index, end_index)

    def highlight_word(self, word, color="blue"):
        """
        Highlights all occurrences of a word in the CTkTextbox.
        If the word starts with '***', the leading '***' is ignored for display.
        """

        textbox = self.textbox
        textbox.configure(state=ctk.NORMAL)

        display_word = word
        search_word = word
        if word.startswith("***"):
            display_word = word.lstrip()[3:].lstrip()
            search_word = display_word

        tag_name = f"tag_{display_word.replace(' ', '_')}"

        textbox.tag_config(tag_name, foreground=color)

        start = "1.0"
        while True:
            pos = textbox.search(search_word, start, stopindex="end")
            if not pos:
                break
            end = f"{pos}+{len(search_word)}c"
            textbox.tag_add(tag_name, pos, end)
            start = end

        textbox.configure(state=ctk.DISABLED)

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
