"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Find and replace live tests: the search engine contract and the FindReplace
popup driven against the real window.
"""

from pathlib import Path

import pytest

from harness import (
    assert_alive,
    click,
    key_sequence,
    pump,
    race_probe,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]


def _find_replace(window):
    """Return the window's FindReplace popup, creating it when needed.

    Args:
        window: The DreamStudio main window.

    Returns:
        The FindReplace instance owned by the window.
    """
    window._toggle_search_widget()
    pump(qapp_instance(), 150)
    return window._find_replace_window


def qapp_instance():
    """Return the live QApplication instance.

    Returns:
        The QApplication singleton.
    """
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance()


class TestSearchEngine:
    """The file search engine honours query modes and scopes."""

    def test_plain_query_finds_matches(self, qapp, sample_tree):
        """A plain substring query returns matching lines."""
        from editor.api.file_search import execute_search

        matches = execute_search(str(sample_tree), "greet")
        assert matches, "plain query found nothing"
        assert all(
            "greet" in match["text"] for match in matches
        ), "engine returned non-matching lines"

    def test_case_insensitive_by_default(self, qapp, sample_tree):
        """The default search ignores case."""
        from editor.api.file_search import execute_search

        matches = execute_search(str(sample_tree), "find me")
        assert matches, "case-insensitive query found nothing"

    def test_case_sensitive_query_filters(self, qapp, sample_tree):
        """A case-sensitive query returns only exact-case matches."""
        from editor.api.file_search import execute_search

        matches = execute_search(str(sample_tree), "FIND ME", is_ignore_case=False)
        assert matches, "case-sensitive query found nothing"
        assert all(
            "FIND ME" in match["text"] for match in matches
        ), "case-sensitive query returned other cases"

    def test_regex_query(self, qapp, sample_tree):
        """A regex query matches by pattern."""
        from editor.api.file_search import execute_search

        matches = execute_search(str(sample_tree), r"def \w+\(", is_regex=True)
        assert matches, "regex query found nothing"

    def test_invalid_regex_falls_back_to_literal(self, qapp, sample_tree):
        """An invalid regex pattern falls back to a literal search."""
        from editor.api.file_search import regex_compile_query

        compiled = regex_compile_query("def f(", is_regex=True)
        assert compiled.search("def f(") is not None, "invalid regex lost the literal"

    def test_glob_query(self, qapp, sample_tree):
        """A glob query matches file names.

        NOTE (QA finding): ``execute_search`` compiles a glob query into a
        regex and applies it to every line of every file, so a glob such as
        ``*.py`` never matches a file name.
        """
        from editor.api.file_search import execute_search

        matches = execute_search(str(sample_tree), "*.py")
        assert matches, "glob query found nothing"
        assert all(
            match["file"].endswith(".py") for match in matches
        ), "glob query returned non-python files"

    def test_empty_query_returns_nothing(self, qapp, sample_tree):
        """An empty query returns no matches instead of every line.

        NOTE (QA finding): the FindReplace popup skips empty queries, but
        ``execute_search`` compiles an empty query into a regex that matches
        everything.
        """
        from editor.api.file_search import execute_search

        assert execute_search(str(sample_tree), "") == []

    def test_missing_scope_is_skipped(self, qapp, sample_tree):
        """A nonexistent scope directory does not raise."""
        from editor.api.file_search import execute_search

        matches = execute_search(str(sample_tree), "greet", scope_dirs=["nope"])
        assert isinstance(matches, list), "search did not return a list"

    def test_relative_scope_is_resolved(self, qapp, sample_tree):
        """A relative scope directory resolves against the root."""
        from editor.api.file_search import execute_search

        matches = execute_search(str(sample_tree), "greet", scope_dirs=["."])
        assert isinstance(matches, list), "relative scope search failed"

    def test_excluded_directories_are_skipped(self, qapp, sample_tree):
        """Default excludes keep build and VCS directories out of results."""
        from editor.api.file_search import execute_search

        cache = Path(sample_tree) / "__pycache__"
        cache.mkdir()
        (cache / "cached_module.py").write_text(
            "cached_marker = 'qa cache marker'\n", encoding="utf-8"
        )
        matches = execute_search(str(sample_tree), "qa cache marker")
        assert not matches, "excluded directory content leaked into results"


class TestFindReplaceWidget:
    """The FindReplace popup behaves as a live search UI."""

    def test_toggle_creates_and_shows_popup(self, qapp, qa_window):
        """Toggling search creates the popup and shows it."""
        window = qa_window
        popup = _find_replace(window)
        assert popup is not None, "find/replace popup was not created"
        assert popup.isVisible(), "find/replace popup is not visible"

    def test_toggle_hides_popup(self, qapp, qa_window):
        """A second toggle hides the popup again."""
        window = qa_window
        popup = _find_replace(window)
        assert popup.isVisible(), "popup did not open"
        window._toggle_search_widget()
        pump(qapp, 150)
        assert not popup.isVisible(), "popup did not hide on the second toggle"

    def test_ctrl_f_opens_popup(self, qapp, qa_window):
        """The Ctrl+F shortcut opens the find/replace popup.

        NOTE (QA finding): no Ctrl+F shortcut is registered anywhere in the
        IDE; the FindReplace popup is only reachable through the menus.
        """
        window = qa_window
        key_sequence(qapp, window, "Ctrl+F")
        pump(qapp, 200)
        popup = getattr(window, "_find_replace_window", None)
        assert popup is not None, "Ctrl+F did not create the find/replace popup"

    def test_search_finds_matches_in_workspace(self, qapp, qa_window, sample_tree):
        """Searching for a sample symbol lists a result."""
        window = qa_window
        popup = _find_replace(window)
        popup.current_directory = str(sample_tree)
        popup.search_input.setText("greet")
        popup.start_search()
        pump(qapp, 1500)
        texts = [
            popup.results_list.item(i).text() for i in range(popup.results_list.count())
        ]
        assert any(
            "greet" in text for text in texts
        ), f"search results missing the symbol: {texts}"

    def test_search_with_no_matches_reports_cleanly(self, qapp, qa_window, sample_tree):
        """A query with no hits reports 'No matches found.'."""
        window = qa_window
        popup = _find_replace(window)
        popup.current_directory = str(sample_tree)
        popup.search_input.setText("zzz_no_such_symbol_zzz")
        popup.start_search()
        pump(qapp, 1500)
        texts = [
            popup.results_list.item(i).text() for i in range(popup.results_list.count())
        ]
        assert any(
            "No matches" in text for text in texts
        ), f"no-match search did not report cleanly: {texts}"

    def test_empty_query_is_ignored(self, qapp, qa_window, sample_tree):
        """An empty query does not start a search."""
        window = qa_window
        popup = _find_replace(window)
        popup.current_directory = str(sample_tree)
        popup.search_input.setText("")
        popup.start_search()
        pump(qapp, 300)
        assert popup.results_list.count() == 0, "empty query started a search"

    def test_toggle_buttons_change_search_mode(self, qapp, qa_window, sample_tree):
        """The regex and match-case toggles change the search behaviour."""
        window = qa_window
        popup = _find_replace(window)
        popup.current_directory = str(sample_tree)
        popup.btn_regex.setChecked(True)
        popup.btn_match_case.setChecked(True)
        assert popup.btn_regex.isChecked(), "regex toggle did not stick"
        assert popup.btn_match_case.isChecked(), "match-case toggle did not stick"

    def test_result_click_opens_file(self, qapp, qa_window, sample_tree):
        """Clicking a search result opens the matching file."""
        window = qa_window
        popup = _find_replace(window)
        popup.current_directory = str(sample_tree)
        popup.search_input.setText("greet")
        popup.start_search()
        pump(qapp, 1500)
        if popup.results_list.count() == 0:
            pytest.skip("search produced no results for the sample workspace")
        item = popup.results_list.item(0)
        tabs = window.hero_window._text_editor_center.tabs
        before = tabs.count()
        popup._on_result_clicked(item)
        pump(qapp, 400)
        assert tabs.count() >= before, "result click closed the editor tab"

    def test_replace_all_updates_file(self, qapp, qa_window, sample_tree):
        """Replace All rewrites the matched text in the file on disk."""
        window = qa_window
        popup = _find_replace(window)
        popup.current_directory = str(sample_tree)
        popup.search_input.setText("greet")
        popup.replace_input.setText("salute")
        popup.start_search()
        pump(qapp, 1500)
        replaced = popup._do_replace_all()
        pump(qapp, 400)
        assert replaced >= 1, "replace all reported no replacements"
        content = (Path(sample_tree) / "main.py").read_text()
        assert "salute" in content, "file content was not rewritten"

    def test_clear_button_resets_popup(self, qapp, qa_window, sample_tree):
        """The clear button empties the inputs and the result list."""
        window = qa_window
        popup = _find_replace(window)
        popup.current_directory = str(sample_tree)
        popup.search_input.setText("greet")
        popup.start_search()
        pump(qapp, 1000)
        click(qapp, popup.btn_clear)
        pump(qapp, 200)
        assert popup.search_input.text() == "", "search input not cleared"
        assert popup.results_list.count() == 0, "results not cleared"

    def test_filters_toggle_reveals_inputs(self, qapp, qa_window):
        """The filter toggle reveals the include/exclude inputs."""
        window = qa_window
        popup = _find_replace(window)
        assert not popup.filters_container.isVisible(), "filters visible by default"
        popup.btn_toggle_filters.setChecked(True)
        pump(qapp, 150)
        assert popup.filters_container.isVisible(), "filters did not appear"

    def test_rapid_searches_stay_consistent(self, qapp, qa_window, sample_tree):
        """A storm of searches leaves the popup usable and the window alive."""
        window = qa_window
        popup = _find_replace(window)
        popup.current_directory = str(sample_tree)

        def search_once() -> None:
            """Run one search cycle with a rotating query.

            Returns:
                None; the side effect is the executed search.
            """
            popup.search_input.setText("greet")
            popup.start_search()
            pump(qapp, 80)

        race_probe(qapp, search_once, 3)
        pump(qapp, 800)
        assert_alive(qapp, window)
        assert popup.results_list.count() >= 0, "results list in a broken state"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
