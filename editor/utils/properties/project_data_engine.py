from editor import *
import yaml


class ProjectDataEngine:
    """
    Handles low-level file extraction and updates for DreamStudio
    workspace metadata.
    """

    def __init__(self, project_dir: Optional[str] = None):
        self.project_dir: Optional[Path] = Path(project_dir) if project_dir else None
        self.ds_dir: Optional[Path] = (
            self.project_dir / ".ds" if self.project_dir else None
        )

    def set_project_dir(self, project_dir: str) -> None:
        """
        Updates the engine target workspace directory path context.
        """
        self.project_dir = Path(project_dir)
        self.ds_dir = self.project_dir / ".ds"

    def is_valid_project(self) -> bool:
        """
        Verifies if the loaded workspace directory contains the required .ds
        footprint.
        """
        return bool(self.ds_dir and self.ds_dir.is_dir())

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

        yaml_path = self.ds_dir / "project_info.yaml"
        if yaml_path.exists():
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f) or {}
                    data["name"] = content.get("name", "")
                    data["authors"] = content.get("authors", "")
            except Exception:
                pass

        txt_path = self.ds_dir / "metadata.txt"
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

        json_path = self.ds_dir / "properties.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    content = json.load(f) or {}
                    data["copyright"] = content.get("copyright", "")
                    data["details"] = content.get("details", "")
            except Exception:
                pass

        data["code_of_conduct"] = self._read_root_doc(
            ["CODE-OF-CONDUCT", "CODE_OF_CONDUCT.md"]
        )
        data["license"] = self._read_root_doc(["LICENSE", "LICENSE.txt", "LICENSE.md"])
        data["contributing"] = self._read_root_doc(["CONTRIBUTING", "CONTRIBUTING.md"])

        return data

    def commit_solution_properties(self, updates: Dict[str, Any]) -> bool:
        """
        Writes revised property dictionaries back to their corresponding file
        descriptors.
        """
        if not self.is_valid_project():
            return False

        try:
            yaml_path = self.ds_dir / "project_info.yaml"
            yaml_data = {
                "name": updates.get("name", ""),
                "authors": updates.get("authors", ""),
            }
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(yaml_data, f, default_flow_style=False)

            json_path = self.ds_dir / "properties.json"
            json_data = {
                "copyright": updates.get("copyright", ""),
                "details": updates.get("details", ""),
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=4)

            self._write_root_doc(
                ["CODE-OF-CONDUCT", "CODE_OF_CONDUCT.md"],
                updates.get("code_of_conduct", ""),
            )
            self._write_root_doc(
                ["LICENSE", "LICENSE.txt", "LICENSE.md"], updates.get("license", "")
            )
            self._write_root_doc(
                ["CONTRIBUTING", "CONTRIBUTING.md"], updates.get("contributing", "")
            )

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
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return

        default_path = self.project_dir / filenames[0]
        with open(default_path, "w", encoding="utf-8") as f:
            f.write(content)
