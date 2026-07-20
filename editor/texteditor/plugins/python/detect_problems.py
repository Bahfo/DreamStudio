# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""Stateless code analysis engine for Python source diagnostics.

This module accepts raw source text and returns structured Diagnostic dataclasses.
It utilizes a graceful degradation strategy: it relies on AST for perfect structural
evaluation, but falls back to native tokenization to maintain whole-file semantic
analysis (undefined names) even when syntax is actively broken during typing.
"""

from __future__ import annotations

import ast
import builtins
import io
import keyword
import logging
import re
import tokenize
from dataclasses import dataclass, field
from typing import List, Optional

import jedi

logger = logging.getLogger("DreamStudio.Diagnostics.Detector")

# ── Severity colour map ───────────────────────────────────────────
SEVERITY_COLORS: dict[str, str] = {
    "error": "#FF0000",
    "warning": "#FFD700",
    "info": "#00BFFF",
}

_VALID_NAMES = set(dir(builtins)) | set(keyword.kwlist)
if hasattr(keyword, "softkwlist"):
    _VALID_NAMES |= set(keyword.softkwlist)
_VALID_NAMES.update({"self", "cls"})


@dataclass(frozen=True)
class Diagnostic:
    line: int
    start_col: int
    end_col: int
    severity: str
    message: str
    color: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "color", SEVERITY_COLORS.get(self.severity, "#FF0000"))


def detect_problems(source: str, file_path: Optional[str] = None) -> List[Diagnostic]:
    """Analyse source and return every detected issue."""
    if not source.strip():
        return []

    diagnostics: List[Diagnostic] = []
    diagnostics.extend(_detect_jedi_issues(source, file_path))
    diagnostics.extend(_detect_ast_warnings(source))

    # Sort sequentially to prevent visual tearing when rendering UI overlays
    diagnostics.sort(key=lambda d: (d.line, d.start_col))
    return diagnostics


# ── Jedi-based detection (errors & semantic scoping) ──────────────


def _detect_jedi_issues(source: str, file_path: Optional[str]) -> List[Diagnostic]:
    results: List[Diagnostic] = []
    source_lines = source.splitlines()

    try:
        script = jedi.Script(code=source, path=file_path or "")

        # 1. Structural Syntax Error Detection (Jedi parso core)
        for err in script.get_syntax_errors():
            start_column = max(0, err.column)
            end_column = start_column + 1

            # Expand the error span across the entire broken token block
            if 0 < err.line <= len(source_lines):
                line_text = source_lines[err.line - 1]
                if start_column < len(line_text):
                    remainder = line_text[start_column:]
                    token_match = re.match(r"^([a-zA-Z0-9_]+)", remainder)
                    if token_match:
                        end_column = start_column + len(token_match.group(1))
                    else:
                        non_wp_match = re.match(r"^([^\s]+)", remainder)
                        if non_wp_match:
                            end_column = start_column + len(non_wp_match.group(1))

            results.append(
                Diagnostic(
                    line=err.line,
                    start_col=start_column,
                    end_col=end_column,
                    severity="error",
                    message=f"Syntax error: {err}",
                )
            )

        # 2. Semantic Checking (Undefined Names) with Fallback Logic
        try:
            tree = ast.parse(source)
            _collect_undefined_names_ast(script, tree, results)
        except SyntaxError:
            # If the user typed random words or invalid structures (def main:),
            # AST crashes. We fall back to standard tokenization to scan the WHOLE file.
            _collect_undefined_names_tokenize(script, source, results)

    except Exception as exc:
        logger.debug("Jedi analysis failed unexpectedly: %s", exc)

    return results


def _collect_undefined_names_ast(
    script: jedi.Script, tree: ast.Module, results: List[Diagnostic]
) -> None:
    """Perfect scoping resolution when the document syntax is valid."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            name = node.id
            if name in _VALID_NAMES:
                continue

            try:
                defs = script.infer(line=node.lineno, column=node.col_offset)
                if not defs:
                    goto_defs = script.goto(line=node.lineno, column=node.col_offset)
                    if not goto_defs:
                        results.append(
                            Diagnostic(
                                line=node.lineno,
                                start_col=node.col_offset,
                                end_col=node.col_offset + len(name),
                                severity="error",
                                message=f"Undefined name: '{name}'",
                            )
                        )
            except Exception:
                continue


def _collect_undefined_names_tokenize(
    script: jedi.Script, source: str, results: List[Diagnostic]
) -> None:
    """Bulletproof semantic scanning when document syntax is actively broken."""
    tokens = []
    try:
        # Generate token list ignoring structural indent/dedent failures
        for tok in tokenize.tokenize(io.BytesIO(source.encode("utf-8")).readline):
            tokens.append(tok)
    except Exception:
        pass  # Evaluate whatever tokens we successfully extracted before fatal string un-closures

    for i, tok in enumerate(tokens):
        if tok.type == tokenize.NAME:
            name = tok.string
            if name in _VALID_NAMES:
                continue

            # Heuristic defense: Avoid false-flagging object attributes (e.g., `sys.GARBAGE`)
            prev_tok = tokens[i - 1] if i > 0 else None
            if prev_tok and prev_tok.string == ".":
                continue

            try:
                defs = script.infer(line=tok.start[0], column=tok.start[1])
                if not defs:
                    goto_defs = script.goto(line=tok.start[0], column=tok.start[1])
                    if not goto_defs:
                        results.append(
                            Diagnostic(
                                line=tok.start[0],
                                start_col=tok.start[1],
                                end_col=tok.end[1],
                                severity="error",
                                message=f"Undefined name: '{name}'",
                            )
                        )
            except Exception:
                continue


# ── AST-based detection (warnings + info) ─────────────────────────


def _detect_ast_warnings(source: str) -> List[Diagnostic]:
    results: List[Diagnostic] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Warnings gracefully disable themselves while syntax is broken
        # to focus user attention on priority red errors.
        return results

    results.extend(_find_unused_imports(tree))
    results.extend(_find_unused_variables(tree, source))
    results.extend(_find_naming_violations(tree))

    return results


def _find_unused_imports(tree: ast.Module) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []
    all_names_used: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            all_names_used.add(node.id)
        elif isinstance(node, ast.Attribute):
            root = node
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                all_names_used.add(root.id)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name
                root_name = alias.name.split(".")[0]
                if root_name not in all_names_used and local_name not in all_names_used:
                    col = getattr(alias, "col_offset", getattr(node, "col_offset", 0))
                    diagnostics.append(
                        Diagnostic(
                            line=node.lineno,
                            start_col=col,
                            end_col=col + len(local_name),
                            severity="warning",
                            message=f"Unused import: '{local_name}'",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                local_name = alias.asname or alias.name
                if local_name != "*" and local_name not in all_names_used:
                    col = getattr(alias, "col_offset", getattr(node, "col_offset", 0))
                    diagnostics.append(
                        Diagnostic(
                            line=node.lineno,
                            start_col=col,
                            end_col=col + len(local_name),
                            severity="warning",
                            message=f"Unused import: '{local_name}'",
                        )
                    )

    return diagnostics


def _find_unused_variables(tree: ast.Module, source: str) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []

    class _UnusedVisitor(ast.NodeVisitor):
        def _check_scope(self, node: ast.AST) -> None:
            defined: dict[str, int] = {}
            used: set[str] = set()

            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    if isinstance(child.ctx, ast.Store):
                        defined.setdefault(child.id, child.lineno)
                    elif isinstance(child.ctx, (ast.Load, ast.Del)):
                        used.add(child.id)

            for name, lineno in defined.items():
                if not name.startswith("_") and name not in used:
                    src_lines = source.splitlines()
                    if lineno <= len(src_lines):
                        m = re.search(rf"\b{re.escape(name)}\b", src_lines[lineno - 1])
                        if m:
                            diagnostics.append(
                                Diagnostic(
                                    line=lineno,
                                    start_col=m.start(),
                                    end_col=m.end(),
                                    severity="warning",
                                    message=f"Unused variable: '{name}'",
                                )
                            )

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._check_scope(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._check_scope(node)
            self.generic_visit(node)

    _UnusedVisitor().visit(tree)
    return diagnostics


def _find_naming_violations(tree: ast.Module) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []
    _snake_case = re.compile(r"^[a-z_][a-z0-9_]*$")

    class _NamingVisitor(ast.NodeVisitor):
        def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            for arg in node.args.args:
                if arg.arg not in ("self", "cls") and not arg.arg.startswith("_"):
                    if not _snake_case.match(arg.arg):
                        diagnostics.append(
                            Diagnostic(
                                line=node.lineno,
                                start_col=arg.col_offset,
                                end_col=arg.col_offset + len(arg.arg),
                                severity="info",
                                message=f"PEP-8: parameter '{arg.arg}' should use snake_case",
                            )
                        )

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._check_function(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._check_function(node)
            self.generic_visit(node)

    _NamingVisitor().visit(tree)
    return diagnostics
