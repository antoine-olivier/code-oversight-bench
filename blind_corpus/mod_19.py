"""CSV table reader for benchmark metadata files."""


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
