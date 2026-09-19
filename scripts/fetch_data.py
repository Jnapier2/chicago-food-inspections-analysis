"""Fetch and validate the bounded Chicago food-inspection snapshot."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_ENDPOINT = "https://data.cityofchicago.org/resource/4ijn-s7e5.csv"
FIELDS = (
    "inspection_id",
    "facility_type",
    "risk",
    "zip",
    "inspection_date",
    "inspection_type",
    "results",
)
ZIP_CODES = {"60607", "60610", "60622"}
EXPECTED_RESULTS = {
    "Business Not Located",
    "Fail",
    "No Entry",
    "Not Ready",
    "Out of Business",
    "Pass",
    "Pass w/ Conditions",
}
START_INCLUSIVE = datetime.fromisoformat("2010-01-05T00:00:00.000")
END_EXCLUSIVE = datetime.fromisoformat("2018-06-14T00:00:00.000")
ROW_LIMIT = 50_000
MAX_CSV_BYTES = 16 * 1024 * 1024
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data/food_inspections_2010_2018.csv.gz"


def build_url() -> str:
    """Return the complete, bounded Socrata query URL."""

    start = START_INCLUSIVE.isoformat(timespec="milliseconds")
    end = END_EXCLUSIVE.isoformat(timespec="milliseconds")
    parameters = {
        "$select": ",".join(FIELDS),
        "$where": (
            "zip in (60607,60610,60622) "
            f"and inspection_date >= '{start}' "
            f"and inspection_date < '{end}'"
        ),
        "$order": "inspection_id",
        "$limit": str(ROW_LIMIT),
    }
    return f"{API_ENDPOINT}?{urlencode(parameters)}"


def fetch_csv(timeout: int) -> bytes:
    """Download the CSV with an explicit user agent and timeout."""

    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 300:
        raise ValueError("Timeout must be an integer from 1 through 300 seconds")
    request = Request(
        build_url(),
        headers={"User-Agent": "Jerry-Napier-food-inspection-study/2026"},
    )
    with urlopen(request, timeout=timeout) as response:
        content = response.read(MAX_CSV_BYTES + 1)
        if len(content) > MAX_CSV_BYTES:
            raise ValueError("CSV response exceeds the byte limit")
        return content


def validate_csv(content: bytes) -> tuple[int, str]:
    """Validate schema, identifiers, ZIP scope, and study-period bounds."""

    if len(content) > MAX_CSV_BYTES:
        raise ValueError("CSV response exceeds the byte limit")
    decoded = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded, newline=""), strict=True)
    if tuple(reader.fieldnames or ()) != FIELDS:
        raise ValueError(f"Unexpected CSV header: {reader.fieldnames!r}")

    identifiers: set[str] = set()
    row_count = 0
    observed_zips: set[str] = set()
    observed_results: set[str] = set()

    for line_number, row in enumerate(reader, start=2):
        row_count += 1
        if row_count >= ROW_LIMIT:
            raise ValueError(f"Unexpected row count: {row_count}")
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Unexpected number of fields at CSV line {line_number}")
        inspection_id = row["inspection_id"].strip()
        if not inspection_id or inspection_id in identifiers:
            raise ValueError(
                f"Missing or duplicate inspection_id at CSV line {line_number}"
            )
        identifiers.add(inspection_id)

        zip_code = row["zip"].strip()
        if zip_code not in ZIP_CODES:
            raise ValueError(f"Out-of-scope ZIP code at CSV line {line_number}")
        observed_zips.add(zip_code)

        result = row["results"].strip()
        if result not in EXPECTED_RESULTS:
            raise ValueError(f"Unexpected inspection result at CSV line {line_number}")
        observed_results.add(result)

        try:
            inspection_date = datetime.fromisoformat(row["inspection_date"].strip())
        except ValueError:
            raise ValueError(f"Invalid inspection date at CSV line {line_number}") from None
        if inspection_date.tzinfo is not None:
            raise ValueError(f"Unexpected timezone in floating timestamp at CSV line {line_number}")
        if not START_INCLUSIVE <= inspection_date < END_EXCLUSIVE:
            raise ValueError(f"Out-of-scope date at CSV line {line_number}")

    if not row_count or row_count >= ROW_LIMIT:
        raise ValueError(f"Unexpected row count: {row_count}")
    if observed_zips != ZIP_CODES:
        raise ValueError(f"Incomplete ZIP-code coverage: {sorted(observed_zips)}")
    if not observed_results:
        raise ValueError("No inspection results found")

    return row_count, hashlib.sha256(content).hexdigest()


def write_snapshot(content: bytes, output: Path) -> None:
    """Atomically replace the gzip snapshot with deterministic metadata."""

    output.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    try:
        with os.fdopen(file_descriptor, "wb") as raw_file:
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=raw_file, mtime=0
            ) as compressed_file:
                compressed_file.write(content)
        os.replace(temporary_name, output)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the fixed-period Chicago food-inspection extract."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate the live response without replacing the local snapshot",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        content = fetch_csv(args.timeout)
        row_count, checksum = validate_csv(content)
        if not args.check_only:
            write_snapshot(content, args.output)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Snapshot refresh failed ({type(exc).__name__}); no successful refresh is claimed.", file=sys.stderr)
        return 2
    action = "validated" if args.check_only else f"wrote {args.output}"
    print(f"{action}: {row_count:,} rows; sha256={checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
