"""Tests for the ``IronicaLexer`` bracket-depth styling cache.

The cache avoids re-scanning bracket depth from byte 0 on every
keystroke.  Its correctness invariant: bracket depth at a position is
identical whether computed in one scan or advanced incrementally across
several scans.

Covers:
- ``_scan_bracket_depth`` segment identity (a+b == ab) for all samples
- Incremental (cached) style path emitting identical styles to a cold
  full-rebuild, for comment/string-free code
- Sequential edits advancing the cache across multiple chunks
- An edit before the cache point falling back to a full rebuild
"""

import pytest
from PyQt6.Qsci import QsciScintilla

from editor.Ironica.regex import IronicaLexer

_CONFIG = {
    "lang": "test_lang",
    "styles": {"keyword": "#FF0000", "string": "#00FF00", "comment": "#888888"},
    "keywords": {"keyword": ["def", "class", "if"]},
}

_ALL_SAMPLES = [
    "def foo():\n    pass\n",
    "def foo(a, b=[1, (2, 3)]):\n    return (a + b) * {1: 2}\n",
    "# comment with ( brackets ) { never [ counted\ns = \"(string)\"\n",
    "if x:\n    y = [1, 2, 3\n    z = {\n    w = (a\n",
    "def a():\n    pass\n\ndef b():\n    pass\n\ndef c():\n    pass\n",
    "s = f\"{(lambda x: x + 1)(1)}\"\n",
]

# Comment/string-free bracket code: safe to split the style range anywhere.
_BRACKET_SAMPLES = [
    "def foo():\n    pass\n",
    "def foo(a, b=[1, (2, 3)]):\n    return (a + b) * {1: 2}\n",
    "if x:\n    y = [1, 2, 3\n    z = {\n    w = (a\n",
]


def _make_editor(qapp_instance):
    editor = QsciScintilla()
    editor.setUtf8(True)
    lexer = IronicaLexer(editor, _CONFIG)
    editor.setLexer(lexer)
    return editor, lexer


def _record_styling(lexer, start, end):
    """Run ``styleText`` and return the emitted ``(length, style)`` calls."""
    calls = []
    original = lexer.setStyling

    def spy(length, style):
        calls.append((length, style))
        original(length, style)

    lexer.setStyling = spy
    try:
        lexer.styleText(start, end)
    finally:
        lexer.setStyling = original
    return calls


def _replay(calls, length):
    """Expand ``(length, style)`` calls into one per-character style list."""
    styles = []
    for span, style in calls:
        styles.extend([style] * span)
    return styles[:length]


class TestScanBracketDepth:
    """Segment identity: depth after [0, stop) equals [0, mid) + [mid, stop)."""

    @pytest.mark.parametrize("code", _ALL_SAMPLES, ids=lambda c: c.splitlines()[0][:24])
    def test_segment_identity(self, qapp_instance, code):
        n = len(code)
        mid = n // 2

        whole = []
        IronicaLexer._scan_bracket_depth(code, 0, n, whole)

        first = []
        IronicaLexer._scan_bracket_depth(code, 0, mid, first)
        IronicaLexer._scan_bracket_depth(code, mid, n, first)

        assert first == whole


class TestBracketDepthCache:
    """Cold and warm styling paths must emit identical styles."""

    @pytest.mark.parametrize("code", _BRACKET_SAMPLES, ids=lambda c: c.splitlines()[0][:24])
    def test_split_at_half_matches_full_rebuild(self, qapp_instance, code):
        editor, lexer = _make_editor(qapp_instance)
        editor.setText(code)
        n = len(code)
        mid = n // 2

        lexer._bracket_cache = None
        cold = _replay(_record_styling(lexer, 0, n), n)

        lexer._bracket_cache = None
        warm = _record_styling(lexer, 0, mid) + _record_styling(lexer, mid, n)

        assert _replay(warm, n) == cold

    @pytest.mark.parametrize("code", _BRACKET_SAMPLES, ids=lambda c: c.splitlines()[0][:24])
    def test_sequential_edits_match_full_rebuild(self, qapp_instance, code):
        editor, lexer = _make_editor(qapp_instance)
        editor.setText(code)
        n = len(code)
        positions = sorted({0, n // 3, (2 * n) // 3, n - 1, n})

        lexer._bracket_cache = None
        cold = _replay(_record_styling(lexer, 0, n), n)

        lexer._bracket_cache = None
        warm = []
        for i in range(len(positions) - 1):
            warm += _record_styling(lexer, positions[i], positions[i + 1])

        assert _replay(warm, n) == cold

    def test_mid_file_edit_falls_back_to_full_rebuild(self, qapp_instance):
        editor, lexer = _make_editor(qapp_instance)
        code = _BRACKET_SAMPLES[0]
        editor.setText(code)
        n = len(code)

        lexer._bracket_cache = None
        _record_styling(lexer, 0, n)
        assert lexer._bracket_cache is not None
        assert lexer._bracket_cache[0] == n

        # An edit before the cache point must trigger a full rebuild.
        cache_pos = lexer._bracket_cache[0]
        early = cache_pos - 3

        cold = _replay(_record_styling(lexer, 0, n), n)
        lexer._bracket_cache = [cache_pos, lexer._bracket_cache[1]]
        rebuilt = _replay(_record_styling(lexer, early, n), n)

        assert rebuilt == cold[early:]


def _split_code(code, byte_pos):
    """Return ``code`` re-encoded as UTF-8 and a *byte_pos* split point."""
    data = code.encode("utf-8")
    assert 0 < byte_pos < len(data)
    return data, byte_pos


class TestByteStateCarry:
    """Cold vs warm styling must match for byte-offset splits into
    multi-byte text, strings, comments and triple-quoted literals."""

    @pytest.mark.parametrize(
        "code",
        [
            "s = \"aπaπa\"\n# ïßπ comment\nx = \"Ωµ\"\n",
            "def f(α, β):\n    return \"τ\" + 'ρ'\n",
        ],
        ids=["multibyte-mixed", "multibyte-identifiers-in-string"],
    )
    def test_multibyte_split_matches_full_rebuild(self, qapp_instance, code):
        editor, lexer = _make_editor(qapp_instance)
        data = code.encode("utf-8")
        n = len(data)
        mid = n // 2

        editor.setText(code)
        lexer._bracket_cache = None
        cold = _replay(_record_styling(lexer, 0, n), n)

        lexer._bracket_cache = None
        warm = _record_styling(lexer, 0, mid) + _record_styling(lexer, mid, n)

        assert _replay(warm, n) == cold

    @pytest.mark.parametrize(
        "code",
        [
            's = "' + ("a" * 60) + '"\n',
            "x = 1  # " + ("comment" * 15) + "\n",
            's = """' + ("b" * 60) + '"""\n',
        ],
        ids=["single-quote", "comment", "triple-quote"],
    )
    def test_state_spans_chunk_boundary(self, qapp_instance, code):
        """A string/comment opened in one chunk and closed in the next."""
        editor, lexer = _make_editor(qapp_instance)
        data = code.encode("utf-8")
        n = len(data)
        mid = n // 2

        editor.setText(code)
        lexer._bracket_cache = None
        cold = _replay(_record_styling(lexer, 0, n), n)

        lexer._bracket_cache = None
        warm = _record_styling(lexer, 0, mid) + _record_styling(lexer, mid, n)

        assert _replay(warm, n) == cold

    def test_keyword_inside_string_not_keyword_styled(self, qapp_instance):
        editor, lexer = _make_editor(qapp_instance)
        code = 'def def():\n    s = "def class if"\n    # def\n'
        editor.setText(code)
        lexer._bracket_cache = None
        styles = _replay(_record_styling(lexer, 0, len(code)), len(code))

        kw = lexer._keyword_map["def"]
        # "def" at the start of the buffer is a keyword...
        assert styles[0] == kw
        # ...but "def class if" inside the double-quoted string is not.
        s_start = code.index('"')
        assert code[s_start + 1 : s_start + 4] == "def"
        assert styles[s_start + 1 : s_start + 4] == [lexer._string_style] * 3
        # nor is the one inside the comment.
        c_start = code.index("#")
        assert styles[c_start] == lexer._comment_style
        assert lexer._comment_style not in [kw] and styles[c_start + 1] == lexer._comment_style

    def test_brackets_inside_comment_and_string_not_counted(self, qapp_instance):
        editor, lexer = _make_editor(qapp_instance)
        code = "x = (\n    # ( ) [ { ignoring\n    s = \"(\"\n    )\n"
        editor.setText(code)
        lexer._bracket_cache = None
        styles = _replay(_record_styling(lexer, 0, len(code)), len(code))

        # The closing paren on the last line must match the opener's depth,
        # i.e. paren style for depth 1 (offset 0), NOT a mismatched depth.
        closing = code.index("    )") + len("    ")
        assert styles[closing] == lexer._paren_offset  # depth 1 paren

    def test_cache_carries_lexical_state_across_calls(self, qapp_instance):
        from editor.Ironica.regex import _ST_DOUBLE, _ST_COMMENT, _ST_DEFAULT

        editor, lexer = _make_editor(qapp_instance)
        code = 's = "unterminated'
        editor.setText(code)
        lexer._bracket_cache = None
        _record_styling(lexer, 0, len(code))

        cache = lexer._bracket_cache
        assert cache is not None
        assert cache[2] == _ST_DOUBLE  # still inside the string

        code2 = code + '"\n# never closed'
        editor.setText(code2)
        lexer._bracket_cache = None
        _record_styling(lexer, 0, len(code2))
        assert lexer._bracket_cache[2] == _ST_COMMENT

        code3 = code2 + " still comment"
        editor.setText(code3)
        lexer._bracket_cache = None
        _record_styling(lexer, 0, len(code3))
        assert lexer._bracket_cache[2] == _ST_COMMENT

        code4 = code2 + "\n"
        editor.setText(code4)
        lexer._bracket_cache = None
        _record_styling(lexer, 0, len(code4))
        assert lexer._bracket_cache[2] == _ST_DEFAULT
