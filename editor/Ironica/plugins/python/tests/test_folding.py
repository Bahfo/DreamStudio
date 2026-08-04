"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the Python plugin's folding integration with the Ironica editor.

Covers the wiring of the ``_setup_folding_display_text`` and
``set_custom_import_fold_text`` editor APIs into the Python plugin's
fold computation flow.
"""

import pytest

from editor.Ironica.plugins.python.folding import (
    compute_fold_regions,
    compute_folds_for_editor,
)

SRC = (
    "import os\n"
    "import sys\n"
    "import re\n"
    "\n"
    "def foo():\n"
    "    pass\n"
)


class _StubFoldManager:
    """Records the regions the plugin pushes to the editor."""

    def __init__(self):
        self.regions = []

    def set_fold_regions(self, regions):
        self.regions = list(regions)


class _StubEditor:
    """Minimal editor double exposing only the folding API surface."""

    def __init__(self, text):
        self._text = text
        self._fold_manager = _StubFoldManager()
        self.fold_text_setup_calls = 0
        self.import_fold_text = []

    def text(self):
        return self._text


class _StubEditorWithFoldText(_StubEditor):
    """Editor double that also provides the fold-display-text APIs."""

    def _setup_folding_display_text(self):
        self.fold_text_setup_calls += 1

    def set_custom_import_fold_text(self, line, import_count):
        self.import_fold_text.append((line, import_count))


class TestComputeFoldsForEditor:
    def test_regions_include_import_block(self):
        ed = _StubEditor(SRC)
        compute_folds_for_editor(ed)
        kinds = [(r.kind, r.start_line, r.end_line) for r in ed._fold_manager.regions]
        assert ("import", 0, 2) in kinds
        assert ("function", 4, 5) in kinds

    def test_enables_fold_display_text(self):
        ed = _StubEditorWithFoldText(SRC)
        compute_folds_for_editor(ed)
        assert ed.fold_text_setup_calls == 1

    def test_tags_import_header_with_import_count(self):
        ed = _StubEditorWithFoldText(SRC)
        compute_folds_for_editor(ed)
        assert ed.import_fold_text == [(0, 3)]

    def test_does_not_tag_non_import_regions(self):
        ed = _StubEditorWithFoldText("def foo():\n    pass\n")
        compute_folds_for_editor(ed)
        assert ed.import_fold_text == []
        assert ed.fold_text_setup_calls == 1

    def test_tolerates_editor_without_new_apis(self):
        ed = _StubEditor(SRC)
        compute_folds_for_editor(ed)
        assert any(r.kind == "import" for r in ed._fold_manager.regions)

    def test_empty_buffer_is_noop(self):
        ed = _StubEditor("")
        compute_folds_for_editor(ed)
        assert ed._fold_manager.regions == []
        assert ed.import_fold_text == []
        assert ed.fold_text_setup_calls == 0


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestEditorIntegration:
    def test_fold_text_does_not_toggle_fold(self, qapp):
        from PyQt6.Qsci import QsciScintilla

        from editor.Ironica.code_editor import CodeEditor
        from editor.Ironica.plugins.registration import register_python_language

        register_python_language()
        ed = CodeEditor(language="python")
        try:
            ed.setText(SRC)
            compute_folds_for_editor(ed)

            folded = [r for r in ed._fold_manager.get_fold_regions() if r.kind == "import"]
            assert len(folded) == 1
            header = folded[0].start_line

            # After a plugin run the import fold must not have been toggled
            # by the fold-display-text call.
            assert ed.SendScintilla(QsciScintilla.SCI_GETFOLDEXPANDED, header) == 1

            # Setting the text on an already-collapsed fold keeps it collapsed.
            ed._fold_manager.collapse_region(folded[0])
            ed.set_custom_import_fold_text(header, 3)
            assert ed.SendScintilla(QsciScintilla.SCI_GETFOLDEXPANDED, header) == 0
        finally:
            ed.deleteLater()
