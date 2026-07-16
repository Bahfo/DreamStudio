# Code to obtain project environment properties and info.

import os
import sys
import platform
import sysconfig


def get_interpreter_info() -> dict:
    """
    Extracts the Python interpreter engine configurations and
    runtime variables, then returns a dictionary containing all
    these information.
    """
    version = platform.python_version()
    compiler = platform.python_compiler()
    implementation = platform.python_implementation()
    api_version = getattr(sys, "api_version", None)
    hex_version = sys.hexversion

    return {
        "version": version,
        "compiler": compiler,
        "implementation": implementation,
        "api_version": api_version,
        "hex_version": hex_version,
    }


def get_interpreter_path() -> dict:
    """
    Returns the interpreter path information.
    """
    executable = sys.executable
    prefix = sys.prefix
    stdlib_dir = sysconfig.get_path("stdlib")
    purelib_dir = sysconfig.get_path("purelib")
    sys_path = sys.prefix

    return {
        "executable": executable,
        "prefix": prefix,
        "stdlib_dir": stdlib_dir,
        "purelib_dir": purelib_dir,
        "sys_path": sys_path,
    }


def get_env_variables() -> dict:
    """
    Returns environment variables.
    """
    return {
        "vevn_path": os.environ.get("VIRTUAL_ENV"),
        "python_path": os.environ.get("PYTHONPATH"),
    }
