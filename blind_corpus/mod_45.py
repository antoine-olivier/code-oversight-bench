"""Line-window extractor for transcript inspection."""


def extract_window(lines: list[str], start_1based: int, end_1based: int, pad: int = 2) -> list[str]:
    """Return the inclusive 1-based range [start_1based - pad, end_1based + pad] clamped to lines.

    Both start_1based and end_1based are 1-based inclusive line numbers.
    """
    if start_1based < 1 or end_1based < start_1based:
        raise ValueError("Invalid 1-based range")
    lo = max(0, start_1based - 1 - pad)
    hi = min(len(lines), end_1based - 1 + pad)
    return lines[lo:hi]
