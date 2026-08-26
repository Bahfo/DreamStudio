"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Errors analysis module walker for Python files written using `ast` and `os`.
This error walker scans whole directories and files for problems. It returns
a detailed dictionary of file path of error, line number, and a description
of the error provided by `ast` syntax errors.
"""

from editor import *


class ProblemsAnalyzer:
    def __init__(self, codebase_path: str):
        self.codebase_path = codebase_path
        self.required_extensions = [".py", ".pyi"]
        self.dictionary_of_errors = {"errors": [], "warnings": []}

    def return_analysis_result(self):
        for root, dirs, files in os.walk(self.codebase_path):
            dirs[:] = [
                directory
                for directory in dirs
                if directory not in {"venv", ".venv", "__pycache__", ".git"}
            ]
            for file in files:
                file_path = os.path.join(root, file)
                if pathlib.Path(file_path).suffix in self.required_extensions:
                    try:
                        with open(file_path, "r") as f:
                            content = f.read()
                            ast.parse(content)

                    except SyntaxError as e:
                        self.dictionary_of_errors["errors"].append(
                            {
                                "file_path": file_path,
                                "error_line": e.lineno,
                                "error_offset": e.offset,
                                "error_msg": e.msg,
                            }
                        )

                    except Exception as e:
                        print("ERROR: ", e)

    def return_errors(self):
        self.return_analysis_result()
        return self.dictionary_of_errors
