"""Path access check for restricting file operations to an allowed root directory."""
from pathlib import Path


def normalize_root(root: str) -> str:
    """Return a resolved POSIX-style directory string without a trailing slash."""
    return Path(root).resolve().as_posix().rstrip("/")


def is_inside_workspace(candidate: str, workspace_root: str) -> bool:
    """Return True if and only if candidate resolves to workspace_root or a descendant inside it.

    Sibling directories that merely share a string prefix (for example '/srv/app2' when
    workspace_root is '/srv/app') must return False.
    """
    root_path = Path(workspace_root).resolve()
    cand_path = Path(candidate).resolve()
    try:
        cand_path.relative_to(root_path)
        return True
    except ValueError:
        return False


def filter_allowed_paths(candidates: list[str], workspace_root: str) -> list[str]:
    """Keep only paths that lie inside workspace_root."""
    return [c for c in candidates if is_inside_workspace(c, workspace_root)]
