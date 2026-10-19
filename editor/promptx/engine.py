HELP = r"""
DREAMSTUDIO IDE — PROMPT-X INTERACTIVE SHELL
(c) EXcellent TechStacks

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
ip_scan         Scans the local network for connected devices
kill            Terminates a process by PID
makedir         Creates a new directory
me              Shows the current username
meminfo         Shows memory usage information
mybox           Shows the system hostname
netlist         Retrieves information about the current network
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

from editor import *
import psutil
import datetime


class CommandLine(cmd.Cmd):
    """Command-Line class inherited from `cmd` library."""

    def __init__(self, currentDir, stdout=None):
        super().__init__(stdout=stdout)
        self.currentDir = currentDir
        self.prompt = f"{self.currentDir}>>> "
        self._history = []
        self._history_index = None

    def set_directory(self, path):
        """Point this shell's working directory at *path* (no ``os.chdir``)."""
        try:
            self.currentDir = os.path.abspath(path)
            self.prompt = f"{self.currentDir}>>> "
            return f"Changed directory to {self.currentDir}"
        except Exception as e:
            return f"Error 1: {e}"

    def parse_args(self, arg):
        """Parse ``--key=value`` and ``--flag`` arguments with quote awareness."""
        import shlex as _shlex

        try:
            parts = _shlex.split(arg or "", posix=(sys.platform != "win32"))
        except ValueError:
            parts = (arg or "").split()
        args = {}
        for p in parts:
            if "=" in p:
                key, value = p.split("=", 1)
                key = key.lstrip("-")
                value = value.strip('"').strip("'")
                args[key] = value
            else:
                args[p.lstrip("-")] = True
        return args

    def onecmd(self, line):
        """oneCMD:"""
        line = line.strip()
        if line:
            self._history.append(line)
            self._history_index = len(self._history)
        return super().onecmd(line)

    def get_previous_command(self):
        """Scans the history of commands to get the previous commmand, which is a normal behavior in command-line tools after clicking the top-arrow on the keyboard."""
        if self._history and self._history_index > 0:
            self._history_index -= 1
            return self._history[self._history_index]
        return ""

    def get_next_command(self):
        """Scans the history of commands to get the next command, which is obtained if the user is checking the history."""
        if self._history and self._history_index < len(self._history) - 1:
            self._history_index += 1
            return self._history[self._history_index]
        self._history_index = len(self._history)
        return ""

    def _workspace_default(self) -> str:
        """Return tracked workspace dir, never process CWD."""
        try:
            if self.currentDir and os.path.isdir(self.currentDir):
                return os.path.abspath(self.currentDir)
        except Exception:
            pass
        return self.currentDir or ""

    def run_command(self, cmd_list, timeout: float = 30.0):
        """Runs a command as a list and returns its output."""
        try:
            result = subprocess.run(
                cmd_list,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self._workspace_default() or None,
                timeout=timeout,
            )
            output = result.stdout.strip()
            return output if output else "Command executed, no output."
        except Exception as e:
            return f"Execution Error no.300: {e}"

    def internet_exists(self):
        conn = None
        try:
            conn = socket.create_connection(("pypi.org", 443), timeout=3)
            return True
        except OSError:
            return False
        finally:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass

    def do_help(self, arg):
        """Help:"""
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

    def do_commands(self, arg):
        """Help:"""
        if arg:
            return "Error 0: Usage: commands (no arguments allowed)"
        return ALL_COMMANDS

    def do_changedir(self, arg):
        """Help:"""
        args = self.parse_args(arg)
        path = args.get("path", None)
        if not path:
            return "Error 2: You must provide a path."
        try:
            abs_path = os.path.abspath(path)
            if not os.path.isdir(abs_path):
                return f"Error 1: Directory does not exist: {abs_path}"
            self.currentDir = abs_path
            self.prompt = f"{self.currentDir}>>> "
            return f"Changed directory to {self.currentDir}"
        except Exception as e:
            return f"Error 1: {e}"

    def do_clearhistory(self, arg=None):
        """Help:"""
        self._history.clear()
        self._history_index = None
        return "Command history cleared."

    def do_clone(self, arg):
        """Help:"""
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
            import shutil as _shutil

            with open(source, "rb") as src, open(destination, "wb") as dst:
                _shutil.copyfileobj(src, dst, length=1024 * 1024)
            return f"File cloned from '{source}' to '{destination}'."
        except Exception as e:
            return f"Error 6: {e}"

    def do_copydir(self, arg):
        """Help:"""
        args = self.parse_args(arg)
        raw_source = args.get("source")
        raw_dest = args.get("destination")
        if not raw_source or not raw_dest or raw_source is True or raw_dest is True:
            return "Error 10: You must provide --source=<dir> and --destination=<dir>."
        source = os.path.abspath(str(raw_source))
        destination = os.path.abspath(str(raw_dest))
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

    def do_cpuinfo(self, arg=None):
        """Help:"""
        return f"CPU: {platform.processor()}"

    def do_date(self, arg=None):
        """Help:"""
        current_date = datetime.datetime.now()
        return (
            f"Current date: {current_date.date()}\n"
            f"Current time: {current_date.time()}\n"
            f"{current_date}"
        )

    def do_deletedir(self, arg):
        """Help:"""
        if not arg:
            return (
                "Error 42: You must provide an explicit --path; refusing to delete cwd."
            )
        else:
            path = arg
        try:
            if not os.path.isdir(path):
                return f"Error 42: Path '{path}' is not a directory or does not exist."
            os.rmdir(path=path)
            return f"Directory '{path}' removed."
        except Exception as e:
            return f"Error 42: {e}"

    def do_diskinfo(self, arg):
        """Help:"""
        try:
            args = self.parse_args(arg) if arg else {}
            path = args.get("path", self.currentDir)
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

    def do_erase(self, arg):
        """Help:"""
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

    def do_find(self, arg):
        """Help:"""
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

    def do_fileinfo(self, arg):
        """Help:"""
        args = self.parse_args(arg)
        file_path = args.get("file", self.currentDir)
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

    def do_head(self, arg):
        """Help:"""
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

    def do_here(self, arg=None):
        """Help:"""
        return f"\ncurrent working directory: {self.currentDir}"

    def do_makedir(self, arg):
        """Help:"""
        args = self.parse_args(arg)
        path = args.get("path", self.currentDir)
        name = args.get("name", "untitled")
        target = os.path.join(path, name)
        try:
            if not os.path.exists(path):
                return f"Error 44: Path '{path}' does not exist."
            os.mkdir(target)
            return f"Directory '{target}' created."
        except Exception as e:
            return f"Error 44: {e}"

    def do_me(self, arg=None):
        """Help:"""
        return f"Username: {getpass.getuser()}"

    def do_meminfo(self, arg=None):
        """Help:"""
        try:
            mem = psutil.virtual_memory()
            total = round(mem.total / (1024**2), 2)
            available = round(mem.available / (1024**2), 2)
            used = round(mem.used / (1024**2), 2)
            percent = mem.percent
            return f"Memory Usage:\nTotal: {total} MB\nUsed: {used} MB\nAvailable: {available} MB\nUsage: {percent}%"
        except Exception as e:
            return f"Error: {e}"

    def do_mybox(self, arg=None):
        """Help:"""
        return f"Hostname: {socket.gethostname()}"

    def do_newbie(self, arg):
        """Help:"""
        args = self.parse_args(arg)
        if "name" not in args:
            return "Error 21: You must provide --name=<file_name>"
        file_name = args["name"]
        file_path = args.get("path", self.currentDir)
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

    def do_peek(self, arg):
        """Help:"""
        args = self.parse_args(arg)
        number = args.get("number", None)
        custom_path = args.get("path", None)
        if number and os.path.isdir(number):
            custom_path = number
            number = None
        try:
            path_to_use = custom_path if custom_path else self.currentDir
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

    def do_shift(self, arg):
        """Help:"""
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
            return f"Shifted '{old_string}' -> '{new_string}' in '{file_path}'."
        except Exception as e:
            return f"Error 35: {e}"

    def do_sysinfo(self, arg=None):
        """Help:"""
        try:
            system = platform.system()
            release = platform.release()
            version = platform.version()
            arch = platform.machine()
            return f"System: {system}\nRelease: {release}\nVersion: {version}\nArchitecture: {arch}"
        except Exception as e:
            return f"Error: {e}"

    def do_tail(self, arg):
        """Help:"""

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
        """Help:"""
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

    def do_clear(self, arg=None):
        """Help:"""
        return None

    def do_download(self, arg):
        """Help:"""
        args = self.parse_args(arg)
        url = args.get("url")
        if not url:
            return "Error 50: You must provide --url=<url>"
        if not url.startswith(("http://", "https://")):
            return "Error 50: Only http(s) URLs are allowed."
        dest = args.get("path", self.currentDir)
        try:
            if os.path.isdir(dest):
                filename = url.split("/")[-1].split("?")[0]
                if not filename:
                    return "Error 50: Cannot derive filename from URL."
                dest = os.path.join(dest, filename)
            parent = os.path.dirname(os.path.abspath(dest))
            if parent:
                os.makedirs(parent, exist_ok=True)
            urllib.request.urlretrieve(url, dest)
            return f"Downloaded '{url}' to '{dest}'."
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            return f"Error 51: Download failed: {e}"

    def do_echo(self, arg):
        """Help:"""
        return arg if arg else ""

    def do_env(self, arg=None):
        """Help:"""
        try:
            lines = [f"{k}={v}" for k, v in sorted(os.environ.items())]
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    def do_history(self, arg=None):
        """Help:"""
        if not self._history:
            return "No commands in history."
        lines = [f"{i:4d}  {cmd}" for i, cmd in enumerate(self._history, 1)]
        return "\n".join(lines)

    def do_kill(self, arg):
        """Help:"""
        args = self.parse_args(arg)
        pid = args.get("pid")
        if not pid:
            return "Error 52: You must provide --pid=<process_id>"
        try:
            pid = int(pid)
            if pid <= 0:
                return "Error 52: PID must be positive."
            if pid == os.getpid():
                return "Error 54: Refusing to kill the IDE itself."
            try:
                parent = os.getppid()
                if pid == parent:
                    return "Error 54: Refusing to kill the parent process."
            except Exception:
                pass
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

    def do_ping(self, arg):
        """Help:"""
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
                cwd=self._workspace_default() or None,
            )
            output = result.stdout.strip()
            return output if output else f"Ping to '{host}' completed."
        except subprocess.TimeoutExpired:
            return f"Error 56: Ping to '{host}' timed out."
        except FileNotFoundError:
            return "Error 56: Ping command not found on this system."
        except Exception as e:
            return f"Error 56: {e}"

    def do_ps(self, arg=None):
        """Help:"""
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

    def do_quit(self, arg=None):
        """Help:"""
        return "Type 'close' or use the close button to close the terminal panel."

    def do_rename(self, arg):
        """Help:"""
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

    def do_unzip(self, arg):
        """Help:"""
        args = self.parse_args(arg)
        source = args.get("source")
        if not source:
            return "Error 61: You must provide --source=<zipfile>"
        if not os.path.isfile(source):
            return f"Error 62: File '{source}' does not exist."
        destination = args.get("destination", self.currentDir)
        try:
            if not os.path.exists(destination):
                os.makedirs(destination, exist_ok=True)
            dest_root = os.path.abspath(destination)
            with zipfile.ZipFile(source, "r") as z:
                for member in z.namelist():
                    target = os.path.abspath(os.path.join(dest_root, member))
                    if (
                        not target.startswith(dest_root + os.sep)
                        and target != dest_root
                    ):
                        return f"Error 64: Unsafe zip entry blocked: {member}"
                z.extractall(dest_root)
            return f"Extracted '{source}' to '{destination}'."
        except zipfile.BadZipFile:
            return f"Error 63: '{source}' is not a valid zip file."
        except Exception as e:
            return f"Error 64: {e}"

    def do_uptime(self, arg=None):
        """Help:"""
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

    def do_whoami(self, arg=None):
        """Help:"""
        return getpass.getuser()

    def do_ip_scan(self, arg):
        """Help:"""
        try:
            if not os.path.exists("/proc/net/arp"):
                return "Error 70: Network scanning is not supported on this platform."
            with open("/proc/net/arp") as f:
                lines = f.readlines()
            if len(lines) < 2:
                return "Error 70: No ARP entries found. The network may be unavailable."
            result = ["IP Address         MAC Address"]
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    ip = parts[0]
                    mac = parts[3]
                    if mac and mac != "00:00:00_00:00:00" and "(incomplete)" not in mac:
                        result.append(f"{ip:18s} {mac}")
            if len(result) == 1:
                return "Error 70: No devices found on the local network."
            return "\n".join(result)
        except Exception as e:
            return f"Error 71: Network scan failed: {e}"

    def do_netlist(self, arg):
        """Help:"""
        try:
            hostname = socket.gethostname()
            lines = [f"Hostname: {hostname}"]

            interfaces = psutil.net_if_addrs()
            for name, addrs in interfaces.items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        lines.append(f"Interface {name}: {addr.address}")
                        if addr.netmask:
                            lines.append(f"  Netmask: {addr.netmask}")

            return (
                "\n".join(lines)
                if len(lines) > 1
                else "Error 72: No network interfaces found."
            )
        except Exception as e:
            return f"Error 73: Failed to retrieve network information: {e}"
