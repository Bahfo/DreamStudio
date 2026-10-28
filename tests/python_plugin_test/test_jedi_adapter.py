"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the Jedi isolation adapter, both with scripted doubles and real Jedi.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from editor.Ironica.plugins.python import jedi_adapter as adapter_module
from editor.Ironica.plugins.python.domain_models import (
    CompletionDetails,
    DefinitionLocation,
    HoverDetails,
    PythonContext,
)
from editor.Ironica.plugins.python.jedi_adapter import JediAdapter


def _context(
    source: str = "x = 1\n",
    line: int = 1,
    column: int = 0,
    file_path: str | None = None,
    project_root: str | None = None,
) -> PythonContext:
    """Build a context with explicit, readable arguments."""
    return PythonContext(source, line, column, file_path, project_root)


class _FakeParam:
    """Minimal stand-in for a Jedi parameter."""

    def __init__(
        self,
        name: str,
        annotation: str = "",
        default: str | None = None,
        signature: str | None = None,
        raise_on_string: bool = False,
    ) -> None:
        self.name = name
        self.annotation = annotation
        self.default = default
        self._signature = signature if signature is not None else name
        self._raise = raise_on_string

    def to_string(self) -> str:
        if self._raise:
            raise RuntimeError("parameter rendering failed")
        return self._signature


class _FakeSignature:
    """Minimal stand-in for a Jedi signature."""

    def __init__(
        self,
        parameters: list[_FakeParam],
        annotation: str = "",
        rendered: str = "f()",
    ) -> None:
        self.params = parameters
        self.annotation = annotation
        self._rendered = rendered

    def to_string(self) -> str:
        return self._rendered


class _FakeDefinition:
    """Minimal stand-in for a Jedi name definition."""

    def __init__(
        self,
        name: str = "value",
        kind: str = "variable",
        description: str = "value",
        signatures: list[_FakeSignature] | None = None,
        docstring: str | None = None,
    ) -> None:
        self.name = name
        self.type = kind
        self.description = description
        self._signatures = signatures or []
        self._docstring = docstring

    def get_signatures(self):
        return self._signatures

    def docstring(self):
        return self._docstring


class _FakeCompletion:
    """Minimal stand-in for a Jedi completion."""

    def __init__(
        self,
        name: str,
        kind: str | None = "statement",
        signatures: list[object] | None = None,
        signature_error: Exception | None = None,
    ) -> None:
        self.name = name
        self.type = kind
        self._signatures = signatures or []
        self._signature_error = signature_error

    def get_signatures(self):
        if self._signature_error is not None:
            raise self._signature_error
        return self._signatures


class _FakeScript:
    """Configurable stand-in for ``jedi.Script``."""

    def __init__(
        self,
        help_result=None,
        infer_result=None,
        goto_result=None,
        completions=None,
        help_error: Exception | None = None,
        infer_error: Exception | None = None,
        goto_error: Exception | None = None,
        complete_error: Exception | None = None,
        goto_type_error_first: bool = False,
    ) -> None:
        self.help_result = help_result
        self.infer_result = infer_result
        self.goto_result = goto_result
        self.completions = completions or []
        self.help_error = help_error
        self.infer_error = infer_error
        self.goto_error = goto_error
        self.complete_error = complete_error
        self.goto_type_error_first = goto_type_error_first
        self.calls: list[tuple[str, dict]] = []

    def help(self, **kwargs):
        self.calls.append(("help", kwargs))
        if self.help_error is not None:
            raise self.help_error
        return self.help_result or []

    def infer(self, **kwargs):
        self.calls.append(("infer", kwargs))
        if self.infer_error is not None:
            raise self.infer_error
        return self.infer_result or []

    def goto(self, **kwargs):
        self.calls.append(("goto", kwargs))
        if self.goto_type_error_first:
            self.goto_type_error_first = False
            raise TypeError("follow_imports unsupported")
        if self.goto_error is not None:
            raise self.goto_error
        return self.goto_result or []

    def complete(self, **kwargs):
        self.calls.append(("complete", kwargs))
        if self.complete_error is not None:
            raise self.complete_error
        return self.completions


class TestDefaultExtraction:
    """Tests for parsing a rendered parameter into a default value."""

    @pytest.mark.parametrize(
        ("rendered", "expected"),
        [
            ("value=42", "42"),
            ("value='hello'", "'hello'"),
            ("value=None", "None"),
            ("value = [1, 2]", "[1, 2]"),
            ("value=a=b", "a=b"),
        ],
    )
    def test_default_is_taken_after_the_first_equals(self, rendered, expected):
        """Everything after the first ``=`` becomes the default text."""
        parameter = _FakeParam("value", signature=rendered)

        assert JediAdapter._extract_default_from_signature(parameter) == expected

    @pytest.mark.parametrize("rendered", ["value", "value=", "value=   "])
    def test_parameters_without_a_default_yield_none(self, rendered):
        """A missing or empty default is reported as ``None``."""
        parameter = _FakeParam("value", signature=rendered)

        assert JediAdapter._extract_default_from_signature(parameter) is None

    def test_rendering_failure_is_tolerated(self):
        """A Jedi rendering error does not break the hover request."""
        parameter = _FakeParam("value", raise_on_string=True)

        assert JediAdapter._extract_default_from_signature(parameter) is None


class TestScriptConstruction:
    """Tests for ``_get_script`` and project resolution."""

    def test_script_without_paths_has_no_project(self, monkeypatch):
        """A buffer with no path builds a bare script."""
        recorded = {}
        monkeypatch.setattr(
            adapter_module.JediAdapter,
            "_resolve_project",
            staticmethod(lambda ctx: None),
        )

        def fake_script(**kwargs):
            recorded.update(kwargs)
            return object()

        monkeypatch.setattr(adapter_module.jedi, "Script", fake_script)

        assert JediAdapter()._get_script(_context()) is not None
        assert recorded == {"code": "x = 1\n", "path": None}

    def test_resolved_project_is_passed_to_the_script(self, monkeypatch):
        """A resolved project is forwarded to Jedi."""
        project = object()
        recorded = {}
        monkeypatch.setattr(
            adapter_module.JediAdapter,
            "_resolve_project",
            staticmethod(lambda ctx: project),
        )

        def fake_script(**kwargs):
            recorded.update(kwargs)
            return object()

        monkeypatch.setattr(adapter_module.jedi, "Script", fake_script)

        context = _context(file_path="/tmp/module.py")
        JediAdapter()._get_script(context)

        assert recorded["project"] is project
        assert recorded["path"] == "/tmp/module.py"

    def test_script_construction_failure_returns_none(self, monkeypatch, caplog):
        """A constructor exception is logged and converted to ``None``."""

        def broken_script(**kwargs):
            raise RuntimeError("script construction failed")

        monkeypatch.setattr(adapter_module.jedi, "Script", broken_script)

        with caplog.at_level("ERROR", logger="DreamStudio.PythonSupport.JediAdapter"):
            assert JediAdapter()._get_script(_context()) is None

        assert "Failed to instantiate Jedi Script" in caplog.text

    def test_project_uses_existing_file_directory(self, tmp_path, monkeypatch):
        """An existing buffer directory becomes Jedi's project path."""
        recorded = {}

        def fake_project(**kwargs):
            recorded.update(kwargs)
            return object()

        monkeypatch.setattr(adapter_module.jedi, "Project", fake_project)
        file_path = tmp_path / "module.py"
        file_path.write_text("x = 1\n", encoding="utf-8")

        project = JediAdapter._resolve_project(_context(file_path=str(file_path)))

        assert project is not None
        assert recorded["path"] == str(tmp_path)
        assert str(tmp_path) in recorded["added_sys_path"]

    def test_project_root_and_file_directory_are_both_on_sys_path(
        self, tmp_path, monkeypatch
    ):
        """The explicit project root wins as the project path."""
        recorded = {}
        monkeypatch.setattr(
            adapter_module.jedi, "Project", lambda **kwargs: recorded.update(kwargs)
        )
        project_dir = tmp_path / "project"
        package_dir = project_dir / "pkg"
        package_dir.mkdir(parents=True)
        file_path = package_dir / "module.py"
        file_path.write_text("x = 1\n", encoding="utf-8")

        JediAdapter._resolve_project(
            _context(file_path=str(file_path), project_root=str(project_dir))
        )

        assert recorded["path"] == str(project_dir)
        assert set(recorded["added_sys_path"]) == {
            str(package_dir),
            str(project_dir),
        }

    @pytest.mark.parametrize("file_path", [None, "/does/not/exist/module.py"])
    def test_missing_directories_yield_no_project(self, file_path):
        """Paths that are not directories cannot anchor a project."""
        assert JediAdapter._resolve_project(_context(file_path=file_path)) is None

    def test_project_creation_failure_yields_none(self, tmp_path, monkeypatch):
        """A failing ``jedi.Project`` degrades to no project."""
        file_path = tmp_path / "module.py"
        file_path.write_text("x = 1\n", encoding="utf-8")

        def broken_project(**kwargs):
            raise RuntimeError("project failed")

        monkeypatch.setattr(adapter_module.jedi, "Project", broken_project)

        assert JediAdapter._resolve_project(_context(file_path=str(file_path))) is None

    def test_project_root_must_exist(self, tmp_path):
        """A configured but nonexistent project root is ignored."""
        file_path = tmp_path / "module.py"
        file_path.write_text("x = 1\n", encoding="utf-8")

        project = JediAdapter._resolve_project(
            _context(file_path=str(file_path), project_root=str(tmp_path / "missing"))
        )

        assert project is not None


class TestHoverWithScriptedJedi:
    """Tests for hover mapping and fallbacks with a controlled script."""

    @staticmethod
    def _adapter_with(script, monkeypatch) -> JediAdapter:
        adapter = JediAdapter()
        monkeypatch.setattr(adapter, "_get_script", lambda context: script)
        return adapter

    def test_signature_parameters_and_docstring_are_mapped(self, monkeypatch):
        """Jedi signatures become the rich hover domain model."""
        signature = _FakeSignature(
            parameters=[
                _FakeParam("name", annotation="str"),
                _FakeParam("times", annotation="int", default="2"),
            ],
            annotation="str",
            rendered="greet(name: str, times: int=2) -> str",
        )
        script = _FakeScript(
            help_result=[
                _FakeDefinition(
                    name="greet",
                    kind="function",
                    description="greet",
                    signatures=[signature],
                    docstring="Return a greeting.",
                )
            ]
        )
        adapter = self._adapter_with(script, monkeypatch)

        details = adapter.get_hover(_context(line=3, column=4))

        assert details is not None
        assert details.name == "greet"
        assert details.kind == "function"
        assert details.signature == "greet(name: str, times: int=2) -> str"
        assert [(p.name, p.type_hint, p.default_value) for p in details.parameters] == [
            ("name", "str", None),
            ("times", "int", "2"),
        ]
        assert details.return_type == "str"
        assert details.docstring == "Return a greeting."
        assert script.calls == [("help", {"line": 3, "column": 4})]

    def test_default_is_extracted_from_rendered_parameter(self, monkeypatch):
        """A parameter without ``.default`` still reports its rendered default."""
        signature = _FakeSignature(
            parameters=[
                _FakeParam("count", signature="count=7"),
            ]
        )
        script = _FakeScript(help_result=[_FakeDefinition(signatures=[signature])])
        adapter = self._adapter_with(script, monkeypatch)

        details = adapter.get_hover(_context())

        assert details is not None
        assert details.parameters[0].default_value == "7"

    def test_empty_help_result_falls_back_to_infer(self, monkeypatch):
        """An empty ``help`` result is retried with ``infer``."""
        script = _FakeScript(
            help_result=[],
            infer_result=[_FakeDefinition(name="inferred", kind="variable")],
        )
        adapter = self._adapter_with(script, monkeypatch)

        details = adapter.get_hover(_context())

        assert details is not None
        assert details.name == "inferred"
        assert [call[0] for call in script.calls] == ["help", "infer"]

    def test_help_failure_yields_none_without_infer(self, monkeypatch):
        """Current contract: a ``help`` exception aborts instead of inferring."""
        script = _FakeScript(
            help_error=RuntimeError("help failed"),
            infer_result=[_FakeDefinition(name="inferred", kind="variable")],
        )
        adapter = self._adapter_with(script, monkeypatch)

        assert adapter.get_hover(_context()) is None
        assert [call[0] for call in script.calls] == ["help"]

    def test_both_lookups_empty_yields_none(self, monkeypatch):
        """No Jedi definition means no hover details."""
        adapter = self._adapter_with(_FakeScript(), monkeypatch)

        assert adapter.get_hover(_context()) is None

    def test_infer_failure_yields_none(self, monkeypatch):
        """A failure during the infer fallback is swallowed."""
        script = _FakeScript(
            help_result=[],
            infer_error=RuntimeError("infer failed"),
        )
        adapter = self._adapter_with(script, monkeypatch)

        assert adapter.get_hover(_context()) is None

    def test_definition_without_signature_uses_description(self, monkeypatch):
        """Non-callable symbols use Jedi's description as the signature."""
        script = _FakeScript(
            help_result=[
                _FakeDefinition(
                    name="CONSTANT",
                    kind="variable",
                    description="CONSTANT = 42",
                )
            ]
        )
        adapter = self._adapter_with(script, monkeypatch)

        details = adapter.get_hover(_context())

        assert details is not None
        assert details.signature == "CONSTANT = 42"
        assert details.parameters == []
        assert details.return_type is None

    def test_missing_signature_annotation_and_docstring_stay_none(self, monkeypatch):
        """Optional hover fields remain ``None`` when Jedi omits them."""
        signature = _FakeSignature(parameters=[_FakeParam("value")], annotation="")
        script = _FakeScript(
            help_result=[_FakeDefinition(signatures=[signature], docstring="")]
        )
        adapter = self._adapter_with(script, monkeypatch)

        details = adapter.get_hover(_context())

        assert details is not None
        assert details.return_type is None
        assert details.docstring is None
        assert details.parameters[0].type_hint is None

    def test_signature_rendering_failure_yields_none(self, monkeypatch):
        """An unexpected mapping error is caught by the adapter boundary."""

        class BrokenDefinition(_FakeDefinition):
            def get_signatures(self):
                raise RuntimeError("signature failure")

        script = _FakeScript(help_result=[BrokenDefinition()])
        adapter = self._adapter_with(script, monkeypatch)

        assert adapter.get_hover(_context()) is None

    def test_script_unavailable_yields_none(self, monkeypatch):
        """Without a script no Jedi call is attempted."""
        adapter = JediAdapter()
        monkeypatch.setattr(adapter, "_get_script", lambda context: None)

        assert adapter.get_hover(_context()) is None


class TestDefinitionWithScriptedJedi:
    """Tests for go-to-definition mapping and fallbacks."""

    @staticmethod
    def _adapter_with(script, monkeypatch) -> JediAdapter:
        adapter = JediAdapter()
        monkeypatch.setattr(adapter, "_get_script", lambda context: script)
        return adapter

    def test_goto_maps_definition_fields(self, monkeypatch):
        """A Jedi definition becomes a ``DefinitionLocation``."""
        target = SimpleNamespace(
            module_path="/tmp/target.py",
            line=12,
            column=4,
            get_line_code=lambda: "def target():",
        )
        script = _FakeScript(goto_result=[target])
        adapter = self._adapter_with(script, monkeypatch)

        location = adapter.get_definition(_context(line=3, column=5))

        assert location == DefinitionLocation(
            file_path="/tmp/target.py",
            line=12,
            column=4,
            context_line="def target():",
        )
        assert script.calls == [
            ("goto", {"line": 3, "column": 5, "follow_imports": True})
        ]

    def test_missing_module_path_and_line_defaults(self, monkeypatch):
        """Optional target fields fall back to safe defaults."""
        target = SimpleNamespace(
            module_path=None,
            line=None,
            column=None,
            get_line_code=lambda: "",
        )
        script = _FakeScript(goto_result=[target])
        adapter = self._adapter_with(script, monkeypatch)

        location = adapter.get_definition(_context())

        assert location == DefinitionLocation(
            file_path=None, line=1, column=0, context_line=""
        )

    def test_context_line_failure_is_tolerated(self, monkeypatch):
        """A failing ``get_line_code`` does not lose the location."""
        target = SimpleNamespace(
            module_path="/tmp/target.py",
            line=3,
            column=1,
            get_line_code=lambda: (_ for _ in ()).throw(RuntimeError("no code")),
        )
        script = _FakeScript(goto_result=[target])
        adapter = self._adapter_with(script, monkeypatch)

        location = adapter.get_definition(_context())

        assert location is not None
        assert location.context_line is None

    def test_type_error_retries_without_follow_imports(self, monkeypatch):
        """Older Jedi signatures are retried without ``follow_imports``."""
        target = SimpleNamespace(
            module_path="/tmp/target.py",
            line=1,
            column=0,
            get_line_code=lambda: "def target():",
        )
        script = _FakeScript(goto_result=[target], goto_type_error_first=True)
        adapter = self._adapter_with(script, monkeypatch)

        location = adapter.get_definition(_context())

        assert location is not None
        assert [call[0] for call in script.calls] == ["goto", "goto"]
        assert script.calls[1][1] == {"line": 1, "column": 0}

    def test_empty_goto_falls_back_to_infer(self, monkeypatch):
        """When goto finds nothing, infer is consulted."""
        target = SimpleNamespace(
            module_path="/tmp/target.py",
            line=2,
            column=0,
            get_line_code=lambda: "target = 1",
        )
        script = _FakeScript(goto_result=[], infer_result=[target])
        adapter = self._adapter_with(script, monkeypatch)

        location = adapter.get_definition(_context())

        assert location is not None
        assert [call[0] for call in script.calls] == ["goto", "infer"]

    def test_goto_exception_yields_none(self, monkeypatch):
        """A failing goto is reported as no definition."""
        script = _FakeScript(goto_error=RuntimeError("goto failed"))
        adapter = self._adapter_with(script, monkeypatch)

        assert adapter.get_definition(_context()) is None

    def test_empty_goto_and_infer_yield_none(self, monkeypatch):
        """No definitions from either lookup means ``None``."""
        adapter = self._adapter_with(_FakeScript(), monkeypatch)

        assert adapter.get_definition(_context()) is None

    def test_infer_exception_yields_none(self, monkeypatch):
        """A failure during the infer fallback yields ``None``."""
        script = _FakeScript(infer_error=RuntimeError("infer failed"))
        adapter = self._adapter_with(script, monkeypatch)

        assert adapter.get_definition(_context()) is None

    def test_script_unavailable_yields_none(self, monkeypatch):
        """Without a script no definition is attempted."""
        adapter = JediAdapter()
        monkeypatch.setattr(adapter, "_get_script", lambda context: None)

        assert adapter.get_definition(_context()) is None


class TestCompletionsWithScriptedJedi:
    """Tests for completion mapping and its error boundary."""

    @staticmethod
    def _adapter_with(script, monkeypatch) -> JediAdapter:
        adapter = JediAdapter()
        monkeypatch.setattr(adapter, "_get_script", lambda context: script)
        return adapter

    def test_completions_map_all_fields(self, monkeypatch):
        """Name, insert text, kind, and joined signatures are preserved."""
        first = _FakeCompletion(
            "path",
            kind="function",
            signatures=[
                SimpleNamespace(to_string=lambda: "path(*parts)"),
                SimpleNamespace(to_string=lambda: "path()"),
            ],
        )
        second = _FakeCompletion("pardir", kind="module")
        script = _FakeScript(completions=[first, second])
        adapter = self._adapter_with(script, monkeypatch)

        results = adapter.get_completions(_context(line=2, column=5))

        assert results == [
            CompletionDetails(
                text="path",
                insert_text="path",
                kind="function",
                signature="path(*parts), path()",
            ),
            CompletionDetails(
                text="pardir",
                insert_text="pardir",
                kind="module",
                signature="",
            ),
        ]
        assert script.calls == [("complete", {"line": 2, "column": 5})]

    def test_signature_rendering_failure_keeps_completion(self, monkeypatch):
        """A broken signature only blanks the signature field."""
        script = _FakeScript(
            completions=[
                _FakeCompletion(
                    "value", signature_error=RuntimeError("signature failed")
                )
            ]
        )
        adapter = self._adapter_with(script, monkeypatch)

        results = adapter.get_completions(_context())

        assert results == [CompletionDetails("value", "value", "statement", "")]

    def test_missing_kind_becomes_empty_string(self, monkeypatch):
        """A ``None`` Jedi kind becomes an empty string."""
        script = _FakeScript(completions=[_FakeCompletion("value", kind=None)])
        adapter = self._adapter_with(script, monkeypatch)

        assert adapter.get_completions(_context()) == [
            CompletionDetails("value", "value", "", "")
        ]

    def test_complete_failure_yields_empty_list(self, monkeypatch):
        """A Jedi completion error yields no suggestions."""
        script = _FakeScript(complete_error=RuntimeError("complete failed"))
        adapter = self._adapter_with(script, monkeypatch)

        assert adapter.get_completions(_context()) == []

    def test_script_unavailable_yields_empty_list(self, monkeypatch):
        """Without a script no completion is attempted."""
        adapter = JediAdapter()
        monkeypatch.setattr(adapter, "_get_script", lambda context: None)

        assert adapter.get_completions(_context()) == []


@pytest.mark.integration
class TestRealJediIntegration:
    """End-to-end checks against the installed Jedi version."""

    MODULE = (
        "def greet(name: str, times: int = 2) -> str:\n"
        '    """Return a greeting."""\n'
        "    return name * times\n"
        "\n"
        'result = greet("hi")\n'
    )

    def test_hover_reports_function_details(self, tmp_path):
        """Real Jedi hover exposes the callable contract."""
        path = tmp_path / "module.py"
        path.write_text(self.MODULE, encoding="utf-8")
        adapter = JediAdapter()

        details = adapter.get_hover(
            _context(self.MODULE, line=5, column=12, file_path=str(path))
        )

        assert isinstance(details, HoverDetails)
        assert details.name == "greet"
        assert details.kind == "function"
        assert "greet(" in details.signature
        assert [parameter.name for parameter in details.parameters] == [
            "name",
            "times",
        ]
        assert details.parameters[1].default_value == "2"
        assert details.docstring is not None
        assert "Return a greeting." in details.docstring

    def test_definition_reports_the_local_function(self, tmp_path):
        """Real Jedi resolves a same-file call to its definition line."""
        source = (
            "def target(value: int) -> int:\n"
            "    return value\n"
            "\n"
            "answer = target(3)\n"
        )
        path = tmp_path / "module.py"
        path.write_text(source, encoding="utf-8")
        adapter = JediAdapter()

        location = adapter.get_definition(
            _context(source, line=4, column=12, file_path=str(path))
        )

        assert isinstance(location, DefinitionLocation)
        assert os.path.abspath(location.file_path) == os.path.abspath(path)
        assert location.line == 1
        assert location.column == 4
        assert location.context_line.startswith("def target(")

    def test_completions_include_an_imported_attribute(self, tmp_path):
        """Real Jedi completes attributes of an imported module."""
        source = "import os\nos.pa\n"
        path = tmp_path / "module.py"
        path.write_text(source, encoding="utf-8")
        adapter = JediAdapter()

        completions = adapter.get_completions(
            _context(source, line=2, column=5, file_path=str(path))
        )

        names = {completion.text for completion in completions}
        assert "path" in names
        assert all(
            isinstance(completion, CompletionDetails) for completion in completions
        )
        assert all(
            completion.insert_text == completion.text for completion in completions
        )

    def test_hover_on_unknown_symbol_yields_none(self, tmp_path):
        """Unresolvable names do not fabricate hover details."""
        source = "unknown_name\n"
        path = tmp_path / "module.py"
        path.write_text(source, encoding="utf-8")

        assert (
            JediAdapter().get_hover(
                _context(source, line=1, column=2, file_path=str(path))
            )
            is None
        )

    def test_empty_source_is_handled(self):
        """An empty buffer yields no hover/definition but builtin completions."""
        adapter = JediAdapter()

        assert adapter.get_hover(_context("", line=1, column=0)) is None
        assert adapter.get_definition(_context("", line=1, column=0)) is None
        completions = adapter.get_completions(_context("", line=1, column=0))
        assert completions
        assert all(
            isinstance(completion, CompletionDetails) for completion in completions
        )
