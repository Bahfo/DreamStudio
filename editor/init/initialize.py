"""
(C) COPYRIGHT 2026 The DreamStudio Project Contributors.
Developed and Maintained Mainly by Excellent Technologies.

Backed initializer when starting DreamStudio.
"""

# Written by Bahaa Nofal - 4/2026

import os
import sys
import json
import atexit
import shutil
import getpass
import platform

from typing import Any
from datetime import datetime


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    path = os.path.abspath(__file__)
    for _ in range(3):
        path = os.path.dirname(path)
    return path


def assets_exist(file_name=None) -> bool:
    base_dir = get_base_dir()
    assets_path = os.path.join(base_dir, "assets")

    if file_name:
        assets_path = os.path.join(assets_path, file_name)

    return os.path.exists(assets_path)


def return_log_message(error_msg, traceback_str) -> dict[Any, Any]:
    """Writes error details in a standardized way"""
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "error": error_msg,
        "traceback": traceback_str,
    }
    return log_data


def check_env_path(target_variable) -> bool:
    path_string = os.environ.get("PATH", "")
    separator = ";" if platform.system() == "Windows" else ":"
    individual_paths = path_string.split(separator)

    normalized_target = os.path.normpath(target_variable)
    normalized_paths = [os.path.normpath(p) for p in individual_paths]

    return normalized_target in normalized_paths


def check_debuggers_paths(variable_to_check):
    """Bootstraps preloading debuggers and shows erros if any occurs,
    and returns a boolean if the variable exists or not."""
    if variable_to_check == "Python":
        python_dir = os.path.dirname(sys.executable)
        return {"Python": check_env_path(python_dir)}
    elif variable_to_check == "GCC":
        gcc_exe = shutil.which("gcc")
        gcc_dir = os.path.dirname(gcc_exe) if gcc_exe else None
        return {"GCC": check_env_path(gcc_dir)}


config_file = {
    "general_info": {
        "module": "DreamStudio",
        "version": "1.0.1",
        "System": platform.system(),
        "Node Name": platform.node(),
        "Machine": platform.machine(),
        "User": getpass.getuser(),
        "Home Directory": os.path.expanduser("~"),
    },
    "init": {
        "check_if_assets_exist": assets_exist(),
        "check_if_system_assets_exist": assets_exist("system"),
        "check_if_logo_assets_exist": assets_exist("logos"),
        "check_if_types_assets_exist": assets_exist("types"),
    },
    "errors": (check_debuggers_paths("Python"), check_debuggers_paths("GCC")),
}


class Initializer:
    def __init__(self):
        self.check_config_file()

    def check_config_file(self):
        script_path = sys.path[0]
        json_path = os.path.join(script_path, "config.json")

        if os.path.exists(json_path):
            with open(json_path, encoding="UTF-8", mode="r") as file:
                data = json.load(file)
                print(data)

        else:
            data = config_file
            with open(json_path, encoding="UTF-8", mode="w") as file:
                json.dump(data, file, indent=4)

    def update_user_info(self):
        pass


app = Initializer()
