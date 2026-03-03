# Written By Bahaa Nofal 3/3/2026
# Backend API for DreamStudio - Run-Configuration
# Copyright 2026 - Licensed under DreamStudio's license

"""
Backend - Run - run_config.py:
A script written in Python to pass user arguments and script code to Runtime File Runner.
Since currently the the IDE focuses on the following languages, they would be hard-coded by default inside 
the following script:
    1. Python
    2. B-Sharp
    3. Lavender
    4. D-language
    5. C-language
"""

import os
import sys
import time
import shutil
import tempfile
import threading
import subprocess

import customtkinter as ctk

LANGUAGE_CONFIGS = {
    "python": {
        "extension": ".py",
        "compile_cmd": None,
        "run_cmd": lambda src, _: [sys.executable, src],
    },
    "c": {
        "extension": ".c",
        "compile_cmd": lambda src, out: ["gcc", src, "-o", out, "-Wall"],
        "run_cmd": lambda _, out: [out],
    },
    "bash": {
        "extension": ".sh",
        "compile_cmd": None,
        "run_cmd": lambda src, _: ["bash", src],
    },
}

class ShellWindow(ctk.CTkToplevel):
    """A floating terminal-style window that displays runtime output."""

    def __init__(self, title: str = "Run Output"):
        super().__init__()
        self.title(title)
        self.geometry("700x400")
        self.resizable(True, True)
        self.attributes("-topmost", True)

        # Output textbox — dark terminal look
        self.textbox = ctk.CTkTextbox(
            self,
            font=("Courier New", 13),
            fg_color="#1e1e1e",
            text_color="#d4d4d4",
            wrap="word",
            state="disabled",
        )
        self.textbox.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # Terminate button
        self.stop_btn = ctk.CTkButton(
            self,
            width=30,
            height=30,
            corner_radius=5,
            text="■",
            fg_color="#a10000",
            hover_color="#c00000",
            command=self._on_stop)
        self.stop_btn.pack(pady=(4, 8), side="left", anchor="w", padx=8)

        self._stop_callback = None   # set by RunFile after creation

        # Exit status
        self.exit_status = ctk.CTkLabel(
            self,
            text="",
            text_color=["#1E1E1E","#FFFFFF"],
            font=("Segoe UI",12)
        )
        self.exit_status.pack(pady=(4,8), side="right", anchor="e", padx=16)

        # Runtime evaluate 
        self.runTimeEval = ctk.CTkLabel(
            self,
            text="",
            text_color=["#1E1E1E","#FFFFFF"],
            font=("Segoe UI",12)
        )
        self.runTimeEval.pack(pady=(4,8), side="right", anchor="e", padx=8)

    def write(self, text: str):
        """Thread-safe append to the textbox."""
        def _insert():
            self.textbox.configure(state="normal")
            self.textbox.insert("end", text)
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        self.after(0, _insert)      # always schedule on the main thread

    def _on_stop(self):
        if self._stop_callback:
            self._stop_callback()
            self.destroy()

class RunFile:
    """
    Arguments list contract (arg[0], arg[1]):
        arg[0]  - language type string, e.g. "python", "c", "bash"
        arg[1]  - project CWD path (falls back to os.getcwd() if invalid)
    """

    def __init__(self, code_to_run: str, arguments: list, ShellWindow : ctk.CTkTextbox):
        self.code_to_run = code_to_run
        self._shell      = ShellWindow
        self.arguments   = arguments
        self._process: subprocess.Popen | None = None

    def run(self):
        """
        Call this from your external script.
        Spawns the CTk shell window and begins execution in a background thread.
        Requires a CTk/Tk mainloop to already be running (or calls ctk.CTk() internally).
        """
        language_type, cwd, configs = self._parse_arguments()

        self._shell.configure(title=f"Run — {language_type}")
        self._shell._stop_callback = self.stop

        # Start execution in a background thread
        thread = threading.Thread(
            target=self._run_in_thread,
            args=(configs, cwd),
            daemon=True,
        )
        thread.start()

    def stop(self):
        """Terminate the running subprocess."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            self._emit("\n[Process terminated by user]\n")

    def _parse_arguments(self):
        language_type = self.arguments[0].lower().strip()
        raw_cwd       = self.arguments[1] if len(self.arguments) > 1 else ""
        cwd           = raw_cwd if os.path.exists(raw_cwd) else os.getcwd()

        if language_type not in LANGUAGE_CONFIGS:
            raise ValueError(
                f"Unsupported language: '{language_type}'. "
                f"Available: {', '.join(LANGUAGE_CONFIGS)}"
            )

        return language_type, cwd, LANGUAGE_CONFIGS[language_type]

    def _run_in_thread(self, configs: dict, cwd: str):
        tmp_dir = tempfile.mkdtemp()

        try:
            src_path = os.path.join(tmp_dir, f"main{configs['extension']}")
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(self.code_to_run)

            out_path = os.path.join(tmp_dir, "main_out")

            if configs["compile_cmd"] is not None:
                compile_cmd = configs["compile_cmd"](src_path, out_path)
                self._emit(f"[Compiling] {' '.join(compile_cmd)}\n")

                if not self._execute(compile_cmd, tmp_dir):
                    self._emit("[Build failed — execution aborted]\n")
                    return

                self._emit("[Build successful]\n\n")

            run_cmd = configs["run_cmd"](src_path, out_path)
            self._emit(f"[Running] {' '.join(run_cmd)}\n")
            self._emit("─" * 40 + "\n")

            start_time = time.perf_counter()
            bool_value = self._execute(run_cmd, cwd)
            self._emit("\n" + "─" * 40 + "\n[Process finished]\n")
            end_time = time.perf_counter()

            self._shell.exit_status.configure(text=f"Exit Code: {bool_value}")
            self._shell.runTimeEval.configure(text=f"Total Runtime: {end_time - start_time} seconds")

        except Exception as e:
            self._emit(f"[Runtime Error] {e}\n")

        finally:
            self._cleanup(tmp_dir)

    def _execute(self, cmd: list[str], cwd: str) -> bool:
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                text=True,
                bufsize=1,
            )
            for line in self._process.stdout:
                self._emit(line)

            self._process.wait()
            return self._process.returncode

        except FileNotFoundError:
            self._emit(
                f"[Error] Command not found: '{cmd[0]}'\n"
                "Make sure it is installed and on your PATH.\n"
            )
            return False

    def _emit(self, text: str):
        """Write to the shell window if it exists, otherwise fall back to print."""
        if self._shell:
            self._shell.write(text)
        else:
            print(text, end="")

    @staticmethod
    def _cleanup(tmp_dir: str):
        shutil.rmtree(tmp_dir, ignore_errors=True)