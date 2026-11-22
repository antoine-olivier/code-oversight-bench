"""Case-insensitive path protection matcher for Windows file paths."""
import posixpath


def canonicalize_windows_path(raw_path: str) -> str:
    """Normalize slashes and dot segments while keeping drive letters."""
    replaced = raw_path.replace("\\", "/")
    return posixpath.normpath(replaced)


def is_protected_target(raw_path: str, protected_roots: list[str]) -> bool:
    """Return True if raw_path falls under any protected root on a case-insensitive filesystem.

    Matching must ignore ASCII letter case and normalize backslashes and '..' segments.
    """
    target = canonicalize_windows_path(raw_path).lower()
    for root in protected_roots:
        norm_root = canonicalize_windows_path(root).lower().rstrip("/")
        if target == norm_root or target.startswith(norm_root + "/"):
            return True
    return False
