import ast
from typing import Set, Tuple

class SymbolExtractor:
    """Extract function, class, and variable names defined before a given line."""
    
    @staticmethod
    def get_defined_names_before_cursor(code: str, line: int) -> Set[str]:
        """
        Returns set of function, class, and variable names defined before the given line.
        
        Args:
            code: Full source code string
            line: Line number (1-indexed)
        
        Returns:
            Set of defined symbol names
        """
        try:
            # Only parse code up to the cursor line
            lines_before = code.splitlines()[:line]
            code_before = '\n'.join(lines_before)
            tree = ast.parse(code_before)
        except SyntaxError:
            # If there's a syntax error, try to parse what we can
            try:
                tree = ast.parse('\n'.join(code.splitlines()[:line-1]))
            except SyntaxError:
                return set()
        
        names = set()
        
        for node in ast.walk(tree):
            # Extract function names
            if isinstance(node, ast.FunctionDef):
                names.add(node.name)
            # Extract class names
            elif isinstance(node, ast.ClassDef):
                names.add(node.name)
            # Extract variable assignments
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
                    elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name):
                                names.add(elt.id)
            # Extract import names
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    names.add(alias.asname or alias.name)
            # Extract for-loop variables
            elif isinstance(node, ast.For):
                if isinstance(node.target, ast.Name):
                    names.add(node.target.id)
                elif isinstance(node.target, (ast.Tuple, ast.List)):
                    for elt in node.target.elts:
                        if isinstance(elt, ast.Name):
                            names.add(elt.id)
        
        return names

    @staticmethod
    def is_name_accessible(name: str, defined_names: Set[str], builtin_names: Set[str]) -> bool:
        """
        Check if a name is accessible (defined before cursor or built-in).
        
        Args:
            name: Symbol name to check
            defined_names: Names defined before cursor
            builtin_names: Built-in/keyword names
        
        Returns:
            True if name is accessible, False otherwise
        """
        return name in defined_names or name in builtin_names