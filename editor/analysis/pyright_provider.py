"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

basedpyright semantic/type diagnostics provider for the Problems scanner.

basedpyright complements the other providers with the diagnostics they cannot
produce: unresolved names and imports, undefined attributes, invalid calls and
type mismatches. Its CLI emits structured JSON
(``--outputjson`` → ``generalDiagnostics[]`` with severity, message, rule and
an exact character range), which maps directly onto the shared ``Problem``
model.

Design constraints honoured here:

* optional — a missing binary is reported as a *provider note*, never as an
  error, so the panel never shows a false failure for an uninstalled tool;
* isolated — every failure mode (missing binary, non-zero exit, timeout,
  malformed JSON) becomes a :class:`ProviderResult` with ``error`` set, which
  the composition layer records while keeping the other providers' output;
* read-only — analysis never writes into the workspace;
* workspace-configured — invoked with the workspace as ``cwd`` so
  ``pyproject.toml`` / ``basedpyrightconfig.json`` are honoured;
* buffer aware — pyright's CLI has no stdin mode, so unsaved buffers are only
  analyzed when the installed build advertises one; otherwise the provider
  reports a note and the built-in/Ruff buffer results stand on their own.
"""

from editor import *

import json
import logging
import shutil
import subprocess

from editor.analysis.types import (
    Problem,
    ProblemProvider,
    ProblemSeverity,
    ProviderResult,
)

logger = logging.getLogger(__name__)

#: Environment variable holding an explicit basedpyright executable path.
BASEDPYRIGHT_PATH_ENV = "DREAMSTUDIO_BASEDPYRIGHT"

#: Source tag attached to every diagnostic produced by this provider.
BASEDPYRIGHT_SOURCE = "pyright"

#: Wall-clock budget for a whole-workspace run.
WORKSPACE_TIMEOUT_SECONDS = 300

#: Wall-clock budget for a single-file run.
FILE_TIMEOUT_SECONDS = 120

#: Exit codes that still carry a valid JSON payload.
_SUCCESS_CODES = (0, 1)

_MISSING = "not installed (basedpyright executable not found)"
_BAD_OUTPUT = "basedpyright returned invalid JSON output"
_NO_BUFFER_SUPPORT = "basedpyright CLI has no stdin mode"

_SEVERITY_MAP = {
    "error": ProblemSeverity.ERROR,
    "warning": ProblemSeverity.WARNING,
    "warning2": ProblemSeverity.WARNING,
    "information": ProblemSeverity.INFO,
    "note": ProblemSeverity.INFO,
    "hint": ProblemSeverity.TYPO,
    "unused": ProblemSeverity.TYPO,
    "unusedcode": ProblemSeverity.TYPO,
    "unreachable": ProblemSeverity.TYPO,
    "deprecated": ProblemSeverity.TYPO,
}

#: Cached stdin capability probe (None = not probed yet).
_SUPPORTS_STDIN: Optional[bool] = None

#: Workspace mirrors reused for unsaved-buffer analysis, keyed by root.
_MIRRORS: Dict[str, str] = {}


def _drop_all_mirrors() -> None:
    """Remove every cached mirror workspace (interpreter shutdown)."""
    for root in list(_MIRRORS):
        _remove_mirror(_MIRRORS.pop(root))


atexit.register(_drop_all_mirrors)


def basedpyright_command(executable: Optional[list] = None) -> Optional[list]:
    """Return the basedpyright argv prefix, or ``None`` when unavailable.

    Resolution order: explicit *executable*, ``DREAMSTUDIO_BASEDPYRIGHT``,
    ``PATH``, a workspace-local ``node_modules/.bin``, then the Python
    distribution entry point.

    Args:
        executable: Explicit argv prefix (used by tests and callers that
            already resolved one).

    Returns:
        Argv prefix such as ``["basedpyright"]``, or ``None``.
    """
    if executable:
        return list(executable)

    override = os.environ.get(BASEDPYRIGHT_PATH_ENV, "").strip()
    if override:
        resolved = shutil.which(override) or override
        if resolved and (os.path.isfile(resolved) or shutil.which(override)):
            return [resolved]

    on_path = shutil.which("basedpyright") or shutil.which("pyright")
    if on_path:
        return [on_path]

    for root in (os.getcwd(), resource_root()):
        candidate = os.path.join(root, "node_modules", ".bin", "basedpyright")
        if os.path.isfile(candidate):
            return [candidate]

    try:
        import importlib.util

        if importlib.util.find_spec("basedpyright") is not None:
            return [sys.executable, "-m", "basedpyright"]
    except Exception:
        pass
    return None


def find_basedpyright(root: Optional[str] = None) -> Optional[list]:
    """Discover the basedpyright argv prefix for *root*.

    Args:
        root: Workspace directory searched for ``node_modules/.bin`` first.

    Returns:
        Argv prefix, or ``None`` when basedpyright is not installed.
    """
    if root:
        candidate = os.path.join(root, "node_modules", ".bin", "basedpyright")
        if os.path.isfile(candidate):
            return [candidate]
    return basedpyright_command()


def resource_root() -> str:
    """Return the IDE installation directory."""
    from editor.utils.resource_path import resource_path

    return resource_path(".")


def map_severity(value: object) -> ProblemSeverity:
    """Map a basedpyright severity string onto the shared severity model.

    Args:
        value: Raw severity reported by basedpyright.

    Returns:
        The matching :class:`ProblemSeverity`; unknown values become ``TYPO``
        so they stay visible as style-level hints.
    """
    normalized = str(value or "").strip().lower()
    return _SEVERITY_MAP.get(normalized, ProblemSeverity.TYPO)


def supports_stdin(command: Optional[list] = None) -> bool:
    """Return ``True`` when the installed build can read from stdin.

    The probe runs ``--help`` once per process and caches the answer. When the
    binary is missing the answer is ``False``.

    Args:
        command: Explicit argv prefix; auto-discovered when omitted.

    Returns:
        ``True`` only when the CLI advertises a stdin option.
    """
    global _SUPPORTS_STDIN
    if command is None and _SUPPORTS_STDIN is not None:
        return _SUPPORTS_STDIN
    argv = command or find_basedpyright()
    if not argv:
        return False
    try:
        completed = subprocess.run(  # noqa: S603 - fixed, read-only argv
            [*argv, "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    help_text = f"{completed.stdout}\n{completed.stderr}".lower()
    result = "stdin" in help_text
    if command is None:
        _SUPPORTS_STDIN = result
    return result


class BasedPyrightProvider(ProblemProvider):
    """Read-only ``basedpyright --outputjson`` provider.

    Attributes:
        root: Workspace directory used as the subprocess working directory.
        executable: Resolved argv prefix (``None`` auto-discovers).
        last_error: Failure message of the most recent run, or ``None``.
        last_note: Non-fatal note about provider capabilities, or ``None``.
    """

    def __init__(self, root: str, executable: Optional[list] = None) -> None:
        self.root = os.path.abspath(root or "") or os.getcwd()
        self.executable = executable
        self.last_error: Optional[str] = None
        self.last_note: Optional[str] = None

    # ------------------------------------------------------------------
    # Public provider API
    # ------------------------------------------------------------------

    def collect(self) -> List[Problem]:
        """Analyze the whole workspace.

        Returns:
            List of :class:`Problem` items; failures are exposed through
            :attr:`last_error` and return an empty list.
        """
        return self.scan_workspace().problems

    def scan_workspace(self) -> ProviderResult:
        """Run basedpyright over the workspace and normalize the JSON.

        Returns:
            A :class:`ProviderResult` carrying diagnostics or an ``error``.
        """
        command = self.executable or find_basedpyright(self.root)
        if not command:
            self.last_error = None
            self.last_note = _MISSING
            logger.info("basedpyright not installed; skipping workspace %s", self.root)
            return ProviderResult([], None, _MISSING)
        self.last_note = None
        argv = [*command, "--outputjson", "--level", "warning", "."]
        return self._run(argv, timeout=WORKSPACE_TIMEOUT_SECONDS)

    def analyze_file(self, path: str) -> ProviderResult:
        """Analyze a single saved file.

        Args:
            path: Absolute path of the file to analyze.

        Returns:
            A :class:`ProviderResult` for that file.
        """
        command = self.executable or find_basedpyright(self.root)
        if not command:
            self.last_error = None
            self.last_note = _MISSING
            return ProviderResult([], None, _MISSING)
        self.last_note = None
        argv = [
            *command,
            "--outputjson",
            "--level",
            "warning",
            "--skipunannotated",
            path,
        ]
        return self._run(argv, timeout=FILE_TIMEOUT_SECONDS)

    def analyze_source(self, path: str, content: str) -> ProviderResult:
        """Analyze an in-memory buffer when the CLI supports stdin.

        Args:
            path: Buffer path used for diagnostics and as filename context.
            content: In-memory editor text.

        Returns:
            A :class:`ProviderResult`; when the installed build has no stdin
            mode the result is *successful but empty* with :attr:`last_note`
            set, so the caller can surface the capability gap without
            reporting a provider failure.
        """
        command = self.executable or find_basedpyright(self.root)
        if not command:
            self.last_error = None
            self.last_note = _MISSING
            return ProviderResult([], None, _MISSING)
        if not supports_stdin(command):
            return self._analyze_via_mirror(command, path, content)
        argv = [
            *command,
            "--outputjson",
            "--level",
            "warning",
            "--stdin",
            path,
        ]
        return self._run(argv, timeout=FILE_TIMEOUT_SECONDS, stdin_text=content)

    # ------------------------------------------------------------------
    # Buffer analysis without a stdin mode
    # ------------------------------------------------------------------

    def _analyze_via_mirror(
        self, command: List[str], path: str, content: str
    ) -> ProviderResult:
        """Analyze an unsaved buffer through a mirrored workspace shadow.

        basedpyright's CLI cannot read stdin, so the in-memory text is written
        into a throw-away mirror of the workspace (the real entries are
        symlinked, the edited file is a real copy). Imports, configuration and
        project layout therefore resolve exactly as they do in the workspace,
        while the analyzer still sees the *unsaved* text.

        Args:
            command: Resolved argv prefix.
            path: Buffer path (must live inside the workspace root).
            content: In-memory editor text.

        Returns:
            A :class:`ProviderResult`; capability or mirror problems produce a
            note instead of a failure so the caller keeps the other providers.
        """
        mirror = None
        try:
            absolute = os.path.abspath(path)
            if not absolute.startswith(os.path.abspath(self.root) + os.sep):
                self.last_note = _NO_BUFFER_SUPPORT
                return ProviderResult([], None, _NO_BUFFER_SUPPORT)
            mirror = _mirror_for(self.root)
            if mirror is None:
                self.last_note = _NO_BUFFER_SUPPORT
                return ProviderResult([], None, _NO_BUFFER_SUPPORT)
            relative = os.path.relpath(absolute, os.path.abspath(self.root))
            self._materialize_shadow_path(mirror, relative)
            shadow = os.path.join(mirror, relative)
            # The mirror entry is a symlink into the real workspace: replace it
            # with a real file first so the buffer is never written *through* it.
            if os.path.islink(shadow) or os.path.isfile(shadow):
                os.unlink(shadow)
            with open(shadow, "w", encoding="utf-8") as handle:
                handle.write(content)
            if not os.path.realpath(shadow).startswith(os.path.realpath(mirror)):
                self.last_note = "buffer analysis unavailable: unsafe mirror path"
                return ProviderResult([], None, self.last_note)
            argv = [
                *command,
                "--outputjson",
                "--level",
                "warning",
                relative,
            ]
            try:
                completed = subprocess.run(  # noqa: S603 - fixed, read-only argv
                    argv,
                    cwd=mirror,
                    capture_output=True,
                    text=True,
                    timeout=FILE_TIMEOUT_SECONDS,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                self.last_error = (
                    f"basedpyright timed out after {FILE_TIMEOUT_SECONDS}s"
                )
                return ProviderResult([], self.last_error)
            except (OSError, ValueError) as exc:
                self.last_error = f"basedpyright failed to run: {exc}"
                return ProviderResult([], self.last_error)
            if completed.returncode not in _SUCCESS_CODES:
                detail = [
                    line
                    for line in (completed.stderr or "").splitlines()
                    if line.strip()
                ]
                message = detail[-1] if detail else f"exit code {completed.returncode}"
                self.last_error = (
                    f"basedpyright failed (exit {completed.returncode}): {message}"
                )
                return ProviderResult([], self.last_error)
            try:
                payload = json.loads(completed.stdout or "{}")
            except (ValueError, TypeError) as exc:
                self.last_error = f"{_BAD_OUTPUT}: {exc}"
                return ProviderResult([], self.last_error)
            if not isinstance(payload, dict):
                self.last_error = f"{_BAD_OUTPUT}: expected a JSON object"
                return ProviderResult([], self.last_error)
            real_root = os.path.abspath(self.root)
            problems = []
            for problem in self.normalize(payload, root=mirror):
                reported = problem.file_path
                if reported.startswith(mirror + os.sep) or reported == mirror:
                    problem.file_path = os.path.join(
                        real_root, os.path.relpath(reported, mirror)
                    )
                if problem.file_path == absolute:
                    problems.append(problem)
            self.last_error = None
            self.last_note = None
            return ProviderResult(problems)
        except Exception as exc:  # noqa: BLE001 - provider isolation boundary
            self.last_note = f"buffer analysis unavailable: {exc}"
            logger.info("basedpyright buffer mirror unavailable: %s", exc)
            return ProviderResult([], None, self.last_note)
        finally:
            if mirror is not None:
                _forget_shadow(mirror, path)

    @staticmethod
    def _materialize_shadow_path(mirror: str, relative: str) -> None:
        """Create real directories for *relative* inside *mirror*.

        Mirror entries are symlinks into the real workspace, so a nested path
        must be rebuilt as real directories (with symlinked siblings) before
        the shadow file can be written safely.

        Args:
            mirror: Mirror root directory.
            relative: Workspace-relative path of the buffer.
        """
        parts = relative.split(os.sep)[:-1]
        current = mirror
        for part in parts:
            current = os.path.join(current, part)
            if os.path.islink(current):
                os.unlink(current)
            if not os.path.isdir(current):
                os.makedirs(current, exist_ok=True)
                real_parent = os.path.join(
                    os.path.realpath(os.path.dirname(current)), part
                )
                try:
                    for entry in os.listdir(real_parent):
                        if entry == "__pycache__":
                            continue
                        os.symlink(
                            os.path.join(real_parent, entry),
                            os.path.join(current, entry),
                        )
                except OSError:
                    continue

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run(
        self,
        argv: List[str],
        timeout: int,
        stdin_text: Optional[str] = None,
    ) -> ProviderResult:
        """Execute basedpyright read-only and normalize the result.

        Args:
            argv: Full argv for the invocation.
            timeout: Wall-clock budget in seconds.
            stdin_text: Buffer text for stdin mode, ``None`` otherwise.

        Returns:
            Normalized :class:`ProviderResult`.
        """
        try:
            completed = subprocess.run(  # noqa: S603 - fixed, read-only argv
                argv,
                cwd=self.root,
                input=stdin_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.last_error = f"basedpyright timed out after {timeout}s"
            logger.warning("basedpyright timed out (%s): %s", self.root, timeout)
            return ProviderResult([], self.last_error)
        except (OSError, ValueError) as exc:
            self.last_error = f"basedpyright failed to run: {exc}"
            logger.warning("basedpyright execution failed for %s: %s", self.root, exc)
            return ProviderResult([], self.last_error)

        if completed.returncode not in _SUCCESS_CODES:
            detail = [
                line for line in (completed.stderr or "").splitlines() if line.strip()
            ]
            message = detail[-1] if detail else f"exit code {completed.returncode}"
            self.last_error = (
                f"basedpyright failed (exit {completed.returncode}): {message}"
            )
            logger.warning("basedpyright failed for %s: %s", self.root, self.last_error)
            return ProviderResult([], self.last_error)

        try:
            payload = json.loads(completed.stdout or "{}")
        except (ValueError, TypeError) as exc:
            self.last_error = f"{_BAD_OUTPUT}: {exc}"
            logger.warning("basedpyright output not JSON for %s: %s", self.root, exc)
            return ProviderResult([], self.last_error)

        if not isinstance(payload, dict):
            self.last_error = f"{_BAD_OUTPUT}: expected a JSON object"
            return ProviderResult([], self.last_error)

        problems = self.normalize(payload)
        self.last_error = None
        return ProviderResult(problems)

    def normalize(self, payload: dict, root: Optional[str] = None) -> List[Problem]:
        """Convert basedpyright JSON diagnostics into :class:`Problem` items.

        Args:
            payload: Decoded ``--outputjson`` object.
            root: Directory relative paths are resolved against; defaults to
                the provider's workspace root.

        Returns:
            Normalized problems with absolute paths, preserved rule codes and
            exact start/end ranges.
        """
        base = os.path.abspath(root or self.root)
        entries = payload.get("generalDiagnostics")
        if not isinstance(entries, list):
            return []
        problems: List[Problem] = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            filename = str(item.get("file") or "")
            if not filename:
                continue
            span = self._range_of(item.get("range"))
            line, column, end_line, end_column = span
            message = str(item.get("message") or "basedpyright diagnostic")
            code = item.get("rule") or item.get("code")
            problems.append(
                Problem(
                    file_path=os.path.abspath(
                        filename
                        if os.path.isabs(filename)
                        else os.path.join(base, filename)
                    ),
                    severity=map_severity(item.get("severity")),
                    message=message,
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column,
                    source=BASEDPYRIGHT_SOURCE,
                    code=str(code) if code else None,
                )
            )
        return problems

    @staticmethod
    def _range_of(span: object) -> tuple:
        """Return a normalized ``(line, column, end_line, end_column)``.

        Args:
            span: The ``range`` object from a basedpyright diagnostic.

        Returns:
            1-based tuple; missing or malformed ranges collapse to
            ``(1, 1, 1, 2)``.
        """
        if not isinstance(span, dict):
            return 1, 1, 1, 2
        start = span.get("start") or {}
        end = span.get("end") or {}
        try:
            line = max(1, int(start.get("line", 0)) + 1)
        except (TypeError, ValueError):
            line = 1
        try:
            column = max(1, int(start.get("character", 0)) + 1)
        except (TypeError, ValueError):
            column = 1
        if "line" in end:
            try:
                end_line = max(1, int(end.get("line") or 0) + 1)
            except (TypeError, ValueError):
                end_line = line
        else:
            end_line = line
        if "character" in end:
            try:
                end_column = max(1, int(end.get("character") or 0) + 1)
            except (TypeError, ValueError):
                end_column = column + 1
        else:
            end_column = column + 1
        if (end_line, end_column) < (line, column):
            end_line, end_column = line, column + 1
        return line, column, end_line, end_column


# ----------------------------------------------------------------------
# Workspace mirrors for unsaved-buffer analysis
# ----------------------------------------------------------------------


def _link_workspace(mirror: str, directory: str) -> None:
    """Symlink every entry of *directory* into *mirror*.

    Args:
        mirror: Mirror root that receives the links.
        directory: Real directory whose entries are linked.
    """
    try:
        existing = set(os.listdir(mirror))
    except OSError:
        existing = set()
    try:
        entries = [name for name in os.listdir(directory) if name != "__pycache__"]
    except OSError:
        return
    for entry in entries:
        if entry in existing:
            continue
        try:
            os.symlink(os.path.join(directory, entry), os.path.join(mirror, entry))
        except OSError:
            continue


def _mirror_for(root: str) -> Optional[str]:
    """Return a reusable symlink mirror of *root*.

    The mirror keeps workspace imports, configuration and sibling modules
    resolvable while the edited file itself is written as a real shadow copy.
    It is cached per workspace so repeated buffer analyses do not re-link the
    whole tree.

    Args:
        root: Workspace directory to mirror.

    Returns:
        Mirror directory, or ``None`` when it cannot be created.
    """
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        return None
    cached = _MIRRORS.get(root)
    if cached and os.path.isdir(cached):
        _link_workspace(cached, root)
        return cached
    if cached:
        _MIRRORS.pop(root, None)
    try:
        mirror = tempfile.mkdtemp(prefix="dreamstudio-buffer-")
    except OSError as exc:
        logger.debug("Mirror creation failed: %s", exc)
        return None
    _link_workspace(mirror, root)
    _MIRRORS[root] = mirror
    return mirror


def _forget_shadow(mirror: str, path: str) -> None:
    """Delete the shadow copy written for *path*.

    Args:
        mirror: Mirror root.
        path: Real workspace path of the analyzed buffer.
    """
    try:
        root = next((real for real, temp in _MIRRORS.items() if temp == mirror), None)
        if root is None:
            return
        relative = os.path.relpath(os.path.abspath(path), root)
        shadow = os.path.join(mirror, relative)
        if os.path.isfile(shadow) and not os.path.islink(shadow):
            os.unlink(shadow)
    except (OSError, ValueError):
        pass


def _remove_mirror(mirror: str) -> None:
    """Delete a mirror workspace and its shadow copies."""
    try:
        for dirpath, dirnames, filenames in os.walk(mirror, topdown=False):
            for name in filenames:
                try:
                    os.unlink(os.path.join(dirpath, name))
                except OSError:
                    continue
            for name in dirnames:
                target = os.path.join(dirpath, name)
                try:
                    if os.path.islink(target):
                        os.unlink(target)
                    else:
                        os.rmdir(target)
                except OSError:
                    continue
        os.rmdir(mirror)
    except OSError:
        pass
