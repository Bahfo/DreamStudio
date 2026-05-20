"""Tests for JediWorker environment setup."""

import os
import sys
import tempfile


class FakeJediEnv:
    """Stand-in for jedi.Environment."""

    def __init__(self, path=None):
        self.path = path


class FakeJediWorker:
    """Simulates the environment management of JediWorker."""

    def __init__(self):
        self.current_venv_path = None
        self._jedi_env = FakeJediEnv()

    def set_virtual_environment(self, venv_path):
        self.current_venv_path = venv_path
        if venv_path and _is_valid_venv(venv_path):
            self._jedi_env = FakeJediEnv(path=venv_path)
        else:
            self._jedi_env = FakeJediEnv()

    def get_venv_path(self):
        return self._jedi_env.path


def _is_valid_venv(path: str) -> bool:
    """Check if a path looks like a valid Python venv."""
    if not path or not os.path.isdir(path):
        return False
    pyvenv = os.path.join(path, "pyvenv.cfg")
    if os.path.isfile(pyvenv):
        return True
    bin_dir = os.path.join(path, "bin")
    if os.path.isdir(bin_dir):
        return any(f.startswith("python") for f in os.listdir(bin_dir)
                   if os.path.isfile(os.path.join(bin_dir, f)))
    return False


def _discover_venv(project_root: str) -> str:
    """Find the venv Python executable path from a project root."""
    for candidate in ["venv", ".venv", ".env"]:
        venv_dir = os.path.join(project_root, candidate)
        if not os.path.isdir(venv_dir):
            continue
        if os.path.isfile(os.path.join(venv_dir, "pyvenv.cfg")):
            for py in ["python3", "python"]:
                py_path = os.path.join(venv_dir, "bin", py)
                if os.path.isfile(py_path):
                    return py_path
    return None


class TestWorkerEnvironment:
    def test_default_env_is_set(self):
        worker = FakeJediWorker()
        assert worker._jedi_env is not None
        assert worker.current_venv_path is None

    def test_set_venv_with_valid_path(self):
        with tempfile.TemporaryDirectory() as td:
            bin_dir = os.path.join(td, "bin")
            os.makedirs(bin_dir)
            py_path = os.path.join(bin_dir, "python3")
            with open(py_path, "w") as f:
                f.write("")
            os.chmod(py_path, 0o755)
            pyvenv = os.path.join(td, "pyvenv.cfg")
            with open(pyvenv, "w") as f:
                f.write("home = /usr\n")

            worker = FakeJediWorker()
            worker.set_virtual_environment(td)
            assert worker.current_venv_path == td
            assert worker._jedi_env.path == td

    def test_set_venv_with_none(self):
        worker = FakeJediWorker()
        worker.set_virtual_environment("/nonexistent")
        assert worker.current_venv_path == "/nonexistent"
        assert worker._jedi_env.path is None

    def test_set_venv_reset_to_none(self):
        worker = FakeJediWorker()
        worker.set_virtual_environment("/tmp")
        worker.set_virtual_environment(None)
        assert worker.current_venv_path is None

    def test_discover_venv_finds_venv_dir(self):
        with tempfile.TemporaryDirectory() as td:
            venv_dir = os.path.join(td, "venv")
            os.makedirs(os.path.join(venv_dir, "bin"))
            py_path = os.path.join(venv_dir, "bin", "python3")
            with open(py_path, "w") as f:
                f.write("")
            os.chmod(py_path, 0o755)
            with open(os.path.join(venv_dir, "pyvenv.cfg"), "w") as f:
                f.write("home = /usr\n")

            result = _discover_venv(td)
            assert result == py_path

    def test_discover_venv_no_venv(self):
        with tempfile.TemporaryDirectory() as td:
            result = _discover_venv(td)
            assert result is None

    def test_discover_venv_finds_venv_with_python_not_python3(self):
        with tempfile.TemporaryDirectory() as td:
            venv_dir = os.path.join(td, "venv")
            os.makedirs(os.path.join(venv_dir, "bin"))
            py_path = os.path.join(venv_dir, "bin", "python")
            with open(py_path, "w") as f:
                f.write("")
            os.chmod(py_path, 0o755)
            with open(os.path.join(venv_dir, "pyvenv.cfg"), "w") as f:
                f.write("home = /usr\n")

            result = _discover_venv(td)
            assert result == py_path

    def test_venv_without_pyvenv_cfg(self):
        with tempfile.TemporaryDirectory() as td:
            bin_dir = os.path.join(td, "bin")
            os.makedirs(bin_dir)
            with open(os.path.join(bin_dir, "python3"), "w") as f:
                f.write("")
            os.chmod(os.path.join(bin_dir, "python3"), 0o755)
            # No pyvenv.cfg — still valid if bin/python exists
            assert _is_valid_venv(td)

    def test_venv_without_bin_python(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "bin"))
            with open(os.path.join(td, "pyvenv.cfg"), "w") as f:
                f.write("home = /usr\n")
            # bin dir exists but no python binary
            assert _is_valid_venv(td)  # pyvenv.cfg is enough
