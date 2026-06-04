import os
from git import Repo


def return_repository(path: str | None = None) -> Repo | Exception:
    if path is not None:
        try:
            repo = Repo(path)
            return repo
        except Exception as e:
            return e
    else:
        try:
            _dir = os.getcwd()
            repo = Repo(_dir)
            return repo
        except Exception as e:
            return e


def check_last_commits(git_repo: Repo, count: int):
    prev_commits = list(git_repo.iter_commits(all=True, max_count=count))
    tree = prev_commits[0].tree
    return prev_commits, tree


def get_changed_files(repo: Repo) -> list[dict]:
    changed = {}

    # Unstaged changes (working tree vs index)
    try:
        diff = repo.index.diff(None)
        for d in diff:
            path = d.a_path
            ctype = d.change_type
            if ctype == "D":
                changed[path] = {
                    "path": path,
                    "status": "D",
                    "additions": 0,
                    "deletions": 0,
                }
            else:
                lines_added = 0
                lines_deleted = 0
                try:
                    diff_detail = repo.git.diff(d.a_path, numstat=True)
                    if diff_detail:
                        parts = diff_detail.split("\t")
                        if len(parts) >= 2:
                            try:
                                lines_added = int(parts[0])
                                lines_deleted = int(parts[1])
                            except ValueError:
                                pass
                except Exception:
                    pass
                changed[path] = {
                    "path": path,
                    "status": "M",
                    "additions": lines_added,
                    "deletions": lines_deleted,
                }
    except Exception:
        pass

    # Untracked files
    try:
        for ut in repo.untracked_files:
            changed[ut] = {
                "path": ut,
                "status": "U",
                "additions": 0,
                "deletions": 0,
            }
    except Exception:
        pass

    # Staged changes (HEAD vs index)
    try:
        staged = repo.index.diff("HEAD")
        for d in staged:
            path = d.a_path
            ctype = d.change_type
            lines_added = 0
            lines_deleted = 0
            try:
                diff_detail = repo.git.diff("--staged", d.a_path, numstat=True)
                if diff_detail:
                    parts = diff_detail.split("\t")
                    if len(parts) >= 2:
                        try:
                            lines_added = int(parts[0])
                            lines_deleted = int(parts[1])
                        except ValueError:
                            pass
            except Exception:
                pass
            if path not in changed:
                status = "A" if ctype == "A" else "M"
                changed[path] = {
                    "path": path,
                    "status": status,
                    "additions": lines_added,
                    "deletions": lines_deleted,
                }
            else:
                changed[path]["additions"] += lines_added
                changed[path]["deletions"] += lines_deleted
    except Exception:
        pass

    return list(changed.values())


def stage_file(repo: Repo, file_path: str) -> bool:
    try:
        repo.index.add([file_path])
        return True
    except Exception:
        return False


def unstage_file(repo: Repo, file_path: str) -> bool:
    try:
        repo.index.remove([file_path], working_tree=True)
        return True
    except Exception:
        try:
            repo.git.reset("HEAD", file_path)
            return True
        except Exception:
            return False


def commit(repo: Repo, message: str) -> tuple[bool, str]:
    try:
        repo.index.commit(message)
        return True, "Commit successful"
    except Exception as e:
        return False, str(e)


def commit_staged(
    repo: Repo, message: str, files: list[str] | None = None
) -> tuple[bool, str]:
    try:
        if files:
            to_add = []
            to_remove = []
            for f in files:
                if os.path.exists(f):
                    to_add.append(f)
                else:
                    to_remove.append(f)
            if to_add:
                repo.index.add(to_add)
            for f in to_remove:
                try:
                    repo.index.remove([f])
                except Exception:
                    try:
                        repo.git.rm(f)
                    except Exception:
                        pass
        repo.index.commit(message)
        return True, "Commit successful"
    except Exception as e:
        return False, str(e)


def get_blame_info(repo: Repo, file_path: str, line_number: int) -> dict | None:
    try:
        blame_result = repo.blame("HEAD", file_path)
        current_line = 0
        for commit, lines in blame_result:
            current_line += len(lines)
            if current_line > line_number:
                return {
                    "author": commit.author.name,
                    "email": commit.author.email,
                    "date": commit.authored_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "summary": commit.message.strip().split("\n")[0],
                    "hexsha": commit.hexsha[:7],
                }
    except Exception:
        pass
    return None


def get_file_diff(repo: Repo, file_path: str) -> dict:
    try:
        old_content = repo.git.show(f"HEAD:{file_path}")
    except Exception:
        old_content = ""

    new_content = ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            new_content = f.read()
    except Exception:
        pass

    return {
        "old": old_content,
        "new": new_content,
        "path": file_path,
    }


def get_commit_history(repo: Repo, count: int = 50) -> dict:
    try:
        commits = list(repo.iter_commits(all=True, max_count=count))
        head_sha = repo.head.commit.hexsha
        branch = repo.active_branch.name
        return {
            "commits": commits,
            "head_sha": head_sha,
            "branch": branch,
        }
    except Exception as e:
        return {"commits": [], "head_sha": None, "branch": "unknown", "error": str(e)}


if __name__ == "__main__":
    repo = return_repository(None)
    commits, tree = check_last_commits(repo, 5)
    print(commits, tree)
