"""
Stateless service analyzing Cyclomatic Complexity and Nesting Depth using AST.
Does not require imports, runtimes, or filesystem access.
"""

from editor import *
from ..domain_models import ComplexityReport, FunctionComplexity
from ..interfaces import IComplexityService


class ASTComplexityVisitor(ast.NodeVisitor):
    """Calculates nesting depth and cyclomatic complexity for each function declaration."""

    def __init__(self) -> None:
        self.functions: List[FunctionComplexity] = []
        self._current_nesting = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        complexity = 1
        max_nesting = 0

        # Traverse nodes inside this function to calculate complexity and nesting depth
        for child in ast.walk(node):
            # Branches increase cyclomatic complexity
            if isinstance(
                child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With)
            ):
                complexity += 1
            if isinstance(
                child, (ast.BoolOp)
            ):  # Logical checking (and/or splits paths)
                complexity += len(child.values) - 1

        def find_max_nesting(parent_node: ast.AST, current: int) -> int:
            nest_types = (ast.If, ast.For, ast.While, ast.Try)
            next_nest = current + 1 if isinstance(parent_node, nest_types) else current

            highest = next_nest
            for child in ast.iter_child_nodes(parent_node):
                highest = max(highest, find_max_nesting(child, next_nest))
            return highest

        max_nesting = find_max_nesting(node, 0)

        self.functions.append(
            FunctionComplexity(
                name=node.name,
                line=node.lineno,
                cyclomatic_complexity=complexity,
                nesting_depth=max_nesting,
            )
        )
        self.generic_visit(node)


class ComplexityAnalysisService(IComplexityService):
    """
    Stateless code metric assessment engine.
    """

    def analyze_source(self, source_code: str) -> ComplexityReport:
        """Parses the raw source string and collects AST measurements."""
        if not source_code.strip():
            return ComplexityReport(0, 0, 0, 1, [])

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            # Return basic metrics matching a broken parse gracefully
            return ComplexityReport(len(source_code.splitlines()), 0, 0, 1, [])

        # Count primary scopes
        classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        functions = sum(
            1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        )
        total_loc = len(source_code.splitlines())

        visitor = ASTComplexityVisitor()
        visitor.visit(tree)

        max_cc = max((f.cyclomatic_complexity for f in visitor.functions), default=1)

        return ComplexityReport(
            total_loc=total_loc,
            class_count=classes,
            function_count=functions,
            max_cyclomatic_complexity=max_cc,
            functions=visitor.functions,
        )
