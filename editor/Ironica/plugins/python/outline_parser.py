"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Python outline parser for the Python language plugin.
"""

import ast

from editor.utils.file_properties.outline import OutlineNode, OutlineResult, SymbolKind


def parse_python_outline(source_code: str) -> OutlineResult:
    """Parse Python source into an outline tree using the ``ast`` module.

    Produces nodes for top-level and nested classes, functions, async
    functions, and module-level assignments.

    Args:
        source_code: Raw Python source text.

    Returns:
        ``OutlineResult`` with a file-level root node.
    """
    root = OutlineNode(name="", kind=SymbolKind.FILE)

    if not source_code or not source_code.strip():
        return OutlineResult(root=root, language="python")

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return OutlineResult(root=root, language="python")

    lines = source_code.splitlines()

    def _get_end_line(node: ast.AST) -> int:
        """Return the 0-indexed last line of an AST node."""
        if hasattr(node, "end_lineno") and node.end_lineno is not None:
            return node.end_lineno - 1
        return getattr(node, "lineno", 1) - 1

    def _collect_decorators(node: ast.AST) -> list[str]:
        """Extract decorator names from a class or function node."""
        names: list[str] = []
        for dec in getattr(node, "decorator_list", []):
            if isinstance(dec, ast.Name):
                names.append(f"@{dec.id}")
            elif isinstance(dec, ast.Attribute):
                names.append(f"@{dec.attr}")
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    names.append(f"@{dec.func.id}")
                elif isinstance(dec.func, ast.Attribute):
                    names.append(f"@{dec.func.attr}")
                else:
                    names.append("@...")
            else:
                names.append("@...")
        return names

    def _build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Build a minimal signature string for display."""
        parts: list[str] = []
        args = node.args

        all_args = args.posonlyargs + args.args
        defaults_offset = len(all_args) - len(args.defaults)

        for i, arg in enumerate(all_args):
            prefix = ""
            if i >= defaults_offset:
                default = args.defaults[i - defaults_offset]
                if isinstance(default, ast.Constant):
                    prefix = f"={repr(default.value)}"
                else:
                    prefix = "=..."
            ann = ""
            if arg.annotation:
                ann = (
                    f": {ast.get_source_segment(source_code, arg.annotation) or '...'}"
                )
            parts.append(f"{arg.arg}{ann}{prefix}")

        if args.vararg:
            parts.append(f"*{args.vararg.arg}")
        elif args.kwonlyargs:
            parts.append("*")

        for i, arg in enumerate(args.kwonlyargs):
            ann = ""
            if arg.annotation:
                ann = (
                    f": {ast.get_source_segment(source_code, arg.annotation) or '...'}"
                )
            default = ""
            if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
                default = "=..."
            parts.append(f"{arg.arg}{ann}{default}")

        if args.kwarg:
            parts.append(f"**{args.kwarg.arg}")

        ret = ""
        if node.returns:
            ret_ann = ast.get_source_segment(source_code, node.returns) or "..."
            ret = f" -> {ret_ann}"

        async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        return f"{async_prefix}def {node.name}({', '.join(parts)}){ret}"

    def _process_class(node: ast.ClassDef) -> OutlineNode:
        """Process a class definition into an OutlineNode."""
        end = _get_end_line(node)

        decorators = _collect_decorators(node)

        bases: list[str] = []
        for base in node.bases:
            seg = ast.get_source_segment(source_code, base)
            if seg:
                bases.append(seg)
        detail = f"({', '.join(bases)})" if bases else ""

        class_node = OutlineNode(
            name=node.name,
            kind=SymbolKind.CLASS,
            line_start=node.lineno - 1,
            line_end=end,
            col_start=node.col_offset,
            detail=detail,
        )

        for dec_name in decorators:
            class_node.children.append(
                OutlineNode(
                    name=dec_name,
                    kind=SymbolKind.DECORATOR,
                    line_start=node.lineno - 1,
                    line_end=node.lineno - 1,
                )
            )

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                class_node.children.append(_process_method(item, is_class_method=True))
            elif isinstance(item, ast.ClassDef):
                class_node.children.append(_process_class(item))
            elif isinstance(item, (ast.Assign, ast.AnnAssign)):
                for var_node in _process_assignment(item):
                    class_node.children.append(var_node)

        return class_node

    def _process_method(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_class_method: bool = True,
    ) -> OutlineNode:
        """Process a function/method definition into an OutlineNode.

        Args:
            node: The AST function node.
            is_class_method: ``True`` when the function is inside a class
                body (displayed as METHOD), ``False`` for top-level
                functions (displayed as FUNCTION).
        """
        end = _get_end_line(node)
        sig = _build_signature(node)

        decorators = _collect_decorators(node)

        if is_class_method:
            kind = SymbolKind.METHOD
        else:
            kind = SymbolKind.FUNCTION

        method_node = OutlineNode(
            name=node.name,
            kind=kind,
            line_start=node.lineno - 1,
            line_end=end,
            col_start=node.col_offset,
            detail=sig,
        )

        for dec_name in decorators:
            method_node.children.append(
                OutlineNode(
                    name=dec_name,
                    kind=SymbolKind.DECORATOR,
                    line_start=node.lineno - 1,
                    line_end=node.lineno - 1,
                )
            )

        return method_node

    def _process_assignment(node: ast.AST) -> list[OutlineNode]:
        """Process an assignment into variable/constant nodes."""
        nodes: list[OutlineNode] = []
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    kind = (
                        SymbolKind.CONSTANT
                        if target.id.isupper()
                        else SymbolKind.VARIABLE
                    )
                    nodes.append(
                        OutlineNode(
                            name=target.id,
                            kind=kind,
                            line_start=node.lineno - 1,
                            line_end=_get_end_line(node),
                            col_start=node.col_offset,
                        )
                    )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            kind = (
                SymbolKind.CONSTANT if node.target.id.isupper() else SymbolKind.VARIABLE
            )
            ann = ""
            if node.annotation:
                ann = ast.get_source_segment(source_code, node.annotation) or ""
            nodes.append(
                OutlineNode(
                    name=node.target.id,
                    kind=kind,
                    line_start=node.lineno - 1,
                    line_end=_get_end_line(node),
                    col_start=node.col_offset,
                    detail=ann,
                )
            )
        return nodes

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            root.children.append(_process_class(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            root.children.append(_process_method(node, is_class_method=False))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            root.children.extend(_process_assignment(node))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            end = _get_end_line(node)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root.children.append(
                        OutlineNode(
                            name=alias.name,
                            kind=SymbolKind.IMPORT,
                            line_start=node.lineno - 1,
                            line_end=end,
                            col_start=node.col_offset,
                        )
                    )
            else:
                module = node.module or ""
                names = ", ".join(a.name for a in node.names)
                root.children.append(
                    OutlineNode(
                        name=names,
                        kind=SymbolKind.IMPORT,
                        line_start=node.lineno - 1,
                        line_end=end,
                        col_start=node.col_offset,
                    )
                )

    return OutlineResult(root=root, language="python")
