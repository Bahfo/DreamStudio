"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Module to configure run options for DreamStudio for any file type.
"""

import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union

from editor.debugger.run.python_resolver import find_global_python
from editor.utils.io import load_json, save_json


class ConfigRun:
    """Main module to configure run options, save options, and execute them.

    Configuration Example Format:

    ```json
    {
        "config_name": "Name of Your Configuration",
        "file_path": "Path/to/Your/File/to/Run",
        "Arg": "python3",
        "Parameters": [
            "List", "Containing", "Your", "Parameters"
        ]
    }
    ```
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        config_name: str = "dsconfig",
        options: Optional[Dict[str, Any]] = None,
        config_file_path: Optional[str] = None,
    ):
        self.file_path = file_path
        self.config_name = config_name
        self.options = options if options is not None else {}
        self.config_file_path = config_file_path or f"{self.config_name}.json"

        if not self.options:
            self.options = {
                "config_name": self.config_name,
                "file_path": self.file_path or "",
                "Arg": "python3",
                "Parameters": [],
            }

    def save_config(self, save_path: Optional[str] = None, indent: int = 4) -> str:
        """Saves current run configurations into a JSON file.

        Args:
            save_path: Optional path to save to. Defaults to
              `self.config_file_path`.
            indent: Indentation level for pretty-printing JSON.

        Returns:
            The path where the configuration was saved.
        """
        target_path = save_path or self.config_file_path

        self.options["config_name"] = self.config_name
        if self.file_path:
            self.options["file_path"] = self.file_path

        save_json(target_path, self.options, indent=indent)

        self.config_file_path = target_path
        return target_path

    def load_config(self, source_path: Optional[str] = None) -> Dict[str, Any]:
        """Loads and extracts configuration options from a JSON file.

        Args:
            source_path: File path to load JSON from. Defaults to
              `self.config_file_path`.

        Returns:
            The loaded dictionary configuration.
        """
        target_path = source_path or self.config_file_path

        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Config file not found: {target_path}")

        self.options = load_json(target_path, default=None)
        if self.options is None:
            raise ValueError(f"Invalid run configuration: {target_path}")

        self.config_name = self.options.get("config_name", self.config_name)
        self.file_path = self.options.get("file_path", self.file_path)
        self.config_file_path = target_path

        return self.options

    def build_command(self, cwd: Optional[str] = None) -> Tuple[List[str], str]:
        """Resolves the configured executable, target file, and parameters
        into an argv sequence plus a working directory — without launching
        any process.

        Args:
            cwd: Optional working directory override. Defaults to the
              configured file's parent dir when the file exists.

        Returns:
            A `(command_arguments, working_directory)` tuple where the
            arguments keep the interpreter, file path, and parameters as
            separate list entries (safe for exec-style launching).

        Raises:
            ValueError: If no file path is configured or no working
              directory can be determined without using process CWD.
        """
        arg = (
            self.options.get("Arg")
            or self.options.get("interpreter")
            or find_global_python()
        )
        parameters = self.options.get("Parameters", self.options.get("args", []))
        file_to_run = (
            self.file_path
            or self.options.get("file_path")
            or self.options.get("target")
        )

        if not file_to_run:
            raise ValueError("No file path specified in configuration to run.")

        file_to_run = os.path.expanduser(str(file_to_run))

        cmd: List[str] = [str(arg), file_to_run]

        if isinstance(parameters, list):
            cmd.extend(map(str, parameters))
        elif isinstance(parameters, str) and parameters.strip():
            cmd.append(parameters)

        if cwd and os.path.isdir(cwd):
            return cmd, os.path.abspath(cwd)
        return cmd, os.path.dirname(os.path.abspath(file_to_run))

    def run(
        self, cwd: Optional[str] = None, async_mode: bool = True
    ) -> Union[subprocess.Popen, subprocess.CompletedProcess]:
        """Executes the target script using subprocess according to saved config options.

        Args:
            cwd: Working directory for execution (defaults to file's parent
              dir).
            async_mode: If True (recommended for IDEs), returns `Popen` object
              for non-blocking, real-time stdout/stderr streaming. If False,
              blocks until completion and returns `CompletedProcess`.

        Returns:
            `subprocess.Popen` process instance if async_mode is True, else
            `subprocess.CompletedProcess`.
        """
        cmd, work_dir = self.build_command(cwd=cwd)

        if async_mode:
            return subprocess.Popen(
                cmd,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        else:
            return subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)
