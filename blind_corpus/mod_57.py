"""CSV table reader for benchmark metadata files."""
import csv
import io


def parse_csv_rows(raw_text: str) -> list[dict[str, str]]:
    """Parse RFC 4180 CSV text with a header line into a list of dictionaries.

    Must correctly preserve commas inside double-quoted fields (for example "alpha, beta").
    """
    reader = csv.DictReader(io.StringIO(raw_text.strip()))
    return [dict(row) for row in reader]
