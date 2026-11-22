"""HMAC-SHA256 signature helper for webhook payload verification."""
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
