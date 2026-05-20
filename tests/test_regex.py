import re

_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _is_python_keyword(word: str) -> bool:
    keywords = {
        "False", "None", "True", "and", "as", "assert", "async", "await",
        "break", "class", "continue", "def", "del", "elif", "else", "except",
        "finally", "for", "from", "global", "if", "import", "in", "is",
        "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
        "try", "while", "with", "yield",
    }
    return word in keywords


class TestWordRegex:
    def test_matches_simple_identifier(self):
        m = _WORD_RE.match("foo")
        assert m is not None
        assert m.group() == "foo"

    def test_matches_identifier_with_underscore(self):
        m = _WORD_RE.match("my_var_1")
        assert m is not None
        assert m.group() == "my_var_1"

    def test_matches_leading_underscore(self):
        m = _WORD_RE.match("_private")
        assert m is not None
        assert m.group() == "_private"

    def test_matches_dunder(self):
        m = _WORD_RE.match("__init__")
        assert m is not None
        assert m.group() == "__init__"

    def test_matches_upper_case(self):
        m = _WORD_RE.match("JSONParser")
        assert m is not None
        assert m.group() == "JSONParser"

    def test_rejects_empty_string(self):
        m = _WORD_RE.match("")
        assert m is None

    def test_rejects_leading_digit(self):
        m = _WORD_RE.match("1var")
        assert m is None

    def test_rejects_dot_notation(self):
        m = _WORD_RE.match("os.path")
        assert m is not None
        assert m.group() == "os"

    def test_rejects_dollar_sign(self):
        m = _WORD_RE.match("$pecial")
        assert m is None

    def test_full_match_not_just_prefix(self):
        text = "print()"
        matches = list(_WORD_RE.finditer(text))
        assert len(matches) == 1
        assert matches[0].group() == "print"

    def test_multiple_matches_in_line(self):
        text = "x = foo + bar"
        matches = [m.group() for m in _WORD_RE.finditer(text)]
        assert matches == ["x", "foo", "bar"]

    def test_finditer_span_is_correct(self):
        text = "abc def"
        m = list(_WORD_RE.finditer(text))[0]
        assert m.span() == (0, 3)
        assert text[m.start():m.end()] == "abc"

    def test_single_letter(self):
        m = _WORD_RE.match("a")
        assert m is not None
        assert m.group() == "a"

    def test_single_underscore(self):
        m = _WORD_RE.match("_")
        assert m is not None
        assert m.group() == "_"

    def test_unicode_not_matched(self):
        m = _WORD_RE.match("café")
        assert m is not None
        assert m.group() == "caf"


class TestPythonKeyword:
    def test_all_python_keywords_are_recognized(self):
        known = {
            "False", "None", "True", "and", "as", "assert", "async", "await",
            "break", "class", "continue", "def", "del", "elif", "else", "except",
            "finally", "for", "from", "global", "if", "import", "in", "is",
            "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
            "try", "while", "with", "yield",
        }
        for kw in known:
            assert _is_python_keyword(kw), f"{kw!r} should be a keyword"

    def test_builtins_not_confused_as_keywords(self):
        not_keywords = ["print", "len", "str", "int", "list", "dict",
                        "range", "enumerate", "zip", "map", "filter",
                        "open", "type", "isinstance", "super", "object"]
        for name in not_keywords:
            assert not _is_python_keyword(name), f"{name!r} should NOT be a keyword"

    def test_identifiers_not_keywords(self):
        not_keywords = ["my_function", "MyClass", "variable", "_helper",
                        "calculate", "process_data", "handleEvent"]
        for name in not_keywords:
            assert not _is_python_keyword(name), f"{name!r} should NOT be a keyword"
