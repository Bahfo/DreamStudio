"""Tests for the dynamic IDE theme engine (editor/Ironica/retheme.py).

Covers:
    - ``editor_colors`` base colour extraction from the QSS themes
    - ``resolve_language_config`` symbolic-style resolution through the
      active theme palette
    - ``IronicaLexer.retheme`` keeping style 0 and every other style's
      background in sync with the editor background (no white boxes)
    - ``CodeEditor.retheme`` recolouring the visible document
    - ``RethemeEngine`` iterating and toggling across open editors
"""

import pytest
from PyQt6.QtGui import QColor
from PyQt6.Qsci import QsciScintilla


@pytest.fixture(autouse=True)
def _reset_registry():
    from editor.Ironica.language_engine import LanguageRegistry
    from editor.Ironica.retheme import set_active_theme

    LanguageRegistry.reset()
    set_active_theme("dark")
    yield
    LanguageRegistry.reset()


def _style_back(editor, style):
    return editor.SendScintilla(QsciScintilla.SCI_STYLEGETBACK, style)


def _style_fore(editor, style):
    return editor.SendScintilla(QsciScintilla.SCI_STYLEGETFORE, style)


def _rgb(colorref):
    return QColor(colorref & 0xFF, (colorref >> 8) & 0xFF, (colorref >> 16) & 0xFF).name()


class TestEditorColors:
    """Extract base editor colours from the shipped QSS themes."""

    def test_dark_palette(self):
        from editor.Ironica.retheme import editor_colors

        colors = editor_colors("dark")
        assert colors["bg"].name() == "#1e1e1e"
        assert colors["fg"].name() == "#d4d4d4"
        assert colors["sel"].name() == "#264f78"

    def test_light_palette(self):
        from editor.Ironica.retheme import editor_colors

        colors = editor_colors("light")
        assert colors["bg"].name() == "#ffffff"
        assert colors["fg"].name() == "#1e1e1e"

    def test_monokai_palette(self):
        from editor.Ironica.retheme import editor_colors

        colors = editor_colors("monokai")
        assert colors["bg"].name() == "#272822"
        assert colors["fg"].name() == "#f8f8f2"

    def test_unknown_theme_falls_back(self):
        from editor.Ironica.retheme import editor_colors

        colors = editor_colors("not_a_real_theme")
        assert colors["bg"].name() == "#1e1e1e"


class TestResolveLanguageConfig:
    """Symbolic styles resolve through the active theme palette."""

    def test_symbolic_resolution(self):
        from editor.Ironica.retheme import resolve_language_config

        config = {
            "lang": "t",
            "styles": {"keyword": "KEYWORD_COLOR"},
            "palette": {"KEYWORD_COLOR": "#C586C0"},
        }
        resolved = resolve_language_config(config, "monokai")
        assert resolved["styles"]["keyword"] == "#F92672"

    def test_hex_passes_through(self):
        from editor.Ironica.retheme import resolve_language_config

        config = {"lang": "t", "styles": {"keyword": "#112233"}, "palette": {}}
        resolved = resolve_language_config(config, "dark")
        assert resolved["styles"]["keyword"] == "#112233"

    def test_key_order_preserved(self):
        from editor.Ironica.retheme import resolve_language_config

        config = {
            "lang": "t",
            "styles": {"a": "KEYWORD_COLOR", "b": "STRING_COLOR", "c": "#FF0000"},
            "palette": {},
        }
        resolved = resolve_language_config(config, "dark")
        assert list(resolved["styles"].keys()) == ["a", "b", "c"]


class TestIronicaLexerRetheme:
    """Style backgrounds must follow the editor background."""

    def _python_editor(self, qapp_instance):
        from editor.Ironica.code_editor import CodeEditor
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        ed = CodeEditor(language="python")
        ed.setText("def foo(x):\n    return x * 2  # comment\n")
        return ed

    def test_style_zero_follows_theme(self, qapp_instance):
        ed = self._python_editor(qapp_instance)
        try:
            assert _rgb(_style_back(ed, 0)) == "#1e1e1e"
            assert _rgb(_style_fore(ed, 0)) == "#d4d4d4"

            ed.retheme("light")
            assert _rgb(_style_back(ed, 0)) == "#ffffff"
            assert _rgb(_style_fore(ed, 0)) == "#1e1e1e"
        finally:
            ed.deleteLater()

    def test_every_style_background_is_themed(self, qapp_instance):
        ed = self._python_editor(qapp_instance)
        try:
            comment_style = ed._lexer._comment_style
            assert comment_style > 0
            for style in range(comment_style + 1):
                assert _rgb(_style_back(ed, style)) == "#1e1e1e", style

            ed.retheme("tokyonight")
            from editor.Ironica.retheme import editor_colors

            bg = editor_colors("tokyonight")["bg"].name().lower()
            for style in range(ed._lexer._comment_style + 1):
                assert _rgb(_style_back(ed, style)) == bg, style
        finally:
            ed.deleteLater()

    def test_keyword_foreground_follows_theme(self, qapp_instance):
        ed = self._python_editor(qapp_instance)
        try:
            ed.retheme("monokai")
            assert _rgb(_style_fore(ed, 1)) == "#f92672"
        finally:
            ed.deleteLater()


class TestThemeAwareExtras:
    """Fold-margin and minimap follow the theme; variables resolve from
    the theme palette instead of the hard-coded light-blue fallback."""

    def _python_editor(self, qapp_instance):
        from editor.Ironica.code_editor import CodeEditor
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        ed = CodeEditor(language="python")
        ed.setText("def foo(x):\n    return x * 2  # comment\n")
        return ed

    def test_variable_colour_resolves_per_theme(self):
        from editor.Ironica.language_engine import LanguageRegistry
        from editor.Ironica.plugins.registration import register_python_language
        from editor.Ironica.retheme import resolve_language_config

        register_python_language()
        config = LanguageRegistry.get_config("python")
        assert resolve_language_config(config, "light")["styles"]["variable"] == "#001080"
        assert resolve_language_config(config, "dark")["styles"]["variable"] == "#9CDCFE"
        assert resolve_language_config(config, "monokai")["styles"]["variable"] == "#F8F8F2"

    def test_minimap_retheme(self, qapp_instance):
        from editor.Ironica.utils.minimap import MiniMapHostWidget

        ed = self._python_editor(qapp_instance)
        try:
            host = MiniMapHostWidget(ed)
            mm = host.minimap
            mm.retheme("dark", QColor("#1e1e1e"))
            assert mm._line_comment_color.red() == 0x89  # dark COMMENT_COLOR
            assert mm._bg_color.lightness() < 128
            mm.retheme("light", QColor("#ffffff"))
            assert mm._line_comment_color.name() == "#005f00"  # light COMMENT_COLOR
            assert mm._bg_color.lightness() > 200
            host.deleteLater()
        finally:
            ed.deleteLater()

    def test_fold_margin_follows_theme(self, qapp_instance):
        from PyQt6.QtGui import QImage, QPainter

        ed = self._python_editor(qapp_instance)
        try:
            ed.resize(500, 120)
            ed.show()
            qapp_instance.processEvents()

            def fold_pixels(theme):
                ed.retheme(theme)
                qapp_instance.processEvents()
                img = QImage(ed.size(), QImage.Format.Format_RGB32)
                painter = QPainter(img)
                ed.render(painter)
                painter.end()
                x0 = ed.marginWidth(0) + ed.marginWidth(1) + ed.marginWidth(2)
                return {
                    QColor(img.pixel(x, y)).name()
                    for x in range(x0, x0 + ed.marginWidth(3))
                    for y in (20, 40, 60)
                }

            dark = fold_pixels("dark")
            light = fold_pixels("light")
            assert "#272727" in dark
            assert "#dedede" in light
            assert dark != light
        finally:
            ed.deleteLater()


    def test_fold_arrow_pixmaps(self, qapp_instance):
        from editor.Ironica.utils.folding import FoldManager

        ed = self._python_editor(qapp_instance)
        try:
            fm = ed._fold_manager
            up = fm._arrow_pixmap(QColor(200, 200, 200), up=True)
            down = fm._arrow_pixmap(QColor(200, 200, 200), up=False)
            assert up.size().width() == FoldManager.ARROW_SIZE
            assert down.size().width() == FoldManager.ARROW_SIZE

            def drawn(img, x, y):
                return QColor(img.pixel(x, y)).red() > 100

            def spread_at(img, y):
                xs = [x for x in range(img.width()) if drawn(img, x, y)]
                return (max(xs) - min(xs) + 1) if xs else 0

            def orientation(pm):
                img = pm.toImage()
                top = bottom = 0
                for y in range(img.height()):
                    sp = spread_at(img, y)
                    if sp:
                        if top == 0:
                            top = sp
                        bottom = sp
                return top, bottom

            # An up chevron is narrow at its apex (top row) and wide at
            # its base (bottom row); the down chevron is its mirror.
            t_up, b_up = orientation(up)
            t_down, b_down = orientation(down)
            assert t_up < b_up
            assert t_down > b_down
        finally:
            ed.deleteLater()

    def test_fold_arrows_render(self, qapp_instance):
        from editor.Ironica.utils.folding import FoldRegion
        from PyQt6.QtGui import QImage, QPainter

        ed = self._python_editor(qapp_instance)
        try:
            ed.setText("def foo():\n    a = 1\n    b = 2\n    return a + b\n\ndef bar():\n    pass\n")
            ed.resize(500, 120)
            ed.show()
            qapp_instance.processEvents()
            fm = ed._fold_manager
            fm.set_fold_regions(
                [
                    FoldRegion(start_line=0, end_line=3),
                    FoldRegion(start_line=5, end_line=6),
                ]
            )
            ed.retheme("light")
            qapp_instance.processEvents()
            img = QImage(ed.size(), QImage.Format.Format_RGB32)
            painter = QPainter(img)
            ed.render(painter)
            painter.end()
            x0 = ed.marginWidth(0) + ed.marginWidth(1) + ed.marginWidth(2)
            # Light-theme chevron arrows are drawn near #505050.
            found = 0
            for y in range(img.height()):
                for x in range(x0, x0 + ed.marginWidth(3)):
                    c = QColor(img.pixel(x, y))
                    if (
                        abs(c.red() - 0x50) < 40
                        and abs(c.green() - 0x50) < 40
                        and abs(c.blue() - 0x50) < 40
                    ):
                        found += 1
            assert found > 10
        finally:
            ed.deleteLater()


class TestRethemeEngine:
    """Iterate and toggle across open editors."""

    def _window_with_editors(self, qapp_instance, editors):
        from editor.Ironica.code_editor import CodeEditor
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        if not editors:
            editors = [CodeEditor(language="python")]
            editors[0].setText("x = 1\n")

        class Tabs:
            def count(self):
                return len(editors)

            def widget(self, i):
                return type("W", (), {"editor": editors[i]})()

        class Center:
            tabs = Tabs()

        class Hero:
            _text_editor_center = Center()

        class Window:
            hero_window = Hero()
            _current_theme_name = "dark"

        return Window(), editors

    def test_apply_current_recolours_all_editors(self, qapp_instance):
        from editor.Ironica.retheme import RethemeEngine, editor_colors

        window, editors = self._window_with_editors(qapp_instance, [])
        window._current_theme_name = "coffee_dark"
        RethemeEngine.apply_current(window)
        bg = editor_colors("coffee_dark")["bg"].name().lower()
        for ed in editors:
            assert _rgb(_style_back(ed, 0)) == bg

    def test_toggle_advances_theme(self, qapp_instance):
        from editor.Ironica.retheme import RethemeEngine

        window, _ = self._window_with_editors(qapp_instance, [])
        window._current_theme_name = "dark"
        applied = RethemeEngine.toggle(window)
        assert applied != "dark"
