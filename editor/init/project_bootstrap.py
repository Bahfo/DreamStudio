import os
import sys
import yaml
import shutil
import logging
import platform
import subprocess
import threading
import traceback

from typing import Any, Optional

from PyQt6.QtCore import pyqtSignal, QObject

logger = logging.getLogger(__name__)


class ProjectBootstrapWorker(QObject):
    step_changed = pyqtSignal(str, str)
    step_progress = pyqtSignal(str)
    step_failed = pyqtSignal(str, str)
    finished = pyqtSignal(bool)

    def __init__(
        self,
        manifest_path: str,
        target_path: str,
        requested_project_type: str,
        python_version: Optional[str] = None,
        interpreter_location: Optional[str] = None,
    ):
        super().__init__()
        self._manifest_path = manifest_path
        self._target_path = target_path
        self._requested_project_type = requested_project_type
        self._python_version = python_version
        self._interpreter_location = interpreter_location

        self._manifest: Optional[dict] = None
        self._created_dirs: list[str] = []
        self._created_files: list[str] = []
        self._is_windows = platform.system() == "Windows"

    def run(self):
        success = False
        try:
            self._emit_step("load_manifest", "Loading project manifest")
            self._load_manifest()

            self._emit_step("check_python", "Checking Python environment")
            self._check_python()

            self._emit_step("check_project_type", "Verifying project type")
            self._check_project_type()

            self._emit_step("initialization", "Creating project structure")
            self._initialize()

            self._emit_step("post_lifecycle", "Running post-lifecycle steps")
            self._run_post_lifecycle()

            success = True
        except Exception:
            error = traceback.format_exc()
            logger.error("Bootstrap failed: %s", error)
            current_step = getattr(self, "_current_step", "unknown")
            self.step_failed.emit(current_step, error)
            self._rollback()
        finally:
            self.finished.emit(success)

    def _emit_step(self, name: str, description: str) -> None:
        self._current_step = name
        self.step_changed.emit(name, description)

    def _load_manifest(self) -> None:
        if not os.path.isfile(self._manifest_path):
            raise FileNotFoundError(
                f"Manifest file not found: {self._manifest_path}"
            )
        with open(self._manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError("Manifest is not a valid YAML dictionary")
        self._manifest = data

    def _check_python(self) -> None:
        lang = self._manifest.get("language", "")
        if lang != "python":
            raise ValueError(
                f"Unsupported language: '{lang}'. Only 'python' is supported."
            )

        manifest_version = self._manifest.get("version", "")
        if manifest_version and manifest_version != "studio_default_version":
            actual = sys.version_info
            actual_str = f"{actual.major}.{actual.minor}.{actual.micro}"
            if self._python_version and self._python_version != manifest_version:
                self.step_progress.emit(
                    f"Requested Python {self._python_version}, "
                    f"manifest specifies {manifest_version}, "
                    f"actual runtime is {actual_str}"
                )
            else:
                self.step_progress.emit(f"Python runtime: {actual_str}")
        else:
            self.step_progress.emit(
                f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            )

        manifest_interp = self._manifest.get("interpreter_location", "")
        if manifest_interp and manifest_interp != "studio_interpreter_defined_location":
            check_path = self._interpreter_location or manifest_interp
            if not os.path.isfile(check_path):
                raise FileNotFoundError(
                    f"Python interpreter not found at: {check_path}"
                )
            self.step_progress.emit(f"Interpreter verified: {check_path}")
        else:
            self.step_progress.emit(f"Using interpreter: {sys.executable}")

    def _check_project_type(self) -> None:
        manifest_type = self._manifest.get("project_type")
        if manifest_type != self._requested_project_type:
            raise ValueError(
                f"Project type mismatch: manifest specifies '{manifest_type}', "
                f"but '{self._requested_project_type}' was requested"
            )
        self.step_progress.emit(f"Project type verified: {manifest_type}")

    def _initialize(self) -> None:
        init_data = self._manifest.get("initialization", {})
        if not isinstance(init_data, dict):
            raise ValueError("Manifest 'initialization' section is invalid")

        project_path = self._target_path
        self._ensure_dir(project_path)

        for rel_dir in init_data.get("directories", []):
            dir_path = os.path.join(project_path, rel_dir)
            self._ensure_dir(dir_path)
            self.step_progress.emit(f"Created directory: {rel_dir}")

        created_as_template: set[str] = set()
        for tmpl in init_data.get("templates", []):
            if not isinstance(tmpl, dict):
                continue
            target = tmpl.get("target", "")
            contents = tmpl.get("contents", "")
            if not target:
                continue
            file_path = os.path.join(project_path, target)
            parent = os.path.dirname(file_path)
            if parent:
                self._ensure_dir(parent)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(contents)
            self._created_files.append(file_path)
            created_as_template.add(target)
            self.step_progress.emit(f"Created file: {target}")

        for rel_file in init_data.get("files", []):
            if rel_file in created_as_template:
                continue
            file_path = os.path.join(project_path, rel_file)
            parent = os.path.dirname(file_path)
            if parent:
                self._ensure_dir(parent)
            if not os.path.isfile(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("")
                self._created_files.append(file_path)
                self.step_progress.emit(f"Created file: {rel_file}")

    def _ensure_dir(self, path: str) -> None:
        if os.path.isdir(path):
            return
        ancestors: list[str] = []
        current = path
        while current and not os.path.isdir(current):
            ancestors.append(current)
            current = os.path.dirname(current)
        for ancestor in reversed(ancestors):
            os.makedirs(ancestor, exist_ok=True)
            self._created_dirs.append(ancestor)

    def _run_post_lifecycle(self) -> None:
        steps = self._manifest.get("post_lifecycle", [])
        if not isinstance(steps, list):
            return

        project_path = self._target_path

        for step_data in steps:
            if not isinstance(step_data, dict):
                continue
            step_name = step_data.get("step", "unknown")
            desc = step_data.get("desc", "")
            self.step_changed.emit(f"post_{step_name}", desc)

            cmd = step_data.get("wind") if self._is_windows else step_data.get("unix")
            if not cmd:
                raise RuntimeError(
                    f"No command defined for post_lifecycle step "
                    f"'{step_name}' on {platform.system()}"
                )

            if step_name == "create_venv":
                venv_path = os.path.join(project_path, "venv")
                self._created_dirs.append(venv_path)

            self.step_progress.emit(f"Running: {cmd}")
            result = subprocess.run(
                cmd,
                cwd=project_path,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                stdout = result.stdout.strip()
                detail = stderr or stdout or "no output"
                raise RuntimeError(
                    f"Step '{step_name}' failed (exit {result.returncode}): {detail}"
                )

            output = result.stdout.strip()
            if output:
                self.step_progress.emit(output)

    def _rollback(self) -> None:
        self.step_progress.emit("Rolling back created resources...")

        for file_path in reversed(self._created_files):
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                    self.step_progress.emit(f"Removed file: {file_path}")
            except OSError as e:
                logger.warning("Rollback: could not remove file %s: %s", file_path, e)

        for dir_path in reversed(self._created_dirs):
            try:
                if os.path.isdir(dir_path):
                    shutil.rmtree(dir_path, ignore_errors=True)
                    self.step_progress.emit(f"Removed directory: {dir_path}")
            except OSError as e:
                logger.warning(
                    "Rollback: could not remove directory %s: %s", dir_path, e
                )

        self._created_files.clear()
        self._created_dirs.clear()
        self.step_progress.emit("Rollback complete")


class ProjectBootstrap:
    def __init__(
        self,
        manifest_path: str,
        target_path: str,
        requested_project_type: str,
        python_version: Optional[str] = None,
        interpreter_location: Optional[str] = None,
    ):
        self._worker = ProjectBootstrapWorker(
            manifest_path=manifest_path,
            target_path=target_path,
            requested_project_type=requested_project_type,
            python_version=python_version,
            interpreter_location=interpreter_location,
        )
        self._thread = threading.Thread(
            target=self._worker.run,
            name="bootstrap_thread",
            daemon=True,
        )

    @property
    def worker(self) -> ProjectBootstrapWorker:
        return self._worker

    @property
    def step_changed(self):
        return self._worker.step_changed

    @property
    def step_progress(self):
        return self._worker.step_progress

    @property
    def step_failed(self):
        return self._worker.step_failed

    @property
    def finished(self):
        return self._worker.finished

    def start(self) -> None:
        self._thread.start()

    def wait(self, timeout: int = 600000) -> bool:
        self._thread.join(timeout)
        return not self._thread.is_alive()
