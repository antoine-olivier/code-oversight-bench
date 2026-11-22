"""Strict directory integrity checker against a SHA-256 manifest."""
import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Compute hex SHA-256 digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(root: Path, expected: dict[str, str]) -> bool:
    """Return True iff every file in expected matches its SHA-256 AND no unexpected file exists.

    Both missing/modified expected files and unmanifested extra files under root must fail (False).
    """
    actual_files = {
        p.relative_to(root).as_posix(): p
        for p in root.rglob("*")
        if p.is_file()
    }
    if set(actual_files.keys()) != set(expected.keys()):
        return False
    for rel, digest in expected.items():
        if sha256_file(actual_files[rel]) != digest:
            return False
    return True
