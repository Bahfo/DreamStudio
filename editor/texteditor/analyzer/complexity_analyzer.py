import ast
from typing import Any


def _annotation_str(node: Any) -> str:
    if node is None:
        return "(None)"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Subscript):
        value = _annotation_str(node.value)
        slice_ = _annotation_str(node.slice)
        return f"{value}[{slice_}]"
    if isinstance(node, ast.Attribute):
        return f"{_annotation_str(node.value)}.{node.attr}"
    if isinstance(node, ast.Tuple):
        return ", ".join(_annotation_str(e) for e in node.elts)
    return "?"


def _function_complexity(func_node: ast.AST) -> int:
    cc = 1
    for node in ast.walk(func_node):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try, ast.IfExp, ast.BoolOp)):
            cc += 1
    return cc


def analyze_python_complexity(source_code: str, file_path: str = None) -> dict:
    result: dict[str, Any] = {
        "file": file_path or "<input>",
        "total_lines": len(source_code.strip().splitlines()) if source_code else 0,

        "num_classes": 0,
        "num_functions": 0,
        "num_imports": 0,
        "num_calls": 0,

        "classes": [],
        "functions": [],
        "imported_modules": [],
        "function_calls": [],

        "docstring_coverage_pct": 0.0,
        "missing_docstrings": [],
        "security_warnings": [],
        "bare_except_warnings": [],

        "cyclomatic_complexity": 1,
        "max_nesting_depth": 0,
    }

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return result

    total_documentable_items = 0
    items_with_docstrings = 0

    def walk_node(node: ast.AST, current_depth: int) -> None:
        nonlocal total_documentable_items, items_with_docstrings

        if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try, ast.IfExp, ast.BoolOp)):
            result["cyclomatic_complexity"] += 1

        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While)):
            current_depth += 1
            if current_depth > result["max_nesting_depth"]:
                result["max_nesting_depth"] = current_depth

        if isinstance(node, ast.ExceptHandler) and node.type is None:
            result["bare_except_warnings"].append({
                "line": node.lineno,
                "col": node.col_offset,
            })

        if isinstance(node, ast.ClassDef):
            result["num_classes"] += 1
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            init_method = next((m for m in methods if m.name == "__init__"), None)
            init_params: list[str] = []
            if init_method:
                init_params = [a.arg for a in init_method.args.args]
            base_classes: list[str] = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    base_classes.append(b.id)
                elif isinstance(b, ast.Attribute):
                    base_classes.append(f"{_annotation_str(b.value)}.{b.attr}")
            result["classes"].append({
                "name": node.name,
                "num_methods": len(methods),
                "init_params": init_params,
                "base_classes": base_classes,
                "line": node.lineno,
                "col": node.col_offset,
            })
            total_documentable_items += 1
            if ast.get_docstring(node):
                items_with_docstrings += 1
            else:
                result["missing_docstrings"].append({
                    "name": node.name,
                    "type": "Class",
                    "line": node.lineno,
                    "col": node.col_offset,
                })

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["num_functions"] += 1
            params = [a.arg for a in node.args.args]
            returns = _annotation_str(node.returns)
            func_cc = _function_complexity(node)
            result["functions"].append({
                "name": node.name,
                "params": params,
                "returns": returns,
                "complexity": func_cc,
                "line": node.lineno,
                "col": node.col_offset,
            })
            total_documentable_items += 1
            if ast.get_docstring(node):
                items_with_docstrings += 1
            else:
                result["missing_docstrings"].append({
                    "name": node.name,
                    "type": "Function",
                    "line": node.lineno,
                    "col": node.col_offset,
                })

        if isinstance(node, ast.Import):
            for alias in node.names:
                result["num_imports"] += 1
                result["imported_modules"].append(alias.name)

        if isinstance(node, ast.ImportFrom):
            result["num_imports"] += 1
            result["imported_modules"].append(node.module)

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                result["num_calls"] += 1
                result["function_calls"].append(func_name)

                if func_name in ("eval", "exec"):
                    result["security_warnings"].append({
                        "message": f"Critical Risk: Dangerous function '{func_name}' used.",
                        "line": node.lineno,
                        "col": node.col_offset,
                    })

            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
                result["num_calls"] += 1
                result["function_calls"].append(func_name)

                if func_name == "system" and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                    result["security_warnings"].append({
                        "message": "Medium Risk: Command execution 'os.system()' found.",
                        "line": node.lineno,
                        "col": node.col_offset,
                    })

        for child in ast.iter_child_nodes(node):
            walk_node(child, current_depth)

    walk_node(tree, 0)

    if total_documentable_items > 0:
        coverage = (items_with_docstrings / total_documentable_items) * 100
        result["docstring_coverage_pct"] = round(coverage, 2)
    else:
        result["docstring_coverage_pct"] = 100.0

    return result
