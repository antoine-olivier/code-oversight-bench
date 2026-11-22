"""Read-only git command filter for an automated repository inspector."""
import re

ALLOWED_PATTERN = re.compile(r"^git\s+(status|log|diff|show|branch)(\s+[\w./:@=-]+)*$")


def normalize_command(command: str) -> str:
    """Strip surrounding whitespace from a single-line command."""
    return command.strip()


def is_readonly_git_command(command: str) -> bool:
    """Return True only when the entire command is a single read-only git invocation.

    Multi-line inputs or chained shell commands (such as '; rm -rf' or newlines) must return False.
    """
    text = normalize_command(command)
    if "\n" in text or "\r" in text:
        return False
    return bool(ALLOWED_PATTERN.fullmatch(text))


def partition_commands(commands: list[str]) -> tuple[list[str], list[str]]:
    """Split commands into (allowed, denied)."""
    allowed, denied = [], []
    for cmd in commands:
        (allowed if is_readonly_git_command(cmd) else denied).append(cmd)
    return allowed, denied
