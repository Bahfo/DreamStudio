"""Tests for Python lexer regex patterns (both Jedi and fallback)."""

import re

_STR_PREFIX = r"(?:[rR](?:[bBfF])?|[bB][rR]?|[fF][rR]?|[uU])"

_TOKENS = [
    ("decorator", r"@\w+(?:\.\w+)*"),
]
_TOKENS.append(
    ("string3", _STR_PREFIX + r'?"""(?:[^"\\]|\\.|"(?!""))*"""|'
     + _STR_PREFIX + r"?" + r"'''(?:[^'\\]|\\.|'(?!''))*'''")
)
_TOKENS.append(
    ("fstring",
     r'(?:[fF][rR]|[rR][fF]|[fF])"(?:[^"\\]|\\.)*"|'
     r"(?:[fF][rR]|[rR][fF]|[fF])'(?:[^\'\\]|\\.)*'")
)
_TOKENS.append(
    ("string",
     r'(?:[rR][bB]|[bB][rR]|[rRbBuU])?"(?:[^"\\]|\\.)*"|'
     r"(?:[rR][bB]|[bB][rR]|[rRbBuU])?'(?:[^\'\\]|\\.)*'")
)
_TOKENS.append(("comment", r"#.*"))
_TOKENS.append(
    ("number_float",
     r"\b\d[_\d]*\.\d[_\d]*(?:[eE][+-]?\d[_\d]*)?[jJ]?\b|"
     r"\b\d[_\d]*\.(?:[jJ])?(?=\W|$)|"
     r"(?<!\w)\.\d[_\d]*(?:[eE][+-]?\d[_\d]*)?[jJ]?\b|"
     r"\b\d[_\d]*[eE][+-]?\d[_\d]*[jJ]?\b")
)
_TOKENS.append(
    ("number",
     r"\b0[xX][\da-fA-F][\da-fA-F_]*\b|"
     r"\b0[bB][01][01_]*\b|"
     r"\b0[oO][0-7][0-7_]*\b|"
     r"\b\d[_\d]*[jJ]?\b")
)
_TOKENS.append(
    ("operator",
     r"\*\*=|//=|<<=|>>=|->|:=|\.\.\.|"
     r"\*\*|//|<<|>>|==|!=|<=|>=|"
     r"[-+*/%&|^~<>!]=?|@=?|=")
)
_TOKENS.append(("punctuation", r"[;,.:()\[\]{}]"))
_TOKENS.append(("word", r"\b\w+\b"))
_TOKENS.append(("ws", r"\s+"))
_TOKENS.append(("other", r"."))

_JEDI_TOKEN_RE = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in _TOKENS)
)

_FALLBACK_TOKEN_RE = re.compile(
    r'(?P<string3>'
    + _STR_PREFIX + r'?"""(?:[^"\\]|\\.|"(?!""))*"""|'
    + _STR_PREFIX + r"?" + r"'''(?:[^'\\]|\\.|'(?!''))*''')|"
    r'(?P<string>'
    r'(?:[rR][bB]|[bB][rR]|[rRbBuU])?"(?:[^"\\]|\\.)*"|'
    r"(?:[rR][bB]|[bB][rR]|[rRbBuU])?'(?:[^\'\\]|\\.)*')|"
    r"(?P<comment>#.*)|"
    r"(?P<number_float>"
    r"\b\d[_\d]*\.\d[_\d]*(?:[eE][+-]?\d[_\d]*)?[jJ]?\b|"
    r"\b\d[_\d]*\.(?:[jJ])?(?=\W|$)|"
    r"(?<!\w)\.\d[_\d]*(?:[eE][+-]?\d[_\d]*)?[jJ]?\b|"
    r"\b\d[_\d]*[eE][+-]?\d[_\d]*[jJ]?\b"
    r")|"
    r"(?P<number_int>"
    r"\b0[xX][\da-fA-F][\da-fA-F_]*\b|"
    r"\b0[bB][01][01_]*\b|"
    r"\b0[oO][0-7][0-7_]*\b|"
    r"\b\d[_\d]*[jJ]?\b"
    r")|"
    r"(?P<word>\b\w+\b)|"
    r"(?P<ws>\s+)|"
    r"(?P<other>.)"
)

_CAPITAL_WORD_RE = re.compile(r"\b[A-Z][A-Z0-9_]*\b")


def _tokenize(text: str, regex: re.Pattern = _JEDI_TOKEN_RE):
    return list(regex.finditer(text))


def _get_groups(tokens):
    return [(m.lastgroup, m.group()) for m in tokens]


class TestDecorator:
    def test_simple_decorator(self):
        tokens = _tokenize("@staticmethod\ndef foo(): pass")
        first = tokens[0]
        assert first.lastgroup == "decorator"
        assert first.group() == "@staticmethod"

    def test_chained_decorator(self):
        tokens = _tokenize("@app.route('/api')")
        assert tokens[0].lastgroup == "decorator"
        assert tokens[0].group() == "@app.route"

    def test_no_word_after_at(self):
        tokens = _tokenize("@")
        assert tokens[0].lastgroup != "decorator"

    def test_at_operator_not_decorator(self):
        tokens = _tokenize("x @ y")
        at_tok = [t for t in tokens if t.group() == "@"]
        assert at_tok
        assert at_tok[0].lastgroup != "decorator"


class TestString3:
    def test_triple_double(self):
        tokens = _tokenize('"""hello"""')
        assert tokens[0].lastgroup == "string3"
        assert tokens[0].group() == '"""hello"""'

    def test_triple_single(self):
        tokens = _tokenize("'''hello'''")
        assert tokens[0].lastgroup == "string3"
        assert tokens[0].group() == "'''hello'''"

    def test_raw_triple(self):
        tokens = _tokenize('r"""raw"""')
        assert tokens[0].lastgroup == "string3"
        assert tokens[0].group() == 'r"""raw"""'

    def test_multiline(self):
        code = '"""line one\nline two\nline three"""'
        tokens = _tokenize(code)
        assert tokens[0].lastgroup == "string3"
        assert tokens[0].group() == code

    def test_embedded_quote(self):
        code = """'''It's a "test"'''"""
        tokens = _tokenize(code)
        assert tokens[0].lastgroup == "string3"
        assert tokens[0].group() == code

    def test_escaped_quote(self):
        code = '"""hello \\"world\\""""'
        tokens = _tokenize(code)
        assert tokens[0].lastgroup == "string3"
        assert tokens[0].group() == '"""hello \\"world\\""""'

    def test_not_triple_empty(self):
        """Two quotes should not match string3."""
        tokens = _tokenize('""')
        assert tokens[0].lastgroup != "string3"


class TestFString:
    def test_fstring_double(self):
        tokens = _tokenize('f"hello {name}"')
        assert tokens[0].lastgroup == "fstring"
        assert tokens[0].group() == 'f"hello {name}"'

    def test_fstring_single(self):
        tokens = _tokenize("f'hello {name}'")
        assert tokens[0].lastgroup == "fstring"
        assert tokens[0].group() == "f'hello {name}'"

    def test_fstring_escaped(self):
        tokens = _tokenize(r'f"hello \"name\""')
        assert tokens[0].lastgroup == "fstring"
        assert tokens[0].group() == r'f"hello \"name\""'

    def test_fstring_raw(self):
        tokens = _tokenize(r'fr"hello {name}"')
        assert tokens[0].lastgroup == "fstring"


class TestString:
    def test_double_quoted(self):
        tokens = _tokenize('"hello"')
        assert tokens[0].lastgroup == "string"
        assert tokens[0].group() == '"hello"'

    def test_single_quoted(self):
        tokens = _tokenize("'hello'")
        assert tokens[0].lastgroup == "string"

    def test_raw_string(self):
        tokens = _tokenize(r'r"hello\nworld"')
        assert tokens[0].lastgroup == "string"

    def test_bytes_string(self):
        tokens = _tokenize('b"hello"')
        assert tokens[0].lastgroup == "string"

    def test_unicode_string(self):
        tokens = _tokenize('u"hello"')
        assert tokens[0].lastgroup == "string"

    def test_escaped_quotes(self):
        tokens = _tokenize(r'"hello \"world\""')
        assert tokens[0].lastgroup == "string"
        assert tokens[0].group() == r'"hello \"world\""'

    def test_single_quote_in_double(self):
        tokens = _tokenize('"it\'s ok"')
        assert tokens[0].lastgroup == "string"
        assert tokens[0].group() == '"it\'s ok"'

    def test_mismatched_quote_does_not_close(self):
        """A single-quoted string should not close on a double quote."""
        tokens = _tokenize("'hello \"world\"'")
        assert tokens[0].lastgroup == "string"
        assert tokens[0].group() == "'hello \"world\"'"

    def test_empty_string(self):
        tokens = _tokenize('""')
        assert tokens[0].lastgroup == "string"

    def test_identifier_before_quote(self):
        """x\"not a string\" — lexer doesn't validate syntax, strings are always styled."""
        tokens = _tokenize('x"not a string"')
        assert tokens[0].lastgroup == "word"
        assert tokens[1].lastgroup == "string"

    def test_rb_vs_br_prefix(self):
        tokens = _tokenize('rb"bytes" br"bytes"')
        assert tokens[0].lastgroup == "string"
        assert tokens[2].lastgroup == "string"


class TestComment:
    def test_simple_comment(self):
        tokens = _tokenize("# comment")
        assert tokens[0].lastgroup == "comment"
        assert tokens[0].group() == "# comment"

    def test_comment_with_utf8(self):
        tokens = _tokenize("# café ☕")
        assert tokens[0].lastgroup == "comment"

    def test_code_then_comment(self):
        tokens = _tokenize("x = 1  # inline")
        last = tokens[-1]
        assert last.lastgroup == "comment"


class TestNumberFloat:
    def test_simple_float(self):
        tokens = _tokenize("3.14")
        assert tokens[0].lastgroup == "number_float"
        assert tokens[0].group() == "3.14"

    def test_leading_dot(self):
        """.5 should be recognized as a float at line start."""
        tokens = _tokenize(".5")
        assert tokens[0].lastgroup == "number_float"
        assert tokens[0].group() == ".5"

    def test_leading_dot_in_expression(self):
        tokens = _tokenize("x = .5")
        float_tok = [t for t in tokens if t.group() == ".5"]
        assert float_tok
        assert float_tok[0].lastgroup == "number_float"

    def test_trailing_dot_is_float(self):
        """1. should be recognized as a float (trailing dot form)."""
        tokens = _tokenize("1.")
        assert tokens[0].lastgroup == "number_float"
        assert tokens[0].group() == "1."

    def test_dot_attribute_not_float(self):
        tokens = _tokenize("obj.attr")
        dot = [t for t in tokens if t.group() == "."]
        assert dot
        assert dot[0].lastgroup != "number_float"

    def test_scientific_notation(self):
        tokens = _tokenize("1e5")
        assert tokens[0].lastgroup == "number_float"

    def test_imaginary_float(self):
        tokens = _tokenize("3.14j")
        assert tokens[0].lastgroup == "number_float"

    def test_underscore_float(self):
        tokens = _tokenize("1_000.5")
        assert tokens[0].lastgroup == "number_float"

    def test_negative_float(self):
        tokens = _tokenize("-3.14")
        assert tokens[0].lastgroup == "operator"
        assert tokens[1].lastgroup == "number_float"

    def test_imaginary_suffix_only(self):
        """.5j should be a float with imaginary suffix."""
        tokens = _tokenize(".5j")
        assert tokens[0].lastgroup == "number_float"
        assert tokens[0].group() == ".5j"


class TestNumber:
    def test_integer(self):
        tokens = _tokenize("42")
        assert tokens[0].lastgroup == "number"
        assert tokens[0].group() == "42"

    def test_hex(self):
        tokens = _tokenize("0xFF")
        assert tokens[0].lastgroup == "number"

    def test_binary(self):
        tokens = _tokenize("0b1010")
        assert tokens[0].lastgroup == "number"

    def test_octal(self):
        tokens = _tokenize("0o777")
        assert tokens[0].lastgroup == "number"

    def test_underscore_int(self):
        tokens = _tokenize("1_000_000")
        assert tokens[0].lastgroup == "number"

    def test_imaginary_int(self):
        tokens = _tokenize("42j")
        assert tokens[0].lastgroup == "number"

    def test_identifier_not_number(self):
        tokens = _tokenize("var1")
        assert tokens[0].lastgroup == "word"

    def test_float_precedence(self):
        """3.14 should be a float, not two separate tokens."""
        tokens = _tokenize("3.14")
        assert tokens[0].lastgroup == "number_float"
        assert len(tokens) == 1

    def test_hex_vs_identifier(self):
        tokens = _tokenize("0x1A")
        assert tokens[0].lastgroup == "number"
        tokens2 = _tokenize("0xZZ")
        assert tokens2[0].lastgroup == "word"
        assert tokens2[0].group() == "0xZZ"


class TestOperator:
    def test_walrus(self):
        tokens = _tokenize(":=")
        assert tokens[0].lastgroup == "operator"
        assert tokens[0].group() == ":="

    def test_power(self):
        tokens = _tokenize("**")
        assert tokens[0].lastgroup == "operator"

    def test_power_assign(self):
        tokens = _tokenize("**=")
        assert tokens[0].lastgroup == "operator"

    def test_floor_division(self):
        tokens = _tokenize("//")
        assert tokens[0].lastgroup == "operator"

    def test_floor_division_assign(self):
        tokens = _tokenize("//=")
        assert tokens[0].lastgroup == "operator"

    def test_arrow(self):
        tokens = _tokenize("->")
        assert tokens[0].lastgroup == "operator"

    def test_each_operator(self):
        ops = [
            ":=", "**=", "**", "//=", "//", "<<=", ">>=",
            "<<", ">>", "==", "!=", "<=", ">=", "->",
            "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
            "~=", "<", ">", "=", "=", "+", "-", "*", "/",
            "%", "&", "|", "^", "~", "@=", "@", "...",
        ]
        for op in ops:
            tokens = _tokenize(op)
            assert tokens[0].lastgroup == "operator", (
                f"Operator {op!r} not recognized as operator"
            )
            assert tokens[0].group() == op, (
                f"Operator {op!r} has wrong match {tokens[0].group()!r}"
            )

    def test_equal_alone(self):
        tokens = _tokenize("x = 1")
        eq = [t for t in tokens if t.group() == "="]
        assert len(eq) == 1
        assert eq[0].lastgroup == "operator"

    def test_ellipsis(self):
        tokens = _tokenize("...")
        assert tokens[0].lastgroup == "operator"
        assert tokens[0].group() == "..."

    def test_dots_do_not_become_ellipsis_chain(self):
        tokens = _tokenize("...")
        assert len(tokens) == 1

    def test_ellipsis_precedence(self):
        """'...' should be one operator, not three '.' punctuations."""
        tokens = _tokenize("...")
        assert tokens[0].lastgroup == "operator"
        assert tokens[0].group() == "..."
        assert len(tokens) == 1


class TestPunctuation:
    def test_parens(self):
        for ch in "()[]{}:,;.":
            tokens = _tokenize(ch)
            assert tokens[0].lastgroup == "punctuation", (
                f"Char {ch!r} not recognized as punctuation"
            )


class TestWord:
    def test_simple(self):
        tokens = _tokenize("hello")
        assert tokens[0].lastgroup == "word"

    def test_with_underscore(self):
        tokens = _tokenize("my_var")
        assert tokens[0].lastgroup == "word"

    def test_dunder(self):
        tokens = _tokenize("__init__")
        assert tokens[0].lastgroup == "word"

    def test_numbers_not_words(self):
        tokens = _tokenize("42")
        assert tokens[0].lastgroup != "word"


class TestCapitalWord:
    def test_screaming_snake(self):
        assert _CAPITAL_WORD_RE.fullmatch("CONSTANT_NAME")

    def test_camel_case_not_matched(self):
        assert not _CAPITAL_WORD_RE.fullmatch("MyClass")

    def test_single_capital_letter(self):
        assert _CAPITAL_WORD_RE.fullmatch("X")

    def test_lowercase_not_matched(self):
        assert not _CAPITAL_WORD_RE.fullmatch("lowercase")


class TestFullTokenization:
    def test_function_def(self):
        code = "def my_function(arg1, arg2):"
        tokens = _tokenize(code)
        groups = [(t.lastgroup, t.group()) for t in tokens]
        assert ("word", "def") in groups
        assert ("word", "my_function") in groups
        assert ("word", "arg1") in groups
        assert ("word", "arg2") in groups
        assert ("punctuation", "(") in groups
        assert ("punctuation", ")") in groups
        assert ("punctuation", ":") in groups
        assert ("punctuation", ",") in groups

    def test_class_def(self):
        code = "class MyClass(Base):"
        tokens = _tokenize(code)
        groups = [(t.lastgroup, t.group()) for t in tokens]
        assert ("word", "class") in groups
        assert ("word", "MyClass") in groups
        assert ("word", "Base") in groups

    def test_import(self):
        code = "from os import path"
        tokens = _tokenize(code)
        groups = " ".join(t.lastgroup for t in tokens)
        assert "word" in groups

    def test_decorated_function(self):
        code = "@staticmethod\ndef my_func(): pass"
        tokens = _tokenize(code)
        groups = [(t.lastgroup, t.group()) for t in tokens]
        assert ("decorator", "@staticmethod") in groups
        assert ("word", "def") in groups
        assert ("word", "my_func") in groups

    def test_mixed_strings_and_code(self):
        code = 'x = f"hello {name}" + "world"'
        tokens = _tokenize(code)
        groups = [t.lastgroup for t in tokens]
        assert "fstring" in groups
        assert "string" in groups
        assert "operator" in groups

    def test_comment_at_end(self):
        code = "x = 1  # end"
        tokens = _tokenize(code)
        assert tokens[-1].lastgroup == "comment"

    def test_multiline_code(self):
        code = """x = 1
y = 2
z = x + y
"""
        tokens = _tokenize(code)
        assert len(tokens) > 0
        ws_count = sum(1 for t in tokens if t.lastgroup == "ws")
        assert ws_count > 0

    def test_no_unmatched_text(self):
        """Every byte of input should be covered by a token."""
        code = "x = foo/bar.baz@qux # end"
        total_len = sum(len(t.group()) for t in _tokenize(code))
        assert total_len == len(code)

    def test_utf8_ascii_only(self):
        """UTF-8 text within ASCII range should work fine."""
        code = "print('hello')"
        tokens = _tokenize(code)
        total_len = sum(len(t.group()) for t in tokens)
        assert total_len == len(code)


class TestFallbackLexerRegex:
    """Test the fallback lexer's regex patterns specifically."""

    def _ftokens(self, text):
        return list(_FALLBACK_TOKEN_RE.finditer(text))

    def test_triple_string(self):
        tokens = self._ftokens('"""hello"""')
        assert tokens[0].lastgroup == "string3"

    def test_single_string(self):
        tokens = self._ftokens('"hello"')
        assert tokens[0].lastgroup == "string"

    def test_number_float(self):
        tokens = self._ftokens("3.14")
        assert tokens[0].lastgroup == "number_float"

    def test_number_int(self):
        tokens = self._ftokens("42")
        assert tokens[0].lastgroup == "number_int"

    def test_number_hex(self):
        tokens = self._ftokens("0xFF")
        assert tokens[0].lastgroup == "number_int"

    def test_comment(self):
        tokens = self._ftokens("# comment")
        assert tokens[0].lastgroup == "comment"

    def test_word(self):
        tokens = self._ftokens("hello")
        assert tokens[0].lastgroup == "word"

    def test_no_operators_in_fallback(self):
        """Fallback lexer should NOT have an operator group."""
        pattern_str = _FALLBACK_TOKEN_RE.pattern
        assert "operator" not in pattern_str


class TestEdgeCases:
    """Edge cases that have been historically problematic."""

    def test_triple_quote_at_boundary(self):
        """Bare triple quotes without closing are tokenized as empty string + stray quote."""
        tokens = _tokenize('"""')
        assert tokens[0].lastgroup == "string"
        assert tokens[0].group() == '""'
        assert len(tokens) == 2
        assert tokens[1].lastgroup == "other"
        assert tokens[1].group() == '"'

    def test_escaped_backslash_before_quote(self):
        tokens = _tokenize(r'"hello \\"')
        assert tokens[0].lastgroup == "string"
        assert tokens[0].group() == r'"hello \\"'

    def test_multiple_escaped_quotes(self):
        tokens = _tokenize(r'"\"\'\""')
        assert tokens[0].lastgroup == "string"
        assert tokens[0].group() == r'"\"\'\""'

    def test_all_punctuation_in_expression(self):
        code = "if (a, b) == (c, d):"
        tokens = _tokenize(code)
        groups = [t.lastgroup for t in tokens]
        assert "punctuation" in groups
        assert "keyword_operator" not in [t.lastgroup for t in tokens]

    def test_very_long_number(self):
        n = "1234567890" * 10
        tokens = _tokenize(n)
        assert tokens[0].lastgroup == "number"

    def test_operator_precedence(self):
        """Walrus operator should take precedence over = and : separately."""
        tokens = _tokenize(":=")
        assert tokens[0].lastgroup == "operator"
        assert tokens[0].group() == ":="

    def test_triple_quote_not_confused_with_single(self):
        """A line with ''' should not interfere with nearby \"\"\"."""
        code = "'''single''' \"\"\"double\"\"\""
        tokens = _tokenize(code)
        assert tokens[0].lastgroup == "string3"
        assert tokens[0].group() == "'''single'''"
        assert tokens[1].lastgroup == "ws"
        assert tokens[2].lastgroup == "string3"
        assert tokens[2].group() == '"""double"""'

    def test_async_def(self):
        """async def should tokenize as word+ws+word."""
        tokens = _tokenize("async def foo(): pass")
        groups = [(t.lastgroup, t.group()) for t in tokens]
        assert ("word", "async") in groups
        assert ("word", "def") in groups
        assert ("word", "foo") in groups

    def test_binary_operator_vs_bitwise(self):
        """& and | should be operators."""
        tokens = _tokenize("a & b | c")
        op_tokens = [t for t in tokens if t.lastgroup == "operator"]
        op_vals = [t.group() for t in op_tokens]
        assert "&" in op_vals
        assert "|" in op_vals

    def test_shift_operators(self):
        tokens = _tokenize("a << b >> c")
        op_tokens = [t for t in tokens if t.lastgroup == "operator"]
        op_vals = [t.group() for t in op_tokens]
        assert "<<" in op_vals
        assert ">>" in op_vals

    def test_at_operator_in_matrix_mult(self):
        tokens = _tokenize("a @ b")
        at_tok = [t for t in tokens if t.group() == "@" and t.lastgroup == "operator"]
        assert len(at_tok) == 1
