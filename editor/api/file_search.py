"""
(C) COPYRIGHT - 2026 EXcellent TechStacks Cooperation - All Rights Reserved
Background module for searching files across the inner repository for DreamStudio.
"""

from editor import *


def regex_compile_query(query, is_regex=False, is_ignore_case=False):
    """
    Preparses the query ensuring what type of search the user required.
    """
    flags = re.IGNORECASE if is_ignore_case else 0
    try:
        if is_regex:
            return re.compile(query, flags)
        elif "*" in query or "?" in query:
            pat = fnmatch.translate(query)
            if pat.endswith(r"\Z"):
                pat = pat[:-2]
            return re.compile(pat, flags)
        else:
            return re.compile(re.escape(query), flags)
    except re.error:
        return re.compile(re.escape(query), flags)


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
        pass
    return matches


def execute_search(
    root_dir, query, scope_dirs=None, is_regex=False, is_ignore_case=False
):
    """DreamStudio search executor."""
    compiled_pattern = regex_compile_query(query, is_regex, is_ignore_case)
    target_files = []
    from editor.utils.solution.paths import DEFAULT_EXCLUDES

    ignore_dirs = set(DEFAULT_EXCLUDES)
    search_roots = []
    if scope_dirs:
        for sd in scope_dirs:
            p = Path(sd)
            if p.is_absolute():
                search_roots.append(p)
            else:
                search_roots.append(Path(root_dir) / p)
    else:
        search_roots.append(Path(root_dir))

    for root_target in search_roots:
        if not root_target.exists():
            continue

        for root, dirs, files in os.walk(root_target):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                if file.endswith(
                    (
                        ".py",
                        ".pyi",
                        ".js",
                        ".ts",
                        ".c",
                        ".cpp",
                        ".h",
                        ".java",
                        ".go",
                        ".rs",
                        ".json",
                        ".yaml",
                        ".yml",
                        ".toml",
                        ".ini",
                        ".md",
                        ".txt",
                        ".html",
                        ".css",
                    )
                ):
                    target_files.append(Path(root) / file)

    results = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(search_file, f, compiled_pattern) for f in target_files
        ]

        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
            except Exception:
                continue
            if res:
                results.extend(res)

    return results
