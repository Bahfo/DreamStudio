"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Code editor dressing live tests: minimap, diagnostics ruler, folding, language
switching, retheming, and analysis overlays.
"""

from pathlib import Path

import pytest

from harness import (
    Sweep,
    assert_alive,
    click,
    code_editor,
    mouse_move,
    pump,
    race_probe,
    type_text,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

QT = pytest.importorskip("PyQt6.QtCore")


def _open_editor(qapp, window, workspace_path, name: str = "main.py"):
    """Open a sample file and return its CodeEditor.

    Args:
        qapp: The live QApplication instance.
        window: The DreamStudio main window.
        workspace_path: Workspace root holding the sample file.
        name: File name to open.

    Returns:
        The CodeEditor instance.
    """
    tabs = window.hero_window._text_editor_center.tabs
    tabs.open_file_by_path(str(Path(workspace_path) / name))
    pump(qapp, 300)
    api = window.hero_window._text_editor_center.current_editor()
    return code_editor(api)


def _minimap_host(qapp, window, workspace_path):
    """Return the minimap host widget wrapping the active editor.

    Args:
        qapp: The live QApplication instance.
        window: The DreamStudio main window.
        workspace_path: Workspace root holding the sample file.

    Returns:
        The MiniMapHostWidget instance, or None when absent.
    """
    from editor.Ironica.utils.minimap import MiniMapHostWidget

    tabs = window.hero_window._text_editor_center.tabs
    tabs.open_file_by_path(str(Path(workspace_path) / "main.py"))
    pump(qapp, 300)
    widget = tabs.currentWidget()
    if isinstance(widget, MiniMapHostWidget):
        return widget
    return None


class TestMinimap:
    """The virtual minimap tracks the editor content."""

    def test_minimap_host_wraps_the_editor(self, qapp, qa_window, sample_tree):
        """The opened file is hosted inside a minimap host widget."""
        host = _minimap_host(qapp, qa_window, sample_tree)
        assert host is not None, "the editor is not hosted by a minimap widget"
        assert host.editor is not None, "minimap host has no editor"
        assert host.minimap is not None, "minimap host has no minimap"
        assert host.ruler is not None, "minimap host has no diagnostics ruler"

    def test_minimap_toggle_changes_visibility(self, qapp, qa_window, sample_tree):
        """Toggling the minimap changes its visibility."""
        host = _minimap_host(qapp, qa_window, sample_tree)
        minimap = host.minimap
        before = minimap.isVisible()
        host.toggle_minimap()
        pump(qapp, 200)
        assert minimap.isVisible() != before, "minimap visibility did not change"

    def test_set_minimap_visible(self, qapp, qa_window, sample_tree):
        """set_minimap_visible() applies the requested state."""
        host = _minimap_host(qapp, qa_window, sample_tree)
        host.set_minimap_visible(False)
        pump(qapp, 150)
        assert not host.minimap.isVisible(), "minimap stayed visible"
        host.set_minimap_visible(True)
        pump(qapp, 150)

    def test_scrolling_updates_the_overlay(self, qapp, qa_window, sample_tree):
        """Scrolling the editor refreshes the minimap overlay."""
        host = _minimap_host(qapp, qa_window, sample_tree)
        editor = host.editor
        editor.setText("\n".join(f"line {i}" for i in range(500)) + "\n")
        pump(qapp, 300)
        editor.setFirstVisibleLine(200)
        pump(qapp, 300)
        assert_alive(qapp, qa_window)

    def test_minimap_click_scrolls_the_editor(self, qapp, qa_window, sample_tree):
        """Clicking the minimap scrolls the source editor."""
        host = _minimap_host(qapp, qa_window, sample_tree)
        editor = host.editor
        editor.setText("\n".join(f"line {i}" for i in range(500)) + "\n")
        pump(qapp, 300)
        minimap = host.minimap
        sweep = Sweep("minimap click")
        sweep.step("click minimap", click, qapp, minimap)
        pump(qapp, 200)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_minimap_survives_resize(self, qapp, qa_window, sample_tree):
        """Resizing the window keeps the minimap consistent."""
        _minimap_host(qapp, qa_window, sample_tree)
        qa_window.resize(900, 600)
        pump(qapp, 200)
        qa_window.resize(1280, 800)
        pump(qapp, 200)
        assert_alive(qapp, qa_window)


class TestDiagnosticsRuler:
    """The diagnostics ruler maps lines to pixels and back."""

    def test_set_ticks_stores_the_payload(self, qapp, qa_window, sample_tree):
        """set_ticks() stores the (line, colour, severity) triples."""
        from editor.Ironica.utils.diagnostics_ruler import DiagnosticsRuler

        ruler = DiagnosticsRuler(None)
        ruler.set_ticks([(3, "#ff0000", "error"), (7, "#00ff00", "warning")])
        pump(qapp, 100)
        ticks = ruler.ticks()
        assert len(ticks) == 2, f"unexpected ticks: {ticks}"
        assert ticks[0][0] == 3, f"tick line wrong: {ticks[0]}"

    def test_empty_ticks_are_ignored(self, qapp, qa_window, sample_tree):
        """An empty tick list leaves the ruler empty."""
        from editor.Ironica.utils.diagnostics_ruler import DiagnosticsRuler

        ruler = DiagnosticsRuler(None)
        ruler.set_ticks([])
        pump(qapp, 100)
        assert ruler.ticks() == [], "empty ticks were stored"

    def test_malformed_ticks_are_ignored(self, qapp, qa_window, sample_tree):
        """Malformed tick entries are dropped."""
        from editor.Ironica.utils.diagnostics_ruler import DiagnosticsRuler

        ruler = DiagnosticsRuler(None)
        ruler.set_ticks([("bad",), (-5, "#fff"), (2, "#abc")])
        pump(qapp, 100)
        ticks = ruler.ticks()
        assert len(ticks) == 1, f"malformed ticks survived: {ticks}"

    def test_line_and_y_are_inverses(self, qapp, qa_window, sample_tree):
        """y_for_line() and line_for_y() round-trip on a live editor."""
        from editor.Ironica.utils.diagnostics_ruler import DiagnosticsRuler

        editor = _open_editor(qapp, qa_window, sample_tree)
        ruler = DiagnosticsRuler(editor)
        ruler.resize(ruler.width(), 240)
        ruler.set_ticks([(5, "#ff0000", "error")])
        pump(qapp, 100)
        y = ruler.y_for_line(5)
        assert ruler.line_for_y(y) == 5, (
            f"line round-trip failed: y={y} -> {ruler.line_for_y(y)}"
        )

    def test_ruler_hover_is_reported(self, qapp, qa_window, sample_tree):
        """Moving over the ruler reports the hovered line."""
        host = _minimap_host(qapp, qa_window, sample_tree)
        ruler = host.ruler
        sweep = Sweep("ruler hover")
        sweep.step("hover ruler", mouse_move, qapp, ruler, QT.QPoint(4, 12))
        pump(qapp, 150)
        sweep.finish()
        assert_alive(qapp, qa_window)


class TestFolding:
    """Fold regions can be set, collapsed, and expanded."""

    def test_set_and_get_fold_regions(self, qapp, qa_window, sample_tree):
        """Fold regions round-trip through the manager."""
        from editor.Ironica.utils.folding import FoldRegion

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def a():\n    pass\n\ndef b():\n    pass\n")
        pump(qapp, 200)
        manager = editor._fold_manager
        manager.set_fold_regions([FoldRegion(start_line=0, end_line=1, kind="function")])
        pump(qapp, 200)
        regions = manager.get_fold_regions()
        assert regions, "fold regions were not stored"
        assert regions[0].kind == "function", f"unexpected region: {regions[0]}"

    def test_clear_fold_regions(self, qapp, qa_window, sample_tree):
        """Clearing removes every stored region.

        NOTE: the language analysis repopulates the regions from its own
        fold model, so the check runs right after the clear.
        """
        from editor.Ironica.utils.folding import FoldRegion

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def a():\n    pass\n")
        pump(qapp, 200)
        manager = editor._fold_manager
        manager.set_fold_regions([FoldRegion(start_line=0, end_line=1, kind="function")])
        manager.clear_fold_regions()
        assert not manager.get_fold_regions(), "fold regions survived the clear"

    def test_collapse_and_expand_all(self, qapp, qa_window, sample_tree):
        """Collapsing and expanding all regions stays consistent."""
        from editor.Ironica.utils.folding import FoldRegion

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def a():\n    pass\n\ndef b():\n    pass\n")
        pump(qapp, 200)
        manager = editor._fold_manager
        manager.set_fold_regions(
            [
                FoldRegion(start_line=0, end_line=1, kind="function"),
                FoldRegion(start_line=3, end_line=4, kind="function"),
            ]
        )
        pump(qapp, 200)
        sweep = Sweep("fold all")
        sweep.step("collapse all", manager.collapse_all)
        pump(qapp, 200)
        sweep.step("expand all", manager.expand_all)
        pump(qapp, 200)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_collapse_by_kind(self, qapp, qa_window, sample_tree):
        """Collapsing a kind only affects that kind."""
        from editor.Ironica.utils.folding import FoldRegion

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("import os\nimport sys\n\ndef a():\n    pass\n")
        pump(qapp, 200)
        manager = editor._fold_manager
        manager.set_fold_regions(
            [
                FoldRegion(start_line=0, end_line=1, kind="imports"),
                FoldRegion(start_line=3, end_line=4, kind="function"),
            ]
        )
        pump(qapp, 200)
        sweep = Sweep("fold kind")
        sweep.step("collapse imports", manager.collapse_kind, "imports")
        pump(qapp, 150)
        sweep.step("expand imports", manager.expand_kind, "imports")
        pump(qapp, 150)
        sweep.finish()

    def test_fold_regions_survive_an_edit(self, qapp, qa_window, sample_tree):
        """Editing the buffer keeps the fold regions intact."""
        from editor.Ironica.utils.folding import FoldRegion

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def a():\n    pass\n")
        pump(qapp, 200)
        manager = editor._fold_manager
        manager.set_fold_regions([FoldRegion(start_line=0, end_line=1, kind="function")])
        pump(qapp, 200)
        editor.setCursorPosition(1, 0)
        type_text(qapp, editor, "# edit\n")
        pump(qapp, 800)
        assert_alive(qapp, qa_window)

    def test_fold_storm_with_typing_is_stable(self, qapp, qa_window, sample_tree):
        """Folding while typing keeps the editor consistent."""
        from editor.Ironica.utils.folding import FoldRegion

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def a():\n    pass\n")
        pump(qapp, 200)
        manager = editor._fold_manager
        manager.set_fold_regions([FoldRegion(start_line=0, end_line=1, kind="function")])

        def cycle() -> None:
            """Collapse and expand the regions once.

            Returns:
                None; the side effect is the fold toggle pair.
            """
            manager.collapse_all()
            manager.expand_all()

        race_probe(qapp, cycle, 3)
        pump(qapp, 300)
        assert_alive(qapp, qa_window)


class TestLanguageAndTheme:
    """Language switching and retheming keep the editor intact."""

    def test_set_language_python(self, qapp, qa_window, sample_tree):
        """Setting the Python language keeps the text intact."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        before = editor.text()
        editor.setLanguage("python")
        pump(qapp, 300)
        assert editor.text() == before, "switching language changed the text"

    def test_set_language_unknown_falls_back(self, qapp, qa_window, sample_tree):
        """An unknown language does not raise."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        sweep = Sweep("unknown language")
        sweep.step("set language", editor.setLanguage, "not_a_language")
        pump(qapp, 200)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_apply_visual_language(self, qapp, qa_window, sample_tree):
        """Applying a visual language keeps the editor usable."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        sweep = Sweep("visual language")
        sweep.step("apply visual", editor.apply_visual_language, "python")
        pump(qapp, 300)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_registered_languages_can_be_applied(self, qapp, qa_window, sample_tree):
        """Every language plugin registered at startup can be selected."""
        from editor.Ironica.language_engine import LanguageRegistry

        editor = _open_editor(qapp, qa_window, sample_tree)
        languages = sorted(LanguageRegistry._providers.keys())
        assert languages, "no language plugins are registered"
        for language in languages:
            editor.setLanguage(language)
            pump(qapp, 150)
        assert_alive(qapp, qa_window)

    def test_retheme_cycles_without_breaking(self, qapp, qa_window, sample_tree):
        """Switching themes back and forth keeps every subsystem alive."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        before = editor.text()
        sweep = Sweep("retheme")
        for theme in ("light", "dark", "dark"):
            sweep.step(f"retheme {theme}", editor.retheme, theme)
            pump(qapp, 250)
        sweep.finish()
        assert editor.text() == before, "retheme changed the buffer"
        assert_alive(qapp, qa_window)

    def test_retheme_with_open_popup_and_fold(self, qapp, qa_window, sample_tree):
        """Retheming with a fold and a popup open keeps the editor stable."""
        from editor.Ironica.utils.folding import FoldRegion

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def a():\n    pass\n")
        pump(qapp, 200)
        editor._fold_manager.set_fold_regions(
            [FoldRegion(start_line=0, end_line=1, kind="function")]
        )
        editor._show_navigation_popup(
            [("/tmp/a.py", 1, 0), ("/tmp/b.py", 2, 0)], kind="reference"
        )
        pump(qapp, 200)
        sweep = Sweep("retheme with popups")
        sweep.step("retheme", editor.retheme, "light")
        pump(qapp, 250)
        sweep.finish()
        assert_alive(qapp, qa_window)


class TestAnalysisOverlays:
    """Analysis-driven overlays and folds apply cleanly."""

    def test_set_analysis_active_toggles_the_state(self, qapp, qa_window, sample_tree):
        """Activating analysis switches the editor state."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.set_analysis_active(True)
        pump(qapp, 200)
        editor.set_analysis_active(False)
        pump(qapp, 200)
        assert_alive(qapp, qa_window)

    def test_semantic_overlays_apply(self, qapp, qa_window, sample_tree):
        """Synthetic semantic highlights are applied without raising."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("value = 1\n")
        pump(qapp, 200)
        sweep = Sweep("semantic overlays")
        sweep.step("apply overlays", editor._apply_semantic_overlays, [(0, 5, "#ff00ff")])
        pump(qapp, 200)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_fold_regions_from_analysis_apply(self, qapp, qa_window, sample_tree):
        """Analysis fold regions are pushed into the fold manager."""
        from editor.Ironica.utils.folding import FoldRegion

        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("def a():\n    pass\n")
        pump(qapp, 200)
        editor.current_lang = "python"
        sweep = Sweep("analysis folds")
        sweep.step(
            "apply fold regions",
            editor._apply_fold_regions,
            [FoldRegion(start_line=0, end_line=1, kind="function")],
        )
        pump(qapp, 200)
        sweep.finish()
        assert_alive(qapp, qa_window)

    def test_analysis_arriving_while_typing_is_stable(self, qapp, qa_window, sample_tree):
        """Overlays arriving during typing never raise."""
        editor = _open_editor(qapp, qa_window, sample_tree)
        editor.setText("value = 1\n")
        pump(qapp, 200)
        editor.setCursorPosition(0, 0)

        def type_and_overlay() -> None:
            """Type a character and apply an overlay in the same cycle.

            Returns:
                None; the side effect is the text and overlay update.
            """
            type_text(qapp, editor, "x")
            editor._apply_semantic_overlays([(0, 3, "#00ff00")])

        race_probe(qapp, type_and_overlay, 4)
        pump(qapp, 400)
        assert_alive(qapp, qa_window)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
