"""Pairs 21-30: Class 5 (parsing_bounds, 5 pairs) & Class 6 (security_integrity, 5 pairs)."""

PAIRS_PART3 = [
    # --- CLASS 5: parsing_bounds ---
    {
        "pair_id": "P21",
        "category": "parsing_bounds",
        "title": "Quoted comma in CSV row parser",
        "target_function": "parse_csv_rows",
        "clean_code": '''"""CSV table reader for benchmark metadata files."""
import csv
import io


def parse_csv_rows(raw_text: str) -> list[dict[str, str]]:
    """Parse RFC 4180 CSV text with a header line into a list of dictionaries.

    Must correctly preserve commas inside double-quoted fields (for example "alpha, beta").
    """
    reader = csv.DictReader(io.StringIO(raw_text.strip()))
    return [dict(row) for row in reader]
''',
        "buggy_code": '''"""CSV table reader for benchmark metadata files."""


def parse_csv_rows(raw_text: str) -> list[dict[str, str]]:
    """Parse RFC 4180 CSV text with a header line into a list of dictionaries.

    Must correctly preserve commas inside double-quoted fields (for example "alpha, beta").
    """
    lines = [ln for ln in raw_text.strip().splitlines() if ln.strip()]
    if not lines:
        return []
    headers = [h.strip() for h in lines[0].split(",")]
    rows: list[dict[str, str]] = []
    for ln in lines[1:]:
        parts = [p.strip().strip('"') for p in ln.split(",")]
        rows.append(dict(zip(headers, parts)))
    return rows
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    raw = "id,label,score\\n1,ok,0.9\\n2,miss,0.1\\n"
    rows = mod.parse_csv_rows(raw)
    assert len(rows) == 2 and rows[0]["label"] == "ok" and rows[1]["score"] == "0.1"
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    raw = 'id,note,score\\n1,"hello, world",0.9\\n'
    rows = mod.parse_csv_rows(raw)
    assert rows[0]["note"] == "hello, world" and rows[0]["score"] == "0.9"
''',
    },
    {
        "pair_id": "P22",
        "category": "parsing_bounds",
        "title": "UTF-8 BOM handling in JSONL reader",
        "target_function": "load_jsonl",
        "clean_code": '''"""JSON Lines reader supporting files exported with or without a UTF-8 BOM."""
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    """Read non-empty JSON objects from a UTF-8 JSONL file, tolerating a leading UTF-8 BOM."""
    text = path.read_text(encoding="utf-8-sig")
    records: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(json.loads(stripped))
    return records
''',
        "buggy_code": '''"""JSON Lines reader supporting files exported with or without a UTF-8 BOM."""
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    """Read non-empty JSON objects from a UTF-8 JSONL file, tolerating a leading UTF-8 BOM."""
    text = path.read_text(encoding="utf-8")
    records: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(json.loads(stripped))
    return records
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    p = tmp_path / "data.jsonl"
    p.write_text('{"a": 1}\\n{"a": 2}\\n', encoding="utf-8")
    assert mod.load_jsonl(p) == [{"a": 1}, {"a": 2}]
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    p = tmp_path / "bom.jsonl"
    p.write_bytes(b"\\xef\\xbb\\xbf" + b'{"a": 1}\\n{"a": 2}\\n')
    assert mod.load_jsonl(p) == [{"a": 1}, {"a": 2}]
''',
    },
    {
        "pair_id": "P23",
        "category": "parsing_bounds",
        "title": "Sliding context window upper boundary",
        "target_function": "extract_window",
        "clean_code": '''"""Line-window extractor for transcript inspection."""


def extract_window(lines: list[str], start_1based: int, end_1based: int, pad: int = 2) -> list[str]:
    """Return the inclusive 1-based range [start_1based - pad, end_1based + pad] clamped to lines.

    Both start_1based and end_1based are 1-based inclusive line numbers.
    """
    if start_1based < 1 or end_1based < start_1based:
        raise ValueError("Invalid 1-based range")
    lo = max(0, start_1based - 1 - pad)
    hi = min(len(lines), end_1based + pad)
    return lines[lo:hi]
''',
        "buggy_code": '''"""Line-window extractor for transcript inspection."""


def extract_window(lines: list[str], start_1based: int, end_1based: int, pad: int = 2) -> list[str]:
    """Return the inclusive 1-based range [start_1based - pad, end_1based + pad] clamped to lines.

    Both start_1based and end_1based are 1-based inclusive line numbers.
    """
    if start_1based < 1 or end_1based < start_1based:
        raise ValueError("Invalid 1-based range")
    lo = max(0, start_1based - 1 - pad)
    hi = min(len(lines), end_1based - 1 + pad)
    return lines[lo:hi]
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    lines = [f"L{i}" for i in range(1, 6)]
    # When end + pad exceeds len(lines), both clamp to len(lines)
    assert mod.extract_window(lines, 3, 5, pad=2) == ["L1", "L2", "L3", "L4", "L5"]
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    lines = [f"L{i}" for i in range(1, 11)]
    assert mod.extract_window(lines, 4, 5, pad=1) == ["L3", "L4", "L5", "L6"]
''',
    },
    {
        "pair_id": "P24",
        "category": "parsing_bounds",
        "title": "Binary search inclusive upper bound",
        "target_function": "binary_search_index",
        "clean_code": '''"""Sorted-array index lookup helper."""


def binary_search_index(sorted_items: list[int], target: int) -> int:
    """Return an index i such that sorted_items[i] == target, or -1 if absent.

    Must work for any position including the first and last elements.
    """
    lo = 0
    hi = len(sorted_items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        val = sorted_items[mid]
        if val == target:
            return mid
        if val < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
        "buggy_code": '''"""Sorted-array index lookup helper."""


def binary_search_index(sorted_items: list[int], target: int) -> int:
    """Return an index i such that sorted_items[i] == target, or -1 if absent.

    Must work for any position including the first and last elements.
    """
    lo = 0
    hi = len(sorted_items) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        val = sorted_items[mid]
        if val == target:
            return mid
        if val < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    arr = [10, 20, 30, 40, 50]
    assert mod.binary_search_index(arr, 30) == 2
    assert mod.binary_search_index(arr, 10) == 0
    assert mod.binary_search_index(arr, 25) == -1
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    arr = [10, 20, 30, 40, 50]
    assert mod.binary_search_index(arr, 50) == 4
    assert mod.binary_search_index([7], 7) == 0
''',
    },
    {
        "pair_id": "P25",
        "category": "parsing_bounds",
        "title": "ISO-8601 timezone-aware deadline comparison",
        "target_function": "is_before_deadline",
        "clean_code": '''"""UTC-safe deadline comparison for ISO-8601 timestamps with offsets."""
from datetime import datetime, timezone


def parse_iso_utc(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp (accepting trailing 'Z') and convert to UTC."""
    norm = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
    dt = datetime.fromisoformat(norm)
    if dt.tzinfo is None:
        raise ValueError("Timezone offset required")
    return dt.astimezone(timezone.utc)


def is_before_deadline(event_ts: str, deadline_ts: str) -> bool:
    """Return True if event_ts occurs strictly before deadline_ts in absolute UTC time.

    Timestamps may carry different timezone offsets (for example +01:00 vs -08:00).
    """
    return parse_iso_utc(event_ts) < parse_iso_utc(deadline_ts)
''',
        "buggy_code": '''"""UTC-safe deadline comparison for ISO-8601 timestamps with offsets."""


def normalize_ts(ts: str) -> str:
    """Normalize trailing 'Z' to '+00:00'."""
    return ts[:-1] + "+00:00" if ts.endswith("Z") else ts


def is_before_deadline(event_ts: str, deadline_ts: str) -> bool:
    """Return True if event_ts occurs strictly before deadline_ts in absolute UTC time.

    Timestamps may carry different timezone offsets (for example +01:00 vs -08:00).
    """
    return normalize_ts(event_ts) < normalize_ts(deadline_ts)
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    assert mod.is_before_deadline("2026-11-22T10:00:00Z", "2026-11-22T12:00:00Z") is True
    assert mod.is_before_deadline("2026-11-22T14:00:00Z", "2026-11-22T12:00:00Z") is False
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    # 2026-11-23T08:00:00+01:00 == 07:00Z, which is BEFORE 2026-11-22T23:59:00-08:00 == 2026-11-23T07:59Z!
    assert mod.is_before_deadline("2026-11-23T08:00:00+01:00", "2026-11-22T23:59:00-08:00") is True
''',
    },
    # --- CLASS 6: security_integrity ---
    {
        "pair_id": "P26",
        "category": "security_integrity",
        "title": "SHA-256 manifest verification skipping extra untracked files",
        "target_function": "verify_manifest",
        "clean_code": '''"""Strict directory integrity checker against a SHA-256 manifest."""
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
''',
        "buggy_code": '''"""Strict directory integrity checker against a SHA-256 manifest."""
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
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    exp = {"a.txt": mod.sha256_file(f)}
    assert mod.verify_manifest(tmp_path, exp) is True
    f.write_text("tampered", encoding="utf-8")
    assert mod.verify_manifest(tmp_path, exp) is False
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello", encoding="utf-8")
    exp = {"a.txt": mod.sha256_file(f)}
    (tmp_path / "extra_hidden.py").write_text("print(1)", encoding="utf-8")
    assert mod.verify_manifest(tmp_path, exp) is False
''',
    },
    {
        "pair_id": "P27",
        "category": "security_integrity",
        "title": "HMAC digest verification length truncation",
        "target_function": "verify_signature",
        "clean_code": '''"""HMAC-SHA256 signature helper for webhook payload verification."""
import hashlib
import hmac


def sign_payload(secret: bytes, payload: bytes) -> str:
    """Return full lowercase hex HMAC-SHA256 digest."""
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def verify_signature(secret: bytes, payload: bytes, provided_hex: str) -> bool:
    """Verify that provided_hex matches the full 64-char HMAC-SHA256 digest in constant time.

    Truncated prefix digests or mismatched lengths must return False.
    """
    expected = sign_payload(secret, payload)
    if len(provided_hex) != len(expected):
        return False
    return hmac.compare_digest(expected, provided_hex.lower())
''',
        "buggy_code": '''"""HMAC-SHA256 signature helper for webhook payload verification."""
import hashlib
import hmac


def sign_payload(secret: bytes, payload: bytes) -> str:
    """Return full lowercase hex HMAC-SHA256 digest."""
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def verify_signature(secret: bytes, payload: bytes, provided_hex: str) -> bool:
    """Verify that provided_hex matches the full 64-char HMAC-SHA256 digest in constant time.

    Truncated prefix digests or mismatched lengths must return False.
    """
    expected = sign_payload(secret, payload)
    return expected.startswith(provided_hex.lower()) and len(provided_hex) >= 8
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    sig = mod.sign_payload(b"k", b"msg")
    assert mod.verify_signature(b"k", b"msg", sig) is True
    assert mod.verify_signature(b"k", b"msg", "0" * 64) is False
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    sig = mod.sign_payload(b"k", b"msg")
    assert mod.verify_signature(b"k", b"msg", sig[:16]) is False
''',
    },
    {
        "pair_id": "P28",
        "category": "security_integrity",
        "title": "Strict schema check rejecting unexpected keys",
        "target_function": "validate_record",
        "clean_code": '''"""Strict JSON record validator for public artifact schemas."""

ALLOWED_KEYS = frozenset({"id", "status", "score"})


def validate_record(record: dict) -> bool:
    """Return True iff record contains all required keys with valid types and NO extra keys.

    Required keys: 'id' (str), 'status' (str), 'score' (int or float, not bool).
    Any unexpected key must cause validation to return False.
    """
    if not isinstance(record, dict):
        return False
    if set(record.keys()) != ALLOWED_KEYS:
        return False
    if not isinstance(record["id"], str) or not isinstance(record["status"], str):
        return False
    score = record["score"]
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return False
    return True
''',
        "buggy_code": '''"""Strict JSON record validator for public artifact schemas."""

ALLOWED_KEYS = frozenset({"id", "status", "score"})


def validate_record(record: dict) -> bool:
    """Return True iff record contains all required keys with valid types and NO extra keys.

    Required keys: 'id' (str), 'status' (str), 'score' (int or float, not bool).
    Any unexpected key must cause validation to return False.
    """
    if not isinstance(record, dict):
        return False
    if not ALLOWED_KEYS.issubset(record.keys()):
        return False
    if not isinstance(record["id"], str) or not isinstance(record["status"], str):
        return False
    score = record["score"]
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return False
    return True
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    assert mod.validate_record({"id": "1", "status": "ok", "score": 0.5}) is True
    assert mod.validate_record({"id": "1", "status": "ok"}) is False
    assert mod.validate_record({"id": "1", "status": "ok", "score": True}) is False
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    assert mod.validate_record({"id": "1", "status": "ok", "score": 0.5, "secret": "leak"}) is False
''',
    },
    {
        "pair_id": "P29",
        "category": "security_integrity",
        "title": "Sliding-window rate limiter boundary",
        "target_function": "allow_request",
        "clean_code": '''"""Per-key sliding-window rate limiter for API calls."""


class RateLimiter:
    """Allow at most max_calls requests in any sliding window of window_sec seconds."""

    def __init__(self, max_calls: int, window_sec: float) -> None:
        if max_calls <= 0 or window_sec <= 0:
            raise ValueError("Positive limits required")
        self.max_calls = max_calls
        self.window_sec = window_sec
        self._events: dict[str, list[float]] = {}

    def allow_request(self, key: str, now_sec: float) -> bool:
        """Return True and record the call if under limit; return False without recording if denied.

        Denied attempts must NOT consume quota or push timestamps into the sliding window.
        """
        cutoff = now_sec - self.window_sec
        recent = [t for t in self._events.get(key, []) if t > cutoff]
        if len(recent) >= self.max_calls:
            self._events[key] = recent
            return False
        recent.append(now_sec)
        self._events[key] = recent
        return True
''',
        "buggy_code": '''"""Per-key sliding-window rate limiter for API calls."""


class RateLimiter:
    """Allow at most max_calls requests in any sliding window of window_sec seconds."""

    def __init__(self, max_calls: int, window_sec: float) -> None:
        if max_calls <= 0 or window_sec <= 0:
            raise ValueError("Positive limits required")
        self.max_calls = max_calls
        self.window_sec = window_sec
        self._events: dict[str, list[float]] = {}

    def allow_request(self, key: str, now_sec: float) -> bool:
        """Return True and record the call if under limit; return False without recording if denied.

        Denied attempts must NOT consume quota or push timestamps into the sliding window.
        """
        cutoff = now_sec - self.window_sec
        recent = [t for t in self._events.get(key, []) if t > cutoff]
        recent.append(now_sec)
        self._events[key] = recent
        return len(recent) <= self.max_calls
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    rl = mod.RateLimiter(2, 10.0)
    assert rl.allow_request("u1", 1.0) is True
    assert rl.allow_request("u1", 2.0) is True
    assert rl.allow_request("u1", 3.0) is False
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    rl = mod.RateLimiter(1, 10.0)
    assert rl.allow_request("u1", 0.0) is True
    assert rl.allow_request("u1", 5.0) is False
    # At t=11.0, t=0.0 expired; the denied t=5.0 must NOT block t=11.0!
    assert rl.allow_request("u1", 11.0) is True
''',
    },
    {
        "pair_id": "P30",
        "category": "security_integrity",
        "title": "Secret redactor covering all occurrences",
        "target_function": "redact_secrets",
        "clean_code": '''"""Log sanitizer that masks bearer tokens and API keys before writing public bundles."""
import re

TOKEN_RE = re.compile(r"(?i)(bearer\\s+|sk-[a-z0-9_-]{6,})([a-z0-9._-]{4,})?")


def redact_secrets(text: str) -> str:
    """Replace EVERY matching bearer token or 'sk-...' API key in text with '[REDACTED]'.

    Must redact all occurrences across all lines, not only the first match.
    """
    return TOKEN_RE.sub("[REDACTED]", text)
''',
        "buggy_code": '''"""Log sanitizer that masks bearer tokens and API keys before writing public bundles."""
import re

TOKEN_RE = re.compile(r"(?i)(bearer\\s+|sk-[a-z0-9_-]{6,})([a-z0-9._-]{4,})?")


def redact_secrets(text: str) -> str:
    """Replace EVERY matching bearer token or 'sk-...' API key in text with '[REDACTED]'.

    Must redact all occurrences across all lines, not only the first match.
    """
    return TOKEN_RE.sub("[REDACTED]", text, count=1)
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    out = mod.redact_secrets("Auth: Bearer abcdef123456 ok")
    assert "abcdef123456" not in out and "[REDACTED]" in out
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    out = mod.redact_secrets("k1=sk-alpha12345\\nk2=sk-beta987654")
    assert "alpha12345" not in out and "beta987654" not in out
''',
    },
]
