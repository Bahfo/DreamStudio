"""Tests for Python lexer highlighting logic with mocked interfaces."""

import sys
from unittest.mock import MagicMock, call

jedi_mock = MagicMock()
sys.modules["jedi"] = jedi_mock

from editor.texteditor.ironica_lexer.python_jedi_highlighter import (
    PythonJediHighlighter,
    _JediAnalyzer,
    _STYLE_IDS,
    _TRIPLE_DOUBLE,
    _TRIPLE_SINGLE,
)
from editor.texteditor.ironica_lexer.python_lexer import (
    CustomPythonLexer,
    STYLE_DEFAULT,
    STYLE_STRING,
    STYLE_COMMENT,
    STYLE_NUMBER,
    _STATE_NORMAL,
    _STATE_ML_DQUOTE,
    _STATE_ML_SQUOTE,
)


def _make_mock_editor(text="", style_at=None):
    """Create a mock editor with configurable SendScintilla behavior."""
    editor = MagicMock()
    editor.text.return_value = text
    style_at = style_at or {}

    def send_scintilla(cmd, *args):
        if cmd == editor.SCI_GETSTYLEAT:
            return style_at.get(args[0], 0)
        if cmd == editor.SCI_LINEFROMPOSITION:
            txt = text.encode("utf-8")
            pos = args[0]
            return txt[:pos].count(b"\n")
        if cmd == editor.SCI_POSITIONFROMLINE:
            txt = text.encode("utf-8")
            line = args[0]
            lines = txt.split(b"\n")
            offset = 0
            for i in range(line):
                offset += len(lines[i]) + 1
            return offset
        if cmd == editor.SCI_COUNTCHARACTERS:
            txt_bytes = text.encode("utf-8")
            return len(txt_bytes[args[0] : args[1]].decode("utf-8"))
        return 0

    editor.SendScintilla.side_effect = send_scintilla
    return editor


class TestJediHighlighterInitialState:
    def test_returns_none_at_start_zero(self):
        hl = PythonJediHighlighter(MagicMock())
        result = hl._initial_state_for(MagicMock(), b"", 0)
        assert result is None

    def test_returns_none_when_start_less_than_6(self):
        hl = PythonJediHighlighter(MagicMock())
        editor = MagicMock()
        editor.SendScintilla.return_value = _STYLE_IDS.get("default", 0)
        for start in range(1, 6):
            result = hl._initial_state_for(editor, b"abcde", start)
            assert result is None, f"start={start} should return None"

    def test_detects_open_triple_double(self):
        text = 'x = """hello\n'
        full_bytes = text.encode("utf-8")
        style_at = {len(full_bytes) - 2: _STYLE_IDS["string_doc"]}
        editor = _make_mock_editor(text, style_at)
        hl = PythonJediHighlighter(MagicMock())
        result = hl._initial_state_for(editor, full_bytes, 13)
        assert result is not None
        state, quote_char = result
        assert state == _STYLE_IDS["string_doc"]
        assert quote_char == '"'

    def test_detects_open_triple_single(self):
        text = "x = '''hello\n"
        full_bytes = text.encode("utf-8")
        style_at = {len(full_bytes) - 2: _STYLE_IDS["string_doc"]}
        editor = _make_mock_editor(text, style_at)
        hl = PythonJediHighlighter(MagicMock())
        result = hl._initial_state_for(editor, full_bytes, 14)
        assert result is not None
        state, quote_char = result
        assert state == _STYLE_IDS["string_doc"]
        assert quote_char == "'"

    def test_returns_none_when_triples_balanced(self):
        text = 'x = """hello"""\ny = 1\n'
        full_bytes = text.encode("utf-8")
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        result = hl._initial_state_for(editor, full_bytes, 18)
        assert result is None


class TestJediHighlighterStyleText:
    def test_style_text_basic(self):
        text = "x = 1\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))
        assert editor.SendScintilla.call_count >= 2

    def test_style_text_string_and_comment(self):
        text = 'x = "hello"  # end\n'
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))
        assert editor.SendScintilla.call_count >= 6

    def test_style_text_empty_document(self):
        """Empty document has length 0, styleText returns immediately."""
        editor = _make_mock_editor("")
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, 0)
        assert editor.SendScintilla.call_count == 0

    def test_style_text_multiline_string_continuation(self):
        text = '"""hello\nworld\n"""\nx = 1\n'
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        total = len(text.encode("utf-8"))
        hl.styleText(0, total)

    def test_style_text_calls_startstyling(self):
        text = "x = 1\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text))
        start_calls = [
            c for c in editor.SendScintilla.mock_calls
            if c.args and c.args[0] == editor.SCI_STARTSTYLING
        ]
        assert len(start_calls) == 1

    def test_style_text_handles_def_function(self):
        text = "def foo():\n    pass\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_handles_class(self):
        text = "class Foo:\n    pass\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_handles_async_def(self):
        text = "async def foo():\n    pass\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_handles_utf8(self):
        text = "# café ☕\nprint('hello')\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_with_fstring(self):
        text = 'f"hello {name}"\n'
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_handles_decorator(self):
        text = "@staticmethod\ndef foo():\n    pass\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_mid_document(self):
        """Style a slice of the document, not from 0."""
        text = "x = 1\ny = 2\nz = 3\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(6, 12)

    def test_style_text_number_with_underscores(self):
        text = "x = 1_000_000\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_operator_walrus(self):
        text = "if (x := 1):\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_float_variants(self):
        text = "a = 1.5\nb = .5\nc = 1.\nd = 1e5\ne = 3.14j\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_ellipsis(self):
        text = "x = ...\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_prev_was_dot(self):
        """x.y should style y as attribute."""
        text = "obj.attr\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))

    def test_style_text_constant_caps(self):
        text = "MAX_SIZE = 100\n"
        editor = _make_mock_editor(text)
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(editor)
        hl.styleText(0, len(text.encode("utf-8")))


class TestJediHighlighterInit:
    def test_default_style_count(self):
        hl = PythonJediHighlighter(MagicMock())
        assert len(_STYLE_IDS) >= 28

    def test_style_ids_contiguous(self):
        ids = sorted(_STYLE_IDS.values())
        assert ids == list(range(len(ids)))

    def test_shutdown_no_analyzer(self):
        hl = PythonJediHighlighter(MagicMock())
        hl.shutdown()

    def test_shutdown_with_analyzer(self):
        hl = PythonJediHighlighter(MagicMock())
        hl._ensure_analyzer()
        hl.shutdown()

    def test_schedule_analysis_no_crash(self):
        hl = PythonJediHighlighter(MagicMock())
        hl.setEditor(MagicMock())
        hl.schedule_analysis()

    def test_set_environment_no_crash(self):
        hl = PythonJediHighlighter(MagicMock())
        hl.set_environment("/some/venv")
        hl.set_environment(None)


class TestFallbackLexer:
    def _make_fallback(self, text="", state=_STATE_NORMAL):
        parent = MagicMock()
        json_data = {
            "colors_schema": {},
            "words": {},
            "types": {},
            "iterators": {},
            "exceptions": {},
        }
        lexer = CustomPythonLexer(parent, json_data)
        editor = _make_mock_editor(text)
        lexer.setEditor(editor)
        lexer.setState(state)
        return lexer, editor

    def test_default_styles_set(self):
        parent = MagicMock()
        json_data = {
            "colors_schema": {},
            "words": {},
            "types": {},
            "iterators": {},
            "exceptions": {},
        }
        lexer = CustomPythonLexer(parent, json_data)
        assert lexer.word_to_style == {}

    def test_basic_tokenization(self):
        text = "x = 1  # comment\n"
        lexer, editor = self._make_fallback(text)
        lexer.styleText(0, len(text.encode("utf-8")))
        assert editor.SendScintilla.called

    def test_multiline_string_continuation(self):
        text = '"""hello\nworld\n"""\nx = 1\n'
        lexer, editor = self._make_fallback(text, _STATE_NORMAL)
        total = len(text.encode("utf-8"))
        lexer.styleText(0, total)

    def test_state_set_after_continuation(self):
        text = '"""hello\n'
        lexer, editor = self._make_fallback(text, _STATE_NORMAL)
        lexer.styleText(0, len(text.encode("utf-8")))
        assert lexer.state() == _STATE_ML_DQUOTE

    def test_state_normal_after_closed(self):
        text = '"""hello"""\n'
        lexer, editor = self._make_fallback(text, _STATE_NORMAL)
        lexer.styleText(0, len(text.encode("utf-8")))
        assert lexer.state() == _STATE_NORMAL

    def test_state_normal_after_triple_single_closed(self):
        text = "'''hello'''\n"
        lexer, editor = self._make_fallback(text, _STATE_NORMAL)
        lexer.styleText(0, len(text.encode("utf-8")))
        assert lexer.state() == _STATE_NORMAL

    def test_resume_in_multiline_double(self):
        text = "world\n\"\"\"\nx = 1\n"
        lexer, editor = self._make_fallback(text, _STATE_ML_DQUOTE)
        lexer.styleText(0, len(text.encode("utf-8")))
        assert lexer.state() == _STATE_NORMAL

    def test_resume_in_multiline_single(self):
        text = "world\n'''\nx = 1\n"
        lexer, editor = self._make_fallback(text, _STATE_ML_SQUOTE)
        lexer.styleText(0, len(text.encode("utf-8")))
        assert lexer.state() == _STATE_NORMAL

    def test_utf8_comment(self):
        text = "# café ☕\n"
        lexer, editor = self._make_fallback(text)
        lexer.styleText(0, len(text.encode("utf-8")))

    def test_utf8_string(self):
        text = '"café ☕"\n'
        lexer, editor = self._make_fallback(text)
        lexer.styleText(0, len(text.encode("utf-8")))

    def test_mixed_content(self):
        text = (
            '"""docstring"""\n'
            "def foo():\n"
            '    """nested"""\n'
            "    x = 1  # comment\n"
        )
        lexer, editor = self._make_fallback(text)
        lexer.styleText(0, len(text.encode("utf-8")))

    def test_word_to_style_mapping(self):
        parent = MagicMock()
        json_data = {
            "colors_schema": {},
            "words": {"def": "definition", "class": "definition"},
            "types": {"int": "constructor"},
            "iterators": {},
            "exceptions": {},
        }
        lexer = CustomPythonLexer(parent, json_data)
        assert "def" in lexer.word_to_style
        assert "class" in lexer.word_to_style
        assert "int" in lexer.word_to_style


class TestJediAnalyzer:
    def test_create(self):
        jedi_mock.reset_mock()
        analyzer = _JediAnalyzer()
        assert analyzer is not None

    def test_queue_and_clear_cache(self):
        analyzer = _JediAnalyzer()
        analyzer.request_analysis("x = 1", None, None, 1)
        analyzer.clear_cache()

    def test_queue_max_size(self):
        analyzer = _JediAnalyzer()
        for i in range(25):
            analyzer.request_analysis(f"x = {i}", None, None, i)
        assert len(analyzer._queue) <= 20

    def test_shutdown(self):
        analyzer = _JediAnalyzer()
        analyzer.shutdown()
        assert not analyzer._running

    def test_get_name_type_empty(self):
        analyzer = _JediAnalyzer()
        assert analyzer.get_name_type(0, 0, "foo") is None

    def test_cache_stores_and_retrieves(self):
        analyzer = _JediAnalyzer()
        analyzer.cache[(0, 0, "foo")] = "function"
        assert analyzer.get_name_type(0, 0, "foo") == "function"
