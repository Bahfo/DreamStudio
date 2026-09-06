"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Filesystem operation APIs for the DreamStudio Solution Explorer.
Each function is a self-contained operation that can be wired to toolbar
buttons or context-menu actions.
"""

from __future__ import annotations

from editor import *

from editor.widgets.QExitDialog import ConfirmDialog, RenameDialog
from editor.utils.notifications.notification_manager import get_notification_manager


class ExplorerAPI:
    """Stateless helper class that groups all Solution-Explorer file operations.

    Instantiate once per ``SolutionExplorer`` widget and call its methods
    from toolbar buttons or context-menu callbacks.
    """

    _clipboard: dict[str, str] = {}

    @staticmethod
    def _notify_vcs(reason: str = "explorer:api") -> None:
        """Request a VCS rescan after a mutating filesystem operation."""
        try:
            from editor.utils.git_control.status_service import get_status_service

            get_status_service().request_scan(reason)
        except Exception:
            pass

    @staticmethod
    def source_index(tree_view: QTreeView, proxy_index):
        """Resolve a proxy-model index back to its source-model index."""
        model = tree_view.model()
        if hasattr(model, "mapToSource"):
            return model.mapToSource(proxy_index)
        return proxy_index

    @staticmethod
    def selected_source_path(tree_view: QTreeView) -> str | None:
        """Return the absolute filesystem path of the currently selected
        item, or ``None`` if nothing is selected."""
        proxy_index = tree_view.currentIndex()
        if not proxy_index.isValid():
            return None

        source_model = tree_view.model().sourceModel() \
            if hasattr(tree_view.model(), "sourceModel") else tree_view.model()

        source_index = ExplorerAPI.source_index(tree_view, proxy_index)
        return source_model.filePath(source_index)

    @staticmethod
    def parent_dir(path: str) -> str:
        """Return the parent directory of *path*."""
        return os.path.dirname(path)

    @staticmethod
    def item_name(path: str) -> str:
        """Return the file / folder name (basename) of *path*."""
        return os.path.basename(path)

    @staticmethod
    def new_file(parent: QWidget, directory: str) -> str | None:
        """Create a new empty file inside *directory*.

        Prompts the user for a file name via ``QInputDialog``.  Returns the
        absolute path of the created file, or ``None`` on cancellation.
        """
        name, ok = QInputDialog.getText(
            parent, "New File", "File name:", QLineEdit.EchoMode.Normal,
        )
        if not ok or not name.strip():
            return None

        name = name.strip()
        file_path = os.path.join(directory, name)

        if os.path.exists(file_path):
            ConfirmDialog(
                parent, title="Cannot Create",
                message=f"'{name}' already exists.",
                confirm_text="OK", cancel_text="",
            ).exec()
            return None

        try:
            with open(file_path, "w", encoding="utf-8") as fh:
                fh.write("")
        except OSError as exc:
            print(f"[explorer] new_file error: {exc}")
            get_notification_manager().add_error(
                "File Creation Failed",
                f"Could not create file: {exc}",
                "Explorer",
            )
            return None

        ExplorerAPI._notify_vcs("explorer:api:new_file")
        return file_path

    @staticmethod
    def new_folder(parent: QWidget, directory: str) -> str | None:
        """Create a new folder inside *directory*.

        Prompts the user for a folder name.  Returns the absolute path of the
        created folder, or ``None`` on cancellation.
        """
        name, ok = QInputDialog.getText(
            parent, "New Folder", "Folder name:", QLineEdit.EchoMode.Normal,
        )
        if not ok or not name.strip():
            return None

        name = name.strip()
        folder_path = os.path.join(directory, name)

        if os.path.exists(folder_path):
            ConfirmDialog(
                parent, title="Cannot Create",
                message=f"'{name}' already exists.",
                confirm_text="OK", cancel_text="",
            ).exec()
            return None

        try:
            os.makedirs(folder_path, exist_ok=True)
        except OSError as exc:
            print(f"[explorer] new_folder error: {exc}")
            get_notification_manager().add_error(
                "Folder Creation Failed",
                f"Could not create folder: {exc}",
                "Explorer",
            )
            return None

        ExplorerAPI._notify_vcs("explorer:api:new_folder")
        return folder_path

    @staticmethod
    def delete_item(parent: QWidget, path: str) -> bool:
        """Permanently delete a file or folder after user confirmation.

        Shows a destructive confirmation dialog before proceeding.
        Returns ``True`` if the item was deleted, ``False`` otherwise.
        """
        if not os.path.exists(path):
            return False

        kind = "folder" if os.path.isdir(path) else "file"
        name = ExplorerAPI.item_name(path)

        dialog = ConfirmDialog(
            parent,
            title=f"Delete {kind.title()}",
            message=f"Are you sure you want to permanently delete '{name}'?",
            confirm_text="DELETE", cancel_text="CANCEL", destructive=True,
        )
        if dialog.exec() != ConfirmDialog.DialogCode.Accepted:
            return False

        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError as exc:
            print(f"[explorer] delete error: {exc}")
            get_notification_manager().add_error(
                "Delete Failed",
                f"Could not delete '{name}': {exc}",
                "Explorer",
            )
            return False

        ExplorerAPI._notify_vcs("explorer:api:delete")
        return True

    @staticmethod
    def rename_item(parent: QWidget, path: str) -> str | None:
        """Rename a file or folder via a confirmation dialog.

        Returns the new absolute path on success, or ``None`` if the user
        cancelled or the rename failed.
        """
        if not os.path.exists(path):
            return None

        current_name = ExplorerAPI.item_name(path)
        dialog = RenameDialog(
            parent, title="Rename", message="Enter new name:",
            current_text=current_name,
        )
        new_name = dialog.get_name()
        if new_name is None or new_name == current_name:
            return None

        new_path = os.path.join(ExplorerAPI.parent_dir(path), new_name)

        if os.path.exists(new_path):
            ConfirmDialog(
                parent, title="Cannot Rename",
                message=f"'{new_name}' already exists.",
                confirm_text="OK", cancel_text="",
            ).exec()
            return None

        try:
            os.rename(path, new_path)
        except OSError as exc:
            print(f"[explorer] rename error: {exc}")
            get_notification_manager().add_error(
                "Rename Failed",
                f"Could not rename '{current_name}': {exc}",
                "Explorer",
            )
            return None

        ExplorerAPI._notify_vcs("explorer:api:rename")
        return new_path

    @classmethod
    def copy_item(cls, path: str) -> None:
        """Copy *path* to the internal clipboard (does not modify filesystem).

        A subsequent call to ``paste_item`` will duplicate the item.
        """
        if not os.path.exists(path):
            return
        cls._clipboard.clear()
        cls._clipboard["action"] = "copy"
        cls._clipboard["path"] = path

    @classmethod
    def cut_item(cls, path: str) -> None:
        """Mark *path* for moving on the next ``paste_item`` call."""
        if not os.path.exists(path):
            return
        cls._clipboard.clear()
        cls._clipboard["action"] = "cut"
        cls._clipboard["path"] = path

    @classmethod
    def paste_item(cls, parent: QWidget, destination_dir: str) -> str | None:
        """Paste the clipboard contents into *destination_dir*.

        - **copy**: duplicates the file / folder into the destination.
        - **cut**: moves the file / folder into the destination.

        Returns the path of the pasted item, or ``None`` on failure.
        """
        if not cls._clipboard:
            return None

        action = cls._clipboard.get("action", "")
        src_path = cls._clipboard.get("path", "")

        if not src_path or not os.path.exists(src_path):
            cls._clipboard.clear()
            return None

        if not os.path.isdir(destination_dir):
            return None

        name = ExplorerAPI.item_name(src_path)
        dest_path = os.path.join(destination_dir, name)

        if os.path.exists(dest_path):
            base, ext = os.path.splitext(name)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(destination_dir, f"{base} ({counter}){ext}")
                counter += 1

        try:
            if action == "cut":
                shutil.move(src_path, dest_path)
                cls._clipboard.clear()
            elif action == "copy":
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dest_path)
                else:
                    shutil.copy2(src_path, dest_path)
        except OSError as exc:
            print(f"[explorer] paste error: {exc}")
            get_notification_manager().add_error(
                "Paste Failed",
                f"Could not paste item: {exc}",
                "Explorer",
            )
            return None

        cls._notify_vcs("explorer:api:paste")
        return dest_path

    @staticmethod
    def copy_path(path: str) -> None:
        """Copy the absolute filesystem path of *path* to the system clipboard."""
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(path)

    @staticmethod
    def open_in_system_explorer(path: str) -> None:
        """Open *path* in the operating system's default file manager."""
        target = path if os.path.isdir(path) else ExplorerAPI.parent_dir(path)
        try:
            if sys.platform == "win32":
                try:
                    os.startfile(target)
                except OSError as exc:
                    raise OSError(str(exc)) from exc
            elif sys.platform == "darwin":
                subprocess.Popen(
                    ["open", target],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    close_fds=True,
                    start_new_session=True,
                )
            else:
                subprocess.Popen(
                    ["xdg-open", target],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    close_fds=True,
                    start_new_session=True,
                )
        except OSError as exc:
            print(f"[explorer] open_in_system_explorer error: {exc}")
            get_notification_manager().add_error(
                "Open Failed",
                f"Could not open in file manager: {exc}",
                "Explorer",
            )

    @staticmethod
    def refresh_tree(tree_view: QTreeView) -> None:
        """Force the underlying ``QFileSystemModel`` to rescan the filesystem."""
        model = tree_view.model()
        source = model.sourceModel() if hasattr(model, "sourceModel") else model
        if hasattr(source, "setRootPath"):
            root = source.rootPath()
            source.setRootPath("")
            source.setRootPath(root)

    @staticmethod
    def collapse_all(tree_view: QTreeView) -> None:
        """Collapse every expanded node in the tree view."""
        tree_view.collapseAll()

    @staticmethod
    def expand_all(tree_view: QTreeView) -> None:
        """Expand every collapsed node in the tree view."""
        tree_view.expandAll()

    @staticmethod
    def safe_search(
        proxy_model: QSortFilterProxyModel,
        text: str,
        *,
        root_path: str = "",
    ) -> None:
        """Filter the tree view using *text* as a fixed-string match.

        Validates the query before forwarding it to the proxy model so that
        special characters and path-traversal sequences cannot cause
        unexpected behaviour.
        """
        query = text.strip()

        if ".." in query:
            query = ""
        elif root_path and os.path.isabs(query):
            if not query.startswith(root_path):
                query = ""

        # Proxy uses custom _search_text filtering, not filterFixedString
        if hasattr(proxy_model, "set_search_text"):
            proxy_model.set_search_text(query)
        else:
            proxy_model.setFilterFixedString(query)
