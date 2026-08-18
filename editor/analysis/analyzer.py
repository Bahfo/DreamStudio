import platform
import ctypes
import json

from pathlib import Path
from enum import IntEnum


class DiagnosticCategory(IntEnum):
    GrammarError = 0
    GeneralError = 1
    TypoWarning = 2
    UnusedWarning = 3
    SilentCodeWarning = 4


class CodeAnalyzer:
    def __init__(self, lib_dir: str = "."):
        self.lib_path = self._resolve_library_path(lib_dir)
        self.lib = self._load_library()
        self._setup_function_signatures()

    def _resolve_library_path(self, lib_dir: str) -> Path:
        system = platform.system()

        if system == "Windows":
            lib_name = "libanalysis.dll"
        elif system == "Linux":
            lib_name = "libanalysis.so"
        elif system == "Darwin":
            lib_name = "libanalysis.dylib"
        else:
            raise OSError(f"Unsupported operating system: {system}")

        script_dir = Path(__file__).resolve().parent
        full_path = script_dir / "build" / lib_name
        if not full_path.exists():
            raise FileNotFoundError(
                f"Native library '{lib_name}' not found at: {full_path}"
            )
        return full_path

    def _load_library(self) -> ctypes.CDLL:
        try:
            return ctypes.CDLL(str(self.lib_path))
        except Exception as e:
            raise RuntimeError(
                f"Failed to load dynamic library at {self.lib_path}: {e}"
            )

    def _setup_function_signatures(self):
        self.lib.analyze_code.argtypes = [ctypes.c_char_p]
        self.lib.analyze_code.restype = ctypes.c_void_p

        self.lib.free_result.argtypes = [ctypes.c_void_p]
        self.lib.free_result.restype = None

    def analyze(self, source_code: str) -> dict:
        encoded_source = source_code.encode("utf-8")
        raw_ptr = self.lib.analyze_code(encoded_source)

        if not raw_ptr:
            return {}

        try:
            json_bytes = ctypes.string_at(raw_ptr)
            return json.loads(json_bytes.decode("utf-8"))
        finally:
            self.lib.free_result(raw_ptr)


if __name__ == "__main__":
    analyzer = CodeAnalyzer(lib_dir=".")

    test_script = """
import math_utils

def process_items(count):
    var total = count + cont
    return total
    var dead_node = 0
"""

    results = analyzer.analyze(test_script)
    print(json.dumps(results, indent=2))
