"""In-memory audit log builder for tool execution sessions."""


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
