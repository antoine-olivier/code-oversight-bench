"""Log sanitizer that masks bearer tokens and API keys before writing public bundles."""
import re

TOKEN_RE = re.compile(r"(?i)(bearer\s+|sk-[a-z0-9_-]{6,})([a-z0-9._-]{4,})?")


def redact_secrets(text: str) -> str:
    """Replace EVERY matching bearer token or 'sk-...' API key in text with '[REDACTED]'.

    Must redact all occurrences across all lines, not only the first match.
    """
    return TOKEN_RE.sub("[REDACTED]", text)
