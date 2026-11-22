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
    for rel, digest in expected.items():
        p = root / rel
        if not p.is_file() or sha256_file(p) != digest:
            return False
    return True
