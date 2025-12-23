import re
import ast


class PythonHighlighterBase:
    def __init__(self, text_box, path=None):
        self.text_box = text_box
        self.path = path
        self._after_id = None
        self.identifier_cache = {"functions": set(), "classes": set()}
        self.imports = set()

        # Words categories
        self.BLUE_WORDS = {
            "and",
            "class",
            "def",
            "False",
            "global",
            "in",
            "is",
            "lambda",
            "None",
            "nonlocal",
            "not",
            "or",
            "True",
            "self",
            "__name__",
        }
        self.PINK_WORDS = {
            "as",
            "assert",
            "async",
            "await",
            "break",
            "case",
            "continue",
            "del",
            "elif",
            "else",
            "except",
            "finally",
            "for",
            "from",
            "if",
            "import",
            "match",
            "pass",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield",
        }
        self.YELLOW_FUNCTIONS = {
            "abs",
            "all",
            "any",
            "ascii",
            "bin",
            "bool",
            "bytearray",
            "bytes",
            "chr",
            "complex",
            "dict",
            "divmod",
            "enumerate",
            "filter",
            "float",
            "format",
            "frozenset",
            "hash",
            "hex",
            "id",
            "int",
            "len",
            "list",
            "map",
            "max",
            "min",
            "next",
            "oct",
            "ord",
            "pow",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "slice",
            "sorted",
            "str",
            "sum",
            "tuple",
            "type",
            "zip",
            "print",
            "input",
            "dir",
            "help",
            "globals",
            "locals",
            "capitalize",
            "casefold",
            "center",
            "count",
            "encode",
            "endswith",
            "expandtabs",
            "find",
            "format_map",
            "index",
            "isalnum",
            "isalpha",
            "isdecimal",
            "isdigit",
            "isidentifier",
            "islower",
            "isnumeric",
            "isprintable",
            "isspace",
            "istitle",
            "isupper",
            "join",
            "ljust",
            "lower",
            "lstrip",
            "maketrans",
            "partition",
            "replace",
            "rfind",
            "rindex",
            "rjust",
            "rpartition",
            "rsplit",
            "rstrip",
            "split",
            "splitlines",
            "startswith",
            "strip",
            "swapcase",
            "title",
            "translate",
            "upper",
            "zfill",
            "append",
            "extend",
            "insert",
            "remove",
            "pop",
            "clear",
            "sort",
            "reverse",
            "copy",
            "add",
            "difference",
            "difference_update",
            "discard",
            "intersection",
            "intersection_update",
            "isdisjoint",
            "issubset",
            "issuperset",
            "symmetric_difference",
            "symmetric_difference_update",
            "union",
            "update",
        }
        self.GREEN_FUNCTIONS = {
            "callable",
            "classmethod",
            "compile",
            "delattr",
            "eval",
            "exec",
            "getattr",
            "hasattr",
            "isinstance",
            "issubclass",
            "memoryview",
            "object",
            "property",
            "setattr",
            "staticmethod",
            "super",
            "vars",
            "__import__",
        }
        self.ORANGE_REDDISH = {
            "BaseException",
            "Exception",
            "ArithmeticError",
            "AssertionError",
            "AttributeError",
            "BufferError",
            "EOFError",
            "FloatingPointError",
            "GeneratorExit",
            "ImportError",
            "ModuleNotFoundError",
            "IndexError",
            "KeyError",
            "KeyboardInterrupt",
            "MemoryError",
            "NameError",
            "FileNotFoundError",
            "NotImplementedError",
            "OSError",
            "OverflowError",
            "RecursionError",
            "ReferenceError",
            "RuntimeError",
            "StopIteration",
            "StopAsyncIteration",
            "SyntaxError",
            "IndentationError",
            "TabError",
            "SystemError",
            "SystemExit",
            "TypeError",
            "UnboundLocalError",
            "ValueError",
            "ZeroDivisionError",
        }
        self.PURPLE = {
            "+",
            "-",
            "*",
            "/",
            "//",
            "%",
            "**",
            "@",
            "=",
            "+=",
            "-=",
            "*=",
            "/=",
            "//=",
            "%=",
            "**=",
            "@=",
            "&=",
            "|=",
            "^=",
            "<<=",
            "<<",
            ">>=",
        }
        self.GREENISH = {"==", "!=", ">", "<", ">=", "<="}
        self.BLUEISH = {"&", "|", "^", "~", "<<", ">>"}
        self.YELLOW = {"(", ")", "{", "}", "[", "]"}
        self.SPECIAL = {"if not", "is not", "is True", "is False"}

        # Regex precompilation
        self._blue_re = self._make_word_re(self.BLUE_WORDS)
        self._pink_re = self._make_word_re(self.PINK_WORDS)
        self._special_re = self._make_word_re(self.SPECIAL)
        self._yellow_func_re = self._make_word_re(self.YELLOW_FUNCTIONS)
        self._green_func_re = self._make_word_re(self.GREEN_FUNCTIONS)
        self._exception_re = self._make_word_re(self.ORANGE_REDDISH)
        self._ops_re = re.compile(
            "|".join(
                sorted(
                    map(re.escape, self.PURPLE | self.GREENISH | self.BLUEISH),
                    key=len,
                    reverse=True,
                )
            )
        )
        self._number_re = re.compile(r"\b\d+(\.\d+)?\b")
        self._dot_call_re = re.compile(
            r"\b([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*(?=\()"
        )
        self._import_re = re.compile(
            r"\bimport\s+([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)"
        )
        self._from_import_re = re.compile(
            r"\bfrom\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s+import\s+([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)"
        )
        self._triple_string_re = re.compile(r"('''.*?'''|\"\"\".*?\"\"\")", re.DOTALL)
        self._single_string_re = re.compile(r"(\".*?\"|'.*?')")

        self.text_box.bind("<KeyRelease>", self._on_key_release)

    def _make_word_re(self, words):
        if not words:
            return re.compile(r"(?!x)x")
        esc = sorted((re.escape(w) for w in words), key=len, reverse=True)
        return re.compile(r"\b(?:" + "|".join(esc) + r")\b")

    def _abs_to_index(self, abs_pos, code):
        line = code.count("\n", 0, abs_pos) + 1
        last_n = code.rfind("\n", 0, abs_pos)
        col = abs_pos - last_n - 1 if last_n != -1 else abs_pos
        return f"{line}.{col}"

    def _overlaps_any(self, start, end, spans):
        for a, b in spans:
            if not (end <= a or start >= b):
                return True
        return False

    def _on_key_release(self, event):
        if self._after_id:
            self.text_box.after_cancel(self._after_id)
        self._after_id = self.text_box.after(100, self.update_highlight_and_completions)

    def update_highlight_and_completions(self):
        code = self.text_box.get("1.0", "end-1c")
        ids, imports = self.parse_identifiers_and_imports(code)
        self.identifier_cache = ids
        self.imports = imports
        self.highlight_code(code)

    def highlight_code(self, code):
        self.text_box.tag_remove("all", "1.0", "end")
        triple_spans = [
            (m.start(), m.end()) for m in self._triple_string_re.finditer(code)
        ]
        single_spans = [
            (m.start(), m.end()) for m in self._single_string_re.finditer(code)
        ]
        comment_spans = [(m.start(), m.end()) for m in re.finditer(r"#.*", code)]
        protected_spans = triple_spans + single_spans + comment_spans

        for s, e in triple_spans + single_spans:
            self.text_box.tag_add(
                f"string_{s}", self._abs_to_index(s, code), self._abs_to_index(e, code)
            )
            self.text_box.tag_config(f"string_{s}", foreground=self.colors["string"])
        for s, e in comment_spans:
            self.text_box.tag_add(
                f"comment_{s}", self._abs_to_index(s, code), self._abs_to_index(e, code)
            )
            self.text_box.tag_config(f"comment_{s}", foreground=self.colors["comment"])

        abs_pos = 0
        mcall_spans = []
        lines = code.splitlines(keepends=True)
        for line in lines:
            line_start = abs_pos

            for m in self._number_re.finditer(line):
                s = line_start + m.start()
                e = line_start + m.end()
                if self._overlaps_any(s, e, protected_spans):
                    continue
                self.text_box.tag_add(
                    f"num_{s}", self._abs_to_index(s, code), self._abs_to_index(e, code)
                )
                self.text_box.tag_config(f"num_{s}", foreground=self.colors["number"])

            for regex, color in [
                (self._blue_re, "blue_keyword"),
                (self._pink_re, "pink_keyword"),
                (self._special_re, "special_keyword"),
            ]:
                for m in regex.finditer(line):
                    s = line_start + m.start()
                    e = line_start + m.end()
                    if self._overlaps_any(s, e, protected_spans):
                        continue
                    self.text_box.tag_add(
                        f"kw_{s}",
                        self._abs_to_index(s, code),
                        self._abs_to_index(e, code),
                    )
                    self.text_box.tag_config(f"kw_{s}", foreground=self.colors[color])

            for regex, color, words in [
                (
                    self._yellow_func_re,
                    "yellow_function",
                    self.identifier_cache.get("functions", set()),
                ),
                (self._green_func_re, "green_function", self.GREEN_FUNCTIONS),
                (self._exception_re, "exception", self.ORANGE_REDDISH),
            ]:
                for m in regex.finditer(line):
                    s = line_start + m.start()
                    e = line_start + m.end()
                    if self._overlaps_any(s, e, protected_spans):
                        continue
                    self.text_box.tag_add(
                        f"func_{s}",
                        self._abs_to_index(s, code),
                        self._abs_to_index(e, code),
                    )
                    self.text_box.tag_config(f"func_{s}", foreground=self.colors[color])

            for m in self._ops_re.finditer(line):
                s = line_start + m.start()
                e = line_start + m.end()
                if self._overlaps_any(s, e, protected_spans):
                    continue
                self.text_box.tag_add(
                    f"op_{s}", self._abs_to_index(s, code), self._abs_to_index(e, code)
                )
                self.text_box.tag_config(f"op_{s}", foreground=self.colors["operator"])

            for br in self.YELLOW:
                for mm in re.finditer(re.escape(br), line):
                    s = line_start + mm.start()
                    e = line_start + mm.end()
                    if self._overlaps_any(s, e, protected_spans):
                        continue
                    self.text_box.tag_add(
                        f"br_{s}",
                        self._abs_to_index(s, code),
                        self._abs_to_index(e, code),
                    )
                    self.text_box.tag_config(
                        f"br_{s}", foreground=self.colors["bracket"]
                    )

            # Remove variable & attribute highlighting
            # Removed loops for self.identifier_cache["variables"] and _dot_attr_re

            for m in self._dot_call_re.finditer(line):
                qual = m.group(1)
                name = m.group(2)
                s_qual = line_start + m.start(1)
                e_qual = s_qual + len(qual)
                s_name = line_start + m.start(2)
                e_name = s_name + len(name)
                if self._overlaps_any(s_qual, e_name, protected_spans):
                    continue
                if qual in self.imports:
                    self.text_box.tag_add(
                        f"modq_{s_qual}",
                        self._abs_to_index(s_qual, code),
                        self._abs_to_index(e_qual, code),
                    )
                    self.text_box.tag_config(
                        f"modq_{s_qual}", foreground=self.colors["class"]
                    )
                self.text_box.tag_add(
                    f"mcall_{s_name}",
                    self._abs_to_index(s_name, code),
                    self._abs_to_index(e_name, code),
                )
                self.text_box.tag_config(
                    f"mcall_{s_name}", foreground=self.colors["function"]
                )
                mcall_spans.append((s_name, e_name))

            # Imports
            for m in self._import_re.finditer(line):
                names = [n.strip() for n in m.group(1).split(",")]
                for n in names:
                    s = line_start + m.start(1) + m.group(1).find(n)
                    e = s + len(n)
                    if self._overlaps_any(s, e, protected_spans):
                        continue
                    self.imports.add(n)
                    self.text_box.tag_add(
                        f"imp_{s}",
                        self._abs_to_index(s, code),
                        self._abs_to_index(e, code),
                    )
                    self.text_box.tag_config(
                        f"imp_{s}", foreground=self.colors["module"]
                    )
            for m in self._from_import_re.finditer(line):
                pkg = m.group(1)
                items_str = m.group(2)
                pkg_s = line_start + m.start(1)
                pkg_e = pkg_s + len(pkg)
                if not self._overlaps_any(pkg_s, pkg_e, protected_spans):
                    self.imports.add(pkg.split(".")[0])
                    self.text_box.tag_add(
                        f"pkg_{pkg_s}",
                        self._abs_to_index(pkg_s, code),
                        self._abs_to_index(pkg_e, code),
                    )
                    self.text_box.tag_config(
                        f"pkg_{pkg_s}", foreground=self.colors["module"]
                    )
                items = [it.strip() for it in items_str.split(",")]
                for it in items:
                    it_offset = items_str.find(it)
                    s = line_start + m.start(2) + it_offset
                    e = s + len(it)
                    if self._overlaps_any(s, e, protected_spans):
                        continue
                    self.imports.add(it)
                    self.text_box.tag_add(
                        f"imp2_{s}",
                        self._abs_to_index(s, code),
                        self._abs_to_index(e, code),
                    )
                    self.text_box.tag_config(
                        f"imp2_{s}", foreground=self.colors["module"]
                    )

            abs_pos += len(line)

    def parse_identifiers_and_imports(self, code):
        identifiers = {"functions": set(), "classes": set()}
        imports = set()
        try:
            tree = ast.parse(code)
        except Exception:
            return identifiers, imports

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                identifiers["functions"].add(node.name)
                self.generic_visit(node)

            def visit_ClassDef(self, node):
                identifiers["classes"].add(node.name)
                self.generic_visit(node)

            def visit_Import(self, node):
                for n in node.names:
                    imports.add(n.name)

            def visit_ImportFrom(self, node):
                for n in node.names:
                    imports.add(n.name)

        Visitor().visit(tree)
        return identifiers, imports


class PythonHighlighterDark(PythonHighlighterBase):
    def __init__(self, text_box, path=None):
        super().__init__(text_box, path)
        self.colors = {
            "blue_keyword": "#8DA8FF",
            "pink_keyword": "#FD8DA3",
            "yellow_function": "#DCDCAA",
            "green_function": "#4EC9B0",
            "exception": "#F44747",  # exceptions
            "function": "#DCDCAA",  # user-defined functions
            "class": "#4EC9B0",  # class names
            "module": "#9CDCFE",  # imported modules
            "string": "#5FCCA3",  # string literals
            "comment": "#8E8E8E",
            "number": "#B5CEA8",  # numbers
            "operator": "#D4D4D4",  # operators
            "bracket": "#D4D4D4",  # brackets
            "special_keyword": "#569CD6",  # special keywords like is not
        }


class PythonHighlighterLight(PythonHighlighterBase):
    def __init__(self, text_box, path=None):
        super().__init__(text_box, path)
        self.colors = {
            "blue_keyword": "#0000FF",  # keywords like def, class, return
            "pink_keyword": "#FF00FF",  # flow control, async/await
            "yellow_function": "#B8860B",  # built-in functions
            "green_function": "#008B8B",  # special functions
            "exception": "#FF0000",  # exceptions
            "function": "#00008B",  # user-defined functions
            "class": "#800080",  # class names
            "module": "#000080",  # imported modules
            "string": "#A52A2A",  # string literals
            "comment": "#008000",  # comments
            "number": "#FF4500",  # numbers
            "operator": "#000000",  # operators
            "bracket": "#000000",  # brackets
            "special_keyword": "#0000FF",  # special keywords like is not
        }
