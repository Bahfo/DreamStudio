from editor import *
import yaml
from editor.utils.solution.paths import (
    DS_DIR,
    METADATA_FILE,
    PROJECT_INFO_FILE,
    PROPERTIES_FILE,
    SOLUTION_FILE,
)


class ProjectDataEngine:
    """
    Handles low-level file extraction and updates for DreamStudio
    workspace metadata.
    """

    def __init__(self, project_dir: Optional[str] = None):
        self.project_dir: Optional[Path] = Path(project_dir) if project_dir else None
        self.ds_dir: Optional[Path] = (
            self.project_dir / DS_DIR if self.project_dir else None
        )

    def set_project_dir(self, project_dir: str) -> None:
        """
        Updates the engine target workspace directory path context.
        """
        self.project_dir = Path(project_dir)
        self.ds_dir = self.project_dir / DS_DIR

    def is_valid_project(self) -> bool:
        """
        Verifies if the loaded workspace directory contains the required .ds
        footprint.
        """
        if not (self.ds_dir and self.ds_dir.is_dir()):
            return False
        marker = self.ds_dir / SOLUTION_FILE
        return marker.is_file()

    def extract_solution_properties(self) -> Dict[str, Any]:
        """
        Reads all configuration states from the .ds environment directory
        and root files.
        """
        data = {
            "name": "",
            "authors": "",
            "copyright": "",
            "details": "",
            "created_at": "",
            "identifier": "",
            "code_of_conduct": "",
            "license": "",
            "contributing": "",
        }

        if not self.is_valid_project():
            return data

        solution_path = self.ds_dir / SOLUTION_FILE
        solution: dict = {}
        if solution_path.exists():
            try:
                with open(solution_path, "r", encoding="utf-8") as f:
                    solution = yaml.safe_load(f) or {}
                    if not isinstance(solution, dict):
                        try:
                            import json as _json

                            f.seek(0)
                            solution = _json.load(f) or {}
                        except Exception:
                            solution = {}
            except Exception:
                solution = {}

        yaml_path = self.ds_dir / PROJECT_INFO_FILE
        if yaml_path.exists():
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f) or {}
                    data["name"] = content.get("name", "")
                    data["authors"] = content.get("authors", "")
            except Exception:
                pass
        if not data["name"]:
            data["name"] = str(solution.get("name", "") or "")
        if not data["created_at"]:
            data["created_at"] = str(solution.get("created_at", "") or "")

        txt_path = self.ds_dir / METADATA_FILE
        if txt_path.exists():
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                    if len(lines) >= 1:
                        data["created_at"] = lines[0]
                    if len(lines) >= 2:
                        data["identifier"] = lines[1]
            except Exception:
                pass

        json_path = self.ds_dir / PROPERTIES_FILE
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    content = json.load(f) or {}
                    data["copyright"] = content.get("copyright", "")
                    data["details"] = content.get("details", "")
            except Exception:
                pass

        data["code_of_conduct"] = self._root_doc_status(
            ["CODE_OF_CONDUCT.md", "CODE-OF-CONDUCT"]
        )
        data["license"] = self._root_doc_status(
            ["LICENSE.md", "LICENSE", "LICENSE.txt"]
        )
        data["contributing"] = self._root_doc_status(
            ["CONTRIBUTING.md", "CONTRIBUTING"]
        )

        return data

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write atomically via temp file + rename."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
            try:
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp, path)

    def commit_solution_properties(self, updates: Dict[str, Any]) -> bool:
        """
        Writes revised property dictionaries back to their corresponding file
        descriptors.
        """
        if not self.is_valid_project():
            return False

        try:
            yaml_path = self.ds_dir / PROJECT_INFO_FILE
            yaml_data = {
                "name": updates.get("name", ""),
                "authors": updates.get("authors", ""),
            }
            yaml_str = yaml.safe_dump(yaml_data, default_flow_style=False)
            self._atomic_write(yaml_path, yaml_str)

            json_path = self.ds_dir / PROPERTIES_FILE
            json_data = {
                "copyright": updates.get("copyright", ""),
                "details": updates.get("details", ""),
            }
            json_str = json.dumps(json_data, indent=4)
            self._atomic_write(json_path, json_str)

            return True
        except Exception:
            return False

    def _read_root_doc(self, filenames: list[str]) -> str:
        """Helper to scan root workspace for the first matching doc variation."""
        if not self.project_dir:
            return ""
        for name in filenames:
            target_path = self.project_dir / name
            if target_path.exists():
                try:
                    with open(target_path, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass
        return ""

    def _root_doc_status(self, filenames: list[str]) -> str:
        """Report whether an accompanying root doc exists, without its content."""
        if not self.project_dir:
            return "Not found"
        for name in filenames:
            try:
                if (self.project_dir / name).exists():
                    return f"Found ({name})"
            except Exception:
                pass
        return "Not found"

    def _write_root_doc(self, filenames: list[str], content: str) -> None:
        """
        Helper to write documents to an existing match or create a preferred
        default filename.
        """
        if not self.project_dir or content is None:
            return

        for name in filenames:
            target_path = self.project_dir / name
            if target_path.exists():
                try:
                    self._atomic_write(target_path, content)
                except Exception:
                    pass
                return

        default_path = self.project_dir / filenames[0]
        try:
            self._atomic_write(default_path, content)
        except Exception:
            pass
