"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Background module for searching files across the inner repository for DreamStudio.
"""

from editor import *

def regex_compile_query(query, is_regex=False, is_ignore_case=False):
    """
    Preparses the query ensuring what type of search the user required.
    """
    if is_regex:
        if is_ignore_case:
            return re.compile(query, re.IGNORECASE)
        else:
            return re.compile(query)
    elif "*" in query or "?" in query:
        # translate: This converts wildcards to a standard regex pattern
        if is_ignore_case:
            return re.compile(fnmatch.translate(query), re.IGNORECASE)
        else:
            return re.compile(fnmatch.translate(query))
    else:
        if is_ignore_case:
            return re.compile(re.escape(query), re.IGNORECASE)
        else:
            return re.compile(re.escape(query))


def search_file(file_path, compiled_regex):
    """
    Searches for the required regex within the path specified.
    """
    matches = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            for line_num, line in enumerate(file, 1):
                if compiled_regex.search(line):
                    matches.append(
                        {"file": str(file_path), "line": line_num, "text": line.strip()}
                    )
    except (OSError, PermissionError):
        pass  # Ignore
    return matches


def execute_search(
    root_dir, query, scope_dirs=None, is_regex=False, is_ignore_case=False
):
    """
    DreamStudio search executor.

    Searches files across the given path. `scope_dirs` is a list of subdirectories to
    restrict the search.
    """
    compiled_pattern = regex_compile_query(query, is_regex, is_ignore_case)
    target_files = []
    ignore_dirs = {
        ".git",  # Git files
        ".venv",  # Virtual Environment possible name
        "venv",  # Virtual Environment other possible name
        "__pycache__",  # pycache compiled
        "node_modules",  # nodeJS modules
        "build",  # build directory
        "dist",  # distribution directory
        ".idea",  # IntelliJ and PyCharm folder
        ".vscode",  # VSCode folder
        ".vs",  # Visual Studio folder
    }
    search_roots = (
        [Path(root_dir) / sd for sd in scope_dirs] if scope_dirs else [Path(root_dir)]
    )

    for root_target in search_roots:
        if not root_target.exists():
            continue

        for root, dirs, files in os.walk(root_target):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                if file.endswith(
                    (
                        ".py",  # Python
                        ".js",  # JavaScript
                        ".ts",  # TypeScript
                        ".cpp",  # C-Plus-Plus
                        ".h",  # C/C++ Headers
                        ".java",  # Java
                        ".go",  # Go
                        ".json",  # JSON files
                        ".html",  # HTML files
                        ".css",  # Cascadia SS files
                    )
                ):
                    target_files.append(Path(root) / file)

    results = []

    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Chunking tasks maximizes CPU efficiency by reducing IPC overhead
        chunk_size = max(1, len(target_files) // (os.cpu_count() * 4))

        futures = [
            executor.submit(search_file, f, compiled_pattern) for f in target_files
        ]

        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.extend(res)

    return results
