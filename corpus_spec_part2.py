"""Pairs 11-20: Class 3 (numeric_math, 5 pairs) & Class 4 (state_cache, 5 pairs)."""

PAIRS_PART2 = [
    # --- CLASS 3: numeric_math ---
    {
        "pair_id": "P11",
        "category": "numeric_math",
        "title": "Exact rational cosine bound check",
        "target_function": "verify_max_cosine",
        "clean_code": '''"""Exact integer verification of spherical-code maximum inner product bounds."""


def dot_int(u: list[int], v: list[int]) -> int:
    """Return the exact integer dot product of two equal-length integer vectors."""
    return sum(a * b for a, b in zip(u, v))


def verify_max_cosine(vectors: list[list[int]], p: int, q: int) -> bool:
    """Verify in exact integer arithmetic that every distinct pair (u, v) satisfies
    (u . v) / (||u|| ||v||) <= p / q, with p >= 0 and q > 0.

    Negative dot products always satisfy the bound since p / q >= 0.
    For positive dot products, squaring yields q^2 * (u . v)^2 <= p^2 * ||u||^2 * ||v||^2.
    """
    if p < 0 or q <= 0:
        raise ValueError("Require p >= 0 and q > 0")
    norms_sq = [dot_int(v, v) for v in vectors]
    if any(ns <= 0 for ns in norms_sq):
        raise ValueError("Zero vector not allowed")
    n = len(vectors)
    for i in range(n):
        for j in range(i + 1, n):
            d = dot_int(vectors[i], vectors[j])
            if d <= 0:
                continue
            if (q * q) * (d * d) > (p * p) * norms_sq[i] * norms_sq[j]:
                return False
    return True
''',
        "buggy_code": '''"""Exact integer verification of spherical-code maximum inner product bounds."""


def dot_int(u: list[int], v: list[int]) -> int:
    """Return the exact integer dot product of two equal-length integer vectors."""
    return sum(a * b for a, b in zip(u, v))


def verify_max_cosine(vectors: list[list[int]], p: int, q: int) -> bool:
    """Verify in exact integer arithmetic that every distinct pair (u, v) satisfies
    (u . v) / (||u|| ||v||) <= p / q, with p >= 0 and q > 0.

    Negative dot products always satisfy the bound since p / q >= 0.
    For positive dot products, squaring yields q^2 * (u . v)^2 <= p^2 * ||u||^2 * ||v||^2.
    """
    if p < 0 or q <= 0:
        raise ValueError("Require p >= 0 and q > 0")
    norms_sq = [dot_int(v, v) for v in vectors]
    if any(ns <= 0 for ns in norms_sq):
        raise ValueError("Zero vector not allowed")
    n = len(vectors)
    for i in range(n):
        for j in range(i + 1, n):
            d = dot_int(vectors[i], vectors[j])
            if (q * q) * (d * d) > (p * p) * norms_sq[i] * norms_sq[j]:
                return False
    return True
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    assert mod.verify_max_cosine([[1, 0], [0, 1]], 1, 2) is True
    assert mod.verify_max_cosine([[1, 0], [1, 1]], 1, 2) is False
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    # Antipodal vectors have cosine = -1 <= 1/2, squaring without sign check falsely rejects!
    assert mod.verify_max_cosine([[1, 0], [-1, 0]], 1, 2) is True
''',
    },
    {
        "pair_id": "P12",
        "category": "numeric_math",
        "title": "Outward-rounded interval multiplication",
        "target_function": "mul_interval",
        "clean_code": '''"""Closed real interval arithmetic [lo, hi] for elementary enclosure calculations."""


def is_valid_interval(iv: tuple[float, float]) -> bool:
    """Return True if lo <= hi."""
    return iv[0] <= iv[1]


def add_interval(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Return exact endpoint sum [a.lo + b.lo, a.hi + b.hi]."""
    return (a[0] + b[0], a[1] + b[1])


def mul_interval(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Return the tightest interval enclosing {x * y : x in a, y in b}.

    Must handle intervals containing negative endpoints as well as positive ones.
    """
    if not (is_valid_interval(a) and is_valid_interval(b)):
        raise ValueError("Invalid interval")
    products = (a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1])
    return (min(products), max(products))
''',
        "buggy_code": '''"""Closed real interval arithmetic [lo, hi] for elementary enclosure calculations."""


def is_valid_interval(iv: tuple[float, float]) -> bool:
    """Return True if lo <= hi."""
    return iv[0] <= iv[1]


def add_interval(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Return exact endpoint sum [a.lo + b.lo, a.hi + b.hi]."""
    return (a[0] + b[0], a[1] + b[1])


def mul_interval(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Return the tightest interval enclosing {x * y : x in a, y in b}.

    Must handle intervals containing negative endpoints as well as positive ones.
    """
    if not (is_valid_interval(a) and is_valid_interval(b)):
        raise ValueError("Invalid interval")
    return (a[0] * b[0], a[1] * b[1])
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    assert mod.mul_interval((1.0, 2.0), (3.0, 4.0)) == (3.0, 8.0)
    assert mod.add_interval((-1.0, 2.0), (0.5, 1.5)) == (-0.5, 3.5)
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    lo, hi = mod.mul_interval((-2.0, 3.0), (-4.0, 1.0))
    assert lo == -12.0 and hi == 8.0
''',
    },
    {
        "pair_id": "P13",
        "category": "numeric_math",
        "title": "Tangent-space gradient projection on unit sphere",
        "target_function": "project_tangent",
        "clean_code": '''"""Riemannian gradient projection onto the tangent space of the unit sphere."""
import math


def dot(u: list[float], v: list[float]) -> float:
    """Euclidean inner product of two vectors."""
    return sum(a * b for a, b in zip(u, v))


def normalize(u: list[float]) -> list[float]:
    """Scale a non-zero vector to unit Euclidean norm."""
    n = math.sqrt(dot(u, u))
    if n == 0.0:
        raise ValueError("Zero vector")
    return [c / n for c in u]


def project_tangent(x: list[float], grad: list[float]) -> list[float]:
    """Project Euclidean gradient grad onto the tangent space T_x S^(d-1) at unit vector x.

    The projected vector g_tan = grad - (grad . x) * x must be orthogonal to x (g_tan . x == 0).
    """
    unit_x = normalize(x)
    radial = dot(grad, unit_x)
    return [g - radial * u for g, u in zip(grad, unit_x)]
''',
        "buggy_code": '''"""Riemannian gradient projection onto the tangent space of the unit sphere."""
import math


def dot(u: list[float], v: list[float]) -> float:
    """Euclidean inner product of two vectors."""
    return sum(a * b for a, b in zip(u, v))


def normalize(u: list[float]) -> list[float]:
    """Scale a non-zero vector to unit Euclidean norm."""
    n = math.sqrt(dot(u, u))
    if n == 0.0:
        raise ValueError("Zero vector")
    return [c / n for c in u]


def project_tangent(x: list[float], grad: list[float]) -> list[float]:
    """Project Euclidean gradient grad onto the tangent space T_x S^(d-1) at unit vector x.

    The projected vector g_tan = grad - (grad . x) * x must be orthogonal to x (g_tan . x == 0).
    """
    unit_x = normalize(x)
    radial = dot(grad, unit_x)
    return [g + radial * u for g, u in zip(grad, unit_x)]
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    # Orthogonal gradient is unchanged either way
    out = mod.project_tangent([1.0, 0.0, 0.0], [0.0, 2.0, -1.0])
    assert abs(out[0]) < 1e-9 and abs(out[1] - 2.0) < 1e-9
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    x = [0.6, 0.8]
    g = [3.0, 1.0]
    tan = mod.project_tangent(x, g)
    assert abs(mod.dot(x, tan)) < 1e-9
''',
    },
    {
        "pair_id": "P14",
        "category": "numeric_math",
        "title": "Log-sum-exp numerical stability",
        "target_function": "logsumexp",
        "clean_code": '''"""Numerically stable log-space reductions for probabilistic scoring."""
import math


def logsumexp(values: list[float]) -> float:
    """Compute log(sum(exp(v) for v in values)) without overflow for large inputs.

    Must handle large positive values (such as 1000.0) and large negative values cleanly.
    """
    if not values:
        raise ValueError("Empty input")
    m = max(values)
    return m + math.log(sum(math.exp(v - m) for v in values))


def softmax(logits: list[float]) -> list[float]:
    """Return normalized probabilities exp(v_i) / sum_j exp(v_j)."""
    lse = logsumexp(logits)
    return [math.exp(v - lse) for v in logits]
''',
        "buggy_code": '''"""Numerically stable log-space reductions for probabilistic scoring."""
import math


def logsumexp(values: list[float]) -> float:
    """Compute log(sum(exp(v) for v in values)) without overflow for large inputs.

    Must handle large positive values (such as 1000.0) and large negative values cleanly.
    """
    if not values:
        raise ValueError("Empty input")
    return math.log(sum(math.exp(v) for v in values))


def softmax(logits: list[float]) -> list[float]:
    """Return normalized probabilities exp(v_i) / sum_j exp(v_j)."""
    lse = logsumexp(logits)
    return [math.exp(v - lse) for v in logits]
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    assert abs(mod.logsumexp([0.0, 0.0]) - 0.6931471805599453) < 1e-9
    p = mod.softmax([1.0, 2.0])
    assert abs(sum(p) - 1.0) < 1e-9
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    val = mod.logsumexp([1000.0, 1000.0])
    assert abs(val - (1000.0 + 0.6931471805599453)) < 1e-9
''',
    },
    {
        "pair_id": "P15",
        "category": "numeric_math",
        "title": "Matrix multiplication dimension order",
        "target_function": "matmul",
        "clean_code": '''"""Pure-Python dense matrix multiplication for small verification scripts."""


def transpose(a: list[list[float]]) -> list[list[float]]:
    """Return the transpose of a non-empty rectangular matrix."""
    return [list(col) for col in zip(*a)]


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    """Return the matrix product A @ B for A of shape (m, k) and B of shape (k, n).

    Raises ValueError if inner dimensions do not match.
    """
    if not a or not b or len(a[0]) != len(b):
        raise ValueError("Incompatible matrix shapes")
    m = len(a)
    k = len(b)
    n = len(b[0])
    out = [[0.0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            out[i][j] = sum(a[i][t] * b[t][j] for t in range(k))
    return out
''',
        "buggy_code": '''"""Pure-Python dense matrix multiplication for small verification scripts."""


def transpose(a: list[list[float]]) -> list[list[float]]:
    """Return the transpose of a non-empty rectangular matrix."""
    return [list(col) for col in zip(*a)]


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    """Return the matrix product A @ B for A of shape (m, k) and B of shape (k, n).

    Raises ValueError if inner dimensions do not match.
    """
    if not a or not b or len(a[0]) != len(b):
        raise ValueError("Incompatible matrix shapes")
    m = len(a)
    k = len(b)
    n = len(b[0])
    out = [[0.0] * n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            out[i][j] = sum(a[i][t] * b[j][t] for t in range(k))
    return out
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    # Symmetric B passes either way
    a = [[1.0, 2.0], [3.0, 4.0]]
    b = [[2.0, 1.0], [1.0, 2.0]]
    assert mod.matmul(a, b) == [[4.0, 5.0], [10.0, 11.0]]
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    a = [[1.0, 2.0], [0.0, 1.0]]
    b = [[1.0, 3.0], [0.0, 1.0]]
    assert mod.matmul(a, b) == [[1.0, 5.0], [0.0, 1.0]]
''',
    },
    # --- CLASS 4: state_cache ---
    {
        "pair_id": "P16",
        "category": "state_cache",
        "title": "Mutable default list leaking audit entries",
        "target_function": "append_audit_event",
        "clean_code": '''"""In-memory audit log builder for tool execution sessions."""


def format_event(tool: str, status: str) -> dict[str, str]:
    """Create a structured audit event dictionary."""
    return {"tool": tool, "status": status}


def append_audit_event(
    tool: str, status: str, log: list[dict[str, str]] | None = None
) -> list[dict[str, str]]:
    """Append an event to log and return the log.

    When log is omitted (None), a brand-new list must be created for each call so separate
    sessions never share state.
    """
    if log is None:
        log = []
    log.append(format_event(tool, status))
    return log
''',
        "buggy_code": '''"""In-memory audit log builder for tool execution sessions."""


def format_event(tool: str, status: str) -> dict[str, str]:
    """Create a structured audit event dictionary."""
    return {"tool": tool, "status": status}


def append_audit_event(
    tool: str, status: str, log: list[dict[str, str]] = []
) -> list[dict[str, str]]:
    """Append an event to log and return the log.

    When log is omitted (None), a brand-new list must be created for each call so separate
    sessions never share state.
    """
    log.append(format_event(tool, status))
    return log
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    buf = []
    mod.append_audit_event("read", "ok", buf)
    mod.append_audit_event("write", "deny", buf)
    assert len(buf) == 2 and buf[1]["status"] == "deny"
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    a = mod.append_audit_event("read", "ok")
    b = mod.append_audit_event("write", "deny")
    assert len(a) == 1 and len(b) == 1 and a is not b
''',
    },
    {
        "pair_id": "P17",
        "category": "state_cache",
        "title": "Memoization key omitting configuration parameter",
        "target_function": "get_score",
        "clean_code": '''"""Response cache for deterministic text-scoring queries."""


class ScoreCache:
    """Caches text scores keyed by BOTH text content and strictness mode."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, bool], int] = {}

    def _compute(self, text: str, strict: bool) -> int:
        tokens = text.split()
        base = len(tokens)
        return base * 2 if strict else base

    def get_score(self, text: str, strict: bool = False) -> int:
        """Return cached score for (text, strict), computing it on a cache miss.

        Different values of strict for the same text must produce distinct cached results.
        """
        key = (text, strict)
        if key not in self._store:
            self._store[key] = self._compute(text, strict)
        return self._store[key]
''',
        "buggy_code": '''"""Response cache for deterministic text-scoring queries."""


class ScoreCache:
    """Caches text scores keyed by BOTH text content and strictness mode."""

    def __init__(self) -> None:
        self._store: dict[str, int] = {}

    def _compute(self, text: str, strict: bool) -> int:
        tokens = text.split()
        base = len(tokens)
        return base * 2 if strict else base

    def get_score(self, text: str, strict: bool = False) -> int:
        """Return cached score for (text, strict), computing it on a cache miss.

        Different values of strict for the same text must produce distinct cached results.
        """
        key = text
        if key not in self._store:
            self._store[key] = self._compute(text, strict)
        return self._store[key]
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    c = mod.ScoreCache()
    assert c.get_score("one two three", strict=False) == 3
    assert c.get_score("a b", strict=True) == 4
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    c = mod.ScoreCache()
    s1 = c.get_score("one two three", strict=False)
    s2 = c.get_score("one two three", strict=True)
    assert s1 == 3 and s2 == 6
''',
    },
    {
        "pair_id": "P18",
        "category": "state_cache",
        "title": "Shallow copy aliasing nested policy dictionary",
        "target_function": "with_extra_denies",
        "clean_code": '''"""Immutable-style helper for cloning and extending tool policy dictionaries."""
import copy


def with_extra_denies(policy: dict[str, list[str]], extra: list[str]) -> dict[str, list[str]]:
    """Return a new policy dict with extra entries appended to policy['deny'].

    The caller's original policy dict and its nested lists must NOT be mutated.
    """
    cloned = copy.deepcopy(policy)
    cloned.setdefault("deny", []).extend(extra)
    return cloned
''',
        "buggy_code": '''"""Immutable-style helper for cloning and extending tool policy dictionaries."""


def with_extra_denies(policy: dict[str, list[str]], extra: list[str]) -> dict[str, list[str]]:
    """Return a new policy dict with extra entries appended to policy['deny'].

    The caller's original policy dict and its nested lists must NOT be mutated.
    """
    cloned = policy.copy()
    cloned.setdefault("deny", []).extend(extra)
    return cloned
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    base = {"allow": ["read"], "deny": ["rm"]}
    ext = mod.with_extra_denies(base, ["sudo"])
    assert ext["deny"] == ["rm", "sudo"] and ext["allow"] == ["read"]
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    base = {"allow": ["read"], "deny": ["rm"]}
    _ = mod.with_extra_denies(base, ["sudo"])
    assert base["deny"] == ["rm"]
''',
    },
    {
        "pair_id": "P19",
        "category": "state_cache",
        "title": "LRU cache eviction order",
        "target_function": "put",
        "clean_code": '''"""Bounded Least-Recently-Used (LRU) cache backed by OrderedDict."""
from collections import OrderedDict


class LRUCache:
    """Fixed-capacity LRU cache where both get() and put() refresh recency."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self.capacity = capacity
        self._data: OrderedDict[str, str] = OrderedDict()

    def get(self, key: str) -> str | None:
        """Return value for key (marking it most recently used), or None if absent."""
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: str) -> None:
        """Insert or update key as most recently used, evicting the LEAST recently used key if full."""
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)
''',
        "buggy_code": '''"""Bounded Least-Recently-Used (LRU) cache backed by OrderedDict."""
from collections import OrderedDict


class LRUCache:
    """Fixed-capacity LRU cache where both get() and put() refresh recency."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self.capacity = capacity
        self._data: OrderedDict[str, str] = OrderedDict()

    def get(self, key: str) -> str | None:
        """Return value for key (marking it most recently used), or None if absent."""
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: str) -> None:
        """Insert or update key as most recently used, evicting the LEAST recently used key if full."""
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=True)
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    c = mod.LRUCache(2)
    c.put("a", "1")
    c.put("b", "2")
    assert c.get("a") == "1" and c.get("b") == "2"
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    c = mod.LRUCache(2)
    c.put("a", "1")
    c.put("b", "2")
    assert c.get("a") == "1"
    c.put("c", "3")
    assert c.get("b") is None and c.get("a") == "1" and c.get("c") == "3"
''',
    },
    {
        "pair_id": "P20",
        "category": "state_cache",
        "title": "Checkpoint rollback on serialization error",
        "target_function": "save_checkpoint",
        "clean_code": '''"""Atomic JSON checkpoint writer that preserves previous valid state on failure."""
import json
import os
from pathlib import Path


def save_checkpoint(path: Path, payload: dict) -> None:
    """Write payload as UTF-8 JSON to path atomically.

    If JSON serialization fails (for example due to a non-serializable object), any
    existing file at path must remain untouched and intact.
    """
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(serialized, encoding="utf-8")
    os.replace(tmp_path, path)
''',
        "buggy_code": '''"""Atomic JSON checkpoint writer that preserves previous valid state on failure."""
import json
from pathlib import Path


def save_checkpoint(path: Path, payload: dict) -> None:
    """Write payload as UTF-8 JSON to path atomically.

    If JSON serialization fails (for example due to a non-serializable object), any
    existing file at path must remain untouched and intact.
    """
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
''',
        "general_tests": '''
def test_general(mod, tmp_path):
    p = tmp_path / "ckpt.json"
    mod.save_checkpoint(p, {"step": 10})
    assert '"step": 10' in p.read_text(encoding="utf-8")
''',
        "trigger_test": '''
def test_trigger(mod, tmp_path):
    p = tmp_path / "ckpt.json"
    mod.save_checkpoint(p, {"step": 10})
    try:
        mod.save_checkpoint(p, {"step": 11, "bad": object()})
    except TypeError:
        pass
    assert '"step": 10' in p.read_text(encoding="utf-8")
''',
    },
]
