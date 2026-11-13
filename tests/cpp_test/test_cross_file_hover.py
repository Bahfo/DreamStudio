"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Cross-file hover tests: header documentation must reach source symbols.

These tests exercise real libclang parses in temporary projects. They cover
same-directory headers, conventional ``include/`` + ``src/`` layouts without
build metadata, function templates, macros, and unsaved header buffers.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

from editor.Ironica.plugins.cpp.intellisense import args as cpp_args
from editor.Ironica.plugins.cpp.intellisense import headers
from editor.Ironica.plugins.cpp.intellisense.engine import CppEngine
from editor.Ironica.plugins.cpp.models import CppContext
from editor.Ironica.plugins.cpp.navigation.engine import NavigationEngine
from editor.Ironica.plugins.cpp.provider import CppProvider


@pytest.fixture(autouse=True)
def _clear_header_caches():
    """Keep global header/model caches from leaking between tests."""
    headers._resolved.clear()
    headers._unresolved.clear()
    cpp_args._MODEL_CACHE.clear()
    yield
    headers._resolved.clear()
    headers._unresolved.clear()
    cpp_args._MODEL_CACHE.clear()


def _write(path: Path, text: str) -> Path:
    """Write dedented *text* to *path*, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")
    return path


def _token_column(line: str, token: str) -> int:
    """Return the zero-based column of the standalone *token* in *line*."""
    match = re.search(rf"\b{re.escape(token)}\b", line)
    if match is None:
        raise AssertionError(f"{token!r} not found in {line!r}")
    return match.start()


def _line_index(lines: list[str], marker: str) -> int:
    """Return the index of the first line containing *marker*."""
    for index, line in enumerate(lines):
        if marker in line:
            return index
    raise AssertionError(f"{marker!r} not found in source")


def _hover_with_provider(path: Path, marker: str, token: str):
    """Hover *token* on the line containing *marker* via the provider API."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    line_index = _line_index(lines, marker)
    column = _token_column(lines[line_index], token)
    provider = CppProvider()
    provider._file_path = str(path)
    return provider.get_hover_display(text, line_index, column)


def _hover_with_engine(
    path: Path,
    marker: str,
    token: str,
    unsaved: list[tuple[str, str]] | None = None,
):
    """Hover *token* on the line containing *marker* via the engine."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    line_index = _line_index(lines, marker)
    column = _token_column(lines[line_index], token)
    engine = NavigationEngine(CppEngine())
    if unsaved:
        engine.set_unsaved_buffers(unsaved)
    context = CppContext(
        source_code=text,
        line=line_index + 1,
        col=column + 1,
        file_path=str(path),
    )
    return engine.get_hover(context)


class TestHeaderDiscovery:
    """Tests for conventional project include discovery."""

    def test_project_root_finds_include_sibling(self, tmp_path: Path):
        """A project with ``include/`` is recognized without build metadata."""
        project = tmp_path / "project"
        source = _write(project / "src" / "main.cpp", "int main() { return 0; }\n")
        (project / "include").mkdir(parents=True)

        assert headers.project_root_for(str(source)) == str(project)

    def test_project_include_dirs_contains_include(self, tmp_path: Path):
        """Inferred include roots contain the project's ``include/`` folder."""
        project = tmp_path / "project"
        source = _write(project / "src" / "main.cpp", "int main() { return 0; }\n")
        include = project / "include"
        include.mkdir(parents=True)

        assert str(include) in headers.project_include_dirs(str(source))

    def test_locate_header_finds_include_directory(self, tmp_path: Path):
        """A header in ``include/`` is located from the project root."""
        project = tmp_path / "project"
        header = _write(project / "include" / "geom.h", "int area(int w, int h);\n")

        assert headers.locate_header(
            "geom.h",
            [],
            headers.project_root_for(str(project / "src" / "main.cpp")),
        ) == [str(header.parent)]

    def test_locate_header_handles_nested_include_path(self, tmp_path: Path):
        """``core/geom.h`` resolves to the directory before ``core``."""
        project = tmp_path / "project"
        include = project / "include"
        _write(include / "core" / "geom.h", "int area(int w, int h);\n")

        assert headers.locate_header("core/geom.h", [], str(project)) == [str(include)]

    def test_args_for_file_adds_inferred_include_root(self, tmp_path: Path):
        """Compile arguments include the inferred ``include/`` directory."""
        project = tmp_path / "project"
        include = project / "include"
        include.mkdir(parents=True)
        source = _write(project / "src" / "main.cpp", '#include "geom.h"\n')

        arguments = cpp_args.args_for_file(str(source), source.read_text())
        includes = [
            arguments[index + 1]
            for index, argument in enumerate(arguments)
            if argument == "-I"
        ]

        assert str(include) in includes


class TestCrossFileHover:
    """Header documentation must accompany source-side symbols."""

    def test_same_directory_header_docs_at_definition_and_call(self, tmp_path: Path):
        """A same-directory header's docs appear at the definition and call."""
        project = tmp_path / "project"
        _write(
            project / "math.h",
            """
            #pragma once

            /// Adds two integers.
            /// @param a first value
            /// @param b second value
            int add(int a, int b);
            """,
        )
        source = _write(
            project / "math.cpp",
            """
            #include "math.h"

            int add(int a, int b) { return a + b; }

            int main() { return add(1, 2); }
            """,
        )

        definition = _hover_with_provider(source, "int add(int a, int b)", "add")
        call = _hover_with_provider(source, "return add(1, 2)", "add")

        for title, body in (definition, call):
            assert title == "## add (Function)"
            assert "int add(int a, int b)" in body
            assert "Adds two integers." in body
            assert "@param a first value" in body

    def test_include_src_layout_without_build_metadata(self, tmp_path: Path):
        """``include/`` + ``src/`` projects work without CMake or git markers."""
        project = tmp_path / "project"
        _write(
            project / "include" / "geom.h",
            """
            #pragma once

            /// Computes the area of a rectangle.
            /// @param w width
            /// @param h height
            double area(double w, double h);

            /// A point in 2D space.
            struct Point {
                double x;
                double y;
            };
            """,
        )
        geometry = _write(
            project / "src" / "geom.cpp",
            """
            #include "geom.h"

            double area(double w, double h) { return w * h; }
            """,
        )
        main = _write(
            project / "src" / "main.cpp",
            """
            #include "geom.h"

            int main() {
                Point p{1.0, 2.0};
                return (int)area(p.x, p.y);
            }
            """,
        )

        definition = _hover_with_provider(geometry, "double area(double w", "area")
        call = _hover_with_provider(main, "return (int)area", "area")
        point = _hover_with_provider(main, "Point p{", "Point")

        assert "Computes the area of a rectangle." in definition[1]
        assert "double area(double w, double h)" in definition[1]
        assert "Computes the area of a rectangle." in call[1]
        assert point[0] == "## Point (Struct)"
        assert "A point in 2D space." in point[1]

    def test_out_of_line_method_uses_header_docs(self, tmp_path: Path):
        """A method defined in a source file keeps its header documentation."""
        project = tmp_path / "project"
        _write(
            project / "include" / "widget.h",
            """
            #pragma once
            #include <string>

            /// A widget in the UI.
            class Widget {
            public:
                /// Returns the widget label.
                /// @return the label text
                const std::string& label() const;
            };
            """,
        )
        source = _write(
            project / "src" / "widget.cpp",
            """
            #include "widget.h"

            const std::string& Widget::label() const {
                static std::string text;
                return text;
            }
            """,
        )

        title, body = _hover_with_provider(
            source, "const std::string& Widget::label", "label"
        )

        assert title == "## label (Method)"
        assert "const std::string & label() const" in body
        assert "Returns the widget label." in body
        assert "@return the label text" in body

    def test_function_template_call_uses_header_docs(self, tmp_path: Path):
        """Template calls resolve beyond ``OVERLOADED_DECL_REF`` to header docs."""
        project = tmp_path / "project"
        _write(
            project / "include" / "identity.h",
            """
            #pragma once

            /// Returns its argument unchanged.
            /// @tparam T element type
            /// @param value input value
            template <typename T>
            T identity(T value);
            """,
        )
        source = _write(
            project / "src" / "identity.cpp",
            """
            #include "identity.h"

            template <typename T>
            T identity(T value) { return value; }

            int main() { return identity(7); }
            """,
        )

        title, body = _hover_with_provider(source, "return identity(7)", "identity")

        assert title == "## identity (Function template)"
        assert "T identity(T)" in body
        assert "Returns its argument unchanged." in body
        assert "@tparam T element type" in body

    def test_macro_comment_from_header_is_used(self, tmp_path: Path):
        """Macros carry the documentation written above their definition."""
        project = tmp_path / "project"
        _write(
            project / "include" / "config.h",
            """
            #pragma once

            /// The magic configuration value.
            #define MAGIC 42
            """,
        )
        source = _write(
            project / "src" / "config.cpp",
            """
            #include "config.h"

            int value() { return MAGIC; }
            """,
        )

        title, body = _hover_with_provider(source, "return MAGIC", "MAGIC")

        assert title == "## MAGIC (Macro)"
        assert "The magic configuration value." in body

    def test_unsaved_header_docs_are_visible_in_source(self, tmp_path: Path):
        """Documentation typed into an unsaved header reaches the source hover."""
        project = tmp_path / "project"
        header = _write(
            project / "lib.h",
            """
            #pragma once
            int thing(int value);
            """,
        )
        source = _write(
            project / "lib.cpp",
            """
            #include "lib.h"

            int thing(int value) { return value; }
            int call() { return thing(3); }
            """,
        )
        edited_header = header.read_text(encoding="utf-8").replace(
            "int thing(int value);",
            "/// Unsaved header documentation.\nint thing(int value);",
        )

        hover = _hover_with_engine(
            source,
            "return thing(3)",
            "thing",
            unsaved=[(str(header), edited_header)],
        )

        assert hover is not None
        assert hover.docstring == "Unsaved header documentation."

    def test_source_docs_are_kept_when_header_has_none(self, tmp_path: Path):
        """A source-local comment still appears when the header is undocumented."""
        project = tmp_path / "project"
        _write(
            project / "plain.h",
            """
            #pragma once
            int compute(int value);
            """,
        )
        source = _write(
            project / "plain.cpp",
            """
            #include "plain.h"

            /// Computes a value locally.
            int compute(int value) { return value * 2; }
            """,
        )

        hover = _hover_with_provider(source, "int compute(int value)", "compute")

        assert "Computes a value locally." in hover[1]

    def test_regular_method_signature_is_not_lost(self, tmp_path: Path):
        """Cross-file lookup keeps the original signature and kind."""
        project = tmp_path / "project"
        _write(
            project / "include" / "shape.h",
            """
            #pragma once

            /// A drawable shape.
            struct Shape {
                /// Draws the shape.
                void draw() const;
            };
            """,
        )
        source = _write(
            project / "src" / "shape.cpp",
            """
            #include "shape.h"

            void Shape::draw() const {}
            """,
        )

        title, body = _hover_with_provider(source, "void Shape::draw()", "draw")

        assert title == "## draw (Method)"
        assert "void draw() const" in body
        assert "Draws the shape." in body
