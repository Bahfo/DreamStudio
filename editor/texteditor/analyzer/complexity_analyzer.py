import ast

def analyze_python_complexity(source_code: str, file_path: str = None) -> dict:
    result = {
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
        
        "cyclomatic_complexity": 1,
        "max_nesting_depth": 0,
        "bare_except_warnings": 0,
    }

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return result

    total_documentable_items = 0
    items_with_docstrings = 0

    def walk_node(node, current_depth):
        nonlocal total_documentable_items, items_with_docstrings

        if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try, ast.IfExp, ast.BoolOp)):
            result["cyclomatic_complexity"] += 1

        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While)):
            current_depth += 1
            if current_depth > result["max_nesting_depth"]:
                result["max_nesting_depth"] = current_depth

        if isinstance(node, ast.ExceptHandler) and node.type is None:
            result["bare_except_warnings"] += 1

        if isinstance(node, ast.ClassDef):
            result["num_classes"] += 1
            result["classes"].append(node.name)
            total_documentable_items += 1
            if ast.get_docstring(node):
                items_with_docstrings += 1
            else:
                result["missing_docstrings"].append(f"Class: {node.name}")

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["num_functions"] += 1
            result["functions"].append(node.name)
            total_documentable_items += 1
            if ast.get_docstring(node):
                items_with_docstrings += 1
            else:
                result["missing_docstrings"].append(f"Function: {node.name}")

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
                    result["security_warnings"].append(
                        f"Critical Risk: Dangerous function '{func_name}' used at line {node.lineno}."
                    )
            
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
                result["num_calls"] += 1
                result["function_calls"].append(func_name)
                
                if func_name == "system" and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                    result["security_warnings"].append(
                        f"Medium Risk: Command execution 'os.system()' found at line {node.lineno}."
                    )

        for child in ast.iter_child_nodes(node):
            walk_node(child, current_depth)

    walk_node(tree, 0)

    if total_documentable_items > 0:
        coverage = (items_with_docstrings / total_documentable_items) * 100
        result["docstring_coverage_pct"] = round(coverage, 2)
    else:
        result["docstring_coverage_pct"] = 100.0

    return result
