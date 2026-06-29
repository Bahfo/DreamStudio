"""
GitAPI - Wraps backend git_control functions and SourceControl UI.

Provides access to git repository operations.
"""

from typing import Optional


class GitAPI:
    """API for git operations."""

    def __init__(self, main_window):
        self._main = main_window

    def _get_repo(self, path: str = None):
        from backend.git_control import return_repository
        if path is None:
            path = self._main.currentDirectory
        return return_repository(path)

    def getRepository(self, path: str = None):
        """Get a git Repo object for the given path."""
        return self._get_repo(path)

    def getChangedFiles(self, path: str = None) -> list:
        """Get a list of changed files in the repository."""
        repo = self._get_repo(path)
        if isinstance(repo, Exception):
            return []
        from backend.git_control import get_changed_files
        return get_changed_files(repo)

    def stageFile(self, file_path: str, path: str = None) -> bool:
        """Stage a file for commit."""
        repo = self._get_repo(path)
        if isinstance(repo, Exception):
            return False
        from backend.git_control import stage_file
        return stage_file(repo, file_path)

    def unstageFile(self, file_path: str, path: str = None) -> bool:
        """Unstage a file."""
        repo = self._get_repo(path)
        if isinstance(repo, Exception):
            return False
        from backend.git_control import unstage_file
        return unstage_file(repo, file_path)

    def commit(self, message: str, path: str = None) -> tuple:
        """Commit staged changes with a message. Returns (success, message)."""
        repo = self._get_repo(path)
        if isinstance(repo, Exception):
            return False, str(repo)
        from backend.git_control import commit
        return commit(repo, message)

    def commitStaged(self, message: str, files: list = None, path: str = None) -> tuple:
        """Commit specific staged files. Returns (success, message)."""
        repo = self._get_repo(path)
        if isinstance(repo, Exception):
            return False, str(repo)
        from backend.git_control import commit_staged
        return commit_staged(repo, message, files)

    def getFileDiff(self, file_path: str, path: str = None) -> dict:
        """Get the diff for a specific file."""
        repo = self._get_repo(path)
        if isinstance(repo, Exception):
            return {"old": "", "new": "", "path": file_path}
        from backend.git_control import get_file_diff
        return get_file_diff(repo, file_path)

    def getCommitHistory(self, count: int = 50, path: str = None) -> dict:
        """Get commit history. Returns dict with commits, head_sha, branch."""
        repo = self._get_repo(path)
        if isinstance(repo, Exception):
            return {"commits": [], "head_sha": None, "branch": "unknown"}
        from backend.git_control import get_commit_history
        return get_commit_history(repo, count)

    def getBlameInfo(self, file_path: str, line_number: int, path: str = None) -> Optional[dict]:
        """Get blame information for a specific line."""
        repo = self._get_repo(path)
        if isinstance(repo, Exception):
            return None
        from backend.git_control import get_blame_info
        return get_blame_info(repo, file_path, line_number)

    def getLastCommits(self, count: int = 5, path: str = None) -> tuple:
        """Get the last N commits and the tree. Returns (commits, tree)."""
        repo = self._get_repo(path)
        if isinstance(repo, Exception):
            return [], None
        from backend.git_control import check_last_commits
        return check_last_commits(repo, count)

    def refreshSourceControl(self) -> None:
        """Refresh the source control panel."""
        sc = getattr(self._main, "source_control", None)
        if sc is not None and hasattr(sc, "_refresh"):
            sc._refresh()

    def doCommit(self) -> None:
        """Trigger the commit action from the source control panel."""
        sc = getattr(self._main, "source_control", None)
        if sc is not None and hasattr(sc, "_do_commit"):
            sc._do_commit()
