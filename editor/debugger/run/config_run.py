"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Module to configure run options for DreamStudio for any file type.
"""

import os
import sys
import json
import subprocess
from typing import Any, Dict, List, Optional, Union


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

        directory = os.path.dirname(target_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(target_path, "w", encoding="utf-8") as config_file:
            json.dump(self.options, config_file, indent=indent)

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

        with open(target_path, "r", encoding="utf-8") as config_file:
            self.options = json.load(config_file)

        self.config_name = self.options.get("config_name", self.config_name)
        self.file_path = self.options.get("file_path", self.file_path)
        self.config_file_path = target_path

        return self.options

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
        arg = self.options.get("Arg", sys.executable)
        parameters = self.options.get("Parameters", [])
        file_to_run = self.file_path or self.options.get("file_path")

        if not file_to_run:
            raise ValueError("No file path specified in configuration to run.")

        cmd: List[str] = [arg]
        if file_to_run:
            cmd.append(file_to_run)

        if isinstance(parameters, list):
            cmd.extend(map(str, parameters))
        elif isinstance(parameters, str) and parameters.strip():
            cmd.append(parameters)

        work_dir = (
            cwd
            or (
                os.path.dirname(os.path.abspath(file_to_run))
                if os.path.exists(file_to_run)
                else None
            )
            or os.getcwd()
        )

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
