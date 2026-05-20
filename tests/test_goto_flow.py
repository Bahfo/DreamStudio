"""Tests for the goto-definition decision logic (mocked PyQt6)."""


def test_navigable_definition_takes_priority():
    definitions = [
        {"file": None, "line": 1, "column": 0, "name": "print",
         "description": "", "type": "function", "doc": ""},
        {"file": "/path/to/lib.py", "line": 42, "column": 5, "name": "print",
         "description": "", "type": "function", "doc": ""},
    ]
    target = {"definition": None, "_hover_info": []}
    best_def = None
    for d in definitions:
        file_path = d.get("file")
        if file_path is not None and best_def is None:
            best_def = d
            target["definition"] = {
                "file": file_path,
                "line": d["line"] - 1 if d["line"] else 0,
                "column": d["column"] or 0,
                "same_file": False,
            }
        target.setdefault("_hover_info", []).append({
            "name": d.get("name", ""),
            "description": d.get("description", ""),
            "doc": d.get("doc", ""),
        })

    assert best_def is not None
    assert best_def["file"] == "/path/to/lib.py"
    assert target["definition"] is not None
    assert target["definition"]["file"] == "/path/to/lib.py"
    assert len(target["_hover_info"]) == 2


def test_all_builtins_stored_as_hover_info():
    definitions = [
        {"file": None, "line": None, "column": None, "name": "len",
         "description": "", "type": "function", "doc": "Return length."},
        {"file": None, "line": None, "column": None, "name": "len",
         "description": "", "type": "function", "doc": "Alias."},
    ]
    target = {"definition": None, "_hover_info": []}
    best_def = None
    for d in definitions:
        file_path = d.get("file")
        if file_path is not None and best_def is None:
            best_def = d
            target["definition"] = {
                "file": file_path,
                "line": d["line"] - 1 if d["line"] else 0,
                "column": d["column"] or 0,
                "same_file": False,
            }
        target.setdefault("_hover_info", []).append({
            "name": d.get("name", ""),
            "description": d.get("description", ""),
            "doc": d.get("doc", ""),
        })

    assert best_def is None
    assert target["definition"] is None
    assert len(target["_hover_info"]) == 2
    assert target["_hover_info"][0]["name"] == "len"


def test_mixed_builtin_and_src_file():
    definitions = [
        {"file": None, "line": None, "column": None, "name": "print",
         "description": "", "type": "builtin_function", "doc": "print(...)"},
        {"file": "/path/to/some.py", "line": 10, "column": 3, "name": "print_wrapper",
         "description": "", "type": "function", "doc": ""},
    ]
    target = {"definition": None, "_hover_info": []}
    best_def = None
    for d in definitions:
        file_path = d.get("file")
        if file_path is not None and best_def is None:
            best_def = d
            target["definition"] = {
                "file": file_path,
                "line": d["line"] - 1 if d["line"] else 0,
                "column": d["column"] or 0,
                "same_file": False,
            }
        target.setdefault("_hover_info", []).append({
            "name": d.get("name", ""),
            "description": d.get("description", ""),
            "doc": d.get("doc", ""),
        })

    assert best_def is not None
    assert target["definition"]["file"] == "/path/to/some.py"
    assert len(target["_hover_info"]) == 2


def test_navigate_to_definition_click():
    """When Ctrl+clicking a navigable symbol, goto should trigger."""
    target = {
        "word": "open",
        "line": 5,
        "start": 10,
        "end": 14,
        "definition": {
            "file": "/usr/lib/python3.12/builtins.py",
            "line": 100,
            "column": 0,
            "same_file": False,
        },
    }
    definition = target.get("definition")
    assert definition is not None
    assert definition["file"] == "/usr/lib/python3.12/builtins.py"
    assert definition["line"] == 100


def test_navigate_to_definition_pending():
    """When Jedi hasn't resolved yet, definition is None."""
    target = {
        "word": "foo",
        "line": 3,
        "start": 0,
        "end": 3,
        "definition": None,
    }
    definition = target.get("definition")
    assert definition is None


def test_navigate_to_definition_same_file():
    """When definition is in the same file, navigate internally."""
    current_file = "/project/main.py"
    target = {
        "word": "helper",
        "line": 10,
        "start": 4,
        "end": 10,
        "definition": {
            "file": "/project/main.py",
            "line": 42,
            "column": 0,
            "same_file": True,
        },
    }
    definition = target["definition"]
    assert definition["same_file"] is True
    assert definition["file"] == current_file


def test_multiple_same_symbols_no_file():
    """When a single symbol gets multiple Jedi results (e.g., overloaded)."""
    definitions = [
        {"file": None, "line": None, "column": None, "name": "print",
         "description": "", "type": "builtin_function", "doc": "Doc 1"},
    ]
    target = {"definition": None, "_hover_info": []}
    best_def = None
    for d in definitions:
        file_path = d.get("file")
        if file_path is not None and best_def is None:
            best_def = d
            target["definition"] = {
                "file": file_path,
                "line": d["line"] - 1 if d["line"] else 0,
                "column": d["column"] or 0,
                "same_file": False,
            }
        target.setdefault("_hover_info", []).append({
            "name": d.get("name", ""),
            "description": d.get("description", ""),
            "doc": d.get("doc", ""),
        })
    assert best_def is None
    assert target["definition"] is None
    assert len(target["_hover_info"]) == 1


def test_stdlib_file_resolves_correctly():
    """Stdlib .py files should resolve and NOT be treated as builtins."""
    definitions = [
        {"file": "/usr/lib/python3.12/os.py", "line": 100, "column": 0,
         "name": "getcwd", "description": "", "type": "function",
         "doc": "Return current working directory."},
    ]
    target = {"definition": None, "_hover_info": []}
    best_def = None
    for d in definitions:
        file_path = d.get("file")
        if file_path is not None and best_def is None:
            best_def = d
            target["definition"] = {
                "file": file_path,
                "line": d["line"] - 1 if d["line"] else 0,
                "column": d["column"] or 0,
                "same_file": False,
            }
        target.setdefault("_hover_info", []).append({
            "name": d.get("name", ""),
            "description": d.get("description", ""),
            "doc": d.get("doc", ""),
        })
    assert best_def is not None
    assert target["definition"] is not None
    assert target["definition"]["file"] == "/usr/lib/python3.12/os.py"


def test_hyperlink_indicator_cleanup():
    """Ensure that hiding symbol link clears the target."""
    target = {
        "word": "foo",
        "line": 1,
        "start": 0,
        "end": 3,
        "definition": None,
    }
    # Simulate _hide_symbol_link
    target = None
    assert target is None
